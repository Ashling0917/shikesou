"""
食刻搜｜专业食谱搜索引擎
FastAPI 主程序入口

运行：uvicorn main:app --reload
访问：http://127.0.0.1:8000
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, Response

from api import search, ai_assistant, calorie, data_import, category, kitchenware
from api import store

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="食刻搜",
    description="专业食谱搜索引擎 — 数据来自 webdata（菜谱 / 热搜 / 专题 / 厨具）",
    version="1.1.0",
)


@app.on_event("startup")
def _startup_load():
    store.load_data()


app.include_router(search.router)
app.include_router(ai_assistant.router)
app.include_router(calorie.router)
app.include_router(data_import.router)
app.include_router(category.router)
app.include_router(kitchenware.router)

@app.middleware("http")
async def _no_cache_html(request, call_next):
    """开发期禁用 HTML 强缓存，避免旧导航结构残留。"""
    response = await call_next(request)
    path = request.url.path or ""
    if path.endswith(".html") or path in ("/", "/index.html", "/zone.html", "/topics.html", "/kitchen.html", "/assistant.html", "/detail.html", "/calorie.html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/favicon.ico")
def favicon():
    svg = STATIC_DIR / "favicon.svg"
    if svg.exists():
        return FileResponse(svg, media_type="image/svg+xml")
    return Response(status_code=204)


@app.get("/index.html")
def page_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/detail.html")
def page_detail():
    return FileResponse(STATIC_DIR / "detail.html")


@app.get("/assistant.html")
def page_assistant():
    return FileResponse(STATIC_DIR / "assistant.html")


@app.get("/calorie.html")
def page_calorie():
    return FileResponse(STATIC_DIR / "calorie.html")


@app.get("/zone.html")
def page_zone():
    return RedirectResponse(url="/static/topics.html")


@app.get("/topics.html")
def page_topics():
    return FileResponse(STATIC_DIR / "topics.html")


@app.get("/kitchen.html")
def page_kitchen():
    return FileResponse(STATIC_DIR / "kitchen.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
