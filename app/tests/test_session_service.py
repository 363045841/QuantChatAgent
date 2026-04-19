"""
测试会话管理服务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.redis_client import get_redis_client, close_redis_client
from app.services.session_service import get_session_service
from app.services.database_service import get_pool
from app.config import settings


async def test_session_service():
    """测试会话服务"""
    print("=" * 60)
    print("测试会话管理服务")
    print("=" * 60)
    
    # 1. 初始化服务
    print("\n[1] 初始化服务...")
    try:
        redis_client = await get_redis_client()
        pg_pool = await get_pool()
        session_service = await get_session_service(redis_client, pg_pool)
        print("✓ 服务初始化成功")
    except Exception as e:
        print(f"✗ 服务初始化失败: {e}")
        return
    
    # 2. 创建会话
    print("\n[2] 创建会话...")
    session_id = "test-session-001"
    try:
        session = await session_service.get_or_create_session(session_id)
        print(f"✓ 会话创建成功: {session.id}")
        print(f"  消息数: {session.message_count}")
        print(f"  总token数: {session.total_tokens}")
    except Exception as e:
        print(f"✗ 创建会话失败: {e}")
        return
    
    # 3. 保存测试消息
    print("\n[3] 保存测试消息...")
    test_messages = [
        {"role": "system", "content": "你是一个金融分析助手"},
        {"role": "user", "content": "请分析一下贵州茅台的最新股价"},
        {"role": "assistant", "content": "贵州茅台（600519）最新股价为..."},
        {"role": "user", "content": "那五粮液呢？"},
    ]
    
    for i, msg in enumerate(test_messages, 1):
        try:
            saved_msg = await session_service.save_message(
                session_id,
                msg["role"],
                msg["content"]
            )
            print(f"✓ 消息 {i} 保存成功 (tokens: {saved_msg.tokens})")
        except Exception as e:
            print(f"✗ 消息 {i} 保存失败: {e}")
    
    # 4. 获取会话信息
    print("\n[4] 获取会话信息...")
    try:
        session = await session_service.get_session(session_id)
        print(f"✓ 会话信息:")
        print(f"  消息数: {session.message_count}")
        print(f"  总token数: {session.total_tokens}")
    except Exception as e:
        print(f"✗ 获取会话信息失败: {e}")
    
    # 5. 获取滑动窗口历史
    print("\n[5] 获取滑动窗口历史...")
    try:
        history = await session_service.get_sliding_window(session_id)
        print(f"✓ 获取到 {len(history)} 条历史消息")
        for i, msg in enumerate(history, 1):
            print(f"  [{i}] {msg['role']}: {msg['content'][:50]}...")
    except Exception as e:
        print(f"✗ 获取历史失败: {e}")
    
    # 6. 测试消息长度限制
    print("\n[6] 测试消息长度限制...")
    long_content = "A" * (settings.max_message_length + 1)
    try:
        await session_service.save_message(
            session_id,
            "user",
            long_content
        )
        print("✗ 长消息应该被拒绝，但没有")
    except Exception as e:
        print(f"✓ 长消息被正确拒绝: {type(e).__name__}")
    
    # 7. 测试token限制
    print("\n[7] 测试token限制...")
    from app.config import SessionConfig
    print(f"可用历史预算: {SessionConfig.usable_history_budget()} tokens")
    
    # 8. 清空会话
    print("\n[8] 清空会话...")
    try:
        await session_service.clear_session(session_id)
        session = await session_service.get_session(session_id)
        print(f"✓ 会话已清空")
        print(f"  消息数: {session.message_count}")
        print(f"  总token数: {session.total_tokens}")
    except Exception as e:
        print(f"✗ 清空会话失败: {e}")
    
    # 9. 清理资源
    print("\n[9] 清理资源...")
    try:
        await close_redis_client()
        await pg_pool.close()
        print("✓ 资源清理完成")
    except Exception as e:
        print(f"✗ 清理资源失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


async def test_redis_health():
    """测试Redis连接"""
    print("\n" + "=" * 60)
    print("测试Redis连接")
    print("=" * 60)
    
    try:
        redis_client = await get_redis_client()
        is_healthy = await redis_client.health_check()
        
        if is_healthy:
            print(f"✓ Redis连接正常")
            print(f"  Host: {settings.redis_host}:{settings.redis_port}")
            print(f"  DB: {settings.redis_db}")
        else:
            print("✗ Redis连接失败")
        
        await close_redis_client()
    except Exception as e:
        print(f"✗ Redis测试失败: {e}")


async def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "会话管理服务测试" + " " * 28 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # 测试Redis连接
    await test_redis_health()
    
    # 测试会话服务
    await test_session_service()
    
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())