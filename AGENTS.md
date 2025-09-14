% Repository Guidelines

## 项目结构与模块组织
- 核心模块：`main.py`（FastAPI 入口）、`chat_chain.py`（基于 Tongyi/DashScope 的 LangChain 流水线）、`session_manager.py`（会话/历史内存）、`api_with_session.py`（演示 API 变体）。
- 工具与脚本：`chat_client.py`（本地 CLI 调试）。
- 依赖与配置：`requirements.txt`、`.env`（本地仅，勿提交）。
- 测试：请在 `tests/` 下新增 `test_*.py`。

## 构建、运行与开发命令
- 创建虚拟环境并安装依赖：
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- 启动开发服务：`uvicorn main:app --reload`（默认 http://localhost:8000，健康检查 `/health`）。
- 备用演示服务：`python api_with_session.py`。
- 本地快速验证：`python chat_client.py`（发送示例消息）。
- 运行测试：`pytest -q`。

## 代码风格与命名规范
- Python 3.10+；遵循 PEP 8，4 空格缩进。
- 新/改代码必须添加类型注解；对公共函数/类写简洁 docstring。
- 命名：模块/函数 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE_CASE`。
- 导入顺序：标准库、第三方、本地；移除未使用导入。

## 测试指南
- 框架：`pytest`；异步路由使用 `pytest-asyncio` 与 `httpx.AsyncClient` 直接对 FastAPI 应用测试。
- 覆盖重点：`SessionManager`、`ChatChain` 单元测试；`/chat`、`/health` 及会话相关路由的最小集成测试。
- 约定：文件命名 `tests/test_*.py`；测试小而聚焦，可读性优先。

## 提交与 Pull Request
- 提交信息使用祈使语，范围单一，≤72 字符。例如：`api: handle empty history`。
- PR 仅包含一个逻辑变更；填写简介、关联 issue、示例请求/响应（curl/JSON）、以及配置变更说明。
- 行为、环境变量或端点变化需同步更新文档。

## 安全与配置
- 禁止提交密钥。必需环境变量：`DASHSCOPE_API_KEY`（本地可放入 `.env`，生产优先使用环境变量）。
- 开发环境由 `python-dotenv` 加载 `.env`。

## 贡献者提示
- 优先“小步、外科式”修改；避免无讨论的大规模重构/重命名。
- 新依赖与公开 API 变更请在 PR 描述中给出理由与影响范围。

