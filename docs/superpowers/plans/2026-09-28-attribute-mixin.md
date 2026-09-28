# 属性 mixin 化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让库能处理「非编号、不折叠、有属性」的 Markdown 文件，并把文件节点的 `get_text` 收敛为「零参数、永远返回完整正文」的内容层契约。

**Architecture:** 折叠视图从文件节点下沉到标题节点（文件=内容层，标题=视图层）；FrontMatter 从继承链顶抽成两级 mixin（`AttributedMixin` 内核 + `FrontMatterTextFileMixin` 的 `.md` 前缀形态），因为 `.mdp` 文件夹用独立的 `FrontMatter.yaml`，两者真正共享的只有属性字段与 YAML 解析。

**Tech Stack:** Python 3.12、PEP 695 泛型、pydantic / pydantic_yaml、pytest 9、ruff、pyright。

**设计规格:** `docs/superpowers/specs/2026-09-27-attribute-mixin-design.md`（提交 `ce6c561`）

---

## File Structure

**本次修改/新建的文件：**

| 文件 | 动作 | 职责 |
|---|---|---|
| `src/dl909markdowntree/interface.py` | 改 | 删 `FoldableMarkdownTextFileBase.get_text`；`AttributedMarkdownTextFileBase` 换基类 |
| `src/dl909markdowntree/markdown_nodes.py` | 改 | 新增 `_create_text_node` 构造缝；`reload` 改用它 |
| `src/dl909markdowntree/numbered_markdown_nodes.py` | 改 | 覆写 `_create_text_node` 透传 `auto_correct` |
| `src/dl909markdowntree/foldable_markdown_nodes.py` | 改 | `get_text` 改零参；删 `save_to_file`；删无用 `Path` import |
| `src/dl909markdowntree/foldable_markdown_folder_nodes.py` | 改 | `get_text` 改零参 |
| `src/dl909markdowntree/attributed_markdown_nodes.py` | 重写 | 抽 `AttributedMixin` + `FrontMatterTextFileMixin`；新增 `BasicAttributedMarkdownTextFileNode` |
| `src/dl909markdowntree/attributed_markdown_folder_nodes.py` | 改 | 改用 `AttributedMixin`；删空覆写 |
| `src/dl909markdowntree/__init__.py` | 改 | 导出新类 |
| `USAGE.md` | 改 | `get_text(full_text=True)` → `get_text()` |
| `tests/**` | 改 | 24 处机械替换 + 7 处语义改写 + 新增/重写约 8 个测试 |

**提交边界**（用户要求：分两次提交）
- 提交一 = Task 1–4（`get_text` 零参化）
- 提交二 = Task 5–8（属性 mixin 化）

---

### Task 1: 锁定新契约的失败测试

**Files:**
- Modify: `tests/test_foldable_markdown_nodes.py`
- Modify: `tests/test_foldable_markdown_folder_nodes.py`
- Modify: `tests/extra/test_tools.py`

- [ ] **Step 1: 在 `tests/test_foldable_markdown_nodes.py` 末尾追加两个测试**

确认该文件顶部已 import `pytest` 与 `FoldMode`（已 import），直接追加：

```python
def test_foldable_file_get_text_is_full_text_without_parameters(tmp_path):
    """文件节点属于内容层：get_text() 零参数、忽略折叠态、永远返回完整正文"""
    file_path = tmp_path / "foldable.md"
    file_path.write_text("# 1. Title\nContent here\n## 1.1. Sub\nMore content")
    node = FoldableMarkdownTextFileNode(file_path=file_path)
    node.get_root_title().children[0].fold_mode = FoldMode.SHOW_TITLE

    assert node.get_text() == "# 1. Title\nContent here\n## 1.1. Sub\nMore content\n"
    # 阅读视图仍然只在标题节点上
    assert "[text folded]" in node.get_root_title().get_text()


def test_foldable_file_get_text_rejects_fold_parameters(tmp_path):
    """折叠参数已从文件节点移除，传了必须报错而不是被静默忽略"""
    file_path = tmp_path / "foldable.md"
    file_path.write_text("# 1. Title\nContent")
    node = FoldableMarkdownTextFileNode(file_path=file_path)

    with pytest.raises(TypeError):
        node.get_text(full_text=True)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        node.get_text(with_fold_info=False)  # type: ignore[call-arg]
```

- [ ] **Step 2: 在 `tests/test_foldable_markdown_folder_nodes.py` 追加一个测试**

```python
def test_foldable_folder_get_text_is_full_text_while_folded(tmp_path):
    """文件夹同样属于内容层：get_text() 忽略折叠态返回完整正文"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent\n## 1.2. Thesis\nArgument", encoding="utf-8"
    )
    node = FoldableMarkdownFolderNode(file_path=Path(folder))

    assert node.get_text() == (
        "# 1. Intro\n## 1.1. Opening\nContent\n## 1.2. Thesis\nArgument\n"
    )
    assert "[2 child title folded]" in node.get_root_title().get_text()
```

- [ ] **Step 3: 在 `tests/extra/test_tools.py` 的 `test_read_tool_returns_full_text_for_folded_target` 之后追加**

```python
def test_read_tool_full_document_returns_full_text_while_folded(tmp_path):
    """全量读取应返回完整正文，而不是 [text folded] 占位符"""
    doc = _make_folded_doc(tmp_path)
    # 前置：文档确实处于折叠态
    assert "[text folded]" in doc.get_root_title().get_text()

    result = read_tool(doc, None)

    assert "secret hidden line" in result
    assert "hidden sub" in result
    assert "folded" not in result
```

- [ ] **Step 4: 跑测试确认它们是红的**

```bash
.venv/bin/python -m pytest \
  tests/test_foldable_markdown_nodes.py::test_foldable_file_get_text_is_full_text_without_parameters \
  tests/test_foldable_markdown_nodes.py::test_foldable_file_get_text_rejects_fold_parameters \
  tests/test_foldable_markdown_folder_nodes.py::test_foldable_folder_get_text_is_full_text_while_folded \
  tests/extra/test_tools.py::test_read_tool_full_document_returns_full_text_while_folded \
  -q
```

Expected: 4 FAILED。失败原因分别是——前两个 `TypeError: get_text() got an unexpected keyword argument 'full_text'`；第三个 `AssertionError: assert '[2 child title folded]' in '# 1. Intro\n'`（当前返回折叠视图）；第四个 `AssertionError: assert 'secret hidden line' in '# 1. Title [text folded]\n'`。

---

### Task 2: 实施 `get_text` 零参化

**Files:**
- Modify: `src/dl909markdowntree/interface.py:116-137`
- Modify: `src/dl909markdowntree/foldable_markdown_nodes.py:1,182-199`
- Modify: `src/dl909markdowntree/foldable_markdown_folder_nodes.py:107-111`

- [ ] **Step 1: 改 `interface.py` — 删掉 `FoldableMarkdownTextFileBase.get_text`**

把第 116-123 行整块替换为：

```python
class FoldableMarkdownTextFileBase(NumberedMarkdownTextFileBase):
    """可折叠的 Markdown 文件协议

    文件节点只工作在内容层：get_text() 零参数、永远返回完整正文。折叠视图
    属于阅读视角，挂在标题节点上（见 FoldableMarkdownTitleBase.get_text），
    文件节点不再转发 with_fold_info / full_text。
    """

    @abstractmethod
    def get_root_title(self) -> FoldableMarkdownTitleBase: ...
```

（原第 122 行的 `@abstractmethod def get_root_title` 与第 123 行的 `@abstractmethod def get_text(...)` 一起删除。）

- [ ] **Step 2: 改 `foldable_markdown_nodes.py` — 改签名、删覆写、删 import**

第一步，删除第 1 行 `from pathlib import Path`（`save_to_file` 是它唯一的用处，删掉后无引用，ruff 会报 F401）。

第二步，把第 182-199 行整块替换为：

```python
class FoldableMarkdownTextFileNode(
    NumberedMarkdownTextFileNode, FoldableMarkdownTextFileBase
):
    markdown_text_node: FoldableMarkdownTitleNode  # type: ignore - children type is intentionally narrowed from base class
    markdown_text_node_type = FoldableMarkdownTitleNode

    @override
    def get_text(self) -> str:
        """文件正文恒为完整内容，折叠只影响阅读视图（见 get_root_title）"""
        return self.markdown_text_node.get_text(full_text=True)

    @override
    def get_root_title(self) -> FoldableMarkdownTitleBase:
        return self.markdown_text_node
```

注意：`save_to_file` 整个删除——基类 `MarkdownTextFileNode.save_to_file` 是 `f.write(self.get_text())`，新的零参 `get_text()` 已返回完整正文，行为完全一致。**不能删 `get_text`**：基类实现是 `self.markdown_text_node.get_text()`，对折叠标题节点会返回折叠视图。

- [ ] **Step 3: 改 `foldable_markdown_folder_nodes.py` — 改签名**

把第 107-111 行：

```python
    @override
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str:
        return self.markdown_text_node.get_text(
            with_fold_info=with_fold_info, full_text=full_text
        )
```

替换为：

```python
    @override
    def get_text(self) -> str:
        """文件夹正文恒为完整内容，折叠只影响阅读视图"""
        return self.markdown_text_node.get_text(full_text=True)
```

- [ ] **Step 4: 跑 Task 1 的四个测试确认转绿**

```bash
.venv/bin/python -m pytest \
  tests/test_foldable_markdown_nodes.py::test_foldable_file_get_text_is_full_text_without_parameters \
  tests/test_foldable_markdown_nodes.py::test_foldable_file_get_text_rejects_fold_parameters \
  tests/test_foldable_markdown_folder_nodes.py::test_foldable_folder_get_text_is_full_text_while_folded \
  tests/extra/test_tools.py::test_read_tool_full_document_returns_full_text_while_folded \
  -q
```

Expected: 4 passed

- [ ] **Step 5: 跑全量看还有多少红**

```bash
.venv/bin/python -m pytest tests -q 2>&1 | tail -40
```

Expected: 一批 FAILED，全部是 Task 3 要迁移的调用点。

---

### Task 3: 迁移测试调用点

**Files:**
- Modify: `tests/test_attributed_markdown_nodes.py`
- Modify: `tests/test_attributed_markdown_folder_nodes.py`
- Modify: `tests/extra/test_tools.py`
- Modify: `tests/test_foldable_markdown_nodes.py`
- Modify: `tests/test_foldable_markdown_folder_nodes.py`
- Modify: `tests/basic/markdown_nodes/test_protocols.py`

**A 组：24 处机械替换** —— `X.get_text(full_text=True)` → `X.get_text()`，其中 `X` 是文件节点。

- [ ] **Step 1: 用 `edit` 工具逐文件精确替换（禁止用脚本批量替换）**

逐处替换，行号以 Task 2 完成后的当前文件为准，用 `old_string` 精确匹配：

| 文件 | 行号 |
|---|---|
| `tests/test_attributed_markdown_nodes.py` | 188, 206, 294, 312, 345, 378, 420, 475 |
| `tests/test_attributed_markdown_folder_nodes.py` | 121, 122, 137 |
| `tests/extra/test_tools.py` | 56, 63, 68, 74, 85, 91, 100, 106, 114 |
| `tests/test_foldable_markdown_nodes.py` | 271, 287 |
| `tests/basic/markdown_nodes/test_protocols.py` | 77, 184 |

第 77 行在 Task 3 之后会被 Step 3 整段重写，本步可跳过。

**B 组：7 处语义改写** —— 断言折叠视图的，必须改走 `get_root_title()`。

- [ ] **Step 2: 改 7 处语义断言**

1. `tests/test_foldable_markdown_nodes.py`（`test_foldable_markdown_text_file_node_reload`）：

```python
    assert (
        test_file_node.get_root_title().get_text(with_fold_info=False, full_text=False)
        == "# 1. Title\n"
    )
```

2. `tests/test_foldable_markdown_nodes.py`（`test_foldable_markdown_text_file_node_save_while_folded`）末尾两行：

```python
    assert "# 1. Title" in test_file_node.get_root_title().get_text()
    assert "[text folded]" in test_file_node.get_root_title().get_text()
```

3. `tests/test_foldable_markdown_folder_nodes.py`（`test_foldable_markdown_folder_node_get_text_folded`）第 38 行：

```python
    text = node.get_root_title().get_text()
```

4. `tests/test_foldable_markdown_folder_nodes.py`（`test_foldable_markdown_folder_node_fold_and_save_round_trip`）第 129、132 行：

```python
    assert node.get_root_title().get_text() == "# 1. Intro\n## 1.1. Opening [text folded]\n"
```

5. `tests/test_attributed_markdown_nodes.py`（`test_attributed_markdown_text_file_node_fold`）第 473 行：

```python
    assert "Some content here" not in test_file_node.get_root_title().get_text()
```

6. `tests/test_attributed_markdown_folder_nodes.py`（`test_attributed_markdown_folder_node_get_text_folded`）第 136 行：

```python
    assert "Content" not in node.get_root_title().get_text()
```

**C 组：保持不变**（这些是**标题节点**上的调用，不要动）

- `tests/test_markdown_nodes.py:537,541` —— `root = doc.get_root_title()`
- `tests/test_foldable_markdown_nodes.py:94, 234, 348, 411, 414, 442, 446`
- `tests/test_foldable_markdown_nodes.py:26, 31, 38, 56, 80`（标题节点测试内的 folded 断言）

- [ ] **Step 3: 重写 `test_protocols.py` 中编码旧契约的两处**

先在文件顶部补 import（第 1-19 行的 import 块之后加一行）：

```python
import pytest
```

然后把第 69-79 行整个函数替换为：

```python
def test_attributed_node_get_text_takes_no_fold_parameters(tmp_path: Path):
    """文件节点属于内容层：get_text() 零参数、返回完整正文、不接受折叠参数"""
    content = '---\nauthor: test\nversion: "2.0"\n---\n# 1. Title\n## 1.1. Sub\nContent'
    path = tmp_path / "attributed.md"
    path.write_text(content)
    node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )

    assert "Content" in node.get_text()
    # 折叠视图改从标题节点取
    assert "[1 child title folded]" in node.get_root_title().get_text()
    with pytest.raises(TypeError):
        node.get_text(full_text=True)  # type: ignore[call-arg]
```

再把第 160-161 行替换为：

```python
def _use_foldable_protocol(node: FoldableMarkdownTextFileBase) -> str:
    """折叠视图不再挂在文件节点上，改从根标题节点取"""
    return node.get_root_title().get_text(full_text=False, with_fold_info=True)
```

最后把第 181-184 行替换为：

```python
def _use_attributed_protocol(
    node: AttributedMarkdownTextFileBase[_TestAttribute],
) -> str:
    return f"{node.attribute.author}: {node.get_text()}"
```

- [ ] **Step 4: 跑全量测试确认全绿**

```bash
.venv/bin/python -m pytest tests -q 2>&1 | tail -30
```

Expected: 465 passed（461 + Task 1 新增 4 个）

- [ ] **Step 5: 跑 lint 与类型检查**

```bash
.venv/bin/python -m ruff check src tests && \
.venv/bin/python -m ruff format --check src tests && \
.venv/bin/python -m pyright src 2>&1 | tail -12
```

Expected: ruff 两项均通过；pyright 仍是 8 个 `reportMissingImports`，**无新增错误**。

---

### Task 4: 迁移 USAGE.md 并提交

**Files:**
- Modify: `USAGE.md`

- [ ] **Step 1: 找出所有需要改的用法**

```bash
grep -n "get_text(full_text\|get_text(with_fold_info" USAGE.md
```

Expected 命中 §279、§282、§434、§470 四行。

- [ ] **Step 2: 逐处改写**

| 原文 | 新文 |
|---|---|
| `doc.get_text(with_fold_info=False)      # 不含折叠标记` | `doc.get_root_title().get_text(with_fold_info=False)   # 不含折叠标记` |
| `doc.get_text(full_text=True)            # 忽略折叠状态，输出完整内容` | `doc.get_text()                          # 恒为完整内容，与折叠状态无关` |
| `doc.get_text(full_text=True)         # 完整内容` | `doc.get_text()                      # 完整内容` |
| `get_text(full_text=True)`。 | `get_text()`。 |

§279-282 那一段所在的表格/代码块建议补一句说明：**文件节点的 `get_text()` 只在内容层工作，永远返回完整正文；折叠视图属于阅读视角，请用 `get_root_title().get_text()`。**

- [ ] **Step 3: 复查没有残留**

```bash
grep -n "get_text(full_text\|get_text(with_fold_info" USAGE.md README.md
```

Expected: 只剩 `get_root_title().get_text(...)` 形式的标题节点用法。若命中 `README.md` 同样处理。

- [ ] **Step 4: 跑一次完整验证**

```bash
.venv/bin/python -m pytest tests -q 2>&1 | tail -3 && \
.venv/bin/python -m ruff check src tests && \
.venv/bin/python -m ruff format --check src tests
```

Expected: 465 passed，ruff 两项通过

- [ ] **Step 5: 提交一**

```bash
git add -A src tests USAGE.md
git commit -F - <<'EOF'
refactor(interface): 把折叠视图从文件节点下沉到标题节点

文件节点此前转发 get_text(with_fold_info, full_text)，让能力专属参数污染
了内容层接口，也让"非折叠文件上的这两个参数"永远无效。改为分两层：文件
节点 get_text() 零参数、恒返回完整正文；折叠视图只挂在标题节点上，用
get_root_title().get_text() 取。

连带收敛：删掉 FoldableMarkdownTextFileBase.get_text 与两处 save_to_file
（基类实现已正确），三份一模一样的落盘代码塌成一份。

破坏性变更：get_text(full_text=True) 改为 get_text()，get_text(with_fold_info=)
改走 get_root_title()。USAGE.md 与 24 处测试调用点已迁移。

顺带修正一个语义问题：read_tool 无 target 时返回的是折叠视图，满屏
"[text folded]" 占位符；现在返回真实正文，并补了回归测试。
EOF
```

---

### Task 5: 写 mixin 化的失败测试

**Files:**
- Modify: `tests/test_attributed_markdown_nodes.py`

- [ ] **Step 1: 追加三个测试**

```python
def test_basic_attributed_file_node_round_trip(tmp_path):
    """非编号、非折叠、有属性的文件应能建档、写入、重载，且往返幂等"""
    path = tmp_path / "note.md"
    node = BasicAttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    node.set_text("# Note\nbody line\n## Sub\nsub body")
    node.save()

    on_disk = path.read_text(encoding="utf-8")
    assert on_disk.startswith("---\n")
    assert "author: default" in on_disk
    assert "# Note" in on_disk
    assert "sub body" in on_disk

    reopened = BasicAttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    assert reopened.get_text() == "# Note\nbody line\n## Sub\nsub body\n"
    assert reopened.attribute == _TestAttribute()
    # 折叠能力正确地不存在
    assert isinstance(reopened.get_root_title(), MarkdownTitleNode)
    assert not hasattr(reopened.get_root_title(), "fold_mode")


def test_attributed_to_markdown_returns_full_file_content(tmp_path):
    """to_markdown 应给出 FrontMatter + 完整正文，不受折叠态影响"""
    path = tmp_path / "a.md"
    path.write_text(
        '---\nauthor: "me"\nversion: "1.0"\n---\n# 1. T\nsecret\n## 1.1. S\nhidden',
        encoding="utf-8",
    )
    node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    node.get_root_title().children[0].fold_mode = FoldMode.SHOW_TITLE

    md = node.to_markdown()

    assert md.startswith("---\n")
    assert "secret" in md
    assert "hidden" in md
    assert "folded" not in md


def test_attributed_folder_keeps_frontmatter_yaml_form(tmp_path):
    """文件夹仍写独立的 FrontMatter.yaml，不受 .md 前缀形态影响"""
    folder = tmp_path / "book.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: test\nversion: '1.0'\n", encoding="utf-8"
    )
    (folder / "1_One.mdp").write_text("## 1.1. Sub\ncontent", encoding="utf-8")

    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=folder, attribute_type=_ChapterMeta
    )

    assert node.attribute.author == "test"
    assert not (folder / "1_One.mdp").read_text(encoding="utf-8").startswith("---")
```

若 `MarkdownTitleNode` / `FoldMode` 尚未在该文件 import，补进顶部 import 块；`_ChapterMeta` 若不存在，改用该文件已有的属性类或新增一个三字段的 `BaseModel`。

- [ ] **Step 2: 跑测试确认是红的**

```bash
.venv/bin/python -m pytest \
  tests/test_attributed_markdown_nodes.py::test_basic_attributed_file_node_round_trip \
  tests/test_attributed_markdown_nodes.py::test_attributed_to_markdown_returns_full_file_content \
  -q
```

Expected: 2 FAILED。第一个 `ImportError: cannot import name 'BasicAttributedMarkdownTextFileNode'`，第二个 `AttributeError: 'AttributedMarkdownTextFileNode' object has no attribute 'to_markdown'`。

---

### Task 6: 统一标题节点的构造缝

**Files:**
- Modify: `src/dl909markdowntree/markdown_nodes.py:225-276`
- Modify: `src/dl909markdowntree/numbered_markdown_nodes.py:135-140`

- [ ] **Step 1: 在 `MarkdownTextFileNode` 加 `_create_text_node`**

在 `get_root_title` 之前（`markdown_nodes.py` 第 255 行前）插入：

```python
    def _create_text_node(
        self, text: str, auto_correct: bool = True
    ) -> MarkdownTitleNode:
        """由正文构造标题节点树。

        统一构造入口：文件节点原本直接用 markdown_text_node_type.from_text(text)，
        文件夹节点则有 _create_text_node(text, auto_correct)，两处各写各的。
        编号能力由此参数接入——MarkdownTitleNode 没有编号可校正，忽略它即可
        （本方法是私有的，不构成公开契约）。
        """
        return self.markdown_text_node_type.from_text(text)
```

- [ ] **Step 2: `MarkdownTextFileNode.reload` 改用它**

把第 260-263 行：

```python
    @override
    def reload(self):
        self.markdown_text_node = self.markdown_text_node_type.from_text(
            self.file_path.read_text(encoding="utf-8")
        )
```

替换为：

```python
    @override
    def reload(self):
        self.markdown_text_node = self._create_text_node(
            self.file_path.read_text(encoding="utf-8")
        )
```

- [ ] **Step 3: 在 `NumberedMarkdownTextFileNode` 覆写**

把 `numbered_markdown_nodes.py` 第 135-140 行整块替换为：

```python
class NumberedMarkdownTextFileNode(MarkdownTextFileNode, NumberedMarkdownTextFileBase):
    markdown_text_node: NumberedMarkdownTitleNode  # type: ignore - children type is intentionally narrowed from base class
    markdown_text_node_type = NumberedMarkdownTitleNode

    @override
    def _create_text_node(
        self, text: str, auto_correct: bool = True
    ) -> NumberedMarkdownTitleNode:
        return self.markdown_text_node_type.from_text(
            text, auto_correct=auto_correct
        )

    def get_root_title(self) -> NumberedMarkdownTitleBase:
        return self.markdown_text_node
```

`NumberedMarkdownFolderNode._create_text_node`（`markdown_folder_nodes.py:130`）签名与返回类型已一致，**不需要改动**。

- [ ] **Step 4: 跑测试确认行为没变**

```bash
.venv/bin/python -m pytest tests -q 2>&1 | tail -5
```

Expected: 465 passed（此时 Task 5 的两个新测试仍是红的，先忽略它们）

---

### Task 7: 抽 mixin 并改造三个类

**Files:**
- Rewrite: `src/dl909markdowntree/attributed_markdown_nodes.py`
- Modify: `src/dl909markdowntree/attributed_markdown_folder_nodes.py`
- Modify: `src/dl909markdowntree/interface.py:126-137`

- [ ] **Step 1: 改 `interface.py` — `AttributedMarkdownTextFileBase` 换基类**

把第 126 行：

```python
class AttributedMarkdownTextFileBase[T: BaseModel](FoldableMarkdownTextFileBase):
    """带属性的 Markdown 文件协议"""
```

替换为：

```python
class AttributedMarkdownTextFileBase[T: BaseModel](MarkdownTextFileBase):
    """带 FrontMatter 的 Markdown 文件协议：与编号、折叠无关"""
```

该类的 `attribute: T` 与 `create_file` 声明保持原样。

- [ ] **Step 2: 整体重写 `attributed_markdown_nodes.py`**

```python
from pathlib import Path
from typing import override

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from .exceptions import (
    InvalidFrontMatterError,
    MarkdownFileError,
)
from .foldable_markdown_nodes import FoldableMarkdownTextFileNode
from .interface import AttributedMarkdownTextFileBase
from .markdown_nodes import MarkdownTextFileNode, MarkdownTitleNode


class AttributedMixin[T: BaseModel]:
    """FrontMatter 能力的内核：属性字段与 YAML 解析。

    与正文的落盘形态无关——.md 把 FrontMatter 写成正文前缀，.mdp 文件夹写成
    独立的 FrontMatter.yaml，两者真正共享的只有 attribute 与 YAML 解析，
    所以内核必须比两种形态都窄。
    """

    attribute: T
    # 具体类会把它窄化到自己的标题节点类型，与文件节点基类里的做法一致
    markdown_text_node: MarkdownTitleNode

    @staticmethod
    def _read_file(file_path: Path) -> str:
        """读取文件并把 IO / 解码错误收敛为 MarkdownTreeError 家族"""
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise MarkdownFileError(f"无法读取 {file_path}: {e}") from e

    @staticmethod
    def _parse_attribute(
        attribute_type: type[T], yaml_data: str, source: Path | str
    ) -> T:
        """把 FrontMatter 解析为属性对象，解析失败收敛为 MarkdownTreeError"""
        if not yaml_data.strip():
            return attribute_type()
        try:
            return parse_yaml_raw_as(attribute_type, yaml_data)
        except Exception as e:
            # pydantic_yaml 的 ParserError / pydantic 的 ValidationError 都不
            # 属于 MarkdownTreeError，调用方无法用单一类型兜底
            raise InvalidFrontMatterError(
                f"{source} 的 FrontMatter 无法解析为 {attribute_type.__name__}: {e}"
            ) from e


class FrontMatterTextFileMixin[T: BaseModel](AttributedMixin[T]):
    """把 FrontMatter 以 '---' 前缀写进 .md 正文的形态。

    只依赖基类提供的 markdown_text_node / file_path / _create_text_node，
    对标题节点是否编号、是否可折叠一无所知——因此可以直接拼在
    MarkdownTextFileNode 上，得到"非编号、非折叠、有属性"的节点。
    """

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[str, str]:
        """将 ``---\\n<yaml>\\n---\\n<markdown>`` 拆分为 (yaml_data, markdown_content)"""
        if not content.startswith("---\n"):
            raise InvalidFrontMatterError("文件缺少 FrontMatter 起始标记 '---'")
        # 结束标记既可能是 "\n---\n"（后面还有正文），也可能是文件结尾的
        # "\n---"（无尾换行）。只找前者会把后者误判成"缺少结束标记"。
        index = content.find("\n---\n", 3)
        if index == -1:
            if content.endswith("\n---"):
                index = len(content) - 4
            else:
                raise InvalidFrontMatterError("文件缺少 FrontMatter 结束标记 '---'")
        return content[4:index], content[index + 5 :]

    @staticmethod
    @override
    def create_file(
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
    ) -> None:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if attribute is None:
            attribute = attribute_type()
        file_path.write_text(f"---\n{to_yaml_str(attribute)}---\n", encoding="utf-8")

    def to_markdown(self) -> str:
        """完整文件内容：FrontMatter 前缀 + 正文。

        正文恒为完整内容——文件节点只在内容层工作，折叠不影响落盘。
        """
        return f"---\n{to_yaml_str(self.attribute)}---\n{self.get_text()}"

    @override
    def save_to_file(self, file_path: Path) -> None:
        Path(file_path).write_text(self.to_markdown(), encoding="utf-8")

    @override
    def reload(self) -> None:
        content = self._read_file(self.file_path)
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = self._create_text_node(markdown_content)
        self.attribute = self._parse_attribute(
            type(self.attribute), yaml_data, self.file_path
        )

    def __init__(
        self,
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
        auto_correct: bool = True,
        markdown_text_node: MarkdownTitleNode | None = None,
    ):
        file_path = Path(file_path)
        super().__init__(file_path=file_path)
        if not file_path.exists():
            self.create_file(file_path, attribute_type, attribute)
        content = self._read_file(file_path)
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = (
            markdown_text_node
            if markdown_text_node
            else self._create_text_node(markdown_content, auto_correct)
        )
        self.attribute = (
            attribute
            if attribute
            else self._parse_attribute(attribute_type, yaml_data, file_path)
        )


class AttributedMarkdownTextFileNode[T: BaseModel](
    FrontMatterTextFileMixin[T],
    AttributedMarkdownTextFileBase[T],
    FoldableMarkdownTextFileNode,
):
    """带属性的可折叠 Markdown 文件。

    早先直接继承 AttributedMarkdownTextFileBase 而非 MarkdownTextFileNode，
    拿不到基类的 markdown_text_node_type，reload() 等路径会 AttributeError，
    于是不得不把 get_text/set_text/get_markdown_text_node 全部重写一遍。
    改为继承真正的实现基类后，这些重复覆写全部消失。
    """


class BasicAttributedMarkdownTextFileNode[T: BaseModel](
    FrontMatterTextFileMixin[T],
    AttributedMarkdownTextFileBase[T],
    MarkdownTextFileNode,
):
    """非编号、非折叠、有 FrontMatter 的 Markdown 文件。

    早先这类文档无法表达：文件侧继承链严格单调，想要属性就连编号和折叠
    一起要。现在属性是横切关注点，编号与折叠交给用户自己拼。
    """
```

- [ ] **Step 3: 改 `attributed_markdown_folder_nodes.py`**

把第 9 行：

```python
from .attributed_markdown_nodes import AttributedMarkdownTextFileNode
```

替换为：

```python
from .attributed_markdown_nodes import AttributedMixin
```

把第 15 行的 `from .interface import AttributedMarkdownTextFileBase` 保留（类声明里要用）。

把第 71-73 行：

```python
        return AttributedMarkdownTextFileNode._parse_attribute(
            attribute_type, yaml_data, yaml_path
        )
```

替换为：

```python
        return self._parse_attribute(attribute_type, yaml_data, yaml_path)
```

删除第 89-91 行（整个 `get_root_title` 空覆写）：

```python
    @override
    def get_root_title(self) -> FoldableMarkdownTitleBase:
        return super().get_root_title()
```

删除后 `FoldableMarkdownTitleBase` 若不再被使用，连同第 12 行 import 一起删（ruff 会提示）。

- [ ] **Step 4: 跑测试**

```bash
.venv/bin/python -m pytest tests -q 2>&1 | tail -20
```

Expected: 全部 passed（含 Task 5 的三个新测试）

- [ ] **Step 5: 跑 lint 与类型检查**

```bash
.venv/bin/python -m ruff check src tests && \
.venv/bin/python -m ruff format --check src tests && \
.venv/bin/python -m pyright src 2>&1 | tail -15
```

Expected: ruff 两项通过；pyright 仍为 8 个 `reportMissingImports`，**无新增错误**。

若 pyright 报 `reportIncompatibleVariableOverride`，来源是 `AttributedMixin` 声明的 `markdown_text_node: MarkdownTitleNode` 与各具体类的窄化声明冲突。处理方式：保留 `foldable_markdown_nodes.py:185` 与 `attributed_markdown_folder_nodes.py:22` 上已有的 `# pyright: ignore[reportIncompatibleVariableOverride]`，**不要**改成更宽的类型。

---

### Task 8: 导出新类、补协议测试并提交

**Files:**
- Modify: `src/dl909markdowntree/__init__.py`
- Modify: `tests/basic/markdown_nodes/test_protocols.py`

- [ ] **Step 1: 导出新类**

在 `__init__.py` 的第 2 行：

```python
from .attributed_markdown_nodes import AttributedMarkdownTextFileNode
```

改为：

```python
from .attributed_markdown_nodes import (
    AttributedMarkdownTextFileNode,
    BasicAttributedMarkdownTextFileNode,
)
```

在 `__all__` 里，把 `"AttributedMarkdownTextFileNode",` 之后补一行 `"BasicAttributedMarkdownTextFileNode",`（保持字母序：它应排在 `"AttributedMarkdownTextFileBase"` 与 `"FileNode"` 之后、`"FoldMode"` 之前）。

- [ ] **Step 2: 补协议测试**

在 `tests/basic/markdown_nodes/test_protocols.py` 的 import 块里加上 `BasicAttributedMarkdownTextFileNode`，然后在 `test_attributed_node_get_text_takes_no_fold_parameters` 之后追加：

```python
def test_basic_attributed_file_node_satisfies_attributed_protocol(tmp_path: Path):
    """非编号非折叠的带属性文件只满足最小协议，不满足折叠协议"""
    path = tmp_path / "plain-attributed.md"
    path.write_text('---\nauthor: test\nversion: "2.0"\n---\n# Title\nContent')
    node = BasicAttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, AttributedMarkdownTextFileBase)
    assert not isinstance(node, FoldableMarkdownTextFileBase)
    assert node.attribute.author == "test"
    assert "# Title" in node.get_text()
```

- [ ] **Step 3: 跑完整验证**

```bash
.venv/bin/python -m pytest tests -q 2>&1 | tail -5 && \
.venv/bin/python -m ruff check src tests && \
.venv/bin/python -m ruff format --check src tests && \
.venv/bin/python -m pyright src 2>&1 | tail -12
```

Expected: 466 passed（465 + 1 新增）；ruff 两项通过；pyright 8 个 `reportMissingImports`，无新增。

- [ ] **Step 4: 更新 USAGE.md 补新类的用法**

在 USAGE.md 属性（FrontMatter）那一节末尾追加：

```markdown
### 非编号、非折叠的带属性文档

默认的 `AttributedMarkdownTextFileNode` 面向编号 + 折叠 + 属性的文档。只需要
FrontMatter、标题不重不折叠时用 `BasicAttributedMarkdownTextFileNode`，用法一致：

```python
from dl909markdowntree import BasicAttributedMarkdownTextFileNode

class NoteMeta(BaseModel):
    author: str = ""

doc = BasicAttributedMarkdownTextFileNode[NoteMeta](
    file_path=Path("note.md"), attribute_type=NoteMeta
)
doc.set_text("# 随记\n随手写点什么")
doc.save()
```

它只满足 `MarkdownTextFileBase` 与 `AttributedMarkdownTextFileBase`，**不**满足
`FoldableMarkdownTextFileBase`——折叠相关方法正确地不存在。
```

- [ ] **Step 5: 提交二**

```bash
git add -A src tests USAGE.md
git commit -F - <<'EOF'
refactor(Attributed): 把属性抽成 mixin，补上非编号非折叠的带属性文件

继承链严格单调，导致想要 FrontMatter 就必须连编号和折叠一起要。真正的
病根是文件侧把 Attributed 放在链顶纯属历史写法：FrontMatter 只是在正文前
拼一段 YAML，与编号、折叠毫无关系。标题侧的 Markdown→Numbered→Foldable 是
真依赖（折叠状态以编号定位），保持不动。

属性拆成两级而不是一级：.md 把 FrontMatter 写成正文前缀，.mdp 文件夹写成
独立的 FrontMatter.yaml，两者真正共享的只有 attribute 字段与 YAML 解析。
于是 AttributedMixin 是内核，FrontMatterTextFileMixin 是 .md 前缀形态。
同时统一了 markdown_text_node_type.from_text 与文件夹 _create_text_node 两
个各自为政的构造入口。

新增 BasicAttributedMarkdownTextFileNode 拼 MarkdownTextFileNode，一行实现
代码都不用写——折叠方法正确地不存在。AttributedMarkdownTextFileNode 改为
继承真正的实现基类后，四段重复覆写全部消失。

AttributedMarkdownTextFileBase 保留原名，基类换成 MarkdownTextFileBase，
不再保证可折叠——这与 extra/tools.py 里 unfold_tool 早就在做的运行时检查
是一致的。
EOF
```

---

## Self-Review

**1. 规格覆盖** — 逐节对照 `docs/superpowers/specs/2026-09-27-attribute-mixin-design.md`：

| 规格节 | 覆盖任务 |
|---|---|
| 5.1 `get_text` 语义分层（5 处改动） | Task 2 Step 1-3，五处逐条对应 |
| 5.2 属性拆两级 mixin + Protocol 换基类 | Task 7 Step 1-2 |
| 5.3 组合表三个类 | Task 7 Step 2-3 |
| 5.4 统一 `_create_text_node` 构造缝 | Task 6 |
| 6.1 破坏性变更与迁移 | Task 3 A/B/C 三组、Task 4 |
| 6.2 `read_tool` 语义修正 | Task 1 Step 3（先红）、Task 2（转绿） |
| 6.3 工具层类型名不变 | Task 7 Step 1 只换基类，名字不动 |
| 8 验证基线 | 每个 Task 末尾 + Task 4/8 Step 3 |
| 9 风险：调用点迁移面 | Task 3 逐行列出行号，A/B/C 三组分清 |
| 9 风险：类名待确认 | 已采用 `BasicAttributedMarkdownTextFileNode` |
| 9 未纳入：`reload` 不透传 `auto_correct` | 未动（Task 6 Step 2 保持原样，`reload` 调 `_create_text_node(text)` 不传） |

**2. Placeholder 扫描** — 无 TBD / TODO / "类似 Task N"。Task 3 的 A 组用行号表而非逐行代码，因为那是确定性文本替换且行号已核实；B/C 组给出完整替换后代码。

**3. 类型一致性** — `_create_text_node(text, auto_correct=True)` 在 Task 6 定义，`FrontMatterTextFileMixin.__init__`（Task 7）以 `self._create_text_node(markdown_content, auto_correct)` 调用，`reload` 以 `self._create_text_node(markdown_content)` 调用，两处签名一致。`to_markdown()` 在 Task 7 Step 2 定义、Task 5 Step 1 与 Task 8 Step 4 引用，命名一致。`AttributedMixin._parse_attribute` 在 Task 7 Step 2 定义、Step 3 由文件夹调用，路径一致。
