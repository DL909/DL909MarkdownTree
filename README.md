# dl909agentframework

一个面向「树状 Markdown 文档」的轻量 Agent 框架：把 Markdown 文档解析为可折叠、带编号、
带属性的节点树，并通过 OpenAI 兼容的 function-calling 让 LLM 以工具（`read` / `replace` /
`append` / `unfold` / `replace_lines` / `rename_title`）为粒度、在带权限控制的前提下编辑文档。

## 组成

- `tree_doc/` —— 文档节点体系（`Node` 基类 + Markdown / numbered / foldable / attributed 各层），
  以及对应的 `protocols.py` 协议接口。
- `llm/` —— LLM 交互层：
  - `llm_client.py`：`call_llm`、`tool_loop`、交互式对话、面向单文件的
    `call_llm_with_edit_single_markdown_file_tool` 等封装。
  - `tools/`：`registry.py`（`@tool` 装饰器 + `ToolRegistry` / `PermissionToolRegistry`）、
    `permissions.py`（基于节点树继承的权限）、`markdown_edit_tools.py`（内置编辑工具集）、
    `context.py`（工具执行上下文）。

## 安装

```bash
uv sync          # 开发环境（含 pytest / pyright / ruff）
# 或
pip install -e .
```

要求 Python >= 3.11。

## 环境变量

运行前通过 `.env`（`setup_globals()` 会自动加载当前工作目录下的 `.env`）或进程环境提供：

| 变量 | 说明 |
| --- | --- |
| `LLM_API_KEY` | OpenAI 兼容 API key |
| `LLM_API_BASE` | API base url |
| `LLM_MODEL` | 模型名 |
| `LLM_TEMPERATURE` | 采样温度（默认 `0.8`） |
| `MAX_TOOL_LOOP` | 工具调用循环最大迭代次数（默认 `20`） |

## 最小用例

```python
from dl909agentframework.llm.initialization import setup_globals
from dl909agentframework.llm.tools.markdown_edit_tools import (
    create_markdown_edit_tools_registry,
)

setup_globals()  # 加载 .env

# 不带 permissions 时得到普通 ToolRegistry（默认全开）；
# 带 permissions 时得到 PermissionToolRegistry，声明了权限的工具会被强制检查。
registry = create_markdown_edit_tools_registry()

# 传入一个实现了 AttributedMarkdownTextFileProtocol 的文档节点，
# 让 LLM 自主读取并按需调用编辑工具，最终保存文件。
# from dl909agentframework.llm.llm_client import call_llm_with_edit_single_markdown_file_tool
# call_llm_with_edit_single_markdown_file_tool(
#     markdown_file_node=my_node,
#     system_content="你是一个文档编辑助手……",
#     user_content="把第 2 章扩写到 1000 字。",
# )
```

## 权限

`PermissionToolRegistry` 按 `[(node, Permission), ...]` 配置权限，并沿节点树向上继承：

- 权限列表为空 → 默认 `READ_WRITE`（全部允许）。
- 非空但某节点及其祖先都未命中 → 默认 `DENY`。
- `Permission`：`DENY < READ < READ_WRITE`（`NONE` 表示工具不参与权限检查）。

内置工具已声明各自所需权限（如 `replace` 需 `READ_WRITE`、`read` 需 `READ`），
在 `PermissionToolRegistry` 下会被实际强制。

## 开发

```bash
uv run pytest -q        # 测试
uv run pyright src/     # 类型检查
uv run ruff check src/  # lint
```
