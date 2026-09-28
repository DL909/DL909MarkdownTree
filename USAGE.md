# dl909markdowntree 使用文档

> 适用版本：2.0.1 ｜ 要求 Python ≥ 3.12

树状 Markdown 文档解析与读写控制库。将 Markdown 文本解析为带层级的节点树，支持编号、折叠、属性 FrontMatter，以及基于节点树继承的细粒度权限控制。

---

## 目录

1. [安装](#1-安装)
2. [核心概念](#2-核心概念)
3. [快速开始](#3-快速开始)
4. [基础 Markdown 文件节点](#4-基础-markdown-文件节点)
5. [编号文件节点](#5-编号文件节点)
6. [可折叠文件节点](#6-可折叠文件节点)
7. [属性（FrontMatter）文件节点](#7-属性frontmatter文件节点)
8. [文件夹节点（.mdf / .mdp）](#8-文件夹节点mdf--mdp)
9. [节点树通用操作](#9-节点树通用操作)
10. [权限控制](#10-权限控制)
11. [内置工具与 AI 集成](#11-内置工具与-ai-集成)
12. [异常一览](#12-异常一览)
13. [常见问题与已知限制](#13-常见问题与已知限制)
14. [API 速查](#14-api-速查)

---

## 1. 安装

```bash
pip install dl909markdowntree

# 可选功能扩展
pip install "dl909markdowntree[langchain]"   # LangChain 工具集
pip install "dl909markdowntree[mcp]"         # MCP 服务器
pip install "dl909markdowntree[all]"         # 全部扩展

# 使用 uv
uv add dl909markdowntree
```

依赖：`lxml`、`pydantic`、`pydantic-yaml`。

---

## 2. 核心概念

### 2.1 节点树

一份 Markdown 文档被解析为一棵树：

- **根节点**：一个 `level=0` 的占位标题节点，不输出自身标题，其子节点是文档中的一级标题与正文。
- **标题节点**：`level` 对应 `#` 的数量（1–6），`title` 为标题文字。
- **正文节点**：`PlainTextNode`，存放标题与子标题之间的普通文本。

```
根节点 (level=0)
├── PlainTextNode        # 首个标题之前的正文（前言）
├── 标题节点 (level=1)：# 1. 第一章
│   ├── PlainTextNode    # 第一章的正文
│   └── 标题节点 (level=2)：## 1.1. 小节
└── 标题节点 (level=1)：# 2. 第二章
```

所有节点都继承自 `Node`，具备 `parent` / `children` 属性以及统一的树操作（见第 9 节）。

### 2.2 类层次与能力递进

```
Node
├── TextNode（可 get_text / set_text）
│   └── PlainTextNode
└── FileNode（绑定 file_path，可 save / reload）
    ├── PlainTextFileNode
    └── MarkdownTextFileNode                      # 基础 Markdown
        ├── NumberedMarkdownTextFileNode          # + 标题编号
        │   └── FoldableMarkdownTextFileNode      # + 折叠
        │       └── AttributedMarkdownTextFileNode[T]  # + FrontMatter 属性
        └── BasicAttributedMarkdownTextFileNode[T]      # + FrontMatter 属性（不编号不折叠）

NumberedMarkdownFolderNode                         # + 文件夹存储（.mdp 分片）
└── FoldableMarkdownFolderNode                     # + 折叠状态持久化
    └── AttributedMarkdownFolderNode[T]            # + FrontMatter.yaml
```

标题侧是**真**的递进依赖：折叠状态以编号定位，所以 `MarkdownTitleNode` →
`NumberedMarkdownTitleNode` → `FoldableMarkdownTitleNode` 只能逐层加。

文件侧不是。FrontMatter 只是在正文前拼一段 YAML，与编号、折叠毫无关系，
所以它是可横切的 mixin——想要哪几项能力，自己拼即可，不必被动接受整条链。
唯一还没有横切的是「文件夹」：`.mdp` 分片的文件名 `N_title.mdp` 直接硬依赖编号。

每一层都包含上一层的全部能力，按需求选择：

| 需求 | 推荐类型 |
| --- | --- |
| 解析普通 Markdown（`# 标题`） | `MarkdownTextFileNode` |
| 标题自动编号（`# 1. 标题`） | `NumberedMarkdownTextFileNode` |
| 大文档按标题折叠显示 | `FoldableMarkdownTextFileNode` |
| 需要 YAML FrontMatter 元数据 | `AttributedMarkdownTextFileNode[T]` |
| 需要 FrontMatter 但标题不编号也不折叠 | `BasicAttributedMarkdownTextFileNode[T]` |
| 一本书拆分为多个 `.mdp` 文件 | `NumberedMarkdownFolderNode` |
| 折叠 + 文件夹 | `FoldableMarkdownFolderNode` |
| 属性 + 折叠 + 文件夹 | `AttributedMarkdownFolderNode[T]` |

### 2.3 存储约定

| 后缀 / 文件 | 含义 |
| --- | --- |
| `.md` | 普通 Markdown 文件（文本文件节点） |
| `.mdf` | Markdown 文件夹（约定俗成，非强制） |
| `N_标题.mdp` | 文件夹中一级编号节的分片文件 |
| `0.mdp` | 文件夹中的前言（根级正文） |
| `FrontMatter.yaml` | 属性文件夹节点的元数据 |
| `fold_state.json` | 可折叠文件夹节点的折叠状态（自动生成） |

---

## 3. 快速开始

```python
from pydantic import BaseModel
from dl909markdowntree import AttributedMarkdownTextFileNode

class DocAttr(BaseModel):
    author: str = "anonymous"
    tags: list[str] = []

# 文件不存在时自动创建；存在时自动解析
doc = AttributedMarkdownTextFileNode(
    file_path="notes/doc.md",
    attribute_type=DocAttr,
)

doc.set_text(
    "# 1. 概述\n"
    "这是第一章的正文。\n"
    "## 1.1. 背景\n"
    "一些背景说明。\n"
    "# 2. 结论\n"
    "结束。"
)

doc.attribute.author = "DL909"
doc.save()          # 写回 FrontMatter + 完整 Markdown（不含折叠标记）
doc.reload()        # 从磁盘重新加载

root = doc.get_root_title()
chapter = root.recursive_find_title_node_by_name("# 1. 概述")
print(chapter.title)              # 概述
print(chapter.number)             # [1]
print(doc.get_text())
```

注意：**编号 / 折叠 / 属性三类节点要求标题必须带编号**（`# 1. 标题`），
否则解析时抛出 `InvalidNumberedTitleLineError`；
只有普通 `MarkdownTextFileNode` 接受无编号标题（`# 标题`）。

---

## 4. 基础 Markdown 文件节点

### 4.1 创建与加载

```python
from dl909markdowntree import MarkdownTextFileNode

doc = MarkdownTextFileNode("notes/plain.md")
# 文件不存在 -> 自动创建空文件并解析为空树
# 文件已存在 -> 读取并解析

MarkdownTextFileNode.create_file("notes/plain.md")   # 静态方法：仅创建（已存在则清空），无返回值
doc = MarkdownTextFileNode("notes/plain.md")          # 加载刚创建的文件
```

`create_file(file_path)` 会自动创建缺失的父目录；若目标已存在则**清空重写**。

### 4.2 解析规则

- 仅识别行首、顶格的 `#` 到 `######`（`#` 后必须有一个空格且标题非空）为标题；
- 三个及以上反引号（`` ` ``）或波浪号（`~`）的围栏代码块内的 `#` 行不会被解析为标题；
- 形如 `# ` / `## ` 的空标题行（CommonMark 本就不认为是标题）按**普通正文**保留，
  并输出一条 warning，而不是让整篇文档解析失败；
- 代码块未闭合时抛出 `UnclosedCodeBlockError`；
- 标题层级必须比父标题更深，否则抛出 `InvalidTitleLevelError`；
- 同一标题下的连续正文会合并为同一个 `PlainTextNode`。

> `from_line()` 是"解析这一行"的显式 API，行为比整篇解析更严格：空标题行、
> `##` 后面直接换行、行首带缩进等一律抛 `InvalidMarkdownLineError`。
> 整篇解析的容错只作用于 `set_text()` / `from_text()`。

### 4.3 常用操作

```python
doc.set_text("# 第一章\n正文\n## 小节\n更多正文")
doc.get_text()                     # 整篇 Markdown 文本
doc.get_root_title()               # level=0 根标题节点

root = doc.get_root_title()
chapter = root.children[0]                      # 一级标题节点
section = root.recursive_find_title_node_by_name("## 小节")
section.get_title()                             # "## 小节"
section.get_title(show_level_sign=False)        # "小节"
chapter.add_text("追加一段正文")                 # 追加到该标题末尾
doc.save()
```

`recursive_find_title_node_by_name` 需要传入**带 `#` 的完整标题**（可带结尾换行），
如 `"## 1.1. 小节"`；找不到返回 `None`。

---

## 5. 编号文件节点

标题格式为 `# 1. 标题`、`## 1.1. 标题`，解析时对照父节点自动校验并纠正编号。

```python
from dl909markdowntree import NumberedMarkdownTextFileNode

doc = NumberedMarkdownTextFileNode("notes/numbered.md")
doc.set_text("# 9. 错误编号\n## 8.8. 子标题\n正文")
print(doc.get_text())
# # 1. 错误编号
# ## 1.1. 子标题
# 正文
```

默认开启自动纠正（`auto_correct=True`）：编号不符时写日志警告并纠正；
关闭后编号不符抛出 `IncorrectNumberError`，标题行缺少编号段则抛出
`InvalidNumberedTitleLineError`。

```python
from dl909markdowntree import NumberedMarkdownTitleNode, IncorrectNumberError

node = NumberedMarkdownTitleNode(
    level=1, title="测试", number=[1], auto_correct=False
)
try:
    node.set_text("## 1.9. 子标题")     # 期望 [1, 1]，实际 [1, 9]
except IncorrectNumberError:
    print("编号错误")
```

关闭整个文件节点的自动纠正：

```python
doc = NumberedMarkdownTextFileNode("notes/numbered.md")
doc.markdown_text_node.auto_correct = False
```

> 注意：`reload()` 会用默认参数（`auto_correct=True`）重建节点树，
> 关闭状态会丢失，需要在 `reload()` 后重新设置。

编号节点上的 `title` 属性只含标题文字，`number` 是 `list[int]`；
`get_title()` 输出带编号的完整标题，例如 `"## 1.1. 小节"`。

---

## 6. 可折叠文件节点

在编号节点基础上提供按标题折叠的能力：折叠状态下只显示标题与统计标记，
保存时始终写入完整内容（折叠标记永远不会落盘）。

### 6.1 折叠模式

```python
from dl909markdowntree import FoldMode

FoldMode.SHOW_TITLE    # 折叠：仅显示本标题，正文/子标题以标记代替
FoldMode.SHOW_CHILD    # 展开：显示正文与全部子标题
```

- 一级及以下标题默认为 `SHOW_TITLE`；
- 根节点（`level=0`）固定为 `SHOW_CHILD`；
- `set_text()` 成功后保留当前折叠模式。

### 6.2 读取

```python
from dl909markdowntree import FoldableMarkdownTextFileNode

doc = FoldableMarkdownTextFileNode("notes/book.md")
doc.set_text("# 1. 第一章\n正文\n## 1.1. 小节\n更多内容")

doc.get_root_title().get_text()
# '# 1. 第一章 [text folded] [1 child title folded]\n'

doc.get_root_title().get_text(with_fold_info=False)   # 不含折叠标记
# '# 1. 第一章\n'

doc.get_text()                            # 恒为完整内容，与折叠状态无关
# '# 1. 第一章\n正文\n## 1.1. 小节\n更多内容'
```

**文件节点只在内容层工作**：`get_text()` 零参数、永远返回完整正文，折叠状态不影响
落盘与读取。折叠视图属于阅读视角，请从根标题节点取——`doc.get_root_title().get_text()`。

折叠标记格式：`[text folded]`（存在被折叠正文）、`[N child title folded]`
（被折叠的子标题数，超过 10 显示 `[10+ child title folded]`）。

### 6.3 展开

```python
root = doc.get_root_title()
chapter = root.recursive_find_title_node_by_name("# 1. 第一章")

chapter.unfold()                    # 展开单个节点；父节点处于折叠态时抛
                                    # InvalidNodeOperationError
chapter.recursive_unfold()          # 展开自身与所有后代
chapter.recursive_up_unfold()       # 展开自身与所有祖先
root.unfold_by_depth(2)             # depth 从自身计起（1 仅自身，2 含一层子节点）；
                                    # 0 不展开；负数抛 RuntimeError
```

### 6.4 查找

```python
root.recursive_find_title_node_by_name("## 1.1. 小节")
root.recursive_find_title_node_by_name("## 1.1. 小节", within_shown=True)
# within_shown=True 时只搜索"当前可见"（未折叠）的后代
```

### 6.5 保存

```python
doc.save()        # 写磁盘时自动使用 full_text=True，折叠标记不落盘
```

**折叠状态只存在于内存中。** 单个 Markdown 文件的折叠态既不写进文件，也不另存
旁挂文件，因此**新建一个节点对象再打开同一个文件，看到的永远是默认的
`SHOW_TITLE` 折叠模式**。这是有意保留的限制：折叠态是编辑视图的临时状态，
和正文一起序列化会在每次折叠切换时都改动文件，徒增 diff 噪声。

需要跨会话保留折叠态时，请使用 `FoldableMarkdownFolderNode`——文件夹节点会把
折叠态落到目录下的 `fold_state.json`（见 [8.2](#82-可折叠文件夹)）。
如需在单个文件上达到同样效果，得自行在文件外维护状态并在 `reload()` 后回填
`fold_mode`。

---

## 7. 属性（FrontMatter）文件节点

用 Pydantic 模型描述元数据，以 YAML FrontMatter 形式存储：

```markdown
---
author: DL909
tags:
  - demo
---
# 1. 标题
正文
```

```python
from pydantic import BaseModel
from dl909markdowntree import AttributedMarkdownTextFileNode

class DocAttr(BaseModel):
    author: str = "anonymous"
    tags: list[str] = []

doc = AttributedMarkdownTextFileNode(
    file_path="notes/doc.md",
    attribute_type=DocAttr,
    attribute=None,          # 可选：直接传入属性实例（优先于文件内容）
    auto_correct=True,       # 可选：编号自动纠正
    markdown_text_node=None, # 可选：直接传入已解析的标题树（仅更新内存，需调用 save() 写盘）
)

doc.attribute.author             # 读取
doc.attribute.author = "DL909"   # 修改
doc.save()                       # 写回 FrontMatter + 完整正文
doc.reload()                     # 重新读取两者
```

`create_file` 静态方法：

```python
AttributedMarkdownTextFileNode.create_file(
    "notes/new.md", attribute_type=DocAttr,
    attribute=DocAttr(author="DL909"),   # 省略则使用模型默认值
)
```

- FrontMatter 必须由独立的 `---` 行包裹，缺失时抛 `MarkdownTreeError`；
- 允许空 FrontMatter（`---\n---`），此时使用模型默认值；
- `save_to_file(path)` 与 `save()` 都写出 `FrontMatter + 完整 Markdown`。

### 7.1 非编号、非折叠的带属性文档

`AttributedMarkdownTextFileNode` 面向编号 + 折叠 + 属性的文档。只需要
FrontMatter、标题既不重编号也不折叠时用 `BasicAttributedMarkdownTextFileNode`，
用法完全一致：

```python
from dl909markdowntree import BasicAttributedMarkdownTextFileNode

doc = BasicAttributedMarkdownTextFileNode[NoteAttr](
    file_path=Path("note.md"), attribute_type=NoteAttr
)
doc.set_text("# 随记\n随手写点什么")
doc.save()               # 写出 ---\n<yaml>---\n# 随记\n随手写点什么
print(doc.get_text())    # '# 随记\n随手写点什么'
```

它只满足 `MarkdownTextFileBase` 与 `AttributedMarkdownTextFileBase`，
**不**满足 `FoldableMarkdownTextFileBase`——`fold_mode`、`unfold_by_depth`
这类方法正确地不存在，不会静默失效。

两者的 FrontMatter 形态相同（`.md` 正文前缀）；差别只在标题节点能力。
文件夹则用另一种形态：属性写在同目录的独立 `FrontMatter.yaml` 里。

---

## 8. 文件夹节点（.mdf / .mdp）

当文档很大时，可把一个文档拆成一个目录：目录中的每个 `.mdp` 文件保存一个
一级编号节，文件名格式为 `N_标题.mdp`；`0.mdp` 保存第一个一级标题之前的正文。

```
book.mdf/
├── 0.mdp            # 前言（可选），如 "Preface text"
├── 1_概述.mdp       # 对应 "# 1. 概述"，文件内容为节内正文（## 及以下）
├── 2_结论.mdp       # 对应 "# 2. 结论"
└── fold_state.json  # 可折叠文件夹的折叠状态（save 时自动生成）
```

目录中的`.mdp`文件**不包含**自身的一级标题行，只保存节内内容：

```markdown
## 1.1. 小标题
内容……
```

无法匹配 `N_标题.mdp` 的 `.mdp` 文件会抛出 `InvalidMdpFilenameError`；
非 `.mdp` 文件被忽略。

### 8.1 读取与修改

```python
from pathlib import Path
from dl909markdowntree import NumberedMarkdownFolderNode

doc = NumberedMarkdownFolderNode(Path("book.mdf"))
doc.get_text()      # 合成整本书的 Markdown（含 "# N. 标题" 行与前言）
doc.set_text(...)   # 整体替换节点树
doc.save()          # 按节点树写回目录
doc.reload(auto_correct=False)   # 重新扫描目录；可显式控制编号纠正
```

`save()` 的行为：

- 每个一级编号子节点写出为 `N_标题.mdp`（标题更名为文件重命名）；
- 被删除的节点（`deprecated=True` 并 `update()`）对应文件删除；
- 同编号的重复文件被清理，重命名不会静默覆盖同名文件；
- 文件名中的非法字符（`\ / : * ? " < > |` 与控制字符）替换为 `_`，
  消毒后为空则回退为 `untitled`；
- 前言写入 `0.mdp`，无前言时删除既有 `0.mdp`；
- 一级节之后的非节内容会导致 `RuntimeError`。

### 8.2 可折叠文件夹

```python
from pathlib import Path
from dl909markdowntree import FoldableMarkdownFolderNode

doc = FoldableMarkdownFolderNode(Path("book.mdf"))
doc.get_text()                          # 完整内容（恒为完整，不受折叠影响）
doc.get_root_title().get_text()         # 折叠视图
doc.get_root_title().unfold_by_depth(2)   # depth 从自身计起，2 = 自身 + 一级子标题
doc.save()                           # 同时写出 fold_state.json
```

`fold_state.json` 记录非默认折叠状态，键为 `[level, *number]` 的 JSON：

```json
{
  "[1, 1]": "SHOW_CHILD"
}
```

`reload()` 时自动恢复；文件损坏时记录警告并忽略。

### 8.3 属性文件夹

```python
from pydantic import BaseModel
from dl909markdowntree import AttributedMarkdownFolderNode

class BookAttr(BaseModel):
    title: str = "未命名"
    author: str = "anonymous"

book = AttributedMarkdownFolderNode(
    file_path=Path("book.mdf"),   # 文件夹节点建议统一传 Path
    attribute_type=BookAttr,
)
book.attribute.author = "DL909"
book.save()        # 写出 .mdp 分片 + FrontMatter.yaml
book.reload()      # 分别重新加载两者
```

属性存放在目录下的 `FrontMatter.yaml`。若该文件缺失（如手工创建的目录），
使用模型默认值。文件夹节点与文件节点一样，`get_text()` 只在内容层工作、
恒返回完整正文；折叠视图请用 `get_root_title().get_text()`。

---

## 9. 节点树通用操作

所有节点都支持：

```python
node.parent          # 父节点；根为 None
node.children        # 子节点列表
node.deprecated      # 标记为待删除

node.addchild(child) # 加入子节点（只能加入孤儿节点，否则 InvalidNodeOperationError）
node.dispatch()      # 脱离父节点，变为孤儿节点
node.update()        # 递归更新；移除子树中 deprecated=True 的节点，返回自身
node.from_self(**overrides)  # 浅拷贝自身并可覆盖属性
```

标题节点的 `addchild` 有额外语义：

- 加入 `PlainTextNode`：与末尾正文合并；若末尾是标题则递归加入最深层；
- 加入标题节点：层级必须比当前节点更深（否则 `InvalidTitleLevelError`），
  并自动挂到合适的位置（末尾子标题链的最深处）；
- 编号节点加入子标题时会校验/纠正编号。

删除一个节（如从文件夹文档中删掉"第 2 章"）：

```python
root = doc.get_root_title()
root.children[1].deprecated = True
root.update()      # 节点被移除，parent 置空
doc.save()         # 文件夹节点会删除对应的 2_xxx.mdp
```

`str(node)` 等价于 `node.get_text()`。

---

## 10. 权限控制

### 10.1 权限级别

```python
from dl909markdowntree import Permission

Permission.DENY        # 0  不可读写
Permission.READ        # 1  可读不可写
Permission.READ_WRITE  # 2  可读可写
Permission.NONE        # 3  跳过权限检查（仅用于工具声明）
```

数值越大权限越高，比较时使用数值。

### 10.2 继承规则

- 权限表为空 → 全部默认 `READ_WRITE`；
- 权限表非空 → 从目标节点沿父链（或标题路径）向上查找：
  - 命中 `DENY` 立即拒绝（DENY 绝对生效，无法被祖先的高权限覆盖）；
  - 否则取最近的非 DENY 条目；
  - 一路到根仍未命中 → 默认 `DENY`。

`check_permission(node, required)` 返回 `(是否通过, 错误消息)`。
`node=None` 表示根节点。`required=Permission.NONE` 时永远通过。

### 10.3 两种检查器

**NodePermissionChecker**——以节点对象身份为键：

```python
from dl909markdowntree import NodePermissionChecker, Permission

node = doc.get_root_title().recursive_find_title_node_by_name("# 1. 概述")
checker = NodePermissionChecker([
    (None, Permission.READ_WRITE),   # 根：所有节点默认读写
    (node, Permission.READ),         # "# 1. 概述" 及其后代只读
])
checker.check_permission(node, Permission.READ_WRITE)
# (False, "权限不足：节点'概述'需要READ_WRITE权限，但当前对该节点的权限为READ")
checker.set_permissions([(node, Permission.READ_WRITE)])   # 整体替换权限表
```

> `reload()` 会重建节点树，旧节点对象失效，权限条目随之失效，需要重新登记。

**TitlePathPermissionChecker**——以标题路径为键，`reload()` 后依旧有效：

```python
from dl909markdowntree import TitlePathPermissionChecker, Permission

# 登记节点对象（立即解析为路径）
checker = TitlePathPermissionChecker([(node, Permission.READ)])

# 或直接登记路径：从根标题到目标的完整标题元组（带 # 与编号）
checker = TitlePathPermissionChecker([
    (None, Permission.READ_WRITE),                      # 根：其余节点默认读写
    (("# 1. 概述", "## 1.1. 背景"), Permission.DENY),   # 该节禁止访问
])

# 未命中任何条目且无根条目时，默认 DENY
```

> 权限表非空时，务必为根节点（`None`）登记默认权限，否则未列出的节点一律 DENY。

- 路径元素为 `get_title()` 的输出，如 `"# 1. 概述"`、`"## 1.1. 背景"`；
- 根节点统一用 `None` 或空元组 `()` 表示；
- 非标题节点（文件节点等）也视为根节点。

---

## 11. 内置工具与 AI 集成

`extra.tools` 提供 6 个通用 Markdown 编辑工具，LangChain 与 MCP 集成共享同一套实现。

### 11.1 目标标题匹配

`target` 必须是**完整标题**（含 `#` 与编号），例如 `"# 1. 概述"`、`"## 1.1. 背景"`；
编号节点不可省略编号。找不到时返回 `"... failed: no title matching ..."`。

### 11.2 工具列表

```python
from dl909markdowntree.extra.tools import (
    read_tool, replace_tool, append_tool,
    unfold_tool, replace_lines_tool, rename_title_tool,
)

read_tool(doc, checker, target=None)                 # 读全文或某个标题节
replace_tool(doc, checker, target, replace_text)     # 整节替换（可同时改标题）
append_tool(doc, checker, target, append_text)       # 追加正文
unfold_tool(doc, checker, target)                    # 展开并返回完整内容
replace_lines_tool(doc, checker, target, old_lines, new_lines)  # 行级替换
rename_title_tool(doc, checker, target, new_title_name)         # 仅改标题文字
```

行为约定：

- 写操作成功后自动 `save()`；
- 保存失败（`MarkdownTreeError` / `OSError` / `RuntimeError`）会回滚内存修改并返回失败消息；
- 权限不足时抛出 `PermissionError`：LangChain 工具会捕获并转为返回文本；
  MCP 服务不捕获，由 fastmcp 抛出 `ToolError`；
- `replace_lines_tool` 要求精确匹配唯一一处；匹配不到时按行窗口做模糊匹配，
  相似度 ≥ 80% 才替换；匹配到多处时要求提供更多上下文；
- `read_tool` 返回的是当前**折叠视图**；展开请用 `unfold_tool`。

### 11.3 LangChain

```bash
pip install "dl909markdowntree[langchain]"
```

```python
from dl909markdowntree.extra.langchain import MarkdownTreeToolkit

toolkit = MarkdownTreeToolkit(doc, checker=None)   # checker 省略则不检查权限
tools = toolkit.get_tools()                        # 6 个 langchain BaseTool
# 工具名：read / replace / append / unfold / replace_lines / rename_title
```

几个容易踩的点：

- **工具一律返回字符串**，失败时是 `"<动作> failed: <原因>"`，不是抛异常；
  唯一会抛的是 `PermissionError`（权限被拒）。
- **`unfold` 需要写权限**（`READ_WRITE`）：它会改写 `fold_mode` 并 `save()`，
  对文件夹节点还会落盘 `fold_state.json`，属于写操作而非读操作。
- **`rename_title` 拒绝空标题和含换行的标题**。标题文本会被原样拼进
  `# <编号> <标题>` 这一行，含换行就能凭空造出新的标题节点。
  行首带 `#` 是**允许**的——它只会让标题文本本身以 `#` 开头。
- **`replace_lines` 的 `old_lines` 不能为空**：空串在任意文本中匹配无穷多次，
  工具会直接报 `old_lines is empty`。
- **`replace_lines` 先精确匹配**；匹配到多处时报 `N matches found, provide more
  context` 要求补充上下文；一处都匹配不上时按行做相似度打分，≥ 80% 才模糊替换，
  替换的是**打分选中的那个行区间**而非全文首次出现的位置。
- **写入失败会回滚内存状态**。若回滚本身也失败，会记 ERROR 日志并仍然返回
  原始错误信息，此时节点可能处于已修改状态，需要调用方自行重载。

### 11.4 MCP

```bash
pip install "dl909markdowntree[mcp]"
```

```python
from dl909markdowntree.extra.mcp import create_mcp_server

mcp = create_mcp_server(doc, checker=None)   # 返回 FastMCP 实例
mcp.run()                                    # 以 stdio 启动
```

---

## 12. 异常一览

| 异常 | 触发场景 |
| --- | --- |
| `MarkdownTreeError` | 所有自定义异常的基类 |
| `InvalidMarkdownLineError` | 无法从一行解析出合法 Markdown 标题 |
| `InvalidNumberedTitleLineError` | 无法解析出合法编号标题（缺编号/格式错） |
| `InvalidTitleLevelError` | 子标题层级不高于当前标题 |
| `UnclosedCodeBlockError` | 代码围栏未闭合 |
| `IncorrectNumberError` | 关闭 `auto_correct` 后编号仍错误 |
| `InvalidMdpFilenameError` | `.mdp` 文件名不符合 `N_标题.mdp` |
| `InvalidNodeOperationError` | 非法节点操作（加已有父节点的节点、父级折叠时展开等） |

---

## 13. 常见问题与已知限制

1. **编号/折叠/属性节点必须使用编号标题**：`# 1. 标题` 而非 `# 标题`。
   普通 `MarkdownTextFileNode` 无此限制。
2. **折叠视图不含隐藏内容**：`get_text()` 在折叠态下会把隐藏部分替换成
   `[text folded]` 一类占位符，因此在折叠节点上做 `append` 可能丢失隐藏正文、
   `replace_lines` 也匹配不到隐藏行。工具层已对写入类工具取
   `full_text=True`，但直接调节点方法时请自行注意，或先 `unfold()` /
   `recursive_up_unfold()` 展开。
3. **`create_file` 对已存在文件是清空/覆盖语义**：文本文件节点会截断文件，
   属性文件节点会重置 FrontMatter；文件夹节点只创建目录、不破坏已有内容。
4. **`PlainTextFileNode` 不会自动创建缺失文件**，构造时抛 `FileNotFoundError`，
   与其它文件节点行为不同。
5. **`NumberedMarkdownFolderNode` / `FoldableMarkdownFolderNode` 的 `file_path` 需传 `Path`**，
   传 `str` 会抛 `AttributeError`（`AttributedMarkdownFolderNode` 已内部转换）。
6. **解析器只做 CommonMark 的一个子集**，请注意以下几条：
   - 围栏代码块支持反引号与波浪号两种，缩进式代码块**不**支持
     （缩进代码块里的 `#` 行会被当成标题）；
   - 反引号围栏的 info string 里不允许再出现反引号，波浪号围栏则允许——
     这是 CommonMark 的规定，两种围栏行为**故意不同**；
   - 闭合围栏长度必须不小于开启围栏，且允许更长的闭合围栏；
   - 空标题行（`# ` / `## `）按正文保留而非报错，见 [4.2](#42-解析规则)。
7. **单文件的折叠状态不持久化**，重新打开即回到默认折叠模式；
   文件夹节点才会把它写进 `fold_state.json`，见 [6.5](#65-保存)。
8. **`reload()` 会重建节点树**：基于节点对象的 `NodePermissionChecker` 条目失效，
   需改用 `TitlePathPermissionChecker` 或重新登记；文件节点的 `auto_correct`
   自定义设置也会恢复默认。
9. **文件夹节点的 `reload()` 不接受参数**，与 `FileNode.reload()` 保持一致；
   要临时改 `auto_correct` 请用 `reload_with(auto_correct)`，它会记住该设置
   供后续 `reload()` 沿用。
10. **`Permission.NONE` 不能登记为授权值**，调用 `set_permissions()` 时会抛
    `ValueError`。它的数值高于 `READ_WRITE` 且比较用 `>=`，一旦被授权就等价于
    对该节点无条件放行；它只是"跳过权限检查"的工具声明标记。作为工具的
    `required` 参数传入时语义不变。

---

## 14. API 速查

### 文件 / 文件夹节点

| 类型 | 构造签名（关键参数） |
| --- | --- |
| `MarkdownTextFileNode` | `(file_path, markdown_text_node=None)` |
| `NumberedMarkdownTextFileNode` | 同上 |
| `FoldableMarkdownTextFileNode` | 同上 |
| `AttributedMarkdownTextFileNode[T]` | `(file_path, attribute_type, attribute=None, auto_correct=True, markdown_text_node=None)` |
| `BasicAttributedMarkdownTextFileNode[T]` | 同上 |
| `NumberedMarkdownFolderNode` | `(file_path, auto_correct=True, markdown_text_node=None)` |
| `FoldableMarkdownFolderNode` | 同上 |
| `AttributedMarkdownFolderNode[T]` | `(file_path, attribute_type, attribute=None, auto_correct=True, markdown_text_node=None)` |

公共方法：

| 方法 | 说明 |
| --- | --- |
| `create_file(...)` | 静态方法，创建（或覆盖）目标文件/目录 |
| `get_text()` | 获取完整正文。**文件 / 文件夹节点零参数且恒返回完整内容**；折叠视图用 `get_root_title().get_text(with_fold_info, full_text)` |
| `set_text(text)` | 解析文本并替换节点树 |
| `save()` / `save_to_file(path)` | 写回磁盘 |
| `reload(...)` | 从磁盘重新加载 |
| `get_root_title()` | 返回根标题节点 |
| `add_text(text)` | 在自身文本末尾追加（标题节点） |
| `recursive_find_title_node_by_name(name, within_shown=False)` | 按完整标题递归查找 |

### 标题节点属性

| 属性 / 方法 | 说明 |
| --- | --- |
| `level` / `title` | 标题层级与文字 |
| `number` | 编号列表（编号节点） |
| `auto_correct` | 是否自动纠正编号 |
| `fold_mode` | 折叠模式（折叠节点） |
| `get_title(show_level_sign=True)` | 输出标题（含 `#`、编号） |
| `unfold()` / `recursive_unfold()` / `recursive_up_unfold()` / `unfold_by_depth(n)` | 展开相关（折叠节点） |
| `from_line(line)` / `from_text(text)` | 从行 / 文本构造 |

### 权限与工具

| 名称 | 说明 |
| --- | --- |
| `Permission` | `DENY` / `READ` / `READ_WRITE` / `NONE` |
| `NodePermissionChecker(permissions)` | 基于节点对象的检查器（reload 后失效） |
| `TitlePathPermissionChecker(permissions)` | 基于标题路径的检查器（reload 后有效） |
| `check_permission(node, required)` | 返回 `(bool, str)` |
| `MarkdownTreeToolkit(doc, checker).get_tools()` | LangChain 6 工具 |
| `create_mcp_server(doc, checker)` | FastMCP 服务器 |
