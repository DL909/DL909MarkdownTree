"""test_protocols.py - 验证各节点类型满足对应的抽象基类"""

from pathlib import Path

import pytest
from pydantic import BaseModel

from dl909markdowntree import (
    AttributedMarkdownFolderNode,
    AttributedMarkdownTextFileBase,
    AttributedMarkdownTextFileNode,
    BasicAttributedMarkdownTextFileNode,
    FoldableMarkdownFolderNode,
    FoldableMarkdownTextFileBase,
    FoldableMarkdownTextFileNode,
    MarkdownTextFileBase,
    MarkdownTextFileNode,
    NumberedMarkdownFolderNode,
    NumberedMarkdownTextFileBase,
    NumberedMarkdownTextFileNode,
)


class _TestAttribute(BaseModel):
    author: str = "default"
    version: str = "1.0"


# ── Phase 2: FileNode 实现抽象基类 ──────────────────────────────────────────


def test_markdown_text_file_node_satisfies_protocol(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Title\nContent")
    node = MarkdownTextFileNode(file_path=path)
    assert isinstance(node, MarkdownTextFileBase)
    assert node.get_text() == "# Title\nContent"


def test_numbered_markdown_text_file_node_satisfies_protocol(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\nContent")
    node = NumberedMarkdownTextFileNode(file_path=path)
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, NumberedMarkdownTextFileBase)


def test_foldable_markdown_text_file_node_satisfies_protocol(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\n## 1.1. Sub\nContent")
    node = FoldableMarkdownTextFileNode(file_path=path)
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, NumberedMarkdownTextFileBase)
    assert isinstance(node, FoldableMarkdownTextFileBase)


def test_attributed_markdown_text_file_node_satisfies_protocol(tmp_path: Path):
    content = '---\nauthor: test\nversion: "2.0"\n---\n# 1. Title\nContent'
    path = tmp_path / "attributed.md"
    path.write_text(content)
    node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, NumberedMarkdownTextFileBase)
    assert isinstance(node, FoldableMarkdownTextFileBase)
    assert isinstance(node, AttributedMarkdownTextFileBase)
    assert node.attribute.author == "test"


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


def test_basic_attributed_file_node_satisfies_minimal_protocol(tmp_path: Path):
    """非编号非折叠的带属性文件只满足最小协议，不满足折叠协议"""
    path = tmp_path / "plain-attributed.md"
    path.write_text('---\nauthor: test\nversion: "2.0.0"\n---\n# Title\nContent')
    node = BasicAttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, AttributedMarkdownTextFileBase)
    assert not isinstance(node, FoldableMarkdownTextFileBase)
    assert node.attribute.author == "test"
    assert "# Title" in node.get_text()


# ── Phase 3: FolderNode 作为抽象基类的另一实现 ──────────────────────────────


def test_numbered_markdown_folder_node_satisfies_numbered_protocol(tmp_path: Path):
    path = tmp_path / "test.mdf"
    path.mkdir()
    (path / "1_Chapter.mdp").write_text("## 1.1. Section\nContent")
    node = NumberedMarkdownFolderNode(file_path=path)
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, NumberedMarkdownTextFileBase)
    assert isinstance(node, NumberedMarkdownFolderNode)


def test_foldable_folder_node_satisfies_foldable_protocol(tmp_path: Path):
    path = tmp_path / "test.mdf"
    path.mkdir()
    (path / "1_Chapter.mdp").write_text("## 1.1. Section\nContent")
    node = FoldableMarkdownFolderNode(file_path=path)
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, NumberedMarkdownTextFileBase)
    assert isinstance(node, FoldableMarkdownTextFileBase)


def test_attributed_folder_node_satisfies_attributed_protocol(tmp_path: Path):
    path = tmp_path / "test.mdf"
    path.mkdir()
    (path / "FrontMatter.yaml").write_text('author: test_author\nversion: "3.0"\n')
    (path / "1_Chapter.mdp").write_text("## 1.1. Section\nContent")
    node = AttributedMarkdownFolderNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    assert isinstance(node, MarkdownTextFileBase)
    assert isinstance(node, NumberedMarkdownTextFileBase)
    assert isinstance(node, FoldableMarkdownTextFileBase)
    assert isinstance(node, AttributedMarkdownTextFileBase)
    assert node.attribute.author == "test_author"


def test_foldable_folder_node_recursive_find_within_shown(tmp_path: Path):
    """FoldableMarkdownFolderNode 的根标题
    必须正确传递 within_shown 参数"""
    path = tmp_path / "test.mdf"
    path.mkdir()
    (path / "1_Chapter.mdp").write_text(
        "## 1.1. Section\nContent\n### 1.1.1. Deep\nHidden"
    )
    node = FoldableMarkdownFolderNode(file_path=path)
    found = node.get_root_title().recursive_find_title_node_by_name(
        "### 1.1.1. Deep", within_shown=False
    )
    assert found is not None
    assert found.title == "Deep"


# ── 多态测试：同一抽象基类可同时被 FileNode 和 FolderNode 使用 ────────────────


def _use_numbered_protocol(node: NumberedMarkdownTextFileBase) -> str:
    return node.get_text()


def test_polymorphic_numbered_protocol_with_file(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\nContent")
    node = NumberedMarkdownTextFileNode(file_path=path)
    text = _use_numbered_protocol(node)
    assert "# 1. Title" in text


def test_polymorphic_numbered_protocol_with_folder(tmp_path: Path):
    path = tmp_path / "test.mdf"
    path.mkdir()
    (path / "1_Chapter.mdp").write_text("## 1.1. Section\nContent")
    node = NumberedMarkdownFolderNode(file_path=path)
    text = _use_numbered_protocol(node)
    assert "# 1. Chapter" in text


def _use_foldable_protocol(node: FoldableMarkdownTextFileBase) -> str:
    """折叠视图不再挂在文件节点上，改从根标题节点取"""
    return node.get_root_title().get_text(full_text=False, with_fold_info=True)


def test_polymorphic_foldable_protocol_with_file(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\n## 1.1. Sub\nContent")
    node = FoldableMarkdownTextFileNode(file_path=path)
    text = _use_foldable_protocol(node)
    assert "# 1. Title" in text


def test_polymorphic_foldable_protocol_with_folder(tmp_path: Path):
    path = tmp_path / "test.mdf"
    path.mkdir()
    (path / "1_Intro.mdp").write_text("## 1.1. Opening\nContent")
    node = FoldableMarkdownFolderNode(file_path=path)
    text = _use_foldable_protocol(node)
    assert "# 1. Intro" in text


def _use_attributed_protocol(
    node: AttributedMarkdownTextFileBase[_TestAttribute],
) -> str:
    return f"{node.attribute.author}: {node.get_text()}"


def test_polymorphic_attributed_protocol_with_file(tmp_path: Path):
    content = '---\nauthor: alice\nversion: "1.0"\n---\n# 1. Title\nContent'
    path = tmp_path / "attributed.md"
    path.write_text(content)
    node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    result = _use_attributed_protocol(node)
    assert result.startswith("alice:")


def test_polymorphic_attributed_protocol_with_folder(tmp_path: Path):
    path = tmp_path / "test.mdf"
    path.mkdir()
    (path / "FrontMatter.yaml").write_text('author: bob\nversion: "2.0"\n')
    (path / "1_Chapter.mdp").write_text("## 1.1. Section\nContent")
    node = AttributedMarkdownFolderNode[_TestAttribute](
        file_path=path, attribute_type=_TestAttribute
    )
    result = _use_attributed_protocol(node)
    assert result.startswith("bob:")


# ── 方法签名兼容性：不同抽象基类层次的 recursive_find 返回类型 ────────────────


def test_markdown_protocol_returns_markdown_title(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Title\n## Sub\nContent")
    node: MarkdownTextFileBase = MarkdownTextFileNode(file_path=path)
    found = node.get_root_title().recursive_find_title_node_by_name("## Sub")
    assert found is not None
    assert found.title == "Sub"


def test_numbered_protocol_returns_numbered_title(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\n## 1.1. Sub\nContent")
    node: NumberedMarkdownTextFileBase = NumberedMarkdownTextFileNode(file_path=path)
    found = node.get_root_title().recursive_find_title_node_by_name("## 1.1. Sub")
    assert found is not None
    assert found.number == [1, 1]


def test_foldable_protocol_returns_foldable_title(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\n## 1.1. Sub\nContent")
    node: FoldableMarkdownTextFileBase = FoldableMarkdownTextFileNode(file_path=path)
    found = node.get_root_title().recursive_find_title_node_by_name("## 1.1. Sub")
    assert found is not None
    assert hasattr(found, "fold_mode")


def test_attributed_protocol_has_attribute(tmp_path: Path):
    content = '---\nauthor: test\nversion: "1.0"\n---\n# 1. Title\nContent'
    path = tmp_path / "attributed.md"
    path.write_text(content)
    node: AttributedMarkdownTextFileBase[_TestAttribute] = (
        AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=path, attribute_type=_TestAttribute
        )
    )
    assert node.attribute.author == "test"
