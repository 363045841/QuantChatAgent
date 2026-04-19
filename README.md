# QuantAgent - 智能金融数据分析助手

基于 FastAPI 和 LangChain 的智能金融数据分析助手，提供专业的股票查询、数据分析和智能问答功能。

## 项目特性

- 🤖 **智能对话**: 基于 LangChain 构建的智能 Agent，支持自然语言交互
- 📊 **股票数据查询**: 支持股票 K 线数据、历史行情查询
- 🔍 **多维度分析**: 支持按日期、代码等多种方式查询股票数据
- 💬 **流式响应**: 支持实时流式对话输出
- 🚀 **高性能**: 基于 FastAPI 和异步处理架构
- 📝 **API 文档**: 自动生成交互式 API 文档

## 技术栈

- **Web 框架**: FastAPI 0.115.0
- **AI 框架**: LangChain 0.3.7
- **LLM 集成**: LangChain OpenAI 0.2.5
- **数据库**: SQLAlchemy 2.0.36, PostgreSQL
- **向量数据库**: Qdrant 1.12.1
- **异步处理**: httpx, asyncpg
- **工具**: uvicorn, pydantic, python-dotenv

## 快速开始

### 环境要求

- Python >= 3.13.7

### 安装依赖

#### 方式一：使用 pip

```bash
pip install -r requirements.txt
```

#### 方式二：使用 uv（推荐）

```bash
uv sync
```

### 环境配置

1. 复制环境变量示例文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，配置必要的环境变量（如 API Key、数据库连接等）

### 启动项目

#### 方式一：直接运行（推荐）

```bash
python -m app.main
```

#### 方式二：使用 uvicorn

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

#### 方式三：使用 uv

```bash
uv run python -m app.main
```

### 访问服务

启动成功后，可以通过以下地址访问：

- **主页**: http://localhost:8001
- **API 文档**: http://localhost:8001/docs
- **ReDoc 文档**: http://localhost:8001/redoc
- **健康检查**: http://localhost:8001/api/chat/health

## 项目结构

```
quantagentlangchain/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── agents/              # AI Agent
│   │   └── finance_agent.py # 金融分析 Agent
│   ├── api/                 # API 路由
│   │   └── chat.py          # 聊天接口
│   ├── models/              # 数据模型
│   │   ├── chat.py
│   │   └── stock.py
│   ├── services/            # 业务服务
│   │   ├── llm_service.py   # LLM 服务
│   │   └── stock_service.py # 股票数据服务
│   └── tools/               # LangChain 工具
│       ├── stock_tools.py   # 股票查询工具
│       └── code_query.py    # 代码查询工具
├── docs/                    # 文档
├── memory-bank/             # 项目记忆库
├── .env                     # 环境变量（不提交到 Git）
├── .env.example             # 环境变量示例
├── requirements.txt         # Python 依赖
├── pyproject.toml           # 项目配置
└── uv.lock                  # 依赖锁定文件
```

## 使用示例

### 通过 API 文档测试

1. 访问 http://localhost:8001/docs
2. 找到 `/api/chat/chat` 接口
3. 点击 "Try it out"
4. 输入消息，例如："查询贵州茅台最近的股价走势"
5. 点击 "Execute" 执行请求

### 通过 cURL 测试

> 💡 详细的 cURL 命令文档请查看 [API_CURL_COMMANDS.md](./API_CURL_COMMANDS.md)

**基本示例**：

```bash
# 发送普通请求
curl -X POST http://localhost:8001/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询贵州茅台最近的股价走势"}'

# 发送流式请求
curl -N -X GET "http://localhost:8001/api/chat/chat-stream?message=分析最近的股市行情"

# 健康检查
curl -X GET http://localhost:8001/api/chat/health
```

**更多示例**：
- 查询股票代码：`{"message": "查询600519的股票信息"}`
- 查询K线数据：`{"message": "查询sh.600519最近30天的数据"}`
- 查询所有股票：`{"message": "帮我列出所有股票"}`
- 按日期查询：`{"message": "查询2026-03-06有哪些股票数据"}`

📖 **完整 API 文档**: [API_CURL_COMMANDS.md](./API_CURL_COMMANDS.md)

## 开发说明

### 添加新的工具

1. 在 `app/tools/` 目录下创建新的工具文件
2. 使用 LangChain 的 `@tool` 装饰器定义工具函数
3. 在 `app/agents/finance_agent.py` 中导入并注册新工具

### 配置 LLM

在 `app/config.py` 中配置 LLM 相关参数：
- `OPENAI_API_KEY`: OpenAI API Key
- `OPENAI_BASE_URL`: API 基础 URL（支持自定义端点）
- `MODEL_NAME`: 使用的模型名称

## 常见问题

### 导入错误

如果遇到 `ImportError`，请确保：
1. 已安装所有依赖：`pip install -r requirements.txt`
2. Python 版本 >= 3.13.7
3. 虚拟环境已正确激活

### 环境变量配置

`.env` 文件不会被 Git 跟踪，请确保：
1. 复制 `.env.example` 为 `.env`
2. 填写所有必要的环境变量
3. 不要将 `.env` 文件提交到版本控制

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！