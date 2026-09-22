"""经验商店 API：用经验兑换 Tag 卡（递进解锁链）。

- 商品链定义在 SHOP_ITEMS（顺序即解锁顺序，兑换需持有前一件）
- 兑换 = 扣经验 + 直接加入用户 Tag 卡（自动佩戴）
- 每件商品每用户限兑一次（Tag 卡唯一约束兜底）
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.tag_card import UserTagCard
from app.models.user import User

router = APIRouter(prefix="/shop", tags=["shop"])

# 经验商店商品链：兑换第 N 件需持有第 N-1 件
SHOP_ITEMS: list[dict[str, Any]] = [
    {"id": 1, "name": "初出茅庐", "price": 50,
     "prev": None,
     "desc": "你开启了你的传奇 OJ 之路，期望你早日登上巅峰"},
    {"id": 2, "name": "崭露头角", "price": 150,
     "prev": "初出茅庐",
     "desc": "第一道绿题只是开始，前方的路还很长"},
    {"id": 3, "name": "渐入佳境", "price": 400,
     "prev": "崭露头角",
     "desc": "循环与递归已难不倒你，数据结构正在向你招手"},
    {"id": 4, "name": "驾轻就熟", "price": 900,
     "prev": "渐入佳境",
     "desc": "图论与动态规划在你眼中已不再是天书"},
    {"id": 5, "name": "融会贯通", "price": 1800,
     "prev": "驾轻就熟",
     "desc": "你开始享受推导复杂度时的酣畅淋漓"},
    {"id": 6, "name": "炉火纯青", "price": 3500,
     "prev": "融会贯通",
     "desc": "赛场上的你沉着冷静，罚时只是数字"},
    {"id": 7, "name": "登峰造极", "price": 7000,
     "prev": "炉火纯青",
     "desc": "省选难度的题目在你面前逐渐失去神秘"},
    {"id": 8, "name": "出神入化", "price": 12000,
     "prev": "登峰造极",
     "desc": "站在金字塔尖的你，已经是别人的「大佬」了"},
    {"id": 9, "name": "返璞归真", "price": 25000,
     "prev": "出神入化",
     "desc": "万千技巧烂熟于心，你最锋利的武器是最朴素的暴力"},
    {"id": 10, "name": "超凡入圣", "price": 60000,
     "prev": "返璞归真",
     "desc": "别人还在背模板，你已经开始给模板挑毛病了"},
    {"id": 11, "name": "一代宗师", "price": 150000,
     "prev": "超凡入圣",
     "desc": "你随手水掉的讨论帖，都值得别人逐字研读"},
    {"id": 12, "name": "天下无双", "price": 400000,
     "prev": "一代宗师",
     "desc": "排行榜第一名的位置，已经刻上了你的名字"},
    {"id": 13, "name": "前无古人", "price": 1000000,
     "prev": "天下无双",
     "desc": "百万经验的传奇——在你之后，再无来者"},
]


def _item_view(item: dict, owned: bool, prev_owned: bool, experience: int) -> dict:
    can_redeem = (not owned) and prev_owned and experience >= item["price"]
    locked_by = item["prev"] if not prev_owned else None
    return {
        **item,
        "owned": owned,
        "prev_owned": prev_owned,
        "can_redeem": can_redeem,
        "locked_by": locked_by,
        "enough_exp": experience >= item["price"],
    }


@router.get("/items", summary="经验商店商品与我的状态")
async def shop_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    cards = (await db.execute(
        select(UserTagCard).where(UserTagCard.user_id == current_user.id)
    )).scalars().all()
    owned_names = {c.name for c in cards}

    experience = current_user.experience or 0
    items = []
    prev_name = None
    for item in SHOP_ITEMS:
        owned = item["name"] in owned_names
        prev_owned = prev_name is None or prev_name in owned_names
        items.append(_item_view(item, owned, prev_owned, experience))
        prev_name = item["name"]
    return {"experience": experience, "items": items}


@router.post("/redeem", summary="兑换 Tag 卡")
async def redeem(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    item_id = payload.get("item_id")
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    cards = (await db.execute(
        select(UserTagCard).where(UserTagCard.user_id == current_user.id)
    )).scalars().all()
    owned_names = {c.name for c in cards}

    if item["name"] in owned_names:
        raise HTTPException(status_code=400, detail="你已经兑换过该 Tag")

    idx = SHOP_ITEMS.index(item)
    if idx > 0:
        prev_name = SHOP_ITEMS[idx - 1]["name"]
        if prev_name not in owned_names:
            raise HTTPException(
                status_code=400, detail=f"需要先兑换前置 Tag「{prev_name}」"
            )

    experience = current_user.experience or 0
    if experience < item["price"]:
        raise HTTPException(
            status_code=400,
            detail=f"经验不足：还需要 {item['price'] - experience} 经验",
        )

    current_user.experience = experience - item["price"]
    # 兑换即自动佩戴（摘下其他卡）
    for c in cards:
        c.enabled = False
    card = UserTagCard(user_id=current_user.id, name=item["name"], enabled=True)
    db.add(card)
    await db.commit()
    return {
        "success": True,
        "name": item["name"],
        "experience": current_user.experience,
    }


# ================================================================
# 贡献商店：用出题攒下的贡献值兑换 Tag 卡（链式解锁，同经验商店）
# ================================================================
CONTRIBUTION_SHOP_ITEMS: list[dict[str, Any]] = [
    {"id": 101, "name": "初执笔墨", "price": 100,
     "prev": None,
     "desc": "你写下了第一道题，题库因你而更完整"},
    {"id": 102, "name": "命题新秀", "price": 400,
     "prev": "初执笔墨",
     "desc": "题面、数据、标算样样俱全，你的题让人欲罢不能"},
    {"id": 103, "name": "题库基石", "price": 1000,
     "prev": "命题新秀",
     "desc": "你出的题撑起了题库的一片天"},
    {"id": 104, "name": "命题专家", "price": 2500,
     "prev": "题库基石",
     "desc": "原创题、巧妙转化、一题多解，你的题被反复研讨"},
    {"id": 105, "name": "金牌出题人", "price": 6000,
     "prev": "命题专家",
     "desc": "你的题是检验实力的标尺，AC 与否全看临场发挥"},
    {"id": 106, "name": "传奇命题人", "price": 15000,
     "prev": "金牌出题人",
     "desc": "题库因你而有了灵魂，你的名字就是质量的保证"},
]


def _chain_view(
    items: list[dict[str, Any]],
    owned_names: set[str],
    balance: int,
) -> list[dict[str, Any]]:
    """按解锁链生成商品视图（经验/贡献商店共用）。"""
    views = []
    prev_name = None
    for item in items:
        owned = item["name"] in owned_names
        prev_owned = prev_name is None or prev_name in owned_names
        views.append(_item_view(item, owned, prev_owned, balance))
        prev_name = item["name"]
    return views


@router.get("/contribution/items", summary="贡献商店商品与我的状态")
async def contribution_shop_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    cards = (await db.execute(
        select(UserTagCard).where(UserTagCard.user_id == current_user.id)
    )).scalars().all()
    owned_names = {c.name for c in cards}
    contribution = current_user.contribution or 0
    return {
        "contribution": contribution,
        "items": _chain_view(CONTRIBUTION_SHOP_ITEMS, owned_names, contribution),
    }


@router.post("/contribution/redeem", summary="贡献商店兑换 Tag 卡")
async def contribution_redeem(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    item_id = payload.get("item_id")
    item = next(
        (i for i in CONTRIBUTION_SHOP_ITEMS if i["id"] == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    cards = (await db.execute(
        select(UserTagCard).where(UserTagCard.user_id == current_user.id)
    )).scalars().all()
    owned_names = {c.name for c in cards}

    if item["name"] in owned_names:
        raise HTTPException(status_code=400, detail="你已经兑换过该 Tag")

    idx = CONTRIBUTION_SHOP_ITEMS.index(item)
    if idx > 0:
        prev_name = CONTRIBUTION_SHOP_ITEMS[idx - 1]["name"]
        if prev_name not in owned_names:
            raise HTTPException(
                status_code=400, detail=f"需要先兑换前置 Tag「{prev_name}」"
            )

    contribution = current_user.contribution or 0
    if contribution < item["price"]:
        raise HTTPException(
            status_code=400,
            detail=f"贡献不足：还需要 {item['price'] - contribution} 贡献",
        )

    current_user.contribution = contribution - item["price"]
    # 兑换即自动佩戴（摘下其他卡）
    for c in cards:
        c.enabled = False
    card = UserTagCard(user_id=current_user.id, name=item["name"], enabled=True)
    db.add(card)
    await db.commit()
    return {
        "success": True,
        "name": item["name"],
        "contribution": current_user.contribution,
    }
