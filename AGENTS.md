# AGENTS.md

面向 OpenCode 会话的仓库工作指南。仅收录不易从文件名推断、且容易踩坑的事实。

## 开发命令

```bash
uv sync                       # 安装开发依赖（pytest / pyright / ruff）
uv run pytest -q              # 全量测试（205 项，~0.3s，无需 LLM/网络/.env）
uv run pytest tests/test_markdown_nodes.py -q   # 单文件
uv run pytest tests/test_tool_registry.py::test_tool_decorator_builds_schema_from_signature -q
uv run pyright src/           # 类型检查（只检 src/，不检 tests/）
uv run ruff check src/        # lint（只检 src/）
```

提交前建议顺序：`ruff check src/` -> `pyright src/` -> `pytest -q`。

无 CI、无 pre-commit、无 codegen 步骤。

## 包结构

- 仓库目录名拼写为 `DL909AgentFramwork`（少了 `e`），但**导入包名是 `dl909agentframework`**。两处不一致，引用代码时以包名为准。
- `src/` 布局，`pyproject.toml` 设 `pythonpath = ["src"]`，pytest 自动识别，无需手动 `PYTHONPATH`。
- 顶包 `dl909agentframework`：两个子包
  - `tree_doc/` —— Pydantic 节点树（`Node` 基类 → markdown / numbered / foldable / attributed 各层 → folder 节点）。解析走 `_MarkdownParserCore` Mixin 的 Template Method 模式，子类覆写钩子而非重写主循环。
  - `llm/` —— `llm_client.py`（OpenAI 兼容调用、`tool_loop`、交互式封装）与 `tools/`（`registry.py` + `permissions.py` + `context.py` + `markdown_edit_tools.py`）。
- `tree_doc/__init__.py` 只 re-export 了部分模块。**`markdown_folder_nodes`、`plain_text_file_node`、`markdown_parser_core` 未在 `__init__` 中导出**，需用完整路径 `from dl909agentframework.tree_doc.markdown_folder_nodes import MarkdownFolderNode` 引入。

## 工具注册与权限（容易搞错的点）

- `@tool` 装饰器自动从函数签名或 `param_model`（Pydantic）生成 JSON schema。除 `arguments` 外的形参名会从 `ToolContext` 的同名资源**按名注入**（`markdown_file_node` 等）。
- 内置 Markdown 编辑工具实际有 **6 个**：`read`、`unfold`、`replace`、`append`、`replace_lines`、`rename_title`。用 `create_markdown_edit_tools_registry(...)` 工厂创建，各 `allow_*` 开关默认全开。
- 权限三态语义（`permissions.py`）：
  - 权限列表**为空** → 全部节点默认 `READ_WRITE`（全开）。
  - 列表非空但某节点及其祖先都未命中 → 默认 `DENY`。
  - `Permission.NONE` 仅用于工具声明，表示**跳过**权限检查；普通 `ToolRegistry` 完全不检查权限，只有 `PermissionToolRegistry` 会强制。
- 节点匹配用 `is`（身份比较），不是 `==`。权限沿节点树**向上**继承。
- **工具参数中只要含 `"target"` 键**，`PermissionToolRegistry` 就会自动用它定位节点做权限检查；无 `target` 则不检查特定节点。
- `registry.py` 与 `permissions.py` 之间用**延迟导入**避免循环依赖，编辑时不要把延迟 import 提到模块顶部。
- `tool_loop` 退出时会跑 `check_list`：列表中**第一个返回非 `None` 的 check 生效**并短路，其余不执行。`default_must_use_check` 检查所有设了 `must_use_time` 的工具是否达标，未达标会把提示作为 system message 注入并继续循环。

## 运行时环境

- `setup_globals()` 从**当前工作目录**的 `.env` 加载环境变量（`initialization.py`），调用任何 LLM 工作流前需先执行。测试不依赖此项。
- 必需/可选环境变量见 `README.md`「环境变量」表：`LLM_API_KEY`、`LLM_API_BASE`、`LLM_MODEL`、`LLM_TEMPERATURE`（默认 0.8）、`MAX_TOOL_LOOP`（默认 20）。

## 兼容性约束

- `requires-python = ">=3.11"`，`.python-version` 锁 3.13.3。
- 代码刻意避免 3.12 的 `type` 语句以兼容 3.11（见 `registry.py` 顶部注释），新增类型别名用 `TypeAlias`，不要换成 `type X = ...`。
- 测试用 `pyfakefs` 做文件系统隔离（见 `tests/`），新增文件相关测试优先复用该模式，避免触碰真实磁盘。

## 文档陷阱（务必注意）

子目录的两份 README 含**过时且错误**的路径，不要照抄其中的 import：

- `src/dl909agentframework/tree_doc/README.md`：写成 `novelWriter/tree_doc/`、`from tree_doc.markdown_nodes import ...`，文末自称 "Part of the novelWriter project" —— 全部错误。
- `src/dl909agentframework/llm/tools/README.md`：示例用 `from core.tools import ...`、`from core.llm_client import tool_loop` —— 错误。两者还把测试目录写成 `test/`，实际是 `tests/`。

正确导入前缀统一为 `dl909agentframework.tree_doc.*` 和 `dl909agentframework.llm.*`（含 `llm.tools.*`、`llm.llm_client`、`llm.initialization`）。遇到 README 与代码冲突，**以代码为准**。
