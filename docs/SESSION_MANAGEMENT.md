# 会话管理功能部署文档

## 概述

本文档说明如何部署和使用QuantAgent的会话管理功能。该功能实现了基于Redis（热数据）和PostgreSQL（冷数据）的双存储架构，支持滑动窗口历史管理和会话持久化。

## 架构设计

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP/SSE
       ↓
┌─────────────┐
│  Chat API   │
└──────┬──────┘
       │
       ├─────────────┬──────────────┐
       │             │              │
       ↓             ↓              ↓
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Redis   │  │  PG      │  │ LLM API  │
│ (热数据)  │  │ (冷数据)  │  │          │
└──────────┘  └──────────┘  └──────────┘
```

### 存储策略

- **Redis（热数据）**：存储最近100条消息，快速访问
- **PostgreSQL（冷数据）**：持久化所有消息，支持历史查询和恢复

### 滑动窗口机制

- 自动计算可用token预算
- 从最新到最旧填充历史消息
- System Prompt始终保留
- 保底至少保留最后一条用户消息

## 前置要求

### 1. PostgreSQL数据库

确保PostgreSQL已安装并运行：

```bash
# 检查PostgreSQL状态
psql --version

# 连接数据库
psql -U postgres -h localhost
```

### 2. Redis缓存

确保Redis已安装并运行：

```bash
# 检查Redis状态
redis-cli ping

# 应返回: PONG
```

## 安装步骤

### 1. 安装依赖

```bash
cd d:\Code\quantagentlangchain
uv add redis tiktoken
```

### 2. 创建数据库表

执行SQL脚本创建必要的表：

```bash
# 使用psql执行
psql -U postgres -h localhost -d quantagent -f migrations/001_create_chat_tables.sql

# 或者直接在数据库中执行SQL
```

SQL脚本位置：`migrations/001_create_chat_tables.sql`

### 3. 配置环境变量

复制`.env.example`并配置：

```bash
cp .env.example .env
```

编辑`.env`文件，设置以下配置：

```env
# PostgreSQL配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=quantagent
DB_USER=postgres
DB_PASSWORD=your_password_here

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=optional_password

# 会话管理配置（可选，有默认值）
MODEL_CONTEXT_WINDOW=128000
MAX_OUTPUT_TOKENS=4096
SYSTEM_PROMPT_BUDGET=2000
TOOL_SCHEMA_BUDGET=1000
SAFETY_MARGIN=1000

MAX_MESSAGE_LENGTH=50000
MAX_MESSAGE_TOKENS=16000

SESSION_IDLE_TTL=604800  # 7天
SESSION_LOCK_TTL=120
SESSION_LOCK_TIMEOUT=10
REDIS_MAX_MESSAGES=100
```

## 使用方法

### 1. 启动应用

```bash
python -m uvicorn app.main:app --reload
```

或者使用项目启动脚本：

```bash
python main.py
```

### 2. API调用

#### 普通聊天（带会话）

**请求：**
```bash
curl -X POST "http://localhost:8001/api/chat/chat" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session-123" \
  -d '{
    "message": "分析一下贵州茅台的股价"
  }'
```

**响应：**
```json
{
  "reply": "贵州茅台（600519）最新股价为...",
  "session_id": "my-session-123"
}
```

#### 流式聊天（带会话）

**请求：**
```bash
curl -X POST "http://localhost:8001/api/chat/chat-stream" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: my-session-123" \
  -d '{
    "message": "那五粮液呢？"
  }'
```

**响应（SSE）：**
```
data: {"data": "五", "session_id": "my-session-123"}
data: {"data": "粮", "session_id": "my-session-123"}
data: {"data": "液", "session_id": "my-session-123"}
...
```

#### 清空会话

```bash
curl -X POST "http://localhost:8001/api/chat/clear-session" \
  -H "X-Session-ID: my-session-123"
```

### 3. 会话管理说明

- **会话ID管理**：
  - 首次请求：不传`X-Session-ID`，系统自动生成并返回
  - 后续请求：带上返回的`session_id`或`X-Session-ID`头
  - 多用户：每个用户使用不同的session_id

- **会话生命周期**：
  - 默认空闲7天后过期（可配置）
  - 消息永久存储在PostgreSQL中
  - Redis缓存自动过期

- **历史限制**：
  - 单条消息最大50000字符
  - 单条消息最大16000 tokens
  - 自动滑动窗口，控制token总数

## 测试

### 运行测试脚本

```bash
python test_session_service.py
```

测试内容：
- ✓ Redis连接测试
- ✓ 会话创建和获取
- ✓ 消息保存和限制
- ✓ 滑动窗口历史获取
- ✓ 会话清空功能

### 手动测试

使用API文档测试：
```
http://localhost:8001/docs
```

## 故障排查

### 1. Redis连接失败

**错误信息：**
```
Failed to connect to Redis: Error connecting to Redis
```

**解决方案：**
```bash
# 检查Redis是否运行
redis-cli ping

# 如果未运行，启动Redis
redis-server

# 检查配置
# .env中的REDIS_HOST和REDIS_PORT是否正确
```

### 2. PostgreSQL连接失败

**错误信息：**
```
connection to server at "localhost", port 5432 failed
```

**解决方案：**
```bash
# 检查PostgreSQL是否运行
pg_isready

# 如果未运行，启动PostgreSQL
# Windows服务管理器中启动postgresql服务

# 检查数据库是否创建
psql -U postgres -l

# 创建数据库
createdb -U postgres quantagent
```

### 3. 数据库表不存在

**错误信息：**
```
relation "chat_sessions" does not exist
```

**解决方案：**
```bash
# 执行迁移脚本
psql -U postgres -h localhost -d quantagent -f migrations/001_create_chat_tables.sql
```

### 4. Token计算错误

**错误信息：**
```
MessageTooLongError: Message too long in tokens: 17000 > 16000
```

**解决方案：**
- 缩短消息内容
- 或增加`MAX_MESSAGE_TOKENS`配置值

## 性能优化

### 1. Redis配置

生产环境建议：

```env
# 增加最大连接数
REDIS_MAX_CONNECTIONS=100

# 设置密码
REDIS_PASSWORD=strong_password_here

# 考虑使用Redis Cluster
```

### 2. PostgreSQL配置

```env
# 增加连接池大小
DB_MIN_CONNECTIONS=10
DB_MAX_CONNECTIONS=50
```

### 3. 会话配置

```env
# 减少Redis缓存消息数（降低内存使用）
REDIS_MAX_MESSAGES=50

# 调整token预算（根据模型上下文窗口）
MODEL_CONTEXT_WINDOW=128000
MAX_OUTPUT_TOKENS=4096
```

## 监控和维护

### 1. 数据库维护

定期清理过期会话：

```sql
-- 删除30天无活动的会话
DELETE FROM chat_sessions 
WHERE last_activity < NOW() - INTERVAL '30 days';

-- 级联删除相关消息
-- (由于有外键约束，会自动删除)
```

### 2. Redis维护

监控内存使用：

```bash
redis-cli INFO memory
redis-cli INFO stats
```

### 3. 日志监控

查看应用日志：
```
tail -f app.log
```

关键日志：
- `Redis connected` - Redis连接成功
- `PostgreSQL connection pool initialized` - PG连接池初始化成功
- `Session service initialized` - 会话服务初始化成功

## 安全建议

1. **密码管理**：
   - 使用强密码
   - 不要将密码提交到版本控制
   - 使用环境变量或密钥管理系统

2. **网络安全**：
   - 生产环境使用HTTPS
   - 限制CORS来源
   - 配置防火墙规则

3. **数据安全**：
   - 定期备份数据库
   - 启用PostgreSQL WAL归档
   - 考虑数据加密

## 扩展功能

### 1. 用户认证

集成用户系统，关联session_id和user_id：

```python
# 在保存消息时传递user_id
await session_service.save_message(
    session_id, 
    "user", 
    message,
    user_id="user123"
)
```

### 2. 会话分析

添加会话统计功能：

```python
# 获取用户的所有会话
sessions = await session_service.list_sessions(user_id="user123")

# 分析会话数据
for session in sessions:
    print(f"会话: {session.id}")
    print(f"消息数: {session.message_count}")
    print(f"总tokens: {session.total_tokens}")
```

### 3. 导入导出

支持会话数据的导入导出：

```python
# 导出会话历史
messages = await session_service.get_sliding_window(session_id)
with open(f"{session_id}.json", "w") as f:
    json.dump(messages, f)
```

## 常见问题

**Q: 会话数据会丢失吗？**

A: 不会。所有消息永久存储在PostgreSQL中。Redis缓存过期后，会从PostgreSQL自动恢复。

**Q: 如何处理超大对话？**

A: 滑动窗口会自动裁剪历史，确保不超过token预算。建议用户手动清空会话或开始新会话。

**Q: 可以同时支持多少个会话？**

A: 取决于PostgreSQL和Redis的性能。使用默认配置，可轻松支持数千个并发会话。

**Q: 如何备份会话数据？**

A: 直接备份PostgreSQL数据库即可。建议使用pg_dump定期备份。

## 联系支持

如有问题，请查看：
- 项目文档：`docs/`
- API文档：`http://localhost:8001/docs`
- GitHub Issues