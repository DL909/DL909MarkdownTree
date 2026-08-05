"""test_base_nodes.py - 基类节点（Node/TextNode/FileNode/PlainTextNode/TextFileNode）测试"""

import pathlib

import pytest

from dl909markdowntree import FileNode, Node, PlainTextNode, TextFileNode, TextNode


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
    with pytest.raises(AssertionError):
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


def test_text_file_node_init_reads_file(fs):
    fs.create_file("/tmp/plain.txt", contents="initial content")
    node = TextFileNode(file_path=pathlib.Path("/tmp/plain.txt"))
    assert node.get_text() == "initial content"
    assert isinstance(node.textNode, PlainTextNode)


def test_text_file_node_save_writes_disk(fs):
    fs.create_file("/tmp/plain.txt", contents="old")
    node = TextFileNode(file_path=pathlib.Path("/tmp/plain.txt"))
    node.set_text("new content")
    node.save()
    assert pathlib.Path("/tmp/plain.txt").read_text(encoding="utf-8") == "new content"


def test_text_file_node_reload_rerereads_disk(fs):
    fs.create_file("/tmp/plain.txt", contents="first")
    node = TextFileNode(file_path=pathlib.Path("/tmp/plain.txt"))
    pathlib.Path("/tmp/plain.txt").write_text("second", encoding="utf-8")
    node.reload()
    assert node.get_text() == "second"


def test_text_file_node_init_missing_file_raises(fs):
    with pytest.raises(FileNotFoundError):
        TextFileNode(file_path=pathlib.Path("/tmp/not_there.txt"))
