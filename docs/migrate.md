好的，我已经充分了解了 QuantAgent 项目。让我为您总结一下项目的核心内容，然后制定移植到 FastAPI + LangChain 的详细计划。

## 项目概况

**QuantAgent** 是一个基于 Spring Boot + LangChain4j 的智能金融数据分析助手，主要特点：

### 核心功能
- 🤖 使用智谱 AI GLM-4.5-air 模型
- 📊 股票数据查询和分析（K线数据、股票列表）
- 🔧 自动 Tool Calling（AI 自动识别意图调用工具）
- 🌊 SSE 流式响应
- 💾 PostgreSQL 数据库 + Qdrant 向量数据库（RAG）

### 技术架构
```
Java Spring Boot 项目
├── Controller: ChatController (REST API)
├── Service: ZhipuAiService (LLM集成) + StockDataService (数据服务)
├── Tools: Stock, StockQuery, CodeQuery (AI 可调用工具)
├── Interface: FinanceAssistant (AI 助手定义)
└── External: 股票 API 服务
```

### API 接口
- `GET /api/chat/chat?message=xxx` - 普通对话
- `GET /api/chat/chat-stream?message=xxx` - 流式对话（SSE）

---

## 移植到 FastAPI + LangChain 的详细方案

### 阶段一：项目初始化与环境搭建

1. **创建 FastAPI 项目结构**
   ```
   quantagent-langchain/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py              # FastAPI 应用入口
   │   ├── config.py            # 配置管理
   │   ├── models/              # Pydantic 数据模型
   │   │   ├── stock.py
   │   │   └── chat.py
   │   ├── services/            # 业务逻辑层
   │   │   ├── llm_service.py   # LLM 服务
   │   │   ├── stock_service.py # 股票数据服务
   │   │   └── code_service.py  # 股票代码查询服务
   │   ├── tools/               # LangChain 工具
   │   │   ├── stock_tools.py
   │   │   └── code_query.py
   │   ├── api/                 # API 路由
   │   │   └── chat.py
   │   └── agents/              # Agent 配置
   │       └── finance_agent.py
   ├── requirements.txt
   ├── .env.example
   └── README.md
   ```

2. **依赖包安装**
   - FastAPI + Uvicorn（Web 框架）
   - LangChain（LLM 框架）
   - LangChain OpenAI（兼容智谱 AI）
   - Pydantic（数据验证）
   - httpx / aiohttp（异步 HTTP 客户端）
   - python-dotenv（环境变量管理）
   - psycopg2 / asyncpg（PostgreSQL 连接）

### 阶段二：核心服务迁移

3. **配置管理**
   - 创建 `config.py` 管理环境变量
   - 支持 `.env` 文件配置
   - 配置项：智谱 AI API Key、股票 API 地址、数据库配置

4. **LLM 服务集成**
   - 使用 `langchain_openai.ChatOpenAI`（智谱 AI 兼容 OpenAI 接口）
   - 配置流式输出和普通对话
   - 实现 System Prompt（金融分析师"小财"人设）

5. **工具迁移**
   - 将 Java 的 `@Tool` 注解转换为 LangChain `@tool` 装饰器
   - 实现三个核心工具：
     * `get_kline` - 获取 K 线数据
     * `query_recent_days` - 快捷查询最近 N 天
     * `get_all_stocks` - 获取股票列表
     * `query_code_info` - 查询股票代码信息

### 阶段三：Agent 与 API 实现

6. **Finance Agent 构建**
   - 使用 LangChain 的 `create_tool_calling_agent`
   - 绑定工具到 Agent
   - 实现聊天记忆（ChatMessageHistory）

7. **API 路由实现**
   - `GET /api/chat/chat` - 普通对话
   - `GET /api/chat/chat-stream` - 流式对话（Server-Sent Events）
   - 使用 FastAPI 的 `StreamingResponse`

8. **异步支持**
   - 使用 async/await 实现异步 HTTP 请求
   - 集成 `httpx` 异步客户端调用股票 API

### 阶段四：数据库与高级功能

9. **数据库集成**
   - 使用 SQLAlchemy 或 SQLModel（如需要）
   - 迁移 MyBatis Plus 的查询逻辑

10. **Qdrant 向量数据库集成（可选）**
    - 实现知识库检索增强生成（RAG）
    - 使用 LangChain 的 Qdrant 集成

### 阶段五：测试与部署

11. **单元测试**
    - 测试各个工具功能
    - 测试 Agent 对话逻辑

12. **部署文档**
    - Docker 容器化
    - 环境变量配置说明

---

## 技术对比

| 功能 | Java (原项目) | Python (新项目) |
|------|--------------|----------------|
| Web 框架 | Spring Boot | FastAPI |
| LLM 框架 | LangChain4j | LangChain |
| ORM | MyBatis Plus | SQLAlchemy / SQLModel |
| 向量库 | Qdrant Java Client | LangChain Qdrant |
| 异步处理 | Servlet 3.0+ | asyncio |

---

## 关键技术要点

1. **智谱 AI 集成**
   ```python
   from langchain_openai import ChatOpenAI
   
   llm = ChatOpenAI(
       model="glm-4.5-air",
       api_key="your_api_key",
       base_url="https://open.bigmodel.cn/api/paas/v4"
   )
   ```

2. **Tool 定义**
   ```python
   from langchain.tools import tool
   
   @tool
   def get_kline(stock_code: str, start_date: str, end_date: str) -> str:
       """获取股票K线数据"""
       # 实现逻辑
   ```

3. **流式输出**
   ```python
   async def chat_stream(message: str):
       async for chunk in agent.astream({"input": message}):
           yield chunk
   ```

---

## 实施顺序建议

**第一阶段（MVP）**：
- ✅ 基础项目结构
- ✅ LLM 集成
- ✅ 基础工具迁移
- ✅ 普通 API 接口

**第二阶段（完整功能）**：
- ✅ 流式 API 接口
- ✅ 异步支持
- ✅ 数据库集成

**第三阶段（增强功能）**：
- ✅ Qdrant RAG
- ✅ Docker 部署
- ✅ 测试覆盖

---

这个计划是否符合您的预期？如果您确认方案，请 **toggle to Act mode**，我将开始实施移植工作。如果您有任何调整或疑问，请随时告诉我！