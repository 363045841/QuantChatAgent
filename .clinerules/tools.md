# 测试与运行规范 (Testing Protocols)

- **禁止同步测试**: 严禁编写或执行 `python -c "finance_agent.chat(...)"` 这种同步调用脚本。由于金融工具是异步定义的，同步调用必然触发 `StructuredTool does not support sync invocation` 错误。