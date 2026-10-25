"""
搜索、热搜榜单、菜谱详情 —— 基于 webdata 真实数据
"""
from __future__ import annotations

import urllib.error
import urllib.request
from typing import List
from urllib.parse import urlparse

from fastapi import APIRouter, Query
from fastapi.responses import Response

from api import store

router = APIRouter(prefix="/api", tags=["搜索"])

# 外链封面防盗链：经本站代理后浏览器可正常显示
_IMG_HOST_SUFFIXES = (
    "meishitx.com",
    "meishichina.com",
    "ddimg.cn",
    "dangdang.com",
)


def calc_relevance_score(recipe: dict, keyword: str) -> float:
    score = 0.0
    name = recipe.get("菜名", "")
    cat = recipe.get("分类", "")
    feat = recipe.get("特色", "")
    kw = keyword.strip()
    if not kw:
        return 0.0
    if name == kw:
        score += 100
    elif kw in name:
        score += 60
    if kw in cat:
        score += 25
    if kw in feat:
        score += 15
    return score


def simple_search(keyword: str, limit: int = 120) -> List[dict]:
    recipes = store.get_list()
    kw = keyword.strip()
    if not kw:
        return [dict(r) for r in recipes[:limit]]

    results = []
    for r in recipes:
        if (
            kw in r.get("菜名", "")
            or kw in r.get("分类", "")
            or kw in r.get("特色", "")
            or kw in r.get("口味", "")
            or kw in r.get("工艺", "")
        ):
            item = dict(r)
            item["_score"] = calc_relevance_score(r, kw)
            results.append(item)

    results.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return results[:limit]


@router.get("/stats")
def data_stats():
    return {"code": 0, "message": "ok", "data": store.stats()}


@router.get("/search")
def search_recipes(
    keyword: str = Query("", description="搜索关键词，支持菜名、分类、特色"),
    limit: int = Query(120, ge=1, le=300),
):
    results = simple_search(keyword, limit=limit)
    for item in results:
        item.pop("_score", None)
    return {
        "code": 0,
        "message": "ok",
        "keyword": keyword,
        "total": len(results),
        "data": results,
    }


@router.get("/hotrank")
def hot_rank(limit: int = Query(48, ge=1, le=200)):
    ranked = store.get_hot()[:limit]
    return {"code": 0, "message": "ok", "data": ranked}


def _host_allowed(host: str) -> bool:
    host = (host or "").lower()
    return any(host == s or host.endswith("." + s) for s in _IMG_HOST_SUFFIXES)


@router.get("/img")
def proxy_image(url: str = Query(..., description="原始图片 URL")):
    """代理菜谱/厨具外链图片，避免防盗链导致空白。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not _host_allowed(parsed.hostname or ""):
        return Response(status_code=400, content=b"bad url")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://home.meishichina.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = resp.read()
            ctype = resp.headers.get("Content-Type") or "image/jpeg"
            return Response(
                content=data,
                media_type=ctype.split(";")[0].strip(),
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return Response(status_code=502, content=b"fetch failed")


@router.get("/recipe/{recipe_id}")
def recipe_detail(recipe_id: str):
    recipe = store.get_detail(str(recipe_id))
    if not recipe:
        # 热搜行有时自带食材/步骤，作兜底
        for h in store.get_hot():
            if h.get("id") == str(recipe_id):
                recipe = {
                    "id": h["id"],
                    "菜名": h["菜名"],
                    "分类": h.get("分类", ""),
                    "特色": h.get("特色", ""),
                    "口味": h.get("口味", ""),
                    "工艺": h.get("工艺", ""),
                    "耗时": h.get("耗时", ""),
                    "热量": h.get("热量", ""),
                    "热量值": h.get("热量值", ""),
                    "主辅料": h.get("食材", ""),
                    "做法步骤": h.get("做法步骤", ""),
                    "图片": h.get("图片", ""),
                    "链接": h.get("链接", ""),
                    "小窍门": "",
                }
                break
    if not recipe:
        brief = store.get_list_item(str(recipe_id))
        if brief:
            recipe = {
                **brief,
                "主辅料": "",
                "做法步骤": "",
                "小窍门": "",
            }
    if not recipe:
        return {"code": 404, "message": "食谱不存在", "data": None}

    # 补全缺失封面
    if not (recipe.get("图片") or "").strip():
        brief = store.get_list_item(str(recipe_id))
        if brief and brief.get("图片"):
            recipe = dict(recipe)
            recipe["图片"] = brief["图片"]

    ad = store.match_kitchenware(
        category=recipe.get("分类", ""),
        craft=recipe.get("工艺", ""),
    )
    data = dict(recipe)
    data["推荐厨具"] = ad
    return {"code": 0, "message": "ok", "data": data}
