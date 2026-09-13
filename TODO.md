# TODO

## 待修复问题

### 1. [严重] 折叠节点上 append 会丢失隐藏内容

`extra.tools.append_tool` 调用 `FoldableMarkdownTitleNode.add_text`（继承自 `MarkdownTitleNode`），
而 `add_text` 内部使用 `self.get_text()`，对可折叠节点默认返回**折叠视图**（含
`[text folded]` / `[N child title folded]` 标记）：

```python
# MarkdownTitleNode.add_text
def add_text(self, text: str) -> None:
    self.set_text(self.get_text() + "\n" + text)
```

后果：

- 被折叠的正文与被折叠的子标题内容全部丢失；
- 折叠标记 `[text folded]` 会被当作标题文字或正文写入文件。

复现（v2.0.1）：

```python
a = AttributedMarkdownTextFileNode(file_path=p, attribute_type=Attr)
a.set_text("# 1. Title\nSecret hidden line\n## 1.1. Sub\nhidden sub content")
a.save()
append_tool(a, None, "# 1. Title", "appended line")
# 文件变为: '# 1. Title [text folded] [1 child title folded]\n\nappended line'
# 隐藏正文与 Sub 子节内容丢失
```

注意：即使父节点已展开（`fold_mode == SHOW_CHILD`），只要子树中存在处于折叠态的子节点，
`append_tool` 同样会丢失这些子节点的内容。

建议：覆写 `FoldableMarkdownTitleNode.add_text` 使用 `get_text(full_text=True)`；
或在 `append_tool` 中先 `recursive_up_unfold()` 并在追加后按需恢复折叠状态。

### 2. [严重] replace_lines 无法匹配折叠视图中的隐藏行

`extra.tools.replace_lines_tool` 基于 `node.get_text()`（折叠视图）做精确/模糊匹配，
折叠状态下隐藏正文不会出现在 `current_text` 中，只能返回
`no match found (best similarity below 80%)`。

与问题 1 同源。建议在工具层使用 `get_text(full_text=True)` 进行匹配与替换，
或在文档中明确要求先展开。

### 3. NumberedMarkdownFolderNode 不接受 str 路径

其它节点构造均会将 `file_path` 转为 `Path`（如 `MarkdownTextFileNode`），但
`NumberedMarkdownFolderNode.__init__` 直接使用传入值：

```python
NumberedMarkdownFolderNode(file_path=str(path))
# AttributeError: 'str' object has no attribute 'exists'
```

建议：构造开始时统一 `file_path = Path(file_path)`。

### 4. 代码围栏只识别反引号，不识别 `~~~` 与缩进代码块

`MarkdownTitleNode._parse_markdown` 仅用 `` ^(`{3,})([^`\n]*)\n `` 识别围栏：

```python
md.set_text("# T\n~~~\n# not a title\n~~~")
# "# not a title" 被误解析为标题
```

CommonMark 合法的 `~~~` 围栏与缩进代码块内的 `#` 行都会被误解析为标题。
建议支持 `~{3,}` 围栏（可统一抽象围栏字符与长度），并考虑缩进代码块。

### 5. unfold 工具处理非折叠节点时抛未捕获的 AttributeError

`extra.tools.unfold_tool` 直接访问 `node.fold_mode` / `node.unfold()`。
对普通 `MarkdownTextFileNode`（其标题节点为 `MarkdownTitleNode`）：

```python
unfold_tool(MarkdownTextFileNode(p), None, "# Hello")
# AttributeError: 'MarkdownTitleNode' object has no attribute 'fold_mode'
```

`AttributeError` 不在 `_TOOL_OPERATION_ERRORS` 中，也不会被 LangChain / MCP 包装层捕获，
会直接抛给调用方。建议做能力判断并返回 "unfold failed: ..."。

### 6. PlainTextFileNode 不自动创建缺失文件

`MarkdownTextFileNode`、`NumberedMarkdownTextFileNode`、`FoldableMarkdownTextFileNode`、
`AttributedMarkdownTextFileNode` 及文件夹节点在构造时都会自动创建缺失目标，
但 `PlainTextFileNode.__init__` 直接 `open(file_path, "r")`，文件不存在时抛
`FileNotFoundError`，行为不一致。

### 7. AttributedMarkdownTextFileNode FrontMatter 输出多一个空行

`to_yaml_str()` 返回值已以 `\n` 结尾，`create_file` / `save_to_file` 又拼接
`f"---\n{to_yaml_str(...)}\n---\n"`，导致结束标记前多一个空行：

```
---
author: default
tags: []

---
```

而 `AttributedMarkdownFolderNode` 的 `FrontMatter.yaml` 无此空行。解析不受影响，属外观不一致。

### 8. MarkdownTitleNode.addchild 不设置 PlainTextNode 的 parent

```python
n = MarkdownTitleNode(level=1, title="T")
p = PlainTextNode("hello")
n.addchild(p)
p.parent  # None
```

文本子节点（合并分支与新增分支）均未设置 `parent`，`dispatch()` 无法将其从父节点摘除。
标题子节点正常。目前对权限路径解析无实际影响（非标题节点视为根），但结构不完整。
