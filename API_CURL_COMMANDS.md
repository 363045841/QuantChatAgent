# QuantAgent API 接口文档

> 基于 FastAPI 和 LangChain 的智能金融数据分析助手

---

## 📋 目录

- [服务信息](#服务信息)
- [基础接口](#基础接口)
- [聊天接口](#聊天接口)
- [流式接口](#流式接口)
- [完整测试脚本](#完整测试脚本)

---

## 🔧 服务信息

### 启动服务

```bash
# 开发模式（自动重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 服务地址

- **API 服务**: http://localhost:8000
- **Swagger 文档**: http://localhost:8000/docs
- **ReDoc 文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/api/chat/health

---

## 🏠 基础接口

### 1. 根路径 - GET /

获取服务基本信息

```bash
curl -X GET http://localhost:8000/
```

**响应示例**:
```json
{
  "message": "欢迎使用 QuantAgent - 智能金融数据分析助手",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/api/chat/health"
}
```

### 2. 健康检查 - GET /api/chat/health

检查服务健康状态

```bash
curl -X GET http://localhost:8000/api/chat/health
```

**响应示例**:
```json
{
  "status": "ok",
  "service": "QuantAgent Chat API"
}
```

---

## 💬 聊天接口

### 3. 普通对话 - GET /api/chat/chat

发送普通消息，获取完整回复

```bash
curl -X GET "http://localhost:8000/api/chat/chat?message=你好"
```

**带 URL 编码的消息**:
```bash
curl -X GET "http://localhost:8000/api/chat/chat?message=查询贵州茅台的K线数据"
```

**响应示例**:
```json
{
  "reply": "你好！我是小财，一个专业的金融数据分析师..."
}
```

**更复杂的查询**:
```bash
# 查询股票代码
curl -X GET "http://localhost:8000/api/chat/chat?message=查询600519的股票信息"

# 查询K线数据
curl -X GET "http://localhost:8000/api/chat/chat?message=查询sh.600519最近5天的数据"

# 查询所有股票
curl -X GET "http://localhost:8000/api/chat/chat?message=帮我列出所有股票"
```

### 4. 普通对话 - POST /api/chat/chat

发送普通消息（POST 方式）

```bash
curl -X POST http://localhost:8000/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

**带更复杂的消息**:
```bash
curl -X POST http://localhost:8000/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询sh.600519最近10天的日线数据"}'
```

**响应示例**:
```json
{
  "reply": "根据查询结果，以下是sh.600519（贵州茅台）最近10天的日线数据..."
}
```

---

## 🌊 流式接口

### 5. 流式对话 - GET /api/chat/chat-stream

流式返回 AI 回复（Server-Sent Events）

```bash
curl -N -X GET "http://localhost:8000/api/chat/chat-stream?message=你好"
```

**带 URL 编码的消息**:
```bash
curl -N -X GET "http://localhost:8000/api/chat/chat-stream?message=请介绍一下贵州茅台"
```

**流式查询股票数据**:
```bash
curl -N -X GET "http://localhost:8000/api/chat/chat-stream?message=查询600519最近5天的数据"
```

**说明**:
- `-N` 参数禁用缓冲，立即显示输出
- 使用 SSE（Server-Sent Events）协议
- 输出格式为 `data: <content>`

**输出示例**:
```
data: 你好！我是小财，一个专业的金融数据分析师。
data: 我可以帮助你进行各种股票相关的数据分析工作...
```

### 6. 流式对话 - POST /api/chat/chat-stream

流式返回 AI 回复（POST 方式）

```bash
curl -N -X POST http://localhost:8000/api/chat/chat-stream \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

**带更复杂的消息**:
```bash
curl -N -X POST http://localhost:8000/api/chat/chat-stream \
  -H "Content-Type: application/json" \
  -d '{"message": "查询sh.600519的基本信息和最近7天的数据"}'
```

**输出示例**:
```
data: 根据查询结果，贵州茅台（股票代码：sh.600519）
data: 的基本信息如下：
data: 股票代码：sh.600519
data: 证券简称：贵州茅台
...
```

---

## 🧪 完整测试脚本

### Linux/Mac (bash)

创建 `test_api.sh`:

```bash
#!/bin/bash

echo "=========================================="
echo "QuantAgent API 测试"
echo "=========================================="
echo ""

# 1. 健康检查
echo "【测试 1】健康检查"
curl -s http://localhost:8000/api/chat/health
echo -e "\n"

# 2. 普通对话 (GET)
echo "【测试 2】普通对话 (GET)"
curl -s "http://localhost:8000/api/chat/chat?message=你好" | python -m json.tool
echo -e "\n"

# 3. 普通对话 (POST)
echo "【测试 3】普通对话 (POST)"
curl -s -X POST http://localhost:8000/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询sh.600519最近3天的数据"}' | python -m json.tool
echo -e "\n"

# 4. 流式对话 (GET)
echo "【测试 4】流式对话 (GET)"
curl -N -X GET "http://localhost:8000/api/chat/chat-stream?message=你好"
echo -e "\n"

echo "=========================================="
echo "测试完成！"
echo "=========================================="
```

运行测试:
```bash
chmod +x test_api.sh
./test_api.sh
```

### Windows (PowerShell)

创建 `test_api.ps1`:

```powershell
Write-Host "==========================================" -ForegroundColor Green
Write-Host "QuantAgent API 测试"
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# 1. 健康检查
Write-Host "【测试 1】健康检查" -ForegroundColor Yellow
Invoke-RestMethod -Uri "http://localhost:8000/api/chat/health" | ConvertTo-Json
Write-Host ""

# 2. 普通对话 (GET)
Write-Host "【测试 2】普通对话 (GET)" -ForegroundColor Yellow
$body = @{ message = "你好" }
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/chat/chat?message=$($body.message)"
$response | ConvertTo-Json
Write-Host ""

# 3. 普通对话 (POST)
Write-Host "【测试 3】普通对话 (POST)" -ForegroundColor Yellow
$body = @{ message = "查询sh.600519最近3天的数据" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8000/api/chat/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
$response | ConvertTo-Json
Write-Host ""

# 4. 流式对话 (GET)
Write-Host "【测试 4】流式对话 (GET)" -ForegroundColor Yellow
Write-Host "流式输出:" -ForegroundColor Cyan
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/chat/chat-stream?message=你好"
$response.Content
Write-Host ""

Write-Host "==========================================" -ForegroundColor Green
Write-Host "测试完成！"
Write-Host "==========================================" -ForegroundColor Green
```

运行测试:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\test_api.ps1
```

---

## 📝 使用示例

### 场景 1: 查询股票基本信息

```bash
curl -X POST http://localhost:8000/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询600519的股票代码信息"}'
```

### 场景 2: 查询K线数据

```bash
curl -X POST http://localhost:8000/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询sh.600519最近30天的日线数据，复权方式前复权"}'
```

### 场景 3: 查询所有股票列表

```bash
curl -X POST http://localhost:8000/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "帮我列出所有股票"}'
```

### 场景 4: 按日期查询股票

```bash
curl -X POST http://localhost:8000/api/chat/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "查询2026-03-06这一天有哪些股票数据"}'
```

### 场景 5: 流式对话（实时输出）

```bash
curl -N -X GET "http://localhost:8000/api/chat/chat-stream?message=请详细分析一下贵州茅台最近一周的走势"
```

---

## 🚀 高级用法

### 使用 curl 的详细输出

```bash
# 显示请求和响应头
curl -v -X GET "http://localhost:8000/api/chat/chat?message=你好"

# 只显示响应头
curl -I -X GET "http://localhost:8000/api/chat/chat?message=你好"

# 测量响应时间
curl -w "\nTotal time: %{time_total}s\n" \
  -X GET "http://localhost:8000/api/chat/chat?message=你好"
```

### 使用代理

```bash
# 通过代理访问
curl -x http://proxy.example.com:8080 \
  -X GET "http://localhost:8000/api/chat/chat?message=你好"

# 使用 SOCKS5 代理
curl --socks5 localhost:1080 \
  -X GET "http://localhost:8000/api/chat/chat?message=你好"
```

### 保存响应到文件

```bash
# 保存 JSON 响应
curl -X GET "http://localhost:8000/api/chat/chat?message=你好" \
  -o response.json

# 保存流式输出
curl -N -X GET "http://localhost:8000/api/chat/chat-stream?message=你好" \
  -o stream_output.txt
```

---

## ⚠️ 注意事项

1. **URL 编码**: GET 请求中的消息参数需要 URL 编码
2. **引号转义**: JSON 消息中的引号需要转义
3. **超时设置**: 对于复杂查询，建议增加超时时间
4. **流式输出**: 使用 `-N` 参数禁用缓冲
5. **中文支持**: 确保终端支持 UTF-8 编码

---

## 📚 相关文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [LangChain 官方文档](https://python.langchain.com/)
- [curl 官方文档](https://curl.se/docs/)
- [Swagger UI](http://localhost:8000/docs)
- [ReDoc](http://localhost:8000/redoc)

---

**最后更新**: 2026-03-07
**版本**: 0.1.0