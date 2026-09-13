# TODO

## 待修复问题

### 10. [严重] replace_lines 匹配到折叠标记后"成功"并清空隐藏内容

`replace_lines_tool` 在折叠视图上做匹配，用户若以可见的折叠标记 `[text folded]` 为匹配目标，
会命中并返回成功，实际却删除了被折叠的隐藏内容，且会把标记文本落盘：

```python
doc = FoldableMarkdownTextFileNode(file_path=p)
doc.set_text("# 1. Title\nsecret\n## 1.1. Sub\nhidden sub")
doc.get_root_title()  # 折叠态，视图含 "# 1. Title [text folded] [1 child title folded]"
replace_lines_tool(doc, None, "# 1. Title", "[text folded]", "[text hidden]")
# 返回 "replace_lines succeeded"（精确匹配 1 处）
doc.get_root_title().children  # []
doc.get_text(full_text=True)   # '# 1. Title [text hidden] [1 child title folded]'
doc.save()                     # 标记文本写入磁盘
```

与问题 2 不同：问题 2 是匹配不到，这里是"匹配成功并破坏数据"。
建议在 `full_text=True` 的文本上进行匹配与替换。

### 11. [中] AttributedMarkdownFolderNode 已有目录时忽略显式传入的 attribute

当目标目录及 `FrontMatter.yaml` 已存在时，构造传入的 `attribute` 会被文件内容覆盖：

```python
p.mkdir(parents=True, exist_ok=True)
AttributedMarkdownFolderNode(p, Attr, attribute=Attr(author="first"))
n2 = AttributedMarkdownFolderNode(p, Attr, attribute=Attr(author="second"))
n2.attribute.author  # 'first' —— 传入 'second' 被忽略
```

原因：`__init__` 先从文件读取 attribute，随后 `super().__init__` 调用 `self.reload()`，
而 `AttributedMarkdownFolderNode.reload` 又用 `FrontMatter.yaml` 覆盖 `self.attribute`。
`AttributedMarkdownTextFileNode` 则会保留传入的 attribute，二者行为不一致。

### 12. [中] 空 FrontMatter.yaml 使 AttributedMarkdownFolderNode 崩溃

0 字节的 `FrontMatter.yaml` 会触发 pydantic 校验错误：

```python
(p / "FrontMatter.yaml").write_text("", encoding="utf-8")
AttributedMarkdownFolderNode(p, Attr)
# pydantic ValidationError: Input should be a valid dictionary or instance of Attr, input_value=None
```

`AttributedMarkdownTextFileNode` 对空 frontmatter 有 `yaml_data.strip()` 回退到 `attribute_type()`，
而文件夹节点的 `__init__` / `reload` 直接调用 `parse_yaml_raw_as`，无空内容判断。文件缺失可回退默认值，仅空文件崩溃。

### 13. [中] AttributedMarkdownTextFileNode 缺少 get_markdown_text_node()

```python
doc = AttributedMarkdownTextFileNode(file_path=p, attribute_type=Attr)
hasattr(doc, "get_markdown_text_node")  # False
doc.get_markdown_text_node()            # AttributeError
```

`MarkdownTextFileNode` 定义了该方法（`src/dl909markdowntree/markdown_nodes.py:192`），
但 `interface.MarkdownTextFileBase` 未声明它（CHANGELOG 声称已加入 protocol），
且 `AttributedMarkdownTextFileNode` 不继承 `MarkdownTextFileNode`。
建议在接口中声明并让其返回 `self.markdown_text_node`。

### 14. [中] recursive_up_unfold() 对已展开节点提前返回，祖先仍保持折叠

`FoldableMarkdownTitleNode.recursive_up_unfold()` 在 `self` 已是 `SHOW_CHILD` 时提前返回，
不再向上传播：

```python
parent.fold_mode = FoldMode.SHOW_TITLE
child.fold_mode = FoldMode.SHOW_CHILD
child.recursive_up_unfold()
# parent.fold_mode 仍为 SHOW_TITLE
```

该状态可通过 `fold_state.json` 产生（文件只记录子节点为 `SHOW_CHILD`，父节点用默认值）。
建议无论当前状态都向上传播。

### 15. [中] 工具编辑会重置后代折叠状态（文件夹节点会持久化丢失）

工具通过 `set_text` 重建子节点，重建时不保留折叠状态；对
`FoldableMarkdownFolderNode` 该状态会随 `save()` 写入 `fold_state.json`，重开后丢失：

```python
# 1_One.mdp 下含子节点 1.1；先展开 one 与 sub
one.fold_mode = FoldMode.SHOW_CHILD
sub.fold_mode = FoldMode.SHOW_CHILD
doc.save()   # fold_state.json: {"[1,1]":SHOW_CHILD, "[2,1,1]":SHOW_CHILD}
append_tool(doc, None, "# 1. One", "extra")
doc.save()   # fold_state.json 仅剩 {"[1,1]": SHOW_CHILD}
# 重开后 sub.fold_mode == SHOW_TITLE
```

单文件 `FoldableMarkdownTextFileNode` 同样会重置（内存中 `sub` 变为 `SHOW_TITLE`）。
建议 `set_text` 后按 `[level, *number]` 路径恢复折叠状态，或原地编辑而非整体重建。

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
