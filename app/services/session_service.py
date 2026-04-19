"""
会话管理服务 - Redis热数据 + PG冷数据
"""
import json
import time
import asyncio
import logging
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4

import tiktoken
from redis.exceptions import RedisError

from app.config import settings, SessionConfig
from app.models.chat_session import (
    ChatSession, ChatMessage,
    MessageTooLongError, SessionBusyError, SessionNotFoundError
)

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务 - PG为主，Redis为缓存"""

    def __init__(self, redis_client, pg_pool):
        self.redis = redis_client.client
        self.pg = pg_pool
        self._tokenizer = None  # 延迟加载
        self._tokenizer_lock = threading.Lock()

    @property
    def tokenizer(self):
        """延迟加载tokenizer - 线程安全"""
        if self._tokenizer is None:
            with self._tokenizer_lock:
                if self._tokenizer is None:
                    try:
                        self._tokenizer = tiktoken.get_encoding("cl100k_base")
                        logger.info("Tokenizer loaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to load tokenizer: {e}")
                        # 返回一个简单的fallback tokenizer
                        self._tokenizer = _FallbackTokenizer()
        return self._tokenizer
    
    # === 核心方法 ===
    
    async def save_message(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """保存消息 - PG为主，Redis为缓存"""
        
        # 1. 校验消息长度
        if len(content) > settings.max_message_length:
            raise MessageTooLongError(
                f"Message too long: {len(content)} > {settings.max_message_length}"
            )
        
        # 2. 校验token数
        token_count = self._count_tokens(content)
        if token_count > settings.max_message_tokens:
            raise MessageTooLongError(
                f"Message too long in tokens: {token_count} > {settings.max_message_tokens}"
            )
        
        # 3. 确保会话存在
        await self.get_or_create_session(session_id)
        
        # 4. 构建消息对象
        message = {
            'message_id': uuid4(),
            'session_id': session_id,
            'role': role,
            'content': content,
            'tokens': token_count,
            'metadata': metadata or {}
        }
        
        # 5. 先写PG（必须成功）
        saved_message = await self._save_to_postgres(message)
        
        # 6. 再写Redis（允许失败）
        try:
            await self._save_to_redis(session_id, saved_message)
        except RedisError as e:
            logger.warning(f"Redis write failed: {e}")
        
        return saved_message
    
    async def get_sliding_window(self, session_id: str) -> List[Dict[str, Any]]:
        """获取滑动窗口历史"""
        
        # 1. 从Redis加载热数据
        hot_messages = await self._load_hot(session_id)
        
        # 2. 如果没有，从PG恢复
        if not hot_messages:
            hot_messages = await self._restore_from_cold(session_id)
        
        # 3. 应用滑动窗口算法
        return self._apply_sliding_window(hot_messages)
    
    async def get_or_create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        max_retries: int = 3
    ) -> ChatSession:
        """获取或创建会话（带重试机制防止并发竞态）"""
        for attempt in range(max_retries):
            # 1. 先尝试查询
            row = await self.pg.fetchrow(
                "SELECT * FROM chat_sessions WHERE id = $1", session_id
            )
            if row:
                return ChatSession(**dict(row))

            # 2. 尝试插入
            row = await self.pg.fetchrow("""
                INSERT INTO chat_sessions (id, user_id)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
                RETURNING *
            """, session_id, user_id)

            if row:
                return ChatSession(**dict(row))

            # 3. 并发竞态，重试
            logger.debug(f"Session {session_id} race condition, retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(0.05)

        # 4. 最终重试后再次查询（此时其他事务应该已完成）
        row = await self.pg.fetchrow(
            "SELECT * FROM chat_sessions WHERE id = $1", session_id
        )
        if row:
            return ChatSession(**dict(row))

        raise RuntimeError(f"Failed to get or create session {session_id} after {max_retries} retries")
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        row = await self.pg.fetchrow(
            "SELECT * FROM chat_sessions WHERE id = $1", session_id
        )
        return ChatSession(**dict(row)) if row else None
    
    async def list_sessions(
        self, 
        user_id: Optional[str] = None, 
        limit: int = 20
    ) -> List[ChatSession]:
        """列出会话"""
        if user_id:
            rows = await self.pg.fetch("""
                SELECT * FROM chat_sessions 
                WHERE user_id = $1 
                ORDER BY last_activity DESC 
                LIMIT $2
            """, user_id, limit)
        else:
            rows = await self.pg.fetch("""
                SELECT * FROM chat_sessions 
                ORDER BY last_activity DESC 
                LIMIT $1
            """, limit)
        
        return [ChatSession(**dict(row)) for row in rows]
    
    async def clear_session(self, session_id: str):
        """清空会话"""
        # 删除Redis缓存
        key = f"session:{session_id}:messages"
        try:
            await self.redis.delete(key)
        except RedisError as e:
            logger.warning(f"Redis delete failed for session {session_id}: {e}")

        # 删除PG数据
        await self.pg.execute(
            "DELETE FROM chat_messages WHERE session_id = $1", session_id
        )

        # 重置会话计数
        await self.pg.execute("""
            UPDATE chat_sessions
            SET message_count = 0, total_tokens = 0
            WHERE id = $1
        """, session_id)
    
    # === 内部方法 ===
    
    async def _load_hot(self, session_id: str) -> List[Dict[str, Any]]:
        """从Redis加载热数据"""
        key = f"session:{session_id}:messages"
        messages = await self.redis.lrange(key, 0, -1)
        return [json.loads(m) for m in messages]
    
    async def _save_to_redis(self, session_id: str, message: ChatMessage):
        """保存到Redis - 自动裁剪"""
        key = f"session:{session_id}:messages"
        
        # 将ChatMessage转换为字典
        msg_dict = {
            'message_id': message.message_id,
            'session_id': message.session_id,
            'role': message.role,
            'content': message.content,
            'tokens': message.tokens,
            'metadata': message.metadata,
            'created_at': message.created_at,
            'id': message.id
        }
        
        # 序列化消息（处理UUID和datetime）
        serialized = self._serialize_message(msg_dict)
        
        # 使用pipeline批量执行
        pipe = self.redis.pipeline()
        pipe.rpush(key, serialized)
        pipe.ltrim(key, -settings.redis_max_messages, -1)  # 只保留最近N条
        pipe.expire(key, settings.session_idle_ttl)
        await pipe.execute()
    
    async def _save_batch_to_redis(
        self, 
        session_id: str, 
        messages: List[Dict[str, Any]]
    ):
        """批量保存到Redis"""
        key = f"session:{session_id}:messages"
        pipeline = self.redis.pipeline()
        for msg in messages:
            pipeline.rpush(key, self._serialize_message(msg))
        pipeline.ltrim(key, -settings.redis_max_messages, -1)
        pipeline.expire(key, settings.session_idle_ttl)
        await pipeline.execute()
    
    async def _restore_from_cold(self, session_id: str) -> List[Dict[str, Any]]:
        """从PG恢复冷数据 - 分批加载，过滤未完成消息"""
        BATCH_SIZE = 50
        offset = 0
        restored = []
        total_tokens = 0
        token_budget = SessionConfig.usable_history_budget()
        
        while True:
            # 过滤streaming/abandoned消息
            batch = await self.pg.fetch("""
                SELECT * FROM chat_messages 
                WHERE session_id = $1 
                  AND (metadata->>'status' IS NULL 
                       OR metadata->>'status' = 'complete')
                ORDER BY seq_num DESC
                LIMIT $2 OFFSET $3
            """, session_id, BATCH_SIZE, offset)
            
            if not batch:
                break
            
            for row in batch:
                msg = dict(row)
                msg_tokens = msg['tokens'] + 4  # +结构开销
                
                if total_tokens + msg_tokens > token_budget:
                    restored.reverse()
                    if restored:
                        await self._save_batch_to_redis(session_id, restored)
                    return restored
                
                restored.append(msg)
                total_tokens += msg_tokens
            
            offset += BATCH_SIZE
        
        restored.reverse()
        if restored:
            await self._save_batch_to_redis(session_id, restored)
        return restored
    
    async def _save_to_postgres(self, message: Dict[str, Any]) -> ChatMessage:
        """保存消息到PG - 事务保护"""
        async with self.pg.acquire() as conn:
            async with conn.transaction():
                # 1. 获取序号（原子递增）
                row1 = await conn.fetchrow("""
                    UPDATE chat_sessions 
                    SET message_count = message_count + 1, 
                        total_tokens = total_tokens + $2,
                        last_activity = NOW()
                    WHERE id = $1 
                    RETURNING message_count
                """, message['session_id'], message['tokens'])
                
                seq_num = row1['message_count']
                
                # 2. 插入消息
                row2 = await conn.fetchrow("""
                    INSERT INTO chat_messages 
                        (session_id, message_id, seq_num, role, content, tokens, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, created_at
                """, 
                    message['session_id'],
                    message['message_id'],
                    seq_num,
                    message['role'],
                    message['content'],
                    message['tokens'],
                    json.dumps(message.get('metadata', {}))
                )
        
        return ChatMessage(
            id=row2['id'],
            message_id=message['message_id'],
            session_id=message['session_id'],
            seq_num=seq_num,
            role=message['role'],
            content=message['content'],
            tokens=message['tokens'],
            metadata=message.get('metadata', {}),
            created_at=row2['created_at']
        )
    
    def _apply_sliding_window(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用滑动窗口算法 - O(n)优化"""
        
        # 分离System Prompt
        system_msgs = [m for m in messages if m['role'] == 'system']
        non_system = [m for m in messages if m['role'] != 'system']
        
        selected = []
        current_tokens = sum(m['tokens'] + 4 for m in system_msgs)
        budget = SessionConfig.usable_history_budget()
        
        # 从最新到最旧填充 - 使用append最后reverse（O(n)）
        for msg in reversed(non_system):
            cost = msg['tokens'] + 4
            if current_tokens + cost > budget:
                break
            selected.append(msg)
            current_tokens += cost
        
        selected.reverse()
        
        # 保底：至少保留最后一条用户消息
        if not selected and non_system:
            last_msg = non_system[-1]
            truncated = self._truncate_message(last_msg, budget - current_tokens)
            selected = [truncated]
        
        return system_msgs + selected
    
    def _truncate_message(self, msg: Dict[str, Any], max_tokens: int) -> Dict[str, Any]:
        """截断过长的消息（返回副本）"""
        if msg['tokens'] <= max_tokens:
            return msg
        
        truncated = msg.copy()  # 不修改原始对象
        tokens = self.tokenizer.encode(msg['content'])
        truncated_tokens = tokens[:max_tokens]
        truncated['content'] = self.tokenizer.decode(truncated_tokens)
        truncated['tokens'] = len(truncated_tokens)
        return truncated
    
    def _serialize_message(self, msg: Dict[str, Any]) -> str:
        """序列化消息为JSON字符串 - 处理UUID和datetime"""
        serializable = {
            **msg,
            'message_id': str(msg['message_id']) if isinstance(msg['message_id'], UUID) else msg['message_id'],
            'created_at': msg['created_at'].isoformat() if msg.get('created_at') else None,
        }
        return json.dumps(serializable)
    
    def _count_tokens(self, text: str) -> int:
        """计算token数"""
        return len(self.tokenizer.encode(text))
    
    def _real_token_cost(self, msg: Dict[str, Any]) -> int:
        """真实token开销"""
        return msg['tokens'] + 4  # +结构开销
    
    # === 锁管理 ===
    
    async def acquire_lock(
        self, 
        session_id: str, 
        ttl: int = None
    ) -> str:
        """获取会话锁"""
        if ttl is None:
            ttl = settings.session_lock_ttl
            
        lock_key = f"session:{session_id}:lock"
        lock_value = str(uuid4())
        
        deadline = time.time() + settings.session_lock_timeout
        while time.time() < deadline:
            if await self.redis.set(lock_key, lock_value, nx=True, ex=ttl):
                return lock_value
            await asyncio.sleep(0.1)
        
        raise SessionBusyError(f"Session {session_id} is locked")
    
    async def release_lock(self, session_id: str, lock_value: str):
        """释放会话锁 - Lua脚本保证原子性"""
        lock_key = f"session:{session_id}:lock"
        script = """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            else
                return 0
            end
        """
        await self.redis.eval(script, 1, lock_key, lock_value)
    
    async def with_lock(self, session_id: str, func, *args, **kwargs):
        """上下文管理器 - 自动获取和释放锁"""
        lock_value = await self.acquire_lock(session_id)
        try:
            return await func(*args, **kwargs)
        finally:
            await self.release_lock(session_id, lock_value)


class _FallbackTokenizer:
    """
    Fallback tokenizer - 当tiktoken加载失败时使用

    使用简单的启发式规则估算token数量：
    - ASCII字符（英文、数字、符号）≈ 4字符 = 1 token
    - 非ASCII字符（中文等）≈ 1.5字符 = 1 token
    """

    def encode(self, text: str) -> List[int]:
        """
        估算文本的token数量

        返回一个长度为估算token数的列表（内容为占位符）
        调用方只关心 len(encode(text))
        """
        if not text:
            return []

        ascii_count = 0
        non_ascii_count = 0

        for char in text:
            if ord(char) < 128:
                ascii_count += 1
            else:
                non_ascii_count += 1

        # 估算token数量
        estimated_tokens = max(1, ascii_count // 4 + int(non_ascii_count * 0.67))
        return [0] * estimated_tokens

    def decode(self, tokens: List[int]) -> str:
        """
        解码（fallback场景下无法真正解码）

        由于encode返回的是占位符，这里无法恢复原文
        返回空字符串表示无法解码
        """
        return ""


# 全局会话服务实例
_session_service: Optional[SessionService] = None
_session_lock = threading.Lock()


async def get_session_service(redis_client, pg_pool) -> SessionService:
    """获取会话服务单例（线程安全）"""
    global _session_service
    if _session_service is None:
        with _session_lock:
            if _session_service is None:
                _session_service = SessionService(redis_client, pg_pool)
    return _session_service
