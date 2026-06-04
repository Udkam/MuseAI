# MuseAI 后端

MuseAI 后端是面向西安半坡博物馆微信小程序的 FastAPI 服务，负责导览会话、SSE 流式 AI 回答、展厅与展品数据、AI 策展路线、游览报告、RAG 检索、LLM 调用追踪和可选 TTS 能力。

English version: [README_EN.md](./README_EN.md)

## 当前阶段

当前处于 Stage 10D 后的持续优化阶段。后端已经完成四身份导览、动态路线、展厅/展品模式、报告生成、Reflection Engine 最小闭环，并开始支持 DeepSeek 与 Qwen 的 OpenAI-compatible 切换。

当前服务器规格已升级为 2 核 8G。该规格适合小程序初期上线、低到中等并发导览、PostgreSQL/Redis/Elasticsearch 同机部署和流式 LLM 代理。代码仍应避免不必要的额外模型调用。

## 已实现能力

- 游客导览 session 与 `X-Session-Token`。
- `/api/v1/tour/sessions/{id}/chat/stream` SSE 流式导览回答。
- 四类导览身份：
  - `A` 考古研究员
  - `B` 研学记录员
  - `C` 历史追问者
  - `D` 器物研究员
- 三步问卷上下文注入：focus、assumption、guide mode。
- 展厅 slug 规范化和中英文/历史 slug 兼容。
- 展厅进入、展品浏览、提问、深挖等事件记录。
- 报告生成：访问统计、提问线索、复盘清单、认知变化。
- Reflection Engine：不新增数据库、不新增 API、不新增模型调用，基于已有 session/events/report 规则推断认知变化。
- `/api/v1/curator/plan-tour` AI 策展路线接口。
- 公共展品浏览、按展厅筛选、文字搜索。
- RAG 链路：query rewrite、Elasticsearch 检索、rerank、文档过滤、流式生成。
- LLM 分层模型：
  - `LLM_TOUR_MODEL` 用于普通导览对话。
  - `LLM_REPORT_MODEL` 用于报告等更重的总结任务。
  - `LLM_MODEL` 保留为兼容兜底。
- DeepSeek/Qwen 兼容模式：
  - DeepSeek 使用 `thinking={"type":"disabled"}`。
  - Qwen/DashScope 使用 `enable_thinking=false`。
- 导览对话会传递结构化 `conversation_history`，改善连续追问相关性，同时保持检索 query 干净。
- Redis 或 Elasticsearch 不可用时进入 degraded 模式，而不是直接阻断整个服务启动。

## 尚未生产闭环

- 拍照识别展品。
- OCR 或图像检索链路。
- 小程序语音输入。
- 小程序端 TTS 播放闭环。
- 官方室内地图、定位和展品点位。
- 馆方授权的完整展品图像、精确展品清单与空间布局数据。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| API | FastAPI, Pydantic v2 |
| 运行 | Python 3.11+, uv, Uvicorn |
| 数据库 | PostgreSQL / SQLAlchemy async |
| 缓存 | Redis |
| 检索 | Elasticsearch |
| RAG | LangChain, LangGraph, 自定义 retriever/filter |
| LLM | OpenAI-compatible provider |
| Rerank | SiliconFlow / OpenAI / Cohere / custom / mock |
| TTS | Xiaomi MiMo 或 mock provider |
| 测试 | pytest, pytest-asyncio |

## 目录结构

```text
backend/
├─ backend/app/
│  ├─ api/                 # FastAPI routers
│  ├─ application/         # 应用服务与业务编排
│  ├─ config/              # settings 与环境变量校验
│  ├─ domain/              # 领域异常与实体
│  ├─ infra/               # LLM/RAG/数据库/外部服务适配
│  ├─ observability/       # 日志与追踪上下文
│  └─ main.py              # FastAPI app 入口
├─ backend/tests/
├─ scripts/
├─ docs/
├─ docker/
├─ docker-compose.yml
├─ pyproject.toml
├─ .env.example
└─ README.md
```

## 环境变量

复制示例：

```bash
cp .env.example .env
```

关键配置：

```dotenv
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=http://localhost:9200
JWT_SECRET=

LLM_PROVIDER=qwen
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=
LLM_MODEL=qwen-flash
LLM_TOUR_MODEL=qwen-flash
LLM_REPORT_MODEL=qwen-plus
LLM_HEADERS=
LLM_TEMPERATURE=0.6
LLM_MAX_TOKENS=800
LLM_ENABLE_THINKING=false
LLM_COMPAT_MODE=qwen
```

如继续使用 DeepSeek：

```dotenv
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-flash
LLM_TOUR_MODEL=deepseek-v4-flash
LLM_REPORT_MODEL=deepseek-v4-pro
LLM_COMPAT_MODE=deepseek
```

真实 `.env` 不应提交到 Git。备份文件 `.env.backup.*` 也已加入忽略规则。

## 本地运行

```bash
cd backend
uv sync --extra dev
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## 测试

常用快速检查：

```bash
cd backend
py -3 -m py_compile backend/app/config/settings.py backend/app/infra/providers/llm.py backend/app/api/tour.py backend/app/application/tour_chat_service.py
uv run --extra dev pytest backend/tests/unit/test_llm_provider.py backend/tests/unit/test_config.py backend/tests/unit/test_tour_chat.py -q --basetemp .pytest_tmp
```

更完整检查：

```bash
uv run --extra dev pytest -q --basetemp .pytest_tmp
```

## 部署提示

- 生产环境建议用 systemd 或 Docker Compose 托管服务，不建议长期使用裸 `nohup --reload`。
- 小程序正式环境必须使用 HTTPS 域名，并在微信公众平台配置合法 request 域名。
- 2 核 8G 可以承载初期后端、Redis、PostgreSQL、Elasticsearch；如果并发明显增加，应优先拆分 Elasticsearch 或数据库，再考虑升级 CPU。
- 更新 `.env` 后必须重启后端进程，代码更新后也建议重启并检查日志。

