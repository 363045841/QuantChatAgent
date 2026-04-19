"""
测试 API 接口
"""
import asyncio
import httpx


async def test_health_check():
    """测试健康检查"""
    print("=" * 60)
    print("【测试 1】健康检查")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8001/api/chat/health", timeout=5.0)
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
            print("✅ 健康检查通过\n")
        except Exception as e:
            print(f"❌ 健康检查失败: {e}\n")


async def test_chat_get():
    """测试 GET /chat 接口"""
    print("=" * 60)
    print("【测试 2】GET /chat 接口")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://localhost:8001/api/chat/chat",
                params={"message": "你好"},
                timeout=30.0
            )
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()['reply'][:100]}...")
            print("✅ GET /chat 通过\n")
        except Exception as e:
            print(f"❌ GET /chat 失败: {e}\n")


async def test_chat_post():
    """测试 POST /chat 接口"""
    print("=" * 60)
    print("【测试 3】POST /chat 接口")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/chat/chat",
                json={"message": "查询sh.600519最近3天的数据"},
                timeout=30.0
            )
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()['reply'][:150]}...")
            print("✅ POST /chat 通过\n")
        except Exception as e:
            print(f"❌ POST /chat 失败: {e}\n")


async def test_streaming():
    """测试流式接口"""
    print("=" * 60)
    print("【测试 4】流式接口")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "GET",
                "http://localhost:8001/api/chat/chat-stream",
                params={"message": "你好"},
                timeout=30.0
            ) as response:
                print(f"状态码: {response.status_code}")
                print("流式输出:")
                async for chunk in response.aiter_bytes():
                    print(chunk.decode('utf-8'), end='', flush=True)
                print("\n✅ 流式接口通过\n")
        except Exception as e:
            print(f"❌ 流式接口失败: {e}\n")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试 API 接口")
    print("⚠️ 请确保 FastAPI 服务已启动 (uvicorn app.main:app --reload)")
    print("=" * 60 + "\n")
    
    # 先测试健康检查
    await test_health_check()
    
    # 如果健康检查通过，继续其他测试
    await test_chat_get()
    await test_chat_post()
    await test_streaming()
    
    print("=" * 60)
    print("🎉 API 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())