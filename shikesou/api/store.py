"""
从 webdata 加载真实菜谱 / 热搜 / 专题 / 厨具数据。
CSV 为 UTF-8-BOM，解析时去掉 BOM。
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "webdata"
DETAIL_DIR = DATA_DIR / "detail"

_list: List[dict] = []
_list_by_id: Dict[str, dict] = {}
_hot: List[dict] = []
_topics: List[dict] = []
_kitchen: List[dict] = []
_shards: Dict[str, dict] = {}
_loaded = False

# 详情食材索引（懒加载，供小灶灵按食材检索）
_id_to_ing: Dict[str, str] = {}
_id_to_meta: Dict[str, dict] = {}
_ing_index_ready = False

# 解析「鸡蛋 3个」「西红柿2个」「盐 适量」
_ING_ITEM_RE = re.compile(
    r"^(.+?)\s*(\d+(?:\.\d+)?)\s*(g|克|G|个|只|条|根|片|瓣|勺|毫升|ml|ML)?$"
)
_ING_QTY_RE = re.compile(r"适量|少许|少量|若干|一点|一些")


def _read_csv(path: Path) -> List[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            item = {((k or "").lstrip("\ufeff").strip()): (v or "").strip() for k, v in row.items()}
            if any(item.values()):
                rows.append(item)
        return rows


def _rid_from_url(url: str) -> str:
    m = re.search(r"recipe-(\d+)\.html", url or "")
    return m.group(1) if m else ""


def _split_feat(feat: str) -> tuple:
    """特色「咸鲜 · 炒」→ (口味, 工艺)"""
    if not feat:
        return "", ""
    # 兼容全角/半角间隔号
    for sep in ("·", "･", "•", "|"):
        if sep in feat:
            parts = [p.strip() for p in feat.split(sep)]
            if len(parts) >= 2:
                return parts[0], parts[1]
            break
    return feat.strip(), ""


def _normalize_list_row(r: dict) -> dict:
    rid = r.get("菜谱ID", "")
    feat = r.get("特色", "")
    taste, craft = _split_feat(feat)
    heat = r.get("热量(大卡)", "")
    return {
        "id": rid,
        "菜名": r.get("菜名", ""),
        "分类": r.get("分类", ""),
        "特色": feat,
        "口味": taste,
        "工艺": craft,
        "耗时": r.get("耗时", ""),
        "热量": f"{heat}大卡" if heat and not str(heat).endswith("大卡") else heat,
        "热量值": heat,
        "图片": r.get("图片", ""),
        "链接": r.get("链接", ""),
    }


def _normalize_hot_row(r: dict, rank: int) -> dict:
    rid = _rid_from_url(r.get("详情链接", ""))
    feat = r.get("特色", "")
    taste, craft = _split_feat(feat)
    heat = r.get("热量(大卡)", "")
    fav = r.get("收藏数", "0")
    try:
        fav_n = int(float(fav))
    except ValueError:
        fav_n = 0
    return {
        "id": rid,
        "菜名": r.get("菜名", ""),
        "分类": r.get("分类", ""),
        "特色": feat,
        "口味": taste,
        "工艺": craft,
        "耗时": r.get("耗时", ""),
        "热量": f"{heat}大卡" if heat and not str(heat).endswith("大卡") else heat,
        "热量值": heat,
        "食材": r.get("食材", ""),
        "做法步骤": r.get("做法步骤", ""),
        "所属榜单": r.get("所属榜单", ""),
        "收藏数": fav_n,
        "图片": r.get("封面图", ""),
        "链接": r.get("详情链接", ""),
        "排名": rank,
    }


def _normalize_topic_row(r: dict) -> dict:
    heat = r.get("热量(大卡)", "")
    return {
        "专区": r.get("专区", ""),
        "专题": r.get("专题", ""),
        "id": r.get("菜谱ID", ""),
        "菜名": r.get("菜名", ""),
        "分类": r.get("分类", ""),
        "耗时": r.get("耗时", ""),
        "热量": f"{heat}大卡" if heat and not str(heat).endswith("大卡") else heat,
        "热量值": heat,
        "图片": r.get("封面", ""),
        "链接": r.get("链接", ""),
    }


def _normalize_kitchen_row(r: dict) -> dict:
    comments = r.get("评论数", "")
    try:
        comments_n = int(float(comments)) if comments else 0
    except ValueError:
        comments_n = 0
    score = r.get("评分", "")
    return {
        "id": r.get("厨具ID", ""),
        "名称": r.get("名称", ""),
        "品牌": r.get("品牌", ""),
        "品类": r.get("品类", ""),
        "价格": r.get("价格(元)", ""),
        "评分": score,
        "评论数": comments_n,
        "店铺": r.get("店铺", ""),
        "图片": r.get("封面图", ""),
        "链接": r.get("商品链接", ""),
        "投放标签": r.get("投放标签", ""),
    }


def load_data(force: bool = False) -> None:
    global _list, _list_by_id, _hot, _topics, _kitchen, _loaded
    global _shards, _id_to_ing, _id_to_meta, _ing_index_ready
    if _loaded and not force:
        return
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"找不到数据包目录: {DATA_DIR}")

    raw_list = _read_csv(DATA_DIR / "list.csv")
    _list = [_normalize_list_row(r) for r in raw_list]
    _list_by_id = {r["id"]: r for r in _list if r["id"]}

    raw_hot = _read_csv(DATA_DIR / "hot_rank_top.csv")
    _hot = [_normalize_hot_row(r, i + 1) for i, r in enumerate(raw_hot)]

    raw_topics = _read_csv(DATA_DIR / "topics.csv")
    _topics = [_normalize_topic_row(r) for r in raw_topics]

    raw_kw = _read_csv(DATA_DIR / "kitchenware.csv")
    _kitchen = [_normalize_kitchen_row(r) for r in raw_kw]

    if force:
        _shards = {}
        _id_to_ing = {}
        _id_to_meta = {}
        _ing_index_ready = False

    _loaded = True


def _load_all_shards() -> None:
    """预加载全部 detail 分片。"""
    for i in range(10):
        key = str(i)
        if key in _shards:
            continue
        path = DETAIL_DIR / f"{key}.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                _shards[key] = json.load(f)
        else:
            _shards[key] = {}


def ensure_ing_index() -> None:
    """从全部详情构建 id→食材 索引（首次调用时加载）。"""
    global _ing_index_ready, _id_to_ing, _id_to_meta
    ensure_loaded()
    if _ing_index_ready:
        return
    _load_all_shards()
    id_to_ing: Dict[str, str] = {}
    id_to_meta: Dict[str, dict] = {}
    for shard in _shards.values():
        for rid, raw in shard.items():
            if not isinstance(raw, dict):
                continue
            rid = str(raw.get("id") or rid)
            id_to_ing[rid] = raw.get("ing") or ""
            id_to_meta[rid] = {
                "id": rid,
                "菜名": raw.get("name") or "",
                "分类": raw.get("cat") or "",
                "特色": raw.get("feat") or "",
                "耗时": raw.get("time") or "",
                "热量值": str(raw.get("heat") or ""),
                "图片": raw.get("img") or "",
            }
    _id_to_ing = id_to_ing
    _id_to_meta = id_to_meta
    _ing_index_ready = True


def parse_ing_items(ing_str: str) -> List[dict]:
    """解析主辅料字符串为 [{name, amount, qty, unit}]。"""
    items = []
    if not ing_str:
        return items
    for part in re.split(r"[|｜]", ing_str):
        text = part.strip()
        if not text:
            continue
        m = _ING_ITEM_RE.match(text)
        if m:
            name, qty_s, unit = m.group(1).strip(), m.group(2), (m.group(3) or "").strip()
            try:
                qty = float(qty_s)
            except ValueError:
                qty = None
            items.append({
                "name": name,
                "amount": text[len(name):].strip() or qty_s + unit,
                "qty": qty,
                "unit": unit,
            })
            continue
        # 「鸡蛋适量」或纯名称
        name = _ING_QTY_RE.sub("", text).strip() or text
        amount = text[len(name):].strip() if name != text else ("适量" if _ING_QTY_RE.search(text) else "")
        items.append({"name": name, "amount": amount or text, "qty": None, "unit": ""})
    return items


def find_ing_item(ing_str: str, keyword: str) -> Optional[dict]:
    """在食材列表中找含 keyword 的一项。"""
    kw = keyword.strip()
    if not kw:
        return None
    for item in parse_ing_items(ing_str):
        if kw in item["name"] or item["name"] in kw:
            return item
    # 原文包含但解析失败时兜底
    if kw in (ing_str or ""):
        for part in re.split(r"[|｜]", ing_str or ""):
            if kw in part:
                return {"name": kw, "amount": part.strip(), "qty": None, "unit": ""}
    return None


def search_by_ingredient(ingredients: List[str], limit: int = 8) -> List[dict]:
    """
    按食材检索菜谱。多个食材时优先同时包含者。
    热搜收藏数用于排序加权。
    """
    ensure_ing_index()
    keys = [k.strip() for k in ingredients if k and k.strip()]
    if not keys:
        return []

    fav_map = {h["id"]: h.get("收藏数", 0) for h in _hot if h.get("id")}

    scored: List[tuple] = []
    for rid, ing in _id_to_ing.items():
        if not ing:
            continue
        hits = sum(1 for k in keys if k in ing)
        if hits == 0:
            continue
        meta = dict(_id_to_meta.get(rid) or {"id": rid})
        brief = _list_by_id.get(rid)
        if brief:
            meta.setdefault("菜名", brief.get("菜名", ""))
            meta.setdefault("分类", brief.get("分类", ""))
            meta.setdefault("特色", brief.get("特色", ""))
            meta.setdefault("耗时", brief.get("耗时", ""))
            meta.setdefault("热量值", brief.get("热量值", ""))
            meta["热量"] = brief.get("热量", "")
            meta["图片"] = brief.get("图片", "") or meta.get("图片", "")
        else:
            heat = meta.get("热量值", "")
            meta["热量"] = f"{heat}大卡" if heat and not str(heat).endswith("大卡") else heat
        name = meta.get("菜名", "")
        name_bonus = 20 if any(k in name for k in keys) else 0
        score = hits * 100 + name_bonus + min(int(fav_map.get(rid, 0) or 0) / 1000, 50)
        meta["主辅料"] = ing
        meta["_score"] = score
        scored.append((score, meta))

    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for _, item in scored[:limit]:
        item.pop("_score", None)
        out.append(item)
    return out


def search_by_name(keyword: str, limit: int = 5) -> List[dict]:
    """按菜名模糊匹配（精确命中优先）。"""
    ensure_loaded()
    kw = keyword.strip()
    if not kw:
        return []
    exact, partial = [], []
    for r in _list:
        name = r.get("菜名", "")
        if name == kw:
            exact.append(dict(r))
        elif kw in name:
            partial.append(dict(r))
    return (exact + partial)[:limit]


def ensure_loaded() -> None:
    load_data()


def get_list() -> List[dict]:
    ensure_loaded()
    return _list


def get_list_item(rid: str) -> Optional[dict]:
    ensure_loaded()
    return _list_by_id.get(str(rid))


def get_hot() -> List[dict]:
    ensure_loaded()
    return _hot


def get_topics() -> List[dict]:
    ensure_loaded()
    return _topics


def get_kitchen() -> List[dict]:
    ensure_loaded()
    return _kitchen


def get_detail(rid: str) -> Optional[dict]:
    """按菜谱 ID 末位数字加载 detail 分片。"""
    ensure_loaded()
    rid = str(rid)
    if not rid.isdigit():
        return None
    shard_key = rid[-1]
    if shard_key not in _shards:
        path = DETAIL_DIR / f"{shard_key}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            _shards[shard_key] = json.load(f)
    raw = _shards[shard_key].get(rid)
    if not raw:
        return None

    feat = raw.get("feat") or ""
    taste, craft = _split_feat(feat)
    heat = raw.get("heat") or ""
    brief = _list_by_id.get(rid) or {}
    img = (raw.get("img") or "").strip() or brief.get("图片", "")
    return {
        "id": raw.get("id") or rid,
        "菜名": raw.get("name") or brief.get("菜名", ""),
        "分类": raw.get("cat") or brief.get("分类", ""),
        "特色": feat or brief.get("特色", ""),
        "口味": taste or brief.get("口味", ""),
        "工艺": craft or brief.get("工艺", ""),
        "耗时": raw.get("time") or brief.get("耗时", ""),
        "热量": f"{heat}大卡" if heat and not str(heat).endswith("大卡") else (str(heat) or brief.get("热量", "")),
        "热量值": str(heat) or brief.get("热量值", ""),
        "主辅料": raw.get("ing") or "",
        "做法步骤": raw.get("steps") or "",
        "图片": img,
        "链接": raw.get("url") or brief.get("链接", ""),
        "小窍门": "",
    }


def match_kitchenware(category: str = "", craft: str = "") -> Optional[dict]:
    """按投放标签匹配厨具；找不到则回落到「通用」。"""
    ensure_loaded()
    keys = [k for k in (craft, category) if k]

    def hit(item: dict) -> bool:
        tags = item.get("投放标签") or ""
        return any(k and k in tags for k in keys)

    for item in _kitchen:
        if hit(item):
            return item
    for item in _kitchen:
        if "通用" in (item.get("投放标签") or ""):
            return item
    return _kitchen[0] if _kitchen else None


def stats() -> Dict[str, Any]:
    ensure_loaded()
    return {
        "菜谱": len(_list),
        "热搜": len(_hot),
        "专题行": len(_topics),
        "厨具": len(_kitchen),
        "data_dir": str(DATA_DIR),
    }
