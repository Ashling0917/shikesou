"""
灶边好物（厨具）接口
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from api import store

router = APIRouter(prefix="/api/kitchenware", tags=["灶边好物"])


@router.get("/list")
def kitchen_list(
    q: str = Query("", description="搜名称 / 品类 / 店铺"),
    category: str = Query("", description="品类筛选"),
    limit: int = Query(120, ge=1, le=300),
):
    items = store.get_kitchen()
    if category:
        items = [x for x in items if x.get("品类") == category]
    kw = q.strip()
    if kw:
        items = [
            x for x in items
            if kw in x.get("名称", "")
            or kw in x.get("品类", "")
            or kw in x.get("店铺", "")
            or kw in x.get("品牌", "")
        ]
    cats = sorted({x.get("品类") for x in store.get_kitchen() if x.get("品类")})
    return {
        "code": 0,
        "message": "ok",
        "total": len(items),
        "categories": cats,
        "data": items[:limit],
    }


@router.get("/match")
def kitchen_match(
    category: str = Query("", description="菜谱分类"),
    craft: str = Query("", description="工艺，如 炒/炖"),
):
    ad = store.match_kitchenware(category=category, craft=craft)
    return {"code": 0, "message": "ok", "data": ad}
