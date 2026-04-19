# QuantAgent - 智能金融数据分析助手

基于 **FastAPI + LangChain** 的 AI Agent 应用，通过自然语言对话查询中国 A 股市场数据（行情、K 线、新闻等），并返回专业的金融分析结果。

## 核心特性

- **AI Agent 架构** — 基于 LangGraph 构建的金融分析 Agent，自动编排 6 个专业工具
- **股票数据查询** — K 线数据、历史行情、股票代码信息查询
- **RAG 新闻检索** — Qdrant 向量检索 + 百度 Reranker 二阶段精排，提供关联新闻分析
- **流式对话** — SSE 实时流式输出，支持多轮上下文对话
- **会话管理** — PostgreSQL 持久化 + Redis 缓存双层架构，基于 Token 预算的滑动窗口
- **全面懒加载** — 所有外部依赖（LLM、向量库、数据库）延迟初始化，优雅降级

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| AI 框架 | LangChain 0.3 + LangGraph |
| LLM | 百度千帆（OpenAI 兼容接口） |
| Embedding | 智谱 AI embedding-3 |
| Reranker | 百度千帆 qwen3-reranker-8b |
| 关系数据库 | PostgreSQL（asyncpg + SQLAlchemy） |
| 缓存 | Redis |
| 向量数据库 | Qdrant |
| Token 计数 | tiktoken |

## 快速开始

### 环境要求

- Python >= 3.13
- PostgreSQL
- Redis >= 7.3.0
- Qdrant（可选，用于新闻检索）

### 安装

```bash
# 推荐：使用 uv
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
```

编辑 `.env`，填写必要配置：

| 变量 | 说明 | 必填 |
|------|------|------|
| `QIANFAN_API_KEY` | 百度千帆 API Key | 是 |
| `ZHIPU_API_KEY` | 智谱 AI API Key | 是 |
| `DB_PASSWORD` | PostgreSQL 密码 | 是 |
| `REDIS_HOST` / `REDIS_PORT` | Redis 连接信息 | 是 |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant 连接信息 | 否 |
| `BAIDU_RERANKER_API_KEY` | 百度 Reranker API Key | 否 |

### 数据库初始化

```bash
psql -U postgres -d quantagent -f migrations/001_create_chat_tables.sql
```

### 启动

```bash
# 直接运行
python -m app.main

# 或使用 uvicorn（开发模式，热重载）
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

启动后访问：
- API 文档：http://localhost:8001/docs
- 健康检查：http://localhost:8001/api/chat/health

## API 接口

所有接口挂载在 `/api/chat` 路径下，支持 GET/POST 两种方式。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/chat/chat` | 普通对话 |
| `GET` | `/api/chat/chat-stream` | 流式对话（SSE） |
| `POST` | `/api/chat/clear-session` | 清空会话历史 |
| `GET` | `/api/chat/health` | 健康检查 |

**会话管理**：通过 `X-Session-Id` 请求头传递会话 ID，不传则自动创建新会话。

### 示例

```bash
# 普通对话
curl -X POST http://localhost:8001/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询贵州茅台最近的股价走势"}'

# 流式对话
curl -N -X GET "http://localhost:8001/api/chat/chat-stream?message=分析最近的股市行情"

# 带会话的多轮对话
curl -X POST http://localhost:8001/api/chat/chat \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: my-session-123" \
  -d '{"message": "那它的基本面怎么样？"}'
```

> 完整 API 文档参见 [docs/API_CURL_COMMANDS.md](./docs/API_CURL_COMMANDS.md)

## Agent 工具

Agent 自动决策调用以下工具：

| 工具 | 功能 | 示例 |
|------|------|------|
| `get_kline_bao` | 获取 K 线数据（支持日/周/月/分钟线） | "查询sh.600519最近30天的日K线" |
| `query_recent_days_bao` | 快捷查询最近 N 天数据 | "查询贵州茅台近期的行情" |
| `get_all_stocks_bao` | 获取所有股票列表 | "列出所有股票" |
| `get_stocks_by_date_bao` | 获取特定日期股票列表 | "2026-03-06有哪些股票" |
| `query_code_info` | 查询股票代码基本信息 | "查询600519的股票信息" |
| `search_news` | RAG 新闻检索 | "贵州茅台最近有什么新闻" |

## 项目结构

```
app/
├── main.py                 # 应用入口（生命周期、路由注册）
├── config.py               # Pydantic Settings 配置管理
├── agents/
│   └── finance_agent.py    # LangGraph 金融分析 Agent
├── api/
│   └── chat.py             # 聊天 API 路由
├── models/                 # Pydantic/SQLAlchemy 数据模型
├── services/
│   ├── llm_service.py      # LLM 服务（百度千帆）
│   ├── stock_service.py    # 股票数据服务
│   ├── database_service.py # 数据库服务（双连接池）
│   ├── redis_client.py     # Redis 客户端
│   ├── session_service.py  # 会话管理（PG + Redis 滑动窗口）
│   ├── rag_service.py      # RAG 检索服务
│   └── reranker_service.py # Reranker 重排序服务
├── tools/                  # LangChain 工具
│   ├── stock_tools.py      # 股票查询工具（4 个）
│   ├── code_query.py       # 股票代码查询工具
│   └── rag_tools.py        # 新闻搜索工具
└── tests/                  # 测试
migrations/                 # 数据库迁移脚本
docs/                       # 详细文档
```

## 开发

### 添加新工具

1. 在 `app/tools/` 下创建工具文件，使用 `@tool` 装饰器
2. 在 `app/agents/finance_agent.py` 中注册工具

### 环境变量

完整环境变量说明参见 [.env.example](.env.example)。

## 许可证

MIT License
