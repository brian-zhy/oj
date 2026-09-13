"""评测服务：调用 go-judge 完成编译与逐测试点评测。

流程：提交创建后由 BackgroundTasks 触发 judge_submission()：
1. 状态置为 judging
2. 需要编译的语言先编译（copyOutCached 缓存二进制，复用于各测试点）
3. 逐测试点运行：stdin=测试点输入，stdout 与期望输出比对（忽略行尾空白与结尾换行）
4. 汇总状态 / 最大耗时 / 最大内存，回写提交行并更新题目统计
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.problem import Problem
from app.models.submission import Submission, TestCase
from app.models.user import User

logger = logging.getLogger(__name__)

# 语言 → 编译/运行命令（依赖宿主机安装 g++ / gcc / python3）
LANGUAGES: dict[str, dict[str, Any]] = {
    "cpp": {
        "source": "main.cpp",
        "compile": ["g++", "-O2", "-std=c++14", "-fplugin=/usr/local/lib/oj/no_opt_pragma.so", "main.cpp", "-o", "main", "-lm"],
        "run": ["./main"],
        "binary": "main",
    },
    "c": {
        "source": "main.c",
        "compile": ["gcc", "-O2", "-fplugin=/usr/local/lib/oj/no_opt_pragma.so", "main.c", "-o", "main", "-lm"],
        "run": ["./main"],
        "binary": "main",
    },
    "python3": {
        "source": "main.py",
        "compile": None,
        "run": ["python3", "main.py"],
        "binary": None,
    },
}

# go-judge 状态 → 本站状态
SANDBOX_STATUS_MAP = {
    "Time Limit Exceeded": "time_limit_exceeded",
    "Memory Limit Exceeded": "memory_limit_exceeded",
    "Output Limit Exceeded": "runtime_error",
    "Runtime Error": "runtime_error",
    "Nonzero Exit Status": "runtime_error",
    "File Error": "runtime_error",
    "Internal Error": "system_error",
}

# go-judge 默认环境没有 PATH，g++ 会找不到 as/ld 链接器 → 必须显式提供
SANDBOX_ENV = ["PATH=/usr/bin:/bin"]

# 汇总优先级：劣化方向（取整个提交的最差结果）
_SEVERITY = ["accepted", "wrong_answer", "runtime_error", "memory_limit_exceeded", "time_limit_exceeded"]

# 首次 AC 经验表（按难度等级递增，每题每用户仅一次）
XP_BY_DIFFICULTY = {
    "入门": 1,
    "普及-": 5,
    "普及": 10,
    "普及+/提高": 100,
    "提高": 200,
    "提高+/省选-": 500,
    "省选/NOI-": 900,
    "NOI/NOI+/CTSC": 1500,
    "暂无评定": 0,
}

async def adjust_experience_on_difficulty_change(
    db: AsyncSession, problem_id: int, old_difficulty: str, new_difficulty: str
) -> int:
    """题目难度变更时，重算所有首次 AC 该题用户的经验（返回受影响人数）。

    「每题每用户仅一次」——每个 AC 过该题的用户恰好拿过一次该难度的经验，
    故对差值 delta = XP(新) - XP(旧) 整体增减即可；难度多次改动的差值
    会自然抵消（A→B→A 净变化为 0）。
    """
    delta = (XP_BY_DIFFICULTY.get(new_difficulty, 0)
             - XP_BY_DIFFICULTY.get(old_difficulty, 0))
    if delta == 0:
        return 0
    ac_user_ids = (await db.execute(
        select(Submission.user_id).where(
            Submission.problem_id == problem_id,
            Submission.status == "accepted",
        ).distinct()
    )).scalars().all()
    if not ac_user_ids:
        return 0
    await db.execute(
        update(User)
        .where(User.id.in_(ac_user_ids))
        .values(experience=User.experience + delta)
    )
    await db.commit()
    logger.info("P%s 难度 %s → %s，%d 名 AC 用户经验 %+d",
                1000 + problem_id, old_difficulty, new_difficulty,
                len(ac_user_ids), delta)
    return len(ac_user_ids)


# 沙箱资源参数
COMPILE_CPU_NS = 30_000_000_000      # 编译 30s
COMPILE_MEMORY = 1_073_741_824       # 1GB
RUN_PROC_LIMIT = 64
STDOUT_MAX = 16 * 1024 * 1024        # 单点输出上限 16MB
STDERR_MAX = 1024 * 1024


def normalize_output(s: str) -> str:
    """比对前归一化：去掉每行行尾空白与结尾空行。"""
    lines = [line.rstrip() for line in s.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _worse(cur: str, new: str) -> str:
    """返回两者中更劣的状态。"""
    a = _SEVERITY.index(cur) if cur in _SEVERITY else len(_SEVERITY)
    b = _SEVERITY.index(new) if new in _SEVERITY else len(_SEVERITY)
    return new if b >= a else cur


class JudgeError(Exception):
    """评测致命错误（连接沙箱失败等）。"""


async def _run_cmd(client: httpx.AsyncClient, cmd: dict[str, Any]) -> dict[str, Any]:
    try:
        resp = await client.post(f"{settings.GO_JUDGE_URL}/run", json={"cmd": [cmd]})
        resp.raise_for_status()
        results = resp.json()
    except httpx.HTTPError as e:
        raise JudgeError(f"无法连接评测沙箱: {e}") from e
    if not results:
        raise JudgeError("评测沙箱返回为空")
    return results[0]


async def _delete_file(client: httpx.AsyncClient, file_id: str) -> None:
    try:
        await client.delete(f"{settings.GO_JUDGE_URL}/file/{file_id}")
    except httpx.HTTPError:
        logger.warning("清理沙箱缓存文件失败: %s", file_id)


def _basic_files(input_data: str) -> list[dict[str, Any]]:
    """stdin = 测试点输入；stdout/stderr 用管道收集。"""
    return [
        {"content": input_data},
        {"name": "stdout", "max": STDOUT_MAX},
        {"name": "stderr", "max": STDERR_MAX},
    ]


async def judge_submission(submission_id: int) -> None:
    """后台评测入口（自带数据库会话，由 BackgroundTasks 调用）。"""
    async with AsyncSessionLocal() as db:
        try:
            await _judge(db, submission_id)
        except Exception:
            logger.exception("评测提交 %s 失败", submission_id)
            # 兜底：标记系统错误，避免永远停在 judging
            sub = (await db.execute(
                select(Submission).where(Submission.id == submission_id)
            )).scalar_one_or_none()
            if sub is not None and sub.status in ("pending", "judging"):
                sub.status = "system_error"
                sub.error_message = "评测系统内部错误，请稍后重试"
                await db.commit()


async def _judge(db: AsyncSession, submission_id: int) -> None:
    sub = (await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )).scalar_one_or_none()
    if sub is None or sub.status not in ("pending", "judging"):
        return
    problem = (await db.execute(
        select(Problem).where(Problem.id == sub.problem_id)
    )).scalar_one_or_none()
    cases = (await db.execute(
        select(TestCase).where(TestCase.problem_id == sub.problem_id)
        .order_by(TestCase.sort_order.asc(), TestCase.id.asc())
    )).scalars().all()

    if problem is None or not cases:
        sub.status = "system_error"
        sub.error_message = "该题目暂无测试数据"
        await db.commit()
        return

    lang = LANGUAGES.get(sub.language)
    if lang is None:
        sub.status = "system_error"
        sub.error_message = f"不支持的语言: {sub.language}"
        await db.commit()
        return

    sub.status = "judging"
    await db.commit()

    cpu_ns = problem.time_limit * 1_000_000          # ms → ns
    mem_bytes = problem.memory_limit * 1024 * 1024   # MB → bytes

    results: list[dict[str, Any]] = []
    overall: str = "accepted"
    time_used = 0
    memory_used = 0
    error_message: Optional[str] = None
    binary_file_id: Optional[str] = None

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60)) as client:
            # ---- 编译 ----
            if lang["compile"]:
                res = await _run_cmd(client, {
                    "args": lang["compile"],
                    "env": SANDBOX_ENV,
                    "files": [{"content": ""}, {"name": "stdout", "max": STDERR_MAX},
                              {"name": "stderr", "max": STDERR_MAX}],
                    "copyIn": {lang["source"]: {"content": sub.code}},
                    "copyOutCached": [lang["binary"]],
                    "cpuLimit": COMPILE_CPU_NS,
                    "memoryLimit": COMPILE_MEMORY,
                    "procLimit": RUN_PROC_LIMIT,
                })
                if res.get("status") != "Accepted":
                    sub.status = "compile_error"
                    stderr = (res.get("files") or {}).get("stderr") or ""
                    if res.get("status") == "File Error" and not stderr.strip():
                        # 沙箱里找不到编译器可执行文件 → 宿主机没装 g++/gcc
                        sub.error_message = (
                            "编译器不可用：评测沙箱中找不到 g++/gcc，"
                            "请联系管理员在宿主机安装编译器"
                        )
                    else:
                        sub.error_message = (stderr
                                             or (res.get("files") or {}).get("stdout")
                                             or "编译失败")[:20_000]
                    sub.judged_at = datetime.now(timezone.utc)
                    await db.commit()
                    return
                binary_file_id = (res.get("fileIds") or {}).get(lang["binary"])

            # ---- 逐测试点运行 ----
            for i, tc in enumerate(cases, start=1):
                copy_in: dict[str, Any] = (
                    {lang["binary"]: {"fileId": binary_file_id}}
                    if lang["binary"] else {lang["source"]: {"content": sub.code}}
                )
                res = await _run_cmd(client, {
                    "args": lang["run"],
                    "env": SANDBOX_ENV,
                    "files": _basic_files(tc.input_data),
                    "copyIn": copy_in,
                    "cpuLimit": cpu_ns,
                    "memoryLimit": mem_bytes,
                    "procLimit": RUN_PROC_LIMIT,
                })

                sb_status = res.get("status", "")
                case_status = SANDBOX_STATUS_MAP.get(sb_status, "accepted")
                if case_status == "accepted":
                    stdout = (res.get("files") or {}).get("stdout") or ""
                    if normalize_output(stdout) != normalize_output(tc.expected_output):
                        case_status = "wrong_answer"

                case_time_ms = int(res.get("time", 0) / 1_000_000)
                case_mem_kb = int(res.get("memory", 0) / 1024)
                results.append({
                    "case": i,
                    "status": case_status,
                    "time": case_time_ms,
                    "memory": case_mem_kb,
                })
                overall = _worse(overall, case_status)
                time_used = max(time_used, case_time_ms)
                memory_used = max(memory_used, case_mem_kb)

                if case_status == "runtime_error" and error_message is None:
                    err = (res.get("files") or {}).get("stderr") or ""
                    if err.strip():
                        error_message = err[:2000]

                if overall == "time_limit_exceeded":
                    break  # 超时后不再跑剩余点
    except JudgeError as e:
        sub.status = "system_error"
        sub.error_message = str(e)[:2000]
        sub.test_results = results or None
        await db.commit()
        return
    finally:
        if binary_file_id:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
                await _delete_file(client, binary_file_id)

    sub.status = overall
    sub.score = 100 if overall == "accepted" else 0
    sub.time_used = time_used or None
    sub.memory_used = memory_used or None
    sub.error_message = error_message
    sub.test_results = results
    sub.judged_at = datetime.now(timezone.utc)

    # 统计回写：提交数 +1；首次 AC（该用户该题此前无 AC）则通过数 +1 并加经验
    problem.submit_count = (problem.submit_count or 0) + 1
    if overall == "accepted":
        prior_ac = (await db.execute(
            select(Submission.id).where(
                Submission.problem_id == sub.problem_id,
                Submission.user_id == sub.user_id,
                Submission.status == "accepted",
                Submission.id != sub.id,
            ).limit(1)
        )).scalar_one_or_none()
        if prior_ac is None:
            problem.solved_count = (problem.solved_count or 0) + 1
            # 首次 AC 发经验（每题每用户永远只加一次）
            xp = XP_BY_DIFFICULTY.get(problem.difficulty, 0)
            if xp > 0:
                ac_user = await db.get(User, sub.user_id)
                if ac_user is not None:
                    ac_user.experience = (ac_user.experience or 0) + xp
                    logger.info("用户 %s 首次 AC P%s(%s) +%d 经验",
                                ac_user.username, 1000 + sub.problem_id,
                                problem.difficulty, xp)

    await db.commit()
