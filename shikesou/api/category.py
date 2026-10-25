"""
特色专区：基于 topics.csv（养生 / 女性）
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List

from fastapi import APIRouter, Query

from api import store

router = APIRouter(prefix="/api/category", tags=["特色专区"])

ZONE_META = {
    "养生": {
        "id": "yangsheng",
        "name": "养生专区",
        "desc": "清淡滋补、调理日常的专题合集",
        "color": "#7a9e6a",
    },
    "女性": {
        "id": "nvxing",
        "name": "女性健康",
        "desc": "关注气血与营养均衡的专题合集",
        "color": "#c45d7a",
    },
    "女性 / 养生": {
        "id": "both",
        "name": "女性 · 养生",
        "desc": "同时归属女性与养生的交叉专题",
        "color": "#b7791f",
    },
}


@router.get("/list")
def category_list(
    per_topic: int = Query(8, ge=1, le=40, description="每个专题展示菜谱数"),
    max_topics: int = Query(12, ge=1, le=50, description="每个专区最多专题数"),
):
    rows = store.get_topics()
    # 专区 -> 专题 -> 菜谱列表
    buckets: Dict[str, OrderedDict] = {}
    for r in rows:
        zone = r.get("专区") or "其他"
        topic = r.get("专题") or "未命名专题"
        buckets.setdefault(zone, OrderedDict())
        buckets[zone].setdefault(topic, [])
        buckets[zone][topic].append(r)

    result = []
    # 固定顺序：养生、女性、交叉
    order = ["养生", "女性", "女性 / 养生"]
    for zone_name in order:
        topics_map = buckets.get(zone_name)
        if not topics_map:
            continue
        meta = ZONE_META.get(zone_name, {
            "id": zone_name,
            "name": zone_name,
            "desc": "",
            "color": "#c8452d",
        })
        topics_out: List[dict] = []
        total_recipes = 0
        for i, (topic_name, recipes) in enumerate(topics_map.items()):
            if i >= max_topics:
                break
            shown = recipes[:per_topic]
            total_recipes += len(recipes)
            topics_out.append({
                "专题": topic_name,
                "count": len(recipes),
                "recipes": [
                    {
                        "id": x["id"],
                        "菜名": x["菜名"],
                        "分类": x.get("分类", ""),
                        "耗时": x.get("耗时", ""),
                        "热量": x.get("热量", ""),
                        "图片": x.get("图片", ""),
                    }
                    for x in shown
                ],
            })
        # count 用该专区全部行数
        all_count = sum(len(v) for v in topics_map.values())
        result.append({
            "id": meta["id"],
            "name": meta["name"],
            "desc": meta["desc"],
            "color": meta["color"],
            "专区": zone_name,
            "count": all_count,
            "topics": topics_out,
            # 兼容旧前端：扁平 recipes（取前若干）
            "recipes": [
                {
                    "id": x["id"],
                    "菜名": x["菜名"],
                    "耗时": x.get("耗时", ""),
                    "热量": x.get("热量", ""),
                    "图片": x.get("图片", ""),
                }
                for topic in topics_out
                for x in topic["recipes"]
            ][:24],
        })

    return {"code": 0, "message": "ok", "data": result}


@router.get("/topics")
def topic_recipes(
    zone: str = Query("", description="专区名，如 养生 / 女性"),
    topic: str = Query("", description="专题名"),
    limit: int = Query(60, ge=1, le=200),
):
    rows = store.get_topics()
    data = rows
    if zone:
        data = [r for r in data if zone in r.get("专区", "")]
    if topic:
        data = [r for r in data if topic in r.get("专题", "")]
    return {
        "code": 0,
        "message": "ok",
        "total": len(data),
        "data": data[:limit],
    }
