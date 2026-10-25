"""
热量计算接口
参考成人每日推荐约 2000 大卡，计算单样与合计占比
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List

router = APIRouter(prefix="/api/calorie", tags=["热量计算"])

# 常见食材每 100g 热量（大卡）—— 模拟数据，仅供演示参考
# TODO: 后续可从营养数据库 / CSV 导入更完整数据
CALORIE_DB = {
    "鸡蛋": 144,
    "西红柿": 19,
    "番茄": 19,
    "五花肉": 395,
    "猪肉": 242,
    "牛肉": 125,
    "牛腩": 190,
    "鸡胸肉": 133,
    "鸡翅": 194,
    "豆腐": 81,
    "嫩豆腐": 61,
    "土豆": 81,
    "西兰花": 34,
    "排骨": 278,
    "鲈鱼": 105,
    "米饭": 116,
    "面条": 137,
    "食用油": 899,
    "橄榄油": 899,
    "白砂糖": 400,
    "冰糖": 397,
    "花生米": 563,
    "洋葱": 39,
    "大蒜": 126,
    "大白菜": 17,
    "黄瓜": 16,
    "胡萝卜": 41,
    "虾仁": 87,
    "牛奶": 54,
    "面粉": 364,
}

DAILY_CALORIES = 2000  # 成人每日参考摄入


class IngredientItem(BaseModel):
    name: str = Field(..., description="食材名称")
    grams: float = Field(..., gt=0, description="重量（克）")


class CalorieRequest(BaseModel):
    items: List[IngredientItem]


def lookup_per_100g(name: str) -> float:
    """按名称查找每100g热量；未知食材用默认估算值"""
    name = name.strip()
    if name in CALORIE_DB:
        return CALORIE_DB[name]
    # 模糊包含匹配
    for k, v in CALORIE_DB.items():
        if k in name or name in k:
            return v
    # 未知食材默认估算（演示用）
    return 100.0


@router.post("/calc")
def calc_calories(req: CalorieRequest):
    """
    热量计算：接收多条食材名称+克重，
    返回每样热量、总热量、占每日2000大卡百分比。
    """
    details = []
    total = 0.0

    for item in req.items:
        per_100 = lookup_per_100g(item.name)
        cal = round(per_100 * item.grams / 100.0, 1)
        total += cal
        known = item.name.strip() in CALORIE_DB or any(
            k in item.name or item.name in k for k in CALORIE_DB
        )
        details.append({
            "name": item.name,
            "grams": item.grams,
            "per_100g": per_100,
            "calories": cal,
            "known": known,
        })

    total = round(total, 1)
    percent = round(total / DAILY_CALORIES * 100, 1)

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "items": details,
            "total_calories": total,
            "daily_reference": DAILY_CALORIES,
            "percent_of_daily": percent,
            "note": "计算值仅供参考，实际热量因食材品种与烹饪方式而异。",
        },
    }
