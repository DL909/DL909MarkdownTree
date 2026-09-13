# TODO

## 待修复问题

### 16. [低] Node.from_self 浅拷贝，共享 children 列表与 parent 引用

```python
m = MarkdownTitleNode.from_self(n)
m.children is n.children  # True
m.parent is n.parent      # True
m.children.clear()        # n.children 也被清空
```

`NumberedMarkdownTitleNode.from_self` 已显式复制 `number`
（`src/dl909markdowntree/numbered_markdown_nodes.py:66-69`），但未复制 `children`。
建议默认复制子节点列表，并将 `parent` 置为 `None`。

### 17. [低] level-0 占位节点的 get_title() 返回空白垃圾

```python
MarkdownTitleNode(level=0).get_title()          # ' '
NumberedMarkdownTitleNode(level=0).get_title()  # '  '
```

占位节点（level 0）的标题为空，但 `get_title()` 返回由空白拼出的字符串。
权限解析路径会跳过 level 0，实际影响小。建议 `level <= 0` 时直接返回 title。

### 18. [低] pyproject.toml 声明 lxml 依赖但代码未使用

`pyproject.toml` 的 `dependencies` 中声明 `lxml>=6.1.1`，但在 `src/` 与 `tests/` 中均无引用。
建议移除或在文档中说明用途。

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
