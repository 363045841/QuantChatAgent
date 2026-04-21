-- 修改 tokens 约束，允许 tokens = 0
-- 原因：用户消息的 token 数在 API 调用前未知，先存 0

-- 删除旧的检查约束（如果存在）
ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chk_tokens_positive;
ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chk_tokens_non_negative;

-- 添加新的检查约束（允许 tokens >= 0）
ALTER TABLE chat_messages ADD CONSTRAINT chk_tokens_non_negative CHECK (tokens >= 0);
