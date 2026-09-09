"""题目的 Pydantic 模型。"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

# 洛谷 8 级难度（含「暂无评定」）
DIFFICULTIES = [
    "暂无评定",
    "入门",
    "普及-",
    "普及",
    "普及/提高-",
    "普及+/提高",
    "提高+/省选-",
    "省选/NOI-",
    "NOI/NOI+/CTSC",
]
# re.escape：难度名里的 + / - 是正则元字符，不转义会导致这些难度永远校验失败
_DIFF = "|".join(re.escape(d) for d in DIFFICULTIES)


class ProblemSample(BaseModel):
    input: str = Field(default="", max_length=20_000, description="样例输入")
    output: str = Field(default="", max_length=20_000, description="样例输出")


class ProblemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="题目名称")
    difficulty: str = Field(
        default="暂无评定", pattern=f"^({_DIFF})$", description="难度"
    )
    source: str | None = Field(None, max_length=100, description="题目来源")
    tags: list[str] = Field(default_factory=list, max_length=10, description="算法标签")
    description: str = Field(default="", max_length=100_000, description="题目描述（Markdown）")
    background: str = Field(default="", max_length=100_000, description="题目背景（Markdown）")
    input_format: str = Field(default="", max_length=100_000, description="输入格式（Markdown）")
    output_format: str = Field(default="", max_length=100_000, description="输出格式（Markdown）")
    hint: str = Field(default="", max_length=100_000, description="提示说明（Markdown）")
    samples: list[ProblemSample] = Field(default_factory=list, max_length=20, description="样例组")
    time_limit: int = Field(default=1000, ge=100, le=60_000, description="时间限制 (ms)")
    memory_limit: int = Field(default=128, ge=16, le=1024, description="内存限制 (MB)")
    is_public: bool = Field(default=True, description="是否公开（草稿为 false）")

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v: list[str]) -> list[str]:
        """去空白、去引号（引号会破坏标签筛选的 LIKE 定界）、去重、限长。"""
        out: list[str] = []
        for t in v:
            t = t.strip().strip('"')[:20]
            if t and t not in out:
                out.append(t)
        return out


class ProblemUpdate(BaseModel):
    """全部 Optional；路由用 model_dump(exclude_unset=True) 做部分更新。"""

    title: str | None = Field(None, min_length=1, max_length=100, description="题目名称")
    difficulty: str | None = Field(None, pattern=f"^({_DIFF})$", description="难度")
    source: str | None = Field(None, max_length=100, description="题目来源")
    tags: list[str] | None = Field(None, max_length=10, description="算法标签")
    description: str | None = Field(None, max_length=100_000, description="题目描述（Markdown）")
    background: str | None = Field(None, max_length=100_000, description="题目背景（Markdown）")
    input_format: str | None = Field(None, max_length=100_000, description="输入格式（Markdown）")
    output_format: str | None = Field(None, max_length=100_000, description="输出格式（Markdown）")
    hint: str | None = Field(None, max_length=100_000, description="提示说明（Markdown）")
    samples: list[ProblemSample] | None = Field(None, max_length=20, description="样例组")
    time_limit: int | None = Field(None, ge=100, le=60_000, description="时间限制 (ms)")
    memory_limit: int | None = Field(None, ge=16, le=1024, description="内存限制 (MB)")
    is_public: bool | None = Field(None, description="是否公开（草稿为 false）")

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        out: list[str] = []
        for t in v:
            t = t.strip().strip('"')[:20]
            if t and t not in out:
                out.append(t)
        return out
