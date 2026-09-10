"""打卡 API：状态查询与打卡动作。

数据存服务端（users 表），跨设备 / 重装 / 清缓存均一致；
日期按东八区计算，与前端展示（Asia/Shanghai）一致。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/checkin", tags=["checkin"])

# 打卡日界：东八区零点
_TZ_CN = timezone(timedelta(hours=8))


def _today() -> date:
    return datetime.now(_TZ_CN).date()


def _status(user: User) -> dict:
    return {
        "today_checked": user.last_checkin_date == _today(),
        "streak": user.checkin_streak or 0,
        "total": user.checkin_total or 0,
    }


@router.get("", summary="打卡状态")
async def checkin_status(
    current_user: User = Depends(get_current_user),
) -> dict:
    return _status(current_user)


@router.post("", summary="打卡（当日幂等）")
async def checkin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    today = _today()
    if current_user.last_checkin_date == today:
        return _status(current_user)

    yesterday = today - timedelta(days=1)
    if current_user.last_checkin_date == yesterday:
        current_user.checkin_streak = (current_user.checkin_streak or 0) + 1
    else:
        # 断签后重新连击
        current_user.checkin_streak = 1
    current_user.checkin_total = (current_user.checkin_total or 0) + 1
    current_user.last_checkin_date = today
    await db.commit()
    return _status(current_user)
