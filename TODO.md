# TODO

## 待修复问题

（无）

## 文档不一致（USAGE.md）

- **§4.1**：`doc = MarkdownTextFileNode.create_file(...)` 中 `create_file` 返回 `None`，示例将 `None` 赋给 `doc`。
- **§7**：称 `AttributedMarkdownTextFileNode` 的 `markdown_text_node` 参数"会立即写盘"；实测构造后磁盘文件仍为
  `'---\nauthor: default\n\n---\n'`，而内存文本已是 `'# 1. Title\nbody'`（`AttributedMarkdownTextFileNode.__init__` 不保存，
  基类 `MarkdownTextFileNode` 才保存）。
- **§11.2**：称 `PermissionError` 会被"LangChain / MCP 包装层"捕获并返回文本；实际 MCP `server.py` 未捕获，
  fastmcp 会抛 `ToolError`（`tests/extra/test_mcp_server.py` 断言 `pytest.raises(ToolError, match="权限不足")`，
  覆盖 read/replace/append/unfold/replace_lines/rename_title），只有 LangChain toolkit 捕获 `PermissionError`。
- **§8.2**：`doc.get_root_title().unfold_by_depth(1)` 为无效操作（根节点恒为 `SHOW_CHILD`）。
  `tests/test_foldable_markdown_nodes.py:135-140` 定义 depth 从自身计起（`unfold_by_depth(1)` 仅展开自身，
  `(2)` 展开自身及子节点），展开 level-1 标题需传 2；§6.3 未说明 depth 从自身计数。
