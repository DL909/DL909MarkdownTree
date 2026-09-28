# 属性 mixin 化设计规格

日期：2026-09-27
状态：待评审
影响范围：`src/dl909markdowntree/` 的文件节点与 `interface.py`，以及 `USAGE.md`、约 40 处测试调用点

> 本文中的行号对应 `a8c8b2c` 时的代码，实施时以实际代码为准。

## 1. 问题

库的继承树严格单调：文件侧是 `MarkdownTextFileNode → NumberedMarkdownTextFileNode → FoldableMarkdownTextFileNode → AttributedMarkdownTextFileNode`。结果是**无法处理「非编号、不折叠、有属性」的 Markdown 文件**——想要 FrontMatter，就必须连编号和折叠一起要。

用户提出的初步思路是把 `AttributedMarkdownTextFileNode` 进一步泛型化，允许指定其中的 `root_title` 节点类型。但这样会撞上一个两难：

- 只暴露 `MarkdownTitleNode` 的方法，则 `get_text` 的 `full_text` 等参数无法暴露；
- 始终暴露，则这些功能对 `MarkdownTitleNode` 是无效的。

## 2. 诊断

泛型化解决不了这个两难，原因有四层。

### 2.1 标题侧是真依赖链，文件侧是伪依赖链

- 标题侧 `MarkdownTitleNode → NumberedMarkdownTitleNode → FoldableMarkdownTitleNode` 是**真依赖**：折叠状态以编号定位（`fold_state.json` 的键是 `json.dumps([child.level, *child.number])`），`FoldableMarkdownTitleNode.get_text` 的分支也建立在「有 number」之上。保持单调正确，**本次不动**。
- 文件侧 `MarkdownTextFileNode → Numbered → Foldable → Attributed` 是**伪依赖**：FrontMatter 跟编号、折叠毫无关系，只是在正文前拼一段 YAML。`Attributed` 之所以挂在链顶，纯粹是当初在链顶写的这个功能。

文件侧唯一的真依赖是「拥有一个标题节点树」。编号对 `.mdp` 文件夹才是硬依赖（文件名 `N_title.mdp`），对 `.md` 文件不是。

### 2.2 `get_text` 的参数放错了层

`with_fold_info` / `full_text` 是**标题节点的渲染选项**，却被原样转发到了文件节点上。但文件的正文只有一种形态——要落盘的、要给工具做行级编辑的，永远是完整形态；折叠视图是**阅读视图**，属于标题节点。

一旦把这两个参数从文件节点上拿掉，文件节点的 `get_text()` 就是零参数、对任意标题节点类型都成立，**两难自动消失**：不存在「对 `MarkdownTitleNode` 无效的功能」，因为文件节点上本就不该有折叠功能。

### 2.3 工具层早就认为折叠是可选的

`extra/tools.py:155` 的 `unfold_tool` 里有：

```python
if not isinstance(node, FoldableMarkdownTitleBase):
    return f"unfold failed: node '{target}' is not foldable"
```

而六个工具的参数类型都是 `AttributedMarkdownTextFileBase`，该 Protocol 继承自 `FoldableMarkdownTextFileBase`——**类型上要求可折叠，运行时又自己检查「不是 foldable 就报错」**。这个自相矛盾说明工具层的心智模型本来就是「折叠可有可无」，是 Protocol 链把它绑死了。

### 2.4 Protocol 层同时充当实现基类

`interface.py` 里的 Protocol 被实现类直接继承（不只是拿来做注解和结构化约束），Protocol 层级因此成为实现的继承脊梁，所有能力被迫排成一条单调链。识别信号就是 2.3 里那个「类型上强制要求、运行时又当可选」的自相矛盾。

## 3. 被否决的方案

### 3.1 文件节点泛型化（用户原始思路）

两条硬理由：

1. **PEP 696 的类型参数默认值要 Python 3.13**。`class Foo[T = Default]` 是 3.13 才有的语法，而本项目 `requires-python = ">=3.12"`、`ruff target-version = "py312"`、`pyright pythonVersion = "3.12"`，写不出默认值就保不住 `AttributedMarkdownTextFileNode[MyAttr]` 这种既有调用点。
2. **类型参数在运行时不存在**（pyright 擦除），它只影响属性、返回值、签名的静态类型，**改不了类自身的方法集**。真正决定用哪种标题节点的仍是类属性 `markdown_text_node_type`——运行时故事与 mixin 方案一字不差，泛型只多一层静态糖，而那点糖用子类也能拿到。

### 3.2 文件侧全组合化

把编号在文件侧也降为 mixin，让四种组合都成为现成类。改动面过大：需要重排所有文件/文件夹类的 MRO 并同步改 `tools.py` 的参数类型。用户选择不做。

### 3.3 彻底解耦 Protocol

把 `interface.py` 的 Protocol 降为纯结构化类型约束（只用于注解，不参与继承），实现全部走 mixin。概念上最干净，但所有类的 MRO 都要重写，抽象方法检查失效，测试与文档需同步重写。用户选择不做。

## 4. 目标与非目标

**目标**

1. 支持「非编号、不折叠、有属性」的 Markdown 文件。
2. 文件节点接口与标题节点能力解耦，能力专属参数不污染内容层。
3. 消除 `AttributedMarkdownTextFileNode` 中与 `FoldableMarkdownTextFileNode` 重复的覆写。

**非目标**

- 不动标题侧 `Markdown → Numbered → Foldable` 的继承关系。
- 不产出「非编号文件夹」变体（`.mdp` 文件名硬依赖编号）。
- 不解耦 Protocol 与实现的继承关系。
- 不顺带修 `reload()` 不透传 `auto_correct` 的既有行为（全库一致，另议）。

## 5. 设计

### 5.1 `get_text` 语义分层

| 层 | 类型 | 签名与语义 |
|---|---|---|
| 内容层 | 所有**文件**节点（`.md` 与 `.mdp` 文件夹） | `get_text() -> str`，零参数，**永远返回完整正文**，忽略 `fold_mode` |
| 视图层 | `FoldableMarkdownTitleNode` | 保持 `get_text(with_fold_info: bool = True, full_text: bool = False) -> str` 不变 |

具体改动：

- **删除** `interface.py:123` — `FoldableMarkdownTextFileBase.get_text` 的带参版本。删除后所有文件类重新对上 `interface.py:57` 的 `MarkdownTextFileBase.get_text(self) -> str`（该签名本来就在）。
- **改签名** `foldable_markdown_nodes.py:188-191` — `FoldableMarkdownTextFileNode.get_text` 变为零参数 `return self.markdown_text_node.get_text(full_text=True)`。**不是删掉**：基类的实现会返回折叠视图。
- **删除** `foldable_markdown_nodes.py:192-196` — `FoldableMarkdownTextFileNode.save_to_file`。`MarkdownTextFileNode.save_to_file` 是 `f.write(self.get_text())`，新的零参 `get_text()` 已返回完整正文，直接继承即可。三份一模一样的 `save_to_file` 塌成一份。
- **改签名** `foldable_markdown_folder_nodes.py:107-111` — `FoldableMarkdownFolderNode.get_text` 同样改为零参数 `full_text=True`。
- **删除** `attributed_markdown_nodes.py:31-46` 的四个重复覆写（`get_text` / `set_text` / `get_markdown_text_node` / `markdown_text_node_type` 及其上方那段解释为什么不能继承基类的注释）——随 5.3 的继承关系调整自动获得。

### 5.2 属性拆成两级 mixin

**先说清楚为什么是两级。** 文件与文件夹的 FrontMatter 落盘形态并不相同：

| | `.md` 文件 | `.mdp` 文件夹 |
|---|---|---|
| 属性存哪 | 正文前的 `---\n…\n---\n` 前缀 | 目录下的独立 `FrontMatter.yaml` |
| 写盘 | 前缀 + 正文 | 正文走基类，另外写一个 yaml 文件 |
| 解析 | `_split_frontmatter` 切文本 | 直接读 `FrontMatter.yaml` |

两者真正共享的只有「有一个 `attribute` 字段」和「YAML 解析成 pydantic 模型」。所以 mixin 分两级——**共享的归内核，形态不同的留在各自那一级**：

```python
class AttributedMixin[T: BaseModel]:
    """FrontMatter 能力的内核：属性字段 + YAML 解析。与正文落盘形态无关。"""
    attribute: T

    @staticmethod
    def _read_file(file_path: Path) -> str: ...        # 现有，原样搬入

    @staticmethod
    def _parse_attribute(
        attribute_type: type[T], yaml_data: str, source: Path | str
    ) -> T: ...                                       # 现有，原样搬入


class FrontMatterTextFileMixin[T: BaseModel](AttributedMixin[T]):
    """把 FrontMatter 以 '---' 前缀写进 .md 正文的形态。"""
    # _split_frontmatter / create_file / to_markdown / save_to_file /
    # __init__ / reload —— 均从 AttributedMarkdownTextFileNode 搬入，
    # 唯一改动是写盘正文改用零参的 self.get_text()

    def to_markdown(self) -> str:
        """完整文件内容：FrontMatter + 正文。"""
        return f"---\n{to_yaml_str(self.attribute)}---\n{self.get_text()}"

    def save_to_file(self, file_path: Path) -> None:
        Path(file_path).write_text(self.to_markdown(), encoding="utf-8")
```

`to_markdown()` 是从原 `save_to_file` 里拆出来的纯入口，便于测试与调试，也让「FrontMatter 拼接格式」只有一处。

**这里不需要 `_body_text()` 之类的额外钩子。** 早期草案曾设想用私有钩子做多态，但 5.1 已经把不变式确立为「每个文件节点的 `get_text()` 都返回完整正文」，那么 `self.get_text()` 在所有组合下都正确，多加一个钩子只是重复表达同一件事。

**Protocol 层** — `AttributedMarkdownTextFileBase` 保留原名，基类从 `FoldableMarkdownTextFileBase` 换成 `MarkdownTextFileBase`：

```python
class AttributedMarkdownTextFileBase[T: BaseModel](MarkdownTextFileBase):
    """带 FrontMatter 的 Markdown 文件协议：与编号、折叠无关"""
    attribute: T

    @staticmethod
    @abstractmethod
    def create_file(
        file_path: Path, attribute_type: type[T], attribute: T | None = None
    ) -> None: ...
```

不新增「属性 + 折叠」的独立 Protocol——当前无人需要它（YAGNI）。

### 5.3 组合表

```python
# 旧名保留、行为一字不变的兼容壳（正文从 146 行降到约 30 行）
class AttributedMarkdownTextFileNode[T: BaseModel](
    FrontMatterTextFileMixin[T], FoldableMarkdownTextFileNode
): ...

# 新增：非编号、非折叠、有属性
class BasicAttributedMarkdownTextFileNode[T: BaseModel](
    FrontMatterTextFileMixin[T], MarkdownTextFileNode
): ...

# 文件夹只用内核，FrontMatter.yaml 的形态由它自己保留
class AttributedMarkdownFolderNode[T: BaseModel](
    AttributedMixin[T], FoldableMarkdownFolderNode
): ...
```

`BasicAttributedMarkdownTextFileNode` **一行实现代码都不用写**——属性逻辑全在 mixin 里；`get_root_title()` 静态返回 `MarkdownTitleBase`（`get_title` / `set_text` / `recursive_find_title_node_by_name` 都在），折叠方法**正确地不存在**。这正是 2.2 说的：文件节点上不再有折叠参数，也就没有「对 `MarkdownTitleNode` 无效的功能」。

> **命名说明**：用 `Basic` 而非 `Plain`，因为库里已有 `PlainTextFileNode`（无标题纯文本），`PlainAttributed...` 容易被误读成那个。

`AttributedMarkdownFolderNode` 保留自己的 `_load_attribute` / `create_file` / `save_to_file` / `reload`（FrontMatter.yaml 形态），只是把 `_parse_attribute` 的来源从 `AttributedMarkdownTextFileNode._parse_attribute` 改为 `AttributedMixin._parse_attribute`，删掉 `attributed_markdown_folder_nodes.py:90-91` 那个只是 `return super().get_root_title()` 的空覆写。

### 5.4 统一标题节点的构造缝

现有两个各自为政的构造入口：`MarkdownTextFileNode.reload()` 用 `markdown_text_node_type.from_text(text)`，而 `NumberedMarkdownFolderNode` 有 `_create_text_node(text, auto_correct)`。统一成后者：

```python
# MarkdownTextFileNode
def _create_text_node(self, text: str, auto_correct: bool = True) -> MarkdownTitleNode:
    return self.markdown_text_node_type.from_text(text)

# NumberedMarkdownTextFileNode / FoldableMarkdownTextFileNode 覆写
def _create_text_node(
    self, text: str, auto_correct: bool = True
) -> NumberedMarkdownTitleNode:
    return self.markdown_text_node_type.from_text(text, auto_correct=auto_correct)
```

`MarkdownTitleNode.from_text` 不接受 `auto_correct`。这是**私有**方法，让非编号实现「接受但忽略」该参数是安全的——`MarkdownTitleNode` 根本没有编号可校正。`FrontMatterTextFileMixin` 的 `__init__` / `reload` 只认这个缝，于是不含任何类型分支，也不必再加一个类型参数。

## 6. 破坏性变更与迁移

### 6.1 `get_text` 参数

| 旧写法 | 新写法 |
|---|---|
| `doc.get_text(full_text=True)` | `doc.get_text()` |
| `doc.get_text(with_fold_info=False)` | `doc.get_root_title().get_text(with_fold_info=False)` |

`src/` 内共 8 处 `get_text(with_fold_info|full_text)` 调用点，其中 4 处作用在**标题节点**上（`tools.py:29`、`foldable_markdown_nodes.py:67`、`foldable_markdown_folder_nodes.py:35/48`），**保持不变**；其余 4 处作用在文件节点上，随覆写改签名而消失。

`USAGE.md` §279-282、§434-435、§470 的 `get_text(full_text=True)` 用法需改写。

### 6.2 语义修正（预期）

`extra/tools.py:103` 的 `read_tool` 无 target 分支返回 `markdown_node.get_text()`，当前返回的是**折叠视图**——一份满是 `[text folded]` 占位符的内容。改零参后返回真实正文。这是预期修正，但**实施时需实测确认**，不作为既成事实写进发布说明。

### 6.3 保持不变

`extra/tools.py` 六个工具的参数类型 `AttributedMarkdownTextFileBase` 不改名，只是它不再保证可折叠——这与 `unfold_tool` 早就存在的运行时检查是一致的。`extra/mcp/server.py` 与 `extra/langchain/toolkit.py` 只引用该类型名，无需改动。

## 7. 实施步骤

按提交粒度分两次（用户要求：每修完一项或若干同类小修提交一次）：

**提交一 — `get_text` 零参化**

1. 删 `FoldableMarkdownTextFileBase.get_text`（`interface.py:123`）
2. `FoldableMarkdownTextFileNode` / `FoldableMarkdownFolderNode` 的 `get_text` 改为零参数 `full_text=True`
3. 删 `FoldableMarkdownTextFileNode.save_to_file`
4. 迁移测试与 `USAGE.md` 调用点
5. 实测确认 `read_tool` 的行为变化

**提交二 — 属性 mixin 化**

1. 抽 `AttributedMixin[T]` 与 `FrontMatterTextFileMixin[T]`
2. `AttributedMarkdownTextFileBase` 换基类
3. `AttributedMarkdownTextFileNode` 改继承（删四个重复覆写）
4. 新增 `BasicAttributedMarkdownTextFileNode`
5. `AttributedMarkdownFolderNode` 改用 `AttributedMixin`
6. 统一 `_create_text_node` 构造缝
7. `__init__.py` 导出新类

## 8. 验证

改动后必须全绿（命令统一走 `.venv/bin/python -m`）：

```
.venv/bin/python -m pytest tests -q
.venv/bin/python -m ruff check src tests
.venv/bin/python -m ruff format --check src tests
.venv/bin/python -m pyright src
```

基线（`a8c8b2c`）：pytest 461 passed；ruff check / format 均通过；pyright 8 个错误且全部是 `reportMissingImports`（本地 venv 缺可选依赖，CI 装齐后为 0）；覆盖率 99%。**本设计不新增 pyright 错误、不降低覆盖率。**

新功能须有测试覆盖：

- `BasicAttributedMarkdownTextFileNode` 的建档、读写、重载、往返幂等
- 折叠态下文件节点的 `get_text()` 仍返回完整正文（5.1 不变式的回归锁）
- `to_markdown()` 的 FrontMatter 拼接格式
- `AttributedMarkdownFolderNode` 改继承后 FrontMatter.yaml 往返不变

## 9. 风险与未决项

| 项 | 说明 |
|---|---|
| 调用点迁移面 | 约 40 处测试 + `USAGE.md` 三节。机械替换，但断言「文件节点折叠视图」的测试需改走 `get_root_title()`，不能纯文本替换 |
| 行为变更混入 | 提交一同时改了 `read_tool` 的返回值。发布说明要单列 |
| 类名 | `BasicAttributedMarkdownTextFileNode` 尚未最终确认，可在此处提出改名 |
| 未纳入 | `reload()` 不透传 `auto_correct`（`NumberedMarkdownTextFileNode.reload()`、`AttributedMarkdownTextFileNode.reload()` 均如此，全库一致），单独立项 |
