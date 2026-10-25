"""
数据状态接口：真实数据来自 webdata，启动时由 store 加载。
保留 /import/reload 便于热更新 CSV。
"""
from fastapi import APIRouter

from api import store

router = APIRouter(prefix="/import", tags=["数据"])


@router.post("/reload")
def reload_data():
    """重新从 webdata 目录加载全部 CSV。"""
    store.load_data(force=True)
    return {
        "code": 0,
        "message": "已重新加载 webdata",
        "data": store.stats(),
    }


@router.get("/status")
def import_status():
    return {
        "code": 0,
        "message": "ok",
        "data": {
            **store.stats(),
            "source": "webdata CSV + detail JSON 分片",
        },
    }
