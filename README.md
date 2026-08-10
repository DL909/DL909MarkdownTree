# DL909 Markdown Tree

树状 Markdown 文档解析与读写控制库。将 Markdown 文本解析为带层级的节点树，支持编号、折叠、属性 FrontMatter，以及基于节点树继承的细粒度权限控制。

## 模块设计

### 节点体系

所有节点继承自 `Node`（Pydantic BaseModel），分为三类角色：

- **TextNode** — 提供 `get_text()` / `set_text()`，是 Markdown 标题、正文等文本节点的基类。
- **FileNode** — 提供 `save()` / `reload()`，代表磁盘上的文件或文件夹。
- **PlainTextNode** — 纯文本叶节点，无子节点。

```
Node
├── TextNode
│   ├── PlainTextNode
│   ├── MarkdownTitleNode          ← # 标题，level=1..6
│   ├── MarkdownTextNode           ← 根文本，children 为标题序列
│   ├── NumberedMarkdownTitleNode  ← 带编号的标题（# 1.2.3 Title）
│   ├── FoldableMarkdownTitleNode  ← 可折叠标题（fold_mode）
│   └── FoldableMarkdownTextNode
└── FileNode
    ├── MarkdownTextFileNode       ← 包装 MarkdownTextNode，读写 .md 文件
    │   └── NumberedMarkdownTextFileNode
    │       └── FoldableMarkdownTextFileNode
    │           └── AttributedMarkdownTextFileNode[T]  ← 带 FrontMatter YAML 属性
    ├── NumberedMarkdownFolderNode         ← 管理 .mdp 文件夹（0.mdp + N_Title.mdp）
    │   └── FoldableMarkdownFolderNode
    │       └── AttributedMarkdownFolderNode[T]
    └── PlainTextFileNode
```

### Markdown 变体

| 类型 | 说明 |
|:------|:------|
| 基础 | `MarkdownTextFileNode` / `MarkdownTitleNode` — 标准 Markdown 解析，无编号 |
| 带序号 | `NumberedMarkdownTextFileNode` / `NumberedMarkdownTitleNode` — 标题含 `# 1.2.3 Title` 格式编号 |
| 可折叠 | `FoldableMarkdownTextFileNode` / `FoldableMarkdownTitleNode` — `fold_mode` 控制子标题是否展开，`get_text(with_fold_info, full_text)` 控制输出 |
| 带属性 | `AttributedMarkdownTextFileNode[T]` / `AttributedMarkdownFolderNode[T]` — 文件头部 YAML FrontMatter，泛型 `T` 为 Pydantic 模型 |

### 文件夹节点（.mdp）

`*MarkdownFolderNode` （包含 `NumberedmarkdownFolderNode` 、`FoldableMarkdownFolderNode` 和 `AttributedMarkdownFolderNode`） 将目录作为逻辑文件管理：`0.mdp` 为序言，`N_Title.mdp` 为编号章节。`save()` 自动分发到独立文件，`reload()` 重新合成为合成文本后解析；空文件夹调用 `save()` 时仅创建目录，不生成内容文件。

### 协议（Protocols）

`protocols.py` 定义四层协议，用于类型标注和依赖倒置：

```
MarkdownTextFileProtocol
└── NumberedMarkdownTextFileProtocol
    └── FoldableMarkdownTextFileProtocol
        └── AttributedMarkdownTextFileProtocol[T]
```

### 权限控制

`PermissionChecker` 沿节点树向上继承，根据 `[(node, Permission), ...]` 列表检查有效权限：

- `DENY` — 不可读写
- `READ` — 可读不可写
- `READ_WRITE` — 可读可写
- 列表为空 → 默认 `READ_WRITE`；列表非空但未命中 → 默认 `DENY`

## 快速使用

```python
from pathlib import Path
from dl909markdowntree import MarkdownTextFileNode, FoldableMarkdownTextFileNode, AttributedMarkdownTextFileNode
from dl909markdowntree import Permission, PermissionChecker

# 基础：读写标准 Markdown（文件不存在时自动创建空文件）
node = MarkdownTextFileNode(Path("doc.md"))
# set_text() 设置节点存储的markdown文本。注意连续的换行将在解析式被去除。
node.set_text("# Hello\n\n\nSome text.")
# get_text() 返回不带末尾换行的纯 Markdown 文本
print(node.get_text()) # "# Hello\n\nSome text."
node.save()

# 带编号（auto_correct 默认 True，自动纠正编号；传 False 需手动保证编号正确）
from dl909markdowntree import NumberedMarkdownTextFileNode
numbered = NumberedMarkdownTextFileNode(Path("numbered.md"))
numbered.set_text("# Chapter 1\n\nContent.")

# 可折叠
foldable = FoldableMarkdownTextFileNode(Path("fold.md"), auto_correct=True)
# recursive_find_title_node_by_name 参数需包含 "# " 前缀
foldable.recursive_find_title_node_by_name("# 1. Introduction").unfold()

# 带属性（泛型）—— 属性类建议提供默认值，否则创建文件时需传入 attribute
from pydantic import BaseModel
class FrontMatter(BaseModel):
    title: str = "Untitled"
    author: str = "Anonymous"

attributed = AttributedMarkdownTextFileNode(Path("post.md"), attribute_type=FrontMatter)
print(attributed.attribute.title)
# 或创建时传入自定义 attribute
custom_attr = FrontMatter(title="My Post", author="Alice")
# 若文件存在，这将会覆写原始的attribute
attributed2 = AttributedMarkdownTextFileNode(Path("post2.md"), attribute_type=FrontMatter, attribute=custom_attr)

# 文件夹
from dl909markdowntree import NumberedMarkdownFolderNode
folder = NumberedMarkdownFolderNode(Path("my_doc/"))
folder.save()  # 分发为 0.mdp + N_Title.mdp

# 权限
checker = PermissionChecker([(some_title_node, Permission.READ)])
ok, msg = checker.check_permission(some_title_node, Permission.READ_WRITE)
```

### create_file

每个文件/文件夹节点均提供 `create_file` 静态方法，用于手动初始化磁盘上的空文件或空文件夹：

```python
# 文件节点
MarkdownTextFileNode.create_file(Path("doc.md"))
NumberedMarkdownTextFileNode.create_file(Path("numbered.md"))
FoldableMarkdownTextFileNode.create_file(Path("fold.md"))
AttributedMarkdownTextFileNode.create_file(Path("post.md"), attribute_type=FrontMatter)
# 带自定义属性创建
AttributedMarkdownTextFileNode.create_file(Path("post.md"), attribute_type=FrontMatter, attribute=custom_attr)

# 文件夹节点
NumberedMarkdownFolderNode.create_file(Path("my_doc/"))
FoldableMarkdownFolderNode.create_file(Path("foldable_doc/"))
AttributedMarkdownFolderNode.create_file(Path("attr_doc/"), attribute_type=FrontMatter, attribute=custom_attr)
```

`__init__` 在目标文件/文件夹不存在时会自动调用对应的 `create_file`，因此以下两种写法等价：

```python
node = MarkdownTextFileNode(Path("doc.md"))          # 自动创建
MarkdownTextFileNode.create_file(Path("doc.md"))
node = MarkdownTextFileNode(Path("doc.md"))          # 文件已存在，直接读取
```

## 安装

```bash
uv sync          # 开发环境（含 pytest / pyright / ruff）
# 或
pip install -e .
```

要求 Python >= 3.12。

## Extra

### MCP Server

```python
from pathlib import Path
from dl909markdowntree import MarkdownTextFileNode
from dl909markdowntree.extra.mcp import create_mcp_server

node = MarkdownTextFileNode(Path("doc.md"))
server = create_mcp_server(node)
server.run()  # stdio 模式
```

`create_mcp_server` 返回一个 `FastMCP` 实例，暴露 `read` / `replace` / `append` / `unfold` / `replace_lines` / `rename_title` 六个工具。支持可选的 `permissions` 参数，传入 `PermissionChecker` 权限列表。

安装可选依赖：

```bash
pip install "dl909markdowntree[mcp]"
```

### LangChain BaseToolKit

```python
from pathlib import Path
from dl909markdowntree import MarkdownTextFileNode
from dl909markdowntree.extra.langchain import MarkdownTreeToolkit

node = MarkdownTextFileNode(Path("doc.md"))
toolkit = MarkdownTreeToolkit(node)
tools = toolkit.get_tools()  # list[BaseTool]，6 个工具
```

每个工具都带有 `args_schema`（Pydantic 模型），可直接用于 LangChain Agent 或 Chain。支持可选的 `permissions` 参数。

安装可选依赖：

```bash
pip install "dl909markdowntree[langchain]"
```

全部 Extra：

```bash
pip install "dl909markdowntree[all]"
```

## 开发

```bash
uv run pytest -q        # 测试
uv run ruff check src/  # lint
uv run pyright src/     # 类型检查
```
