"""
会话管理服务 - Redis热数据 + PG冷数据
"""

import json
import time
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4

from redis.exceptions import RedisError

from app.config import settings, SessionConfig
from app.models.chat_session import (
    ChatSession,
    ChatMessage,
    MessageTooLongError,
    SessionBusyError,
)

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务 - PG为主, Redis为缓存"""

    def __init__(self, redis_client, pg_pool):
        self.redis = redis_client.client
        self.pg = pg_pool

    # === 核心方法 ===

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        """保存消息 - PG为主, Redis为缓存

        Args:
            session_id: 会话ID
            role: 角色 (user/assistant/system/tool)
            content: 消息内容
            tokens: token数（用户消息传0，助手消息传API返回的completion_tokens）
            metadata: 额外元数据
        """

        # 1. 校验消息长度
        if len(content) > settings.max_message_length:
            raise MessageTooLongError(
                f"Message too long: {len(content)} > {settings.max_message_length}"
            )

        # 2. 确保会话存在
        await self.get_or_create_session(session_id)

        # 3. 构建消息对象
        message = {
            "message_id": uuid4(),
            "session_id": session_id,
            "role": role,
            "content": content,
            "tokens": tokens,
            "metadata": metadata or {},
        }

        # 4. 先写PG（必须成功）
        saved_message = await self._save_to_postgres(message)

        # 5. 再写Redis（允许失败）
        try:
            await self._save_to_redis(session_id, saved_message)
        except RedisError as e:
            logger.warning(f"Redis write failed: {e}")

        return saved_message

    async def get_sliding_window(self, session_id: str) -> List[ChatMessage]:
        """获取滑动窗口历史"""

        # 1. 从Redis加载热数据
        hot_messages = await self._load_hot(session_id)

        # 2. 如果没有, 从PG恢复
        if not hot_messages:
            hot_messages = await self._restore_from_cold(session_id)

        # 3. 应用滑动窗口算法
        return self._apply_sliding_window(hot_messages)

    async def get_or_create_session(
        self, session_id: str, user_id: Optional[str] = None, max_retries: int = 3
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
            row = await self.pg.fetchrow(
                """
                INSERT INTO chat_sessions (id, user_id)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
                RETURNING *
            """,
                session_id,
                user_id,
            )

            if row:
                return ChatSession(**dict(row))

            # 3. 并发竞态, 重试
            logger.debug(
                f"Session {session_id} race condition, retry {attempt + 1}/{max_retries}"
            )
            await asyncio.sleep(0.05)

        # 4. 最终重试后再次查询（此时其他事务应该已完成）
        row = await self.pg.fetchrow(
            "SELECT * FROM chat_sessions WHERE id = $1", session_id
        )
        if row:
            return ChatSession(**dict(row))

        raise RuntimeError(
            f"Failed to get or create session {session_id} after {max_retries} retries"
        )

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        row = await self.pg.fetchrow(
            "SELECT * FROM chat_sessions WHERE id = $1", session_id
        )
        return ChatSession(**dict(row)) if row else None

    async def list_sessions(
        self, user_id: Optional[str] = None, limit: int = 20
    ) -> List[ChatSession]:
        """列出会话"""
        if user_id:
            rows = await self.pg.fetch(
                """
                SELECT * FROM chat_sessions 
                WHERE user_id = $1 
                ORDER BY last_activity DESC 
                LIMIT $2
            """,
                user_id,
                limit,
            )
        else:
            rows = await self.pg.fetch(
                """
                SELECT * FROM chat_sessions 
                ORDER BY last_activity DESC 
                LIMIT $1
            """,
                limit,
            )

        return [ChatSession(**dict(row)) for row in rows]

    async def clear_session(self, session_id: str):
        """清空会话"""
        # 删除Redis缓存
        key = f"session:{session_id}:messages"
        try:
            await self.redis.delete(key)
        except RedisError as e:
            logger.warning(f"Redis delete failed for session {session_id}: {e}")

        # 删除PG数据并重置计数（使用事务）
        async with self.pg.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM chat_messages WHERE session_id = $1", session_id
                )
                await conn.execute(
                    """
                    UPDATE chat_sessions
                    SET message_count = 0, total_tokens = 0
                    WHERE id = $1
                """,
                    session_id,
                )

    async def update_message_tokens(
        self, session_id: str, message_id: UUID, tokens: int
    ):
        """更新消息的 token 数（API 返回后调用）

        Args:
            session_id: 会话ID
            message_id: 消息UUID
            tokens: 实际 token 数
        """
        await self.pg.execute(
            "UPDATE chat_messages SET tokens = $1 WHERE message_id = $2",
            tokens,
            message_id,
        )
        # 更新会话总 token
        await self.pg.execute(
            """
            UPDATE chat_sessions
            SET total_tokens = (
                SELECT COALESCE(SUM(tokens), 0) FROM chat_messages WHERE session_id = $1
            )
            WHERE id = $1
        """,
            session_id,
        )

    # === 内部方法 ===

    async def _load_hot(self, session_id: str) -> List[ChatMessage]:
        """从Redis加载热数据"""
        key = f"session:{session_id}:messages"
        raw_messages = await self.redis.lrange(key, 0, -1)
        messages = []
        for raw in raw_messages:
            data = json.loads(raw)
            # 处理 datetime 字段
            if data.get("created_at"):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            messages.append(ChatMessage(**data))
        return messages

    async def _save_to_redis(self, session_id: str, message: ChatMessage):
        """保存到Redis - 自动裁剪"""
        key = f"session:{session_id}:messages"

        # 序列化消息（处理UUID和datetime）
        serialized = self._serialize_message(message)

        # 使用pipeline批量执行
        pipe = self.redis.pipeline()
        pipe.rpush(key, serialized)
        pipe.ltrim(key, -settings.redis_max_messages, -1)  # 只保留最近N条
        pipe.expire(key, settings.session_idle_ttl)
        await pipe.execute()

    async def _save_batch_to_redis(self, session_id: str, messages: List[ChatMessage]):
        """批量保存到Redis"""
        key = f"session:{session_id}:messages"
        pipeline = self.redis.pipeline()
        for msg in messages:
            pipeline.rpush(key, self._serialize_message(msg))
        pipeline.ltrim(key, -settings.redis_max_messages, -1)
        pipeline.expire(key, settings.session_idle_ttl)
        await pipeline.execute()

    async def _restore_from_cold(self, session_id: str) -> List[ChatMessage]:
        """从PG恢复冷数据 - 分批加载, 过滤未完成消息"""
        BATCH_SIZE = 50
        offset = 0
        restored: List[ChatMessage] = []
        total_tokens = 0
        token_budget = SessionConfig.usable_history_budget()

        while True:
            # 过滤streaming/abandoned消息
            rows = await self.pg.fetch(
                """
                SELECT * FROM chat_messages
                WHERE session_id = $1
                  AND (metadata->>'status' IS NULL
                       OR metadata->>'status' = 'complete')
                ORDER BY seq_num DESC
                LIMIT $2 OFFSET $3
            """,
                session_id,
                BATCH_SIZE,
                offset,
            )

            if not rows:
                break

            for row in rows:
                msg = ChatMessage(**dict(row))
                msg_tokens = msg.tokens + 4  # +结构开销

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
                row1 = await conn.fetchrow(
                    """
                    UPDATE chat_sessions 
                    SET message_count = message_count + 1, 
                        total_tokens = total_tokens + $2,
                        last_activity = NOW()
                    WHERE id = $1 
                    RETURNING message_count
                """,
                    message["session_id"],
                    message["tokens"],
                )

                seq_num = row1["message_count"]

                # 2. 插入消息
                row2 = await conn.fetchrow(
                    """
                    INSERT INTO chat_messages 
                        (session_id, message_id, seq_num, role, content, tokens, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, created_at
                """,
                    message["session_id"],
                    message["message_id"],
                    seq_num,
                    message["role"],
                    message["content"],
                    message["tokens"],
                    json.dumps(message.get("metadata", {})),
                )

        return ChatMessage(
            id=row2["id"],
            message_id=message["message_id"],
            session_id=message["session_id"],
            seq_num=seq_num,
            role=message["role"],
            content=message["content"],
            tokens=message["tokens"],
            metadata=message.get("metadata", {}),
            created_at=row2["created_at"],
        )

    def _apply_sliding_window(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        """应用滑动窗口算法 - 基于数据库中存储的 token 数"""

        # 1. 消息分类：分离系统提示词
        system_msgs = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]

        selected: List[ChatMessage] = []

        # 2. 初始化 Token 计数器（每条消息 +4 结构开销）
        current_tokens = sum(m.tokens + 4 for m in system_msgs)
        budget = SessionConfig.usable_history_budget()

        # 3. 逆向遍历构建滑动窗口
        for msg in reversed(non_system):
            cost = msg.tokens + 4 if msg.tokens > 0 else len(msg.content) // 4 + 4
            if current_tokens + cost > budget:
                break
            selected.append(msg)
            current_tokens += cost

        selected.reverse()

        # 4. 保底机制：至少保留最后一条用户消息
        if not selected and non_system:
            selected = [non_system[-1]]

        return system_msgs + selected

    def _serialize_message(self, msg: ChatMessage) -> str:
        """序列化消息为JSON字符串 - 处理UUID和datetime"""
        serializable = {
            "id": msg.id,
            "message_id": str(msg.message_id),
            "session_id": msg.session_id,
            "seq_num": msg.seq_num,
            "role": msg.role,
            "content": msg.content,
            "tokens": msg.tokens,
            "metadata": msg.metadata,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        return json.dumps(serializable)

    # === 锁管理 ===

    async def acquire_lock(self, session_id: str, ttl: int = None) -> str:
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

    async def run_with_lock(self, session_id: str, func, *args, **kwargs):
        """在会话锁保护下执行函数, 自动获取和释放锁"""
        lock_value = await self.acquire_lock(session_id)
        try:
            return await func(*args, **kwargs)
        finally:
            await self.release_lock(session_id, lock_value)


def create_session_service(redis_client, pg_pool) -> SessionService:
    """创建会话服务实例"""
    return SessionService(redis_client, pg_pool)
