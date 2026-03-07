"""
LLM 服务测试脚本
测试普通对话和流式输出功能
"""
import asyncio
from app.services.llm_service import llm_service


def test_normal_chat():
    """测试普通对话"""
    print("=" * 50)
    print("测试普通对话")
    print("=" * 50)
    
    chat_model = llm_service.get_chat_model()
    system_prompt = llm_service.get_system_prompt()
    
    try:
        response = chat_model.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "你好，请介绍一下你自己。"}
        ])
        
        print(f"AI 回复: {response.content}")
        print("\n✅ 普通对话测试成功！")
        return True
    except Exception as e:
        print(f"\n❌ 普通对话测试失败: {e}")
        return False


async def test_streaming_chat():
    """测试流式对话"""
    print("\n" + "=" * 50)
    print("测试流式对话")
    print("=" * 50)
    
    streaming_model = llm_service.get_streaming_model()
    system_prompt = llm_service.get_system_prompt()
    
    try:
        print("AI 回复 (流式): ", end="", flush=True)
        
        async for chunk in streaming_model.astream([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "你好，请用一句话介绍一下你自己。"}
        ]):
            if chunk.content:
                print(chunk.content, end="", flush=True)
        
        print("\n\n✅ 流式对话测试成功！")
        return True
    except Exception as e:
        print(f"\n\n❌ 流式对话测试失败: {e}")
        return False


if __name__ == "__main__":
    print("开始测试 LLM 服务...\n")
    
    # 测试普通对话
    normal_success = test_normal_chat()
    
    # 测试流式对话
    streaming_success = asyncio.run(test_streaming_chat())
    
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    print(f"普通对话: {'✅ 成功' if normal_success else '❌ 失败'}")
    print(f"流式对话: {'✅ 成功' if streaming_success else '❌ 失败'}")
    
    if normal_success and streaming_success:
        print("\n🎉 所有测试通过！LLM 服务已成功集成。")
    else:
        print("\n⚠️  部分测试失败，请检查配置和网络连接。")