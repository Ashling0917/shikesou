"""
AI助手「小灶灵」
基于 webdata 检索 + 规则模板回答（不调用大模型）。

能力：
1. 食材推荐：「有鸡蛋可以做什么？」
2. 份量估算：「西红柿炒鸡蛋两个人要几个鸡蛋」（数据无几人份，按默认假设估算）
3. 热量查询：「西红柿炒鸡蛋的热量」（直接回菜谱标注热量，改克重去详情页）
4. 烹饪常识兜底：料酒替代、嫩滑技巧、减脂建议等
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter
from pydantic import BaseModel

from api import store

router = APIRouter(prefix="/api/assistant", tags=["小灶灵"])

# 本站菜谱默认按约 2～3 人份理解（数据无官方几人份字段）
DEFAULT_SERVINGS_LOW = 2
DEFAULT_SERVINGS_HIGH = 3
DEFAULT_SERVINGS_MID = 2.5

# 人均经验用量（无原谱数字时使用）
PER_PERSON = {
    "鸡蛋": (1.0, 1.5, "个"),
    "番茄": (0.5, 1.0, "个"),
    "西红柿": (0.5, 1.0, "个"),
    "土豆": (0.5, 1.0, "个"),
    "豆腐": (100, 150, "g"),
    "猪肉": (100, 150, "g"),
    "牛肉": (100, 150, "g"),
    "鸡胸肉": (100, 150, "g"),
    "五花肉": (100, 150, "g"),
    "米饭": (100, 150, "g"),
}

COMMON_INGS = [
    "西红柿", "番茄", "鸡蛋", "土豆", "豆腐", "嫩豆腐",
    "五花肉", "猪肉", "牛肉", "牛腩", "鸡胸肉", "鸡翅", "排骨",
    "鲈鱼", "虾仁", "西兰花", "白菜", "大白菜", "黄瓜", "胡萝卜",
    "洋葱", "大蒜", "粉丝", "面条", "面粉", "米饭", "花生米",
]

CN_NUM = {
    "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


TIP_REPLIES = [
    {
        "keywords": ["料酒", "代替", "替代"],
        "answer": (
            "没有料酒可以用以下方式代替哦～\n"
            "① 黄酒：最接近，按 1:1 替换；\n"
            "② 干白葡萄酒：去腥提香也不错；\n"
            "③ 米醋+清水：少量米醋兑水，适合快炒去腥；\n"
            "④ 如果不喝酒，也可以用姜片、葱段、胡椒粉加强去腥。\n"
            "小灶灵提醒：料酒主要作用是去腥增香，根据菜品灵活调整即可。"
        ),
    },
    {
        "keywords": ["嫩", "滑", "腌制", "技巧"],
        "answer": (
            "想让肉更嫩滑，试试这些小技巧：\n"
            "1. 淀粉+蛋清+少许油抓匀，静置 15 分钟；\n"
            "2. 鸡胸肉可先用刀背拍松再切；\n"
            "3. 滑炒时油温不要太高，快速翻炒断生即可；\n"
            "4. 牛肉可加少许小苏打腌制（冲洗干净再用）。"
        ),
    },
    {
        "keywords": ["减脂", "低卡", "减肥", "少油"],
        "answer": (
            "减脂期做菜建议：\n"
            "· 多用蒸、煮、焯、烤，少油炸；\n"
            "· 用空气炸锅或少油煎代替重油；\n"
            "· 多用菌菇、叶菜增加饱腹感；\n"
            "· 可用黑胡椒、辣椒、柠檬汁提味，少放糖和淀粉勾芡。\n"
            "想查某道菜的热量，直接问我「西红柿炒鸡蛋的热量」；\n"
            "要按克重细算，打开对应菜谱详情页里的「热量计算」即可～"
        ),
    },
]

HELP_ANSWER = (
    "你好，我是小灶灵～可以基于食刻搜菜谱库帮你：\n"
    "· 食材能做什么：例如「有鸡蛋可以做什么？」\n"
    "· 几个人放多少：例如「西红柿炒鸡蛋两个人要几个鸡蛋」\n"
    "  （本站数据无官方几人份，份量按默认约 2～3 人份假设估算）\n"
    "· 查菜热量：例如「西红柿炒鸡蛋的热量」\n"
    "  （想改克重细算，点进详情页的「热量计算」）\n"
    "· 烹饪小常识：料酒替代、嫩滑技巧、减脂建议等\n"
    "换个更具体的问题试试吧～"
)


def _parse_people(q: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*个人?", q)
    if m:
        return int(m.group(1))
    m = re.search(r"([一二两三四五六七八九十])\s*个人?", q)
    if m:
        return CN_NUM.get(m.group(1))
    m = re.search(r"([一二两三四五六七八九十\d]+)\s*人(?:吃|份|用餐)?", q)
    if m:
        raw = m.group(1)
        if raw.isdigit():
            return int(raw)
        if len(raw) == 1 and raw in CN_NUM:
            return CN_NUM[raw]
    return None


def _extract_ingredients(q: str) -> List[str]:
    found = []
    for name in sorted(COMMON_INGS, key=len, reverse=True):
        if name in q and name not in found:
            found.append(name)
    # 「有XXX可以做」兜底抽取
    m = re.search(r"有([^\s，,？?。！!]+?)(?:可以|能|做)", q)
    if m:
        chunk = m.group(1)
        for part in re.split(r"[和与、,/]", chunk):
            part = part.strip()
            if part and part not in found and len(part) <= 8:
                # 去掉「冰箱里」等
                part = re.sub(r"^(冰箱里的?|家里的?|剩下的?)", "", part)
                if part:
                    found.append(part)
    return found


def _is_ingredient_intent(q: str) -> bool:
    patterns = [
        r"可以做(什么|啥|点什么)",
        r"能做(什么|啥)",
        r"做什么(菜|好)",
        r"有.+做",
        r"用.+做(什么|啥|菜)",
        r"冰箱",
        r"推荐.+菜",
    ]
    if any(re.search(p, q) for p in patterns):
        return True
    # 「鸡蛋能做什么」类
    if re.search(r".{1,8}(能|可以)做", q) and _extract_ingredients(q):
        return True
    return False


def _is_calorie_intent(q: str) -> bool:
    """问某道菜热量 / 多少卡。"""
    if not re.search(r"(热量|卡路里|kcal|大卡|多少卡|几大卡|几卡)", q, re.I):
        return False
    # 纯减脂常识（无菜名倾向）交给 tip
    if re.search(r"(减脂|减肥|低卡饮食|怎么减脂)", q) and not re.search(
        r"(炒|烧|蒸|煮|炖|煎|炸|烤|拌|汤|面|饭|蛋|肉|豆腐)", q
    ):
        return False
    return True


def _guess_dish_for_calorie(q: str) -> str:
    s = q
    s = re.sub(r"(的)?\s*(热量|卡路里|kcal)\s*(是多少|多少|有多少)?", " ", s, flags=re.I)
    s = re.sub(r"(有)?(多少|几)\s*(大)?卡(路里)?", " ", s)
    s = re.sub(r"(大概|大约|一共|总共|一盘|一份)", " ", s)
    s = re.sub(r"(怎么算|如何算|怎么查|查询)", " ", s)
    s = re.sub(r"[？?。！!，,、\s]+", " ", s).strip()
    s = re.sub(r"^(请问|问一下|帮我查|查一下|我想知道)", "", s).strip()
    if len(s) >= 2:
        return s
    # 「XX炒YY」兜底
    m = re.search(
        r"([\u4e00-\u9fff]{2,12}(?:炒|烧|蒸|煮|炖|煎|炸|烤|拌)[\u4e00-\u9fff]{1,8})",
        q,
    )
    return m.group(1) if m else ""


def _is_portion_intent(q: str) -> bool:
    people = _parse_people(q)
    amount_ask = bool(
        re.search(r"(多少|几个|几只|几克|放多少|用多少|配比|需要加|要加|该放)", q)
    )
    if people and amount_ask:
        return True
    if people and _extract_ingredients(q):
        return True
    # 「西红柿炒鸡蛋两个人吃」
    if people and re.search(r"(炒|烧|蒸|煮|炖|煎|炸|烤|拌).{0,6}(人|吃)", q):
        return True
    if people and re.search(r".{2,12}(人|吃).{0,8}(鸡蛋|西红柿|番茄|肉)", q):
        return True
    return False


def _guess_dish_name(q: str) -> str:
    """从问句中尽量抽出菜名。"""
    # 去掉人数与用量问法
    s = q
    s = re.sub(r"[一二两三四五六七八九十\d]+\s*个人?(?:吃|份|用餐)?", " ", s)
    s = re.sub(r"(需要|应该|大概|大约)?(加|放|用)?(多少|几个|几只|几克).*$", " ", s)
    s = re.sub(r"(怎么做|如何做|的做法|食谱|菜谱)", " ", s)
    s = re.sub(r"[？?。！!，,、\s]+", " ", s).strip()
    # 常见「菜名+食材」：西红柿炒鸡蛋几个鸡蛋 → 先搜整句缩短
    for ing in sorted(COMMON_INGS, key=len, reverse=True):
        # 若问的是某食材用量，菜名里通常也含该食材，不要删光
        pass
    # 尝试：去掉末尾单独食材词「…几个鸡蛋」已在上面处理
    s = re.sub(r"(要|加|放).*$", "", s).strip()
    if len(s) >= 2:
        return s
    return ""


def _target_ingredient(q: str, dish_name: str) -> str:
    ings = _extract_ingredients(q)
    if not ings:
        return "鸡蛋" if "蛋" in q else ""
    # 优先问句末尾关心的食材；若菜名已含全部，取最长的常见词
    for name in ings:
        if name not in dish_name or len(ings) == 1:
            return name
    return ings[0]


def _fmt_qty(qty: float, unit: str) -> str:
    if abs(qty - round(qty)) < 0.05:
        n = str(int(round(qty)))
    else:
        n = f"{qty:.1f}".rstrip("0").rstrip(".")
    return f"{n}{unit}" if unit else n


def _scale_amount(item: dict, people: int) -> Tuple[str, str]:
    """
    返回 (原谱描述, 建议描述)。
    有数字则按 DEFAULT_SERVINGS_MID 缩放；否则用人均经验。
    """
    name = item.get("name") or ""
    amount = item.get("amount") or "适量"
    qty = item.get("qty")
    unit = item.get("unit") or ""

    original = f"{name} {amount}".strip()

    if qty is not None and qty > 0:
        # 按默认中位人数缩放
        scaled = qty * (people / DEFAULT_SERVINGS_MID)
        # 个数类取整到 0.5
        if unit in ("个", "只", "条", "根", "片", "瓣", "勺") or not unit:
            if unit in ("个", "只", "条", "根", "片", "瓣") or unit == "":
                lo = max(1, int(scaled)) if scaled >= 1 else round(scaled * 2) / 2
                hi = max(lo, int(round(scaled + 0.49)))
                if unit == "" and "蛋" in name:
                    unit = "个"
                if hi > lo:
                    suggest = f"{_fmt_qty(lo, unit)}～{_fmt_qty(hi, unit)}"
                else:
                    suggest = _fmt_qty(lo, unit)
            else:
                suggest = _fmt_qty(round(scaled, 1), unit)
        else:
            suggest = _fmt_qty(round(scaled, 1), unit)
        note = (
            f"原谱写「{amount}」（按本站默认约 {DEFAULT_SERVINGS_LOW}～"
            f"{DEFAULT_SERVINGS_HIGH} 人份理解）。"
            f"{people} 个人建议约 {suggest}。"
        )
        return original, note

    # 无数字：人均经验
    for key, (lo, hi, u) in PER_PERSON.items():
        if key in name or name in key:
            a = lo * people
            b = hi * people
            if u in ("个", "只"):
                suggest = f"{_fmt_qty(a, u)}～{_fmt_qty(b, u)}"
            else:
                suggest = f"{_fmt_qty(a, u)}～{_fmt_qty(b, u)}"
            note = (
                f"原谱写「{amount}」，未标明具体数量。"
                f"按人均经验，{people} 个人建议 {name} 约 {suggest}。"
            )
            return original, note

    note = (
        f"原谱写「{amount}」，本站无几人份数据，也无该食材的人均参考。"
        f"建议先按原谱适量放，再按口味微调。"
    )
    return original, note


def _recipe_line(r: dict, idx: int) -> str:
    rid = r.get("id", "")
    name = r.get("菜名", "")
    meta = " · ".join(
        x for x in [r.get("耗时") or "", r.get("热量") or "", r.get("分类") or ""] if x
    )
    link = f"/static/detail.html?id={rid}" if rid else ""
    line = f"{idx}. {name}"
    if meta:
        line += f"（{meta}）"
    if link:
        line += f"\n   详情：{link}"
    return line


def answer_ingredient(q: str) -> Tuple[str, List[dict]]:
    ings = _extract_ingredients(q)
    if not ings:
        return (
            "想根据食材推荐菜品的话，告诉我家里有什么吧～\n"
            "例如：「有鸡蛋可以做什么？」「有豆腐和西红柿能做什么菜？」",
            [],
        )

    recipes = store.search_by_ingredient(ings, limit=8)
    if not recipes:
        return (
            f"暂时没在菜谱库里找到同时用到「{'、'.join(ings)}」的菜，"
            f"换个食材词试试（如鸡蛋、土豆、豆腐）～",
            [],
        )

    title = f"家里有「{'、'.join(ings)}」的话，食刻搜里可以试试这些："
    lines = [_recipe_line(r, i + 1) for i, r in enumerate(recipes)]
    tip = "\n点开详情可看完整食材和步骤。还想按口味/耗时筛的话，也可以去首页搜索～"
    return title + "\n" + "\n".join(lines) + tip, recipes


def answer_portion(q: str) -> Tuple[str, List[dict]]:
    people = _parse_people(q) or 2
    dish = _guess_dish_name(q)
    # 若猜菜名失败，尝试用「XX炒YY」等残留
    if len(dish) < 2:
        m = re.search(
            r"([\u4e00-\u9fff]{2,12}(?:炒|烧|蒸|煮|炖|煎|炸|烤|拌)[\u4e00-\u9fff]{1,8})",
            q,
        )
        if m:
            dish = m.group(1)

    target = _target_ingredient(q, dish)

    # 未指定菜名：只用人均经验，不瞎匹配一道同名菜
    if len(dish) < 2:
        if target and target in PER_PERSON:
            lo, hi, u = PER_PERSON[target]
            suggest = f"{_fmt_qty(lo * people, u)}～{_fmt_qty(hi * people, u)}"
            text = (
                f"你没有指定具体菜名。按人均经验，{people} 个人做菜时"
                f"「{target}」大约 {suggest}。\n"
                f"说明：本站菜谱数据没有官方「几人份」字段，此为经验估算。\n"
                f"也可以问：「西红柿炒鸡蛋{people}个人要几个鸡蛋」"
            )
            return text, []
        return (
            "可以说得更具体一点，例如：\n"
            "「西红柿炒鸡蛋两个人要几个鸡蛋」\n"
            "我会去菜谱库里查原谱用量，再按人数给出估算～",
            [],
        )

    recipes = store.search_by_name(dish, limit=5)
    if not recipes:
        return (
            f"菜谱库里暂时没找到「{dish}」。\n"
            f"可以换个菜名，或先问「有{target or '鸡蛋'}可以做什么？」",
            [],
        )

    best = recipes[0]
    detail = store.get_detail(str(best["id"])) or best
    ing_str = detail.get("主辅料") or detail.get("食材") or ""
    if not target:
        target = "鸡蛋"

    item = store.find_ing_item(ing_str, target)
    disclaimer = (
        f"\n说明：数据里没有「几人份」字段，以上按默认约 "
        f"{DEFAULT_SERVINGS_LOW}～{DEFAULT_SERVINGS_HIGH} 人份假设估算，仅供参考。"
    )

    head = f"关于「{best.get('菜名', dish)}」（{people} 个人）：\n"

    if not item:
        text = (
            head
            + f"这道菜的食材列表里没有明确写到「{target}」。\n"
            + f"主辅料原文：{ing_str[:120]}{'…' if len(ing_str) > 120 else ''}\n"
            + f"详情：/static/detail.html?id={best.get('id', '')}"
            + disclaimer
        )
        return text, [best]

    _original, note = _scale_amount(item, people)
    text = (
        head
        + note
        + f"\n详情：/static/detail.html?id={best.get('id', '')}"
        + disclaimer
    )
    return text, [best]


def answer_calorie(q: str) -> Tuple[str, List[dict]]:
    dish = _guess_dish_for_calorie(q)
    if len(dish) < 2:
        return (
            "想查哪道菜的热量？可以说「西红柿炒鸡蛋的热量」。\n"
            "我会直接告诉你菜谱标注的大卡数；想改克重细算，再点进详情页的「热量计算」～",
            [],
        )

    recipes = store.search_by_name(dish, limit=5)
    if not recipes:
        return (
            f"菜谱库里暂时没找到「{dish}」，换个菜名再问问热量吧～",
            [],
        )

    # 优先选有热量标注的
    best = None
    for r in recipes:
        heat = (r.get("热量") or r.get("热量值") or "").strip()
        if heat:
            best = r
            break
    if best is None:
        best = recipes[0]

    detail = store.get_detail(str(best["id"])) or best
    name = best.get("菜名") or dish
    heat = (
        (detail.get("热量") or "").strip()
        or (best.get("热量") or "").strip()
        or (
            f"{detail.get('热量值')}大卡"
            if detail.get("热量值")
            else ""
        )
        or (
            f"{best.get('热量值')}大卡"
            if best.get("热量值")
            else ""
        )
    )
    rid = best.get("id", "")
    link = f"/static/detail.html?id={rid}" if rid else ""

    if heat:
        text = (
            f"「{name}」这份菜谱标注热量约 {heat}。\n"
            f"这是原谱估算值；若要按自己的食材克重重算，"
            f"请打开详情页下方的「热量计算」改克重即可。\n"
            f"详情：{link}"
        )
    else:
        text = (
            f"找到了「{name}」，但这份数据里没有写明热量。\n"
            f"你可以打开详情页，在「热量计算」里按食材克重自行估算～\n"
            f"详情：{link}"
        )

    # 若有多份同名/相近菜，顺带提一句
    others = [r for r in recipes[1:4] if r.get("id") != rid]
    if others:
        text += "\n同名相近菜谱也可点下面芯片查看："

    return text, [best] + others


def answer_tip(q: str) -> Optional[str]:
    best = None
    best_hits = 0
    for item in TIP_REPLIES:
        hits = sum(1 for kw in item["keywords"] if kw in q)
        if hits > best_hits:
            best_hits = hits
            best = item
    if best and best_hits > 0:
        return best["answer"]
    return None


def chat_answer(question: str) -> Dict[str, Any]:
    q = question.strip()
    if not q:
        return {"answer": "请先输入你的问题哦～", "mode": "help", "recipes": []}

    # 热量查询优先于笼统减脂 tip，避免「XX的热量」被当成减肥建议
    if _is_calorie_intent(q):
        answer, recipes = answer_calorie(q)
        return {"answer": answer, "mode": "calorie", "recipes": recipes}

    if _is_ingredient_intent(q):
        answer, recipes = answer_ingredient(q)
        return {"answer": answer, "mode": "ingredient", "recipes": recipes}

    if _is_portion_intent(q):
        answer, recipes = answer_portion(q)
        return {"answer": answer, "mode": "portion", "recipes": recipes}

    tip = answer_tip(q)
    if tip:
        return {"answer": tip, "mode": "tip", "recipes": []}

    # 若提到食材但句式不像推荐，仍尝试食材检索
    ings = _extract_ingredients(q)
    if ings and re.search(r"(什么|啥|推荐|菜)", q):
        answer, recipes = answer_ingredient(q)
        return {"answer": answer, "mode": "ingredient", "recipes": recipes}

    return {"answer": HELP_ANSWER, "mode": "help", "recipes": []}


@router.post("/chat")
def chat(req: ChatRequest):
    """小灶灵对话：检索 webdata + 规则模板。"""
    result = chat_answer(req.question)
    # 精简返回给前端的菜谱字段
    slim = [
        {
            "id": r.get("id"),
            "菜名": r.get("菜名"),
            "耗时": r.get("耗时"),
            "热量": r.get("热量"),
            "分类": r.get("分类"),
        }
        for r in (result.get("recipes") or [])
    ]
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "question": req.question,
            "answer": result["answer"],
            "session_id": req.session_id,
            "mode": result["mode"],
            "recipes": slim,
        },
    }
