"""test_base_nodes.py - 基类节点（Node/TextNode/FileNode/PlainTextNode/TextFileNode）测试"""

from pathlib import Path

import pytest

from dl909markdowntree import (
    FileNode,
    InvalidNodeOperationError,
    Node,
    PlainTextFileNode,
    PlainTextNode,
    TextNode,
)

# ─── Node：树结构操作 ──────────────────────────────────────────────────


def test_addchild_wires_parent_and_appends():
    root = Node()
    child = Node()
    root.addchild(child)
    assert child.parent is root
    assert root.children == [child]


def test_addchild_rejects_non_orphan():
    root = Node()
    other = Node()
    child = Node()
    root.addchild(child)
    with pytest.raises(InvalidNodeOperationError):
        other.addchild(child)


def test_dispatch_detaches_from_parent():
    root = Node()
    a = Node()
    b = Node()
    root.addchild(a)
    root.addchild(b)
    a.dispatch()
    assert a.parent is None
    assert root.children == [b]


def test_dispatch_on_orphan_is_noop():
    node = Node()
    node.dispatch()
    assert node.parent is None


# ─── Node：from_self 复制 ─────────────────────────────────────────────


def test_from_self_copies_attributes_and_applies_overrides():
    root = Node()
    child = Node()
    root.addchild(child)
    result = Node.from_self(root, children=[])
    assert result is not root
    assert result.children == []
    assert result.parent is root.parent


def test_from_self_without_overrides_copies_children_list():
    root = Node()
    child = Node()
    root.addchild(child)
    result = Node.from_self(root)
    assert result.children == root.children
    assert result.children is not root.children
    assert result.parent is None


def test_from_self_reparents_shared_children():
    """副本接管共享的子节点：孩子的 parent 必须指向副本，而不是 origin

    否则副本是一棵"反向"的树——对副本的孩子调用 dispatch() 会从 origin
    身上把它摘掉。
    """
    root = Node()
    child = Node()
    root.addchild(child)

    result = Node.from_self(root)

    assert child.parent is result
    child.dispatch()
    assert result.children == []
    assert root.children == [child]  # 原节点仍持有该孩子，只是反向指针已移交副本


def test_from_self_with_empty_children_override_is_detached():
    """传 children=[] 时副本与 origin 完全无关，不牵动任何共享状态"""
    root = Node()
    root.addchild(Node())
    child = root.children[0]

    result = Node.from_self(root, children=[])

    assert result.children == []
    assert child.parent is root


def test_from_self_override_wins_over_copy():
    root = Node()
    root.addchild(Node())
    result = Node.from_self(root, children=[Node()])
    assert result.children is not root.children
    assert len(result.children) == 1


def test_from_self_returns_same_concrete_class():
    node = PlainTextNode("hello")
    result = PlainTextNode.from_self(node, text="world")
    assert isinstance(result, PlainTextNode)
    assert result.get_text() == "world"


# ─── TextNode / FileNode：抽象基类 ─────────────────────────────────────


@pytest.mark.parametrize(
    "cls",
    [TextNode, FileNode],
)
def test_abstract_classes_cannot_be_instantiated(cls):
    with pytest.raises(TypeError):
        cls()


# ─── PlainTextNode ─────────────────────────────────────────────────────


def test_plain_text_node_default_text_is_empty():
    node = PlainTextNode()
    assert node.text == ""
    assert node.get_text() == ""


def test_plain_text_node_init_with_text():
    node = PlainTextNode("hello")
    assert node.get_text() == "hello"


def test_plain_text_node_set_text():
    node = PlainTextNode("before")
    node.set_text("after")
    assert node.get_text() == "after"
    assert node.text == "after"


def test_plain_text_node_str_returns_text():
    node = PlainTextNode("shown")
    assert str(node) == "shown"


# ─── TextFileNode ──────────────────────────────────────────────────────


def test_text_file_node_init_reads_file(tmp_path: Path):
    path = tmp_path / "plain.txt"
    path.write_text("initial content")
    node = PlainTextFileNode(file_path=path)
    assert node.get_text() == "initial content"
    assert isinstance(node.textNode, PlainTextNode)


def test_text_file_node_save_writes_disk(tmp_path: Path):
    plain_file = tmp_path / "plain.txt"
    plain_file.write_text("old")
    node = PlainTextFileNode(file_path=plain_file)
    node.set_text("new content")
    node.save()
    assert plain_file.read_text(encoding="utf-8") == "new content"


def test_text_file_node_reload_rerereads_disk(tmp_path: Path):
    plain_file = tmp_path / "plain.txt"
    plain_file.write_text("first")
    node = PlainTextFileNode(file_path=plain_file)
    plain_file.write_text("second", encoding="utf-8")
    node.reload()
    assert node.get_text() == "second"


def test_text_file_node_init_missing_file_creates_empty(tmp_path: Path):
    path = tmp_path / "not_there.txt"
    node = PlainTextFileNode(file_path=path)
    assert path.exists()
    assert node.get_text() == ""
