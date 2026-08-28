"""管理后台API"""

from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_

from app.core.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.judgement import JudgementLog
from app.schemas.user import UserAdminUpdate, UserAdminResponse

router = APIRouter(prefix="/admin", tags=["admin"])

# ================================================================
# 权限变更分类（与参考项目 analyzePermissionChanges 逻辑一致）
# ================================================================
NORMAL_PERMS = ["can_speak"]
ADMIN_PERMS = ["is_super_admin", "is_admin", "can_manage_users", "can_manage_posts"]


def analyze_permission_changes(changes: dict) -> dict:
    """把权限变更分类为普通/管理的授予与撤销."""
    normal_grants: list = []
    normal_revokes: list = []
    admin_grants: list = []
    admin_revokes: list = []

    for field, value in changes.items():
        change_info = {"permission": field, "new_value": value}

        if field == "is_banned":
            # is_banned 逻辑是反的：false = 授予进入主站
            if value is False:
                normal_grants.append(change_info)
            else:
                normal_revokes.append(change_info)
        elif field in NORMAL_PERMS:
            if value is True:
                normal_grants.append(change_info)
            else:
                normal_revokes.append(change_info)
        elif field in ADMIN_PERMS:
            if value is True:
                admin_grants.append(change_info)
            else:
                admin_revokes.append(change_info)

    return {
        "normal_grants": normal_grants,
        "normal_revokes": normal_revokes,
        "admin_grants": admin_grants,
        "admin_revokes": admin_revokes,
    }


def determine_action_type(changes: dict) -> tuple[str, dict]:
    """根据变更内容确定日志 action_type 与 action_detail.

    返回 (action_type, action_detail)；普通与管理权限混合时抛出 ValueError。
    """
    only_cheater_change = len(changes) == 1 and "is_cheater" in changes
    only_banned_change = len(changes) == 1 and "is_banned" in changes

    analyzed = analyze_permission_changes(changes)
    has_normal = bool(analyzed["normal_grants"] or analyzed["normal_revokes"])
    has_admin = bool(analyzed["admin_grants"] or analyzed["admin_revokes"])

    if has_normal and has_admin:
        raise ValueError("不能同时修改普通权限和管理权限，请分别操作")

    if only_cheater_change:
        action_type = "brown_penalty" if changes["is_cheater"] else "unbrown"
        detail = {
            "changes": [{"permission": "is_cheater", "new_value": changes["is_cheater"]}],
            "category": "cheater",
        }
    elif only_banned_change:
        if changes["is_banned"] is False:
            action_type, detail = "unban", {
                "changes": [{"permission": "is_banned", "new_value": False}],
                "category": "normal",
            }
        else:
            action_type, detail = "ban", {
                "changes": [{"permission": "is_banned", "new_value": True}],
                "category": "normal",
            }
    elif has_normal:
        if analyzed["normal_grants"] and not analyzed["normal_revokes"]:
            action_type, detail = "grant_normal", {
                "changes": analyzed["normal_grants"], "category": "normal"}
        elif analyzed["normal_revokes"] and not analyzed["normal_grants"]:
            action_type, detail = "revoke_normal", {
                "changes": analyzed["normal_revokes"], "category": "normal"}
        else:
            action_type, detail = "ostracism", {
                "changes": analyzed["normal_grants"] + analyzed["normal_revokes"],
                "category": "normal",
            }
    elif has_admin:
        action_type, detail = "admin_rotation", {
            "changes": analyzed["admin_grants"] + analyzed["admin_revokes"],
            "category": "admin",
        }
    else:
        # 没有可记录的权限变更（例如只改了备注等字段），不写日志
        action_type, detail = "", {}

    return action_type, detail


async def insert_judgement_log(
    db: AsyncSession,
    admin_id: int,
    target_user_id: int,
    action_type: str,
    action_detail: dict,
    reason: Optional[str],
) -> None:
    """写入一条陶片放逐日志（reason 为空时不记录，与参考项目一致）."""
    if not reason or not str(reason).strip():
        return
    db.add(JudgementLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action_type=action_type,
        action_detail=action_detail,
        reason=str(reason).strip(),
    ))


@router.get("/users", response_model=List[UserAdminResponse])
async def get_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[UserAdminResponse]:
    """获取用户列表（需要管理员权限）"""

    # 权限检查：只有管理员或超级管理员可以访问
    if not (current_user.is_admin or current_user.is_super_admin or current_user.can_manage_users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    query = select(User)

    # 搜索功能
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.user_number == int(search) if search.isdigit() else False
            )
        )

    query = query.order_by(User.user_number).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return [UserAdminResponse.model_validate(user) for user in users]


@router.put("/users/{user_number}", response_model=UserAdminResponse)
async def update_user(
    user_number: int,
    user_update: UserAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserAdminResponse:
    """更新用户信息（需要管理员权限）"""

    # 权限检查
    if not (current_user.is_admin or current_user.is_super_admin or current_user.can_manage_users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    # 查询目标用户
    result = await db.execute(select(User).where(User.user_number == user_number))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 超级管理是固定身份：拒绝任何针对 is_super_admin 的修改
    if user_update.is_super_admin is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="超级管理员权限不可修改"
        )

    # 更新用户信息
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserAdminResponse.model_validate(user)


@router.post("/users/{user_number}/permissions")
async def update_user_permissions(
    user_number: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新用户权限（需要管理员权限）。

    请求体两种格式：
      - {changes: {field: value, ...}, reason: "原因"}   （推荐，会记录陶片放逐日志）
      - {field: value, ...}                               （兼容旧格式，不记录日志）
    """
    # 兼容两种请求格式
    if "changes" in payload and isinstance(payload["changes"], dict):
        changes = payload["changes"]
        reason = payload.get("reason")
    else:
        changes = {k: v for k, v in payload.items() if k != "reason"}
        reason = None

    # 超级管理是固定身份：拒绝任何针对 is_super_admin 的修改
    if "is_super_admin" in changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="超级管理员权限不可修改"
        )

    # 权限检查
    if not (current_user.is_admin or current_user.is_super_admin or current_user.can_manage_users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )

    # 查询目标用户
    result = await db.execute(select(User).where(User.user_number == user_number))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 不能修改自己的权限
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的权限"
        )

    # 分类校验（普通权限与管理权限不能同时修改）
    try:
        action_type, action_detail = determine_action_type(changes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 授予用户管理/秩序管理权限时，自动授予进入后台权限（与参考项目一致）
    apply_changes = dict(changes)
    if (apply_changes.get("can_manage_users") is True or apply_changes.get("can_manage_posts") is True) \
            and not user.is_admin:
        apply_changes["is_admin"] = True

    # 更新权限
    allowed_permissions = [
        'is_admin', 'is_super_admin', 'can_manage_users',
        'can_manage_posts', 'can_speak', 'is_banned', 'is_cheater'
    ]

    for perm, value in apply_changes.items():
        if perm in allowed_permissions and hasattr(user, perm):
            setattr(user, perm, value)

    if action_type:
        await insert_judgement_log(
            db, current_user.id, user.id, action_type, action_detail, reason
        )

    await db.commit()

    return {"message": "权限更新成功"}