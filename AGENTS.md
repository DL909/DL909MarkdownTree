# AGENTS.md

`dl909markdowntree` — 树状 Markdown 解析与读写控制库（Python >= 3.12，src 布局，uv 管理）。文档/注释以中文为主，代码标识符用英文。

## 命令

```bash
uv sync                                   # 安装 dev 依赖（pytest/ruff/pyright/pdbpp/pyfakefs）
uv run pytest -q                          # 全部测试（约 276 个，秒级完成）
uv run pytest tests/test_xxx.py           # 单个测试文件
uv run ruff check src/                    # lint（只查 src/，不含 tests/）
uv run pyright src/                       # 类型检查（pyright 已在 dev 组，无需单独安装）
```

- 无 CI、无 pre-commit、无 opencode.json，本地手工验证。
- `pyright src/` 当前有 8 个既有错误（langchain toolkit 的 `args_schema` 覆写、`AttributedMarkdownFolderNode.create_file` 签名等），属已知存量问题。**不要对 tests/ 跑 pyright**（约 196 个误报）。改代码时应避免新增错误，但不必消除这些存量。
- 测试大部分用 pyfakefs 的 `fs` fixture（内存文件系统，无真实磁盘 I/O）；但 `tests/test_permissions.py` 与 `tests/extra/` 使用真实 `tmp_path` 写盘。整体无需任何外部服务。

## 架构

- 入口导出见 `src/dl909markdowntree/__init__.py`。四种 Markdown 变体按继承分层：基础 → `Numbered*`（`# 1.2.3 Title`）→ `Foldable*`（fold_mode）→ `Attributed*[T]`（YAML FrontMatter，泛型为 Pydantic 模型）。
- 解析逻辑集中在 `markdown_parser_core.py` 的 `_MarkdownParserCore` Mixin，子类通过重写钩子方法（`_parse_title_line`、`_create_title_node` 等）定制行为。新增变体时优先改这个核心，而不是复制主循环。
- `FolderNode` 系列把目录当逻辑文件：`0.mdp` 为序言、`N_Title.mdp` 为章节，`save()` 分发、`reload()` 合成后解析。空文件夹 `save()` 只建目录不生成内容文件。
- `protocols.py` 定义四层协议供类型标注与依赖倒置；`permissions.py` 的 `PermissionChecker` 沿树向上继承（空列表→`READ_WRITE`，非空未命中→`DENY`）。
- `extra/` 是可选集成（MCP server、LangChain toolkit），依赖 `[mcp]`/`[langchain]` extras，`uv sync` 默认不装。跑 `tests/extra/` 前需 `uv sync --all-extras` 或 `pip install -e ".[all]"`。

## 易踩的 API 约定

- 所有带编号节点 `auto_correct` 默认 `True`（自动纠正编号；传 `False` 则错误编号抛异常）。改动默认值会同时影响磁盘读写格式。
- `recursive_find_title_node_by_name()` 对带编号/可折叠节点要求传 `"# "` 前缀（如 `"# 1. Introduction"`）。
- `__init__` 在文件不存在时会自动 `create_file`，新建节点就会落盘创建空文件；对 Attributed 节点，属性模型建议提供默认值，否则需在构造时传 `attribute`。
- 每个文件/文件夹节点都有静态 `create_file()`，用于手动初始化空文件/文件夹。

## 文档冲突

- README 的「要求 Python >= 3.11」已过时，以 `pyproject.toml`（>=3.12）和 `.python-version`（3.12）为准。
- README 的 `pyright src/` 注释「需单独安装 pyright」过时，dev 组已含 pyright。
