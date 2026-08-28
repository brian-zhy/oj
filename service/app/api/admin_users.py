"""管理员API - 支持原管理后台的所有功能"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.judgement import JudgementLog

router = APIRouter(prefix="/admin", tags=["admin"])


async def check_admin_permission(current_user: User) -> User:
    """检查管理员权限"""
    if not (current_user.is_super_admin or current_user.is_admin or current_user.can_manage_users):
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )
    return current_user


def format_user_for_original(user: User) -> Dict[str, Any]:
    """格式化用户数据为原系统期望的格式"""
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "user_number": user.user_number,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_banned": user.is_banned,
        "is_cheater": user.is_cheater,
        "is_super_admin": user.is_super_admin,
        "is_admin": user.is_admin,
        "can_speak": user.can_speak,
        "can_manage_users": user.can_manage_users,
        "can_manage_posts": user.can_manage_posts,
        "can_assign_admin": getattr(user, 'can_assign_admin', False),
        "avatar_url": user.avatar_url,
        "user_tag": user.user_tag,
        "username_color": user.username_color,
        "bio": user.bio,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_online": getattr(user, 'last_online', None)
    }


@router.get("/users")
async def get_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表 - 支持搜索和分页"""
    await check_admin_permission(current_user)

    # 构建查询
    query = select(User)

    if search:
        # 支持按用户名、邮箱、用户编号搜索
        try:
            user_number = int(search)
            query = query.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                    User.user_number == user_number
                )
            )
        except ValueError:
            # 如果不是数字，只搜索用户名和邮箱
            query = query.where(
                or_(
                    User.username.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # 执行分页查询
    query = query.order_by(User.user_number)
    result = await db.execute(query.limit(limit).offset(offset))
    users = result.scalars().all()

    return {
        "data": [format_user_for_original(user) for user in users],
        "total": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/users/{user_number}")
async def get_user_by_number(
    user_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """根据用户编号获取用户信息"""
    await check_admin_permission(current_user)

    result = await db.execute(
        select(User).where(User.user_number == user_number)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return format_user_for_original(user)


@router.put("/users/{user_number}")
async def update_user(
    user_number: int,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户信息"""
    await check_admin_permission(current_user)

    result = await db.execute(
        select(User).where(User.user_number == user_number)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 权限检查：超级管理员可以修改所有用户
    # 其他管理员不能修改超级管理员
    if not current_user.is_super_admin and user.is_super_admin:
        raise HTTPException(status_code=403, detail="不能修改超级管理员")

    # 超级管理是固定身份：拒绝任何针对 is_super_admin 的修改
    if 'is_super_admin' in updates:
        raise HTTPException(status_code=400, detail="超级管理员权限不可修改")

    # 更新允许的字段
    updatable_fields = [
        'username', 'email', 'bio', 'avatar_url', 'user_tag', 'username_color',
        'is_active', 'is_banned', 'is_cheater',
        'is_admin', 'can_speak', 'can_manage_users', 'can_manage_posts'
    ]

    for field, value in updates.items():
        if field in updatable_fields and hasattr(user, field):
            setattr(user, field, value)

    try:
        await db.commit()
        await db.refresh(user)
        return {
            "success": True,
            "data": format_user_for_original(user)
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/users/{user_number}/permissions")
async def update_user_permissions(
    user_number: int,
    permission_updates: Dict[str, bool],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户权限"""
    await check_admin_permission(current_user)

    result = await db.execute(
        select(User).where(User.user_number == user_number)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 权限检查
    if not current_user.is_super_admin and user.is_super_admin:
        raise HTTPException(status_code=403, detail="不能修改超级管理员权限")

    # 只有超级管理员可以授予超级管理员权限
    if not current_user.is_super_admin and permission_updates.get('is_super_admin'):
        raise HTTPException(status_code=403, detail="只有超级管理员可以授予超级管理员权限")

    # 更新权限字段
    permission_fields = [
        'is_super_admin', 'is_admin', 'can_speak',
        'can_manage_users', 'can_manage_posts'
    ]

    for field, value in permission_updates.items():
        if field in permission_fields and hasattr(user, field):
            setattr(user, field, value)

    try:
        await db.commit()
        await db.refresh(user)
        return {
            "success": True,
            "data": format_user_for_original(user)
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"权限更新失败: {str(e)}")


@router.get("/users/online")
async def get_online_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取在线用户列表"""
    await check_admin_permission(current_user)

    # 获取最近活跃的用户（假设30分钟内有活动即为在线）
    from datetime import datetime, timedelta
    from sqlalchemy import text

    time_threshold = datetime.now() - timedelta(minutes=30)

    # 由于SQLite没有足够的在线状态跟踪，这里返回所有活跃用户
    # 生产环境应该有专门的在线状态跟踪机制
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.is_banned == False
        ).limit(100)
    )
    users = result.scalars().all()

    return {
        "online_users": [format_user_for_original(user) for user in users],
        "online_count": len(users)
    }


@router.post("/users/batch")
async def batch_update_users(
    user_numbers: List[int],
    updates: Dict[str, Any],
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量更新用户（reason 非空时写入陶片放逐日志）"""
    await check_admin_permission(current_user)

    # 超级管理是固定身份：拒绝任何针对 is_super_admin 的修改
    if 'is_super_admin' in updates:
        raise HTTPException(status_code=400, detail="超级管理员权限不可修改")

    # 查询用户
    result = await db.execute(
        select(User).where(User.user_number.in_(user_numbers))
    )
    users = result.scalars().all()

    if not users:
        raise HTTPException(status_code=404, detail="没有找到匹配的用户")

    # 批量操作日志分类（与参考项目 batchAction 逻辑一致）
    field = list(updates.keys())[0] if updates else ''
    new_value = updates.get(field)
    normal_perms = ['can_speak']
    admin_perms = ['is_super_admin', 'is_admin', 'can_manage_users', 'can_manage_posts']

    if field == 'is_banned':
        action_type = 'unban' if new_value is False else 'ban'
        action_detail: Dict[str, Any] = {
            "changes": [{"permission": field, "new_value": new_value}],
            "category": "normal",
        }
    elif field in normal_perms:
        action_type = 'grant_normal' if new_value else 'revoke_normal'
        action_detail = {
            "changes": [{"permission": field, "new_value": new_value}],
            "category": "normal",
        }
    elif field in admin_perms:
        action_type = 'admin_rotation'
        action_detail = {
            "changes": [{"permission": field, "new_value": new_value}],
            "category": "admin",
        }
    else:
        action_type = 'grant_perm' if new_value else 'revoke_perm'
        action_detail = {"permission": field, "new_value": new_value}

    updated_users = []
    for user in users:
        # 不能修改超级管理员（除非自己也是超级管理员）
        if not current_user.is_super_admin and user.is_super_admin:
            continue

        # 不能批量修改自己的权限
        if user.id == current_user.id:
            continue

        # 更新字段
        for field_name, value in updates.items():
            if hasattr(user, field_name):
                setattr(user, field_name, value)

        updated_users.append(user)

        # 每个目标用户写一条日志（reason 为空时跳过）
        if reason and str(reason).strip():
            db.add(JudgementLog(
                admin_id=current_user.id,
                target_user_id=user.id,
                action_type=action_type,
                action_detail=action_detail,
                reason=str(reason).strip(),
            ))

    try:
        await db.commit()
        return {
            "success": True,
            "updated_count": len(updated_users),
            "data": [format_user_for_original(user) for user in updated_users]
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取管理后台统计数据"""
    await check_admin_permission(current_user)

    # 用户统计
    total_users_result = await db.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar() or 0

    active_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )
    active_users = active_users_result.scalar() or 0

    banned_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.is_banned == True)
    )
    banned_users = banned_users_result.scalar() or 0

    admin_users_result = await db.execute(
        select(func.count()).select_from(User).where(
            or_(User.is_super_admin == True, User.is_admin == True)
        )
    )
    admin_users = admin_users_result.scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "banned_users": banned_users,
        "admin_users": admin_users,
        "online_users": active_users  # 简化处理
    }