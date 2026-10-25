# 食刻搜 食谱搜索网站

## 项目介绍

本项目是食刻搜食谱搜索引擎网站，Python FastAPI 后端 + 静态 HTML/CSS/JS 前端。

> 当前状态：**菜谱 / 热搜 / 专题 / 厨具数据来自上级目录 `webdata/`**（CSV + 详情 JSON 分片），启动时由 `api/store.py` 加载。

命名释义：食刻搜 = 食谱 + 即刻，谐音「时刻搜」，想吃立刻搜到。

## 目录结构

```
网站开发/
├── webdata/                 # 真实数据包（CSV + detail 分片）
└── shikesou/
    ├── main.py              # FastAPI 入口
    ├── requirements.txt
    ├── readme.md
    ├── api/
    │   ├── store.py         # 加载 / 查询 webdata
    │   ├── search.py        # 搜索、热搜、详情、图片代理
    │   ├── ai_assistant.py  # 小灶灵（规则引擎）
    │   ├── calorie.py       # 热量计算
    │   ├── data_import.py   # 热更新 reload
    │   ├── category.py      # 特色专区
    │   └── kitchenware.py   # 灶边好物
    └── static/
        ├── index.html       # 搜索首页
        ├── detail.html      # 菜谱详情
        ├── topics.html      # 特色专区
        ├── zone.html        # 兼容跳转 → topics.html
        ├── kitchen.html     # 灶边好物
        ├── assistant.html   # 小灶灵
        ├── calorie.html     # 独立热量页
        ├── favicon.svg
        ├── css/style.css
        ├── js/              # nav / search / img / assistant / calorie
        └── img/             # 小灶灵形象（透明底 PNG）
```

## 启动运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 进入项目目录并启动（需保证同级存在 `../webdata`）：

```bash
cd shikesou
uvicorn main:app --reload
```

3. 浏览器访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 搜索 | 按菜名 / 分类 / 特色 / 口味 / 工艺子串匹配；首页含快捷标签与热搜榜 |
| 详情 | 封面、标签、食材、步骤（按换行拆分）、内嵌热量、推荐厨具 |
| 特色专区 | 养生 / 女性健康等分区菜谱列表（`topics.html`） |
| 灶边好物 | 厨具列表、关键词与品类筛选、外链商品 |
| 小灶灵 | 规则回复：食材推荐菜、份量估算、热量问答；非助手页右下角悬浮入口 |
| 热量 | 详情内嵌 + 独立页；内置常见食材热量表，未知食材标记为估算 |

## 数据说明

数据目录为 `网站开发/webdata/`，字段与用法见该目录下 `README.md`。

| 文件 | 用途 |
| --- | --- |
| `list.csv` | 搜索列表 |
| `hot_rank_top.csv` | 热搜榜 |
| `topics.csv` | 特色专区 |
| `kitchenware.csv` | 厨具推荐（详情页按工艺/分类匹配投放标签） |
| `detail/{0-9}.json` | 菜谱详情分片（食材 `|` 分隔，步骤换行分隔） |

热更新（不重启进程）：

```bash
curl -X POST http://127.0.0.1:8000/import/reload
```

## 接口文档

访问 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) 查看 Swagger。

| 接口路径 | 方法 | 说明 |
| --- | --- | --- |
| `/api/search` | GET | 多维度搜索（keyword） |
| `/api/hotrank` | GET | 热搜榜单 |
| `/api/recipe/{id}` | GET | 食谱详情（含 `推荐厨具`） |
| `/api/img` | GET | 外链图片代理（防盗链） |
| `/api/stats` | GET | 数据条数统计 |
| `/api/calorie/calc` | POST | 热量计算 |
| `/api/assistant/chat` | POST | 小灶灵对话 |
| `/api/category/list` | GET | 特色专区 |
| `/api/kitchenware/list` | GET | 厨具列表 |
| `/import/reload` | POST | 重新加载 webdata |
| `/import/status` | GET | 数据源状态 |

## 页面说明

| 页面 | 路径 | 功能 |
| --- | --- | --- |
| 首页 | `/static/index.html` | 搜索框、快捷标签、热搜榜 |
| 详情 | `/static/detail.html?id=…` | 食材、步骤、热量、推荐厨具 |
| 特色专区 | `/static/topics.html` | 养生 / 女性等专区（`/zone.html` 会跳转到此页） |
| 灶边好物 | `/static/kitchen.html` | 厨具列表与筛选 |
| 小灶灵 | `/static/assistant.html` | AI 厨房助手对话 |
| 热量计算 | `/static/calorie.html` | 独立热量估算页（亦可在详情内使用） |

## 已知限制与后续可选

当前版本面向课程演示，以下为可选增强（非阻塞）：

- [ ] 倒排索引与更好的搜索相关性排序
- [ ] 接入大模型，增强小灶灵问答
- [ ] 扩充热量表 / 对接外部营养数据
- [ ] 特色专区按「专题」层级展开（API 已有专题数据）
- [ ] 爬虫采集（本版本不做）
