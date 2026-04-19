-- 会话管理表创建脚本
-- 创建时间: 2025-03-14

-- 会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    title VARCHAR(255),
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 消息表（普通表，不分区 - 可支撑到百万级数据量）
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    message_id UUID NOT NULL,
    seq_num INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tokens INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 外键约束
    CONSTRAINT fk_session
        FOREIGN KEY (session_id)
        REFERENCES chat_sessions(id)
        ON DELETE CASCADE,
    
    -- 检查约束
    CONSTRAINT chk_role
        CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    CONSTRAINT chk_tokens_non_negative
        CHECK (tokens >= 0)
);

-- 索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_message_id 
    ON chat_messages(message_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_seq 
    ON chat_messages(session_id, seq_num);
CREATE INDEX IF NOT EXISTS idx_session_created 
    ON chat_messages(session_id, created_at);

-- 注释
COMMENT ON TABLE chat_sessions IS '聊天会话表';
COMMENT ON TABLE chat_messages IS '聊天消息表';
COMMENT ON COLUMN chat_messages.message_id IS '消息唯一ID（UUID）';
COMMENT ON COLUMN chat_messages.seq_num IS '会话内消息序号';
COMMENT ON COLUMN chat_messages.metadata IS '额外信息（如工具调用、状态等）';