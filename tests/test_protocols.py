"""test_protocols.py - 验证各节点类型满足对应的 Protocol"""

from pathlib import Path

from pydantic import BaseModel

from dl909agentframework.tree_doc.attributed_markdown_folder_nodes import (
    AttributedMarkdownFolderNode,
)
from dl909agentframework.tree_doc.attributed_markdown_nodes import (
    AttributedMarkdownTextFileNode,
)
from dl909agentframework.tree_doc.foldable_markdown_folder_nodes import (
    FoldableMarkdownFolderNode,
)
from dl909agentframework.tree_doc.foldable_markdown_nodes import (
    FoldableMarkdownTextFileNode,
)
from dl909agentframework.tree_doc.markdown_folder_nodes import MarkdownFolderNode
from dl909agentframework.tree_doc.markdown_nodes import MarkdownTextFileNode
from dl909agentframework.tree_doc.numbered_markdown_nodes import (
    NumberedMarkdownTextFileNode,
)
from dl909agentframework.tree_doc.protocols import (
    AttributedMarkdownTextFileProtocol,
    FoldableMarkdownTextFileProtocol,
    MarkdownTextFileProtocol,
    NumberedMarkdownTextFileProtocol,
)


class _TestAttribute(BaseModel):
    author: str = "default"
    version: str = "1.0"


# ── Phase 2: FileNode 实现 Protocol ──────────────────────────────────────────


def test_markdown_text_file_node_satisfies_protocol(fs):
    fs.create_file("/tmp/test.md", contents="# Title\nContent")
    node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    assert isinstance(node, MarkdownTextFileProtocol)
    assert node.get_text() == "# Title\n\nContent"


def test_numbered_markdown_text_file_node_satisfies_protocol(fs):
    fs.create_file("/var/data/test.md", contents="# 1. Title\nContent")
    node = NumberedMarkdownTextFileNode(file_path=Path("/var/data/test.md"))
    assert isinstance(node, MarkdownTextFileProtocol)
    assert isinstance(node, NumberedMarkdownTextFileProtocol)


def test_foldable_markdown_text_file_node_satisfies_protocol(fs):
    fs.create_file("/tmp/test.md", contents="# 1. Title\n## 1.1. Sub\nContent")
    node = FoldableMarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    assert isinstance(node, MarkdownTextFileProtocol)
    assert isinstance(node, NumberedMarkdownTextFileProtocol)
    assert isinstance(node, FoldableMarkdownTextFileProtocol)


def test_attributed_markdown_text_file_node_satisfies_protocol(fs):
    content = '---\nauthor: test\nversion: "2.0"\n---\n# 1. Title\nContent'
    fs.create_file("/tmp/attributed.md", contents=content)
    node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    assert isinstance(node, MarkdownTextFileProtocol)
    assert isinstance(node, NumberedMarkdownTextFileProtocol)
    assert isinstance(node, FoldableMarkdownTextFileProtocol)
    assert isinstance(node, AttributedMarkdownTextFileProtocol)
    assert node.attribute.author == "test"


def test_attributed_node_get_text_accepts_with_fold_info(fs):
    """AttributedMarkdownTextFileNode.get_text 必须接受 with_fold_info 参数"""
    content = '---\nauthor: test\nversion: "2.0"\n---\n# 1. Title\n## 1.1. Sub\nContent'
    fs.create_file("/tmp/attributed.md", contents=content)
    node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    result = node.get_text(with_fold_info=True, full_text=True)
    assert "# 1. Title" in result
    assert "Content" in result


# ── Phase 3: FolderNode 作为 Protocol 的另一实现 ──────────────────────────────


def test_markdown_folder_node_satisfies_numbered_protocol(fs):
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = MarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert isinstance(node, MarkdownTextFileProtocol)
    assert isinstance(node, NumberedMarkdownTextFileProtocol)
    assert isinstance(node, MarkdownFolderNode)


def test_foldable_folder_node_satisfies_foldable_protocol(fs):
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert isinstance(node, MarkdownTextFileProtocol)
    assert isinstance(node, NumberedMarkdownTextFileProtocol)
    assert isinstance(node, FoldableMarkdownTextFileProtocol)


def test_attributed_folder_node_satisfies_attributed_protocol(fs):
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents='author: test_author\nversion: "3.0"\n',
    )
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = AttributedMarkdownFolderNode[_TestAttribute](
        file_path=Path("/tmp/test.mdf"), attribute_type=_TestAttribute
    )
    assert isinstance(node, MarkdownTextFileProtocol)
    assert isinstance(node, NumberedMarkdownTextFileProtocol)
    assert isinstance(node, FoldableMarkdownTextFileProtocol)
    assert isinstance(node, AttributedMarkdownTextFileProtocol)
    assert node.attribute.author == "test_author"


def test_foldable_folder_node_recursive_find_within_shown(fs):
    """FoldableMarkdownFolderNode.recursive_find_title_node_by_name
    必须正确传递 within_shown 参数"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Chapter.mdp",
        contents="## 1.1 Section\nContent\n### 1.1.1 Deep\nHidden",
    )
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    found = node.recursive_find_title_node_by_name(
        "### 1.1.1. Deep", within_shown=False
    )
    assert found is not None
    assert found.title == "Deep"


# ── 多态测试：同一协议可同时被 FileNode 和 FolderNode 使用 ────────────────────


def _use_numbered_protocol(node: NumberedMarkdownTextFileProtocol) -> str:
    return node.get_text()


def test_polymorphic_numbered_protocol_with_file(fs):
    fs.create_file("/var/data/test.md", contents="# 1. Title\nContent")
    node = NumberedMarkdownTextFileNode(file_path=Path("/var/data/test.md"))
    text = _use_numbered_protocol(node)
    assert "# 1. Title" in text


def test_polymorphic_numbered_protocol_with_folder(fs):
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = MarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    text = _use_numbered_protocol(node)
    assert "# 1. Chapter" in text


def _use_foldable_protocol(node: FoldableMarkdownTextFileProtocol) -> str:
    return node.get_text(full_text=False, with_fold_info=True)


def test_polymorphic_foldable_protocol_with_file(fs):
    fs.create_file("/tmp/test.md", contents="# 1. Title\n## 1.1. Sub\nContent")
    node = FoldableMarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    text = _use_foldable_protocol(node)
    assert "# 1. Title" in text


def test_polymorphic_foldable_protocol_with_folder(fs):
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Opening\nContent")
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    text = _use_foldable_protocol(node)
    assert "# 1. Intro" in text


def _use_attributed_protocol(
    node: AttributedMarkdownTextFileProtocol[_TestAttribute],
) -> str:
    return f"{node.attribute.author}: {node.get_text(full_text=True)}"


def test_polymorphic_attributed_protocol_with_file(fs):
    content = '---\nauthor: alice\nversion: "1.0"\n---\n# 1. Title\nContent'
    fs.create_file("/tmp/attributed.md", contents=content)
    node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    result = _use_attributed_protocol(node)
    assert result.startswith("alice:")


def test_polymorphic_attributed_protocol_with_folder(fs):
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents='author: bob\nversion: "2.0"\n',
    )
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = AttributedMarkdownFolderNode[_TestAttribute](
        file_path=Path("/tmp/test.mdf"), attribute_type=_TestAttribute
    )
    result = _use_attributed_protocol(node)
    assert result.startswith("bob:")


# ── 方法签名兼容性：不同协议层次的 recursive_find 返回类型 ────────────────────


def test_markdown_protocol_returns_markdown_title(fs):
    fs.create_file("/tmp/test.md", contents="# Title\n## Sub\nContent")
    node: MarkdownTextFileProtocol = MarkdownTextFileNode(
        file_path=Path("/tmp/test.md")
    )
    found = node.recursive_find_title_node_by_name("## Sub")
    assert found is not None
    assert found.title == "Sub"


def test_numbered_protocol_returns_numbered_title(fs):
    fs.create_file("/tmp/test.md", contents="# 1. Title\n## 1.1. Sub\nContent")
    node: NumberedMarkdownTextFileProtocol = NumberedMarkdownTextFileNode(
        file_path=Path("/tmp/test.md")
    )
    found = node.recursive_find_title_node_by_name("## 1.1. Sub")
    assert found is not None
    assert found.number == [1, 1]


def test_foldable_protocol_returns_foldable_title(fs):
    fs.create_file("/tmp/test.md", contents="# 1. Title\n## 1.1. Sub\nContent")
    node: FoldableMarkdownTextFileProtocol = FoldableMarkdownTextFileNode(
        file_path=Path("/tmp/test.md")
    )
    found = node.recursive_find_title_node_by_name("## 1.1. Sub")
    assert found is not None
    assert hasattr(found, "fold_mode")


def test_attributed_protocol_has_attribute(fs):
    content = '---\nauthor: test\nversion: "1.0"\n---\n# 1. Title\nContent'
    fs.create_file("/tmp/attributed.md", contents=content)
    node: AttributedMarkdownTextFileProtocol[_TestAttribute] = (
        AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
        )
    )
    assert node.attribute.author == "test"
