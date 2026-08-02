from pathlib import Path

import pytest

from dl909markdowntree.numbered_markdown_nodes import (
    NumberedMarkdownTextNode,
    NumberedMarkdownTitleNode,
    NumberedMarkdownTextFileNode,
)
from dl909markdowntree.plain_text_nodes import PlainTextNode


def test_parse_title():
    assert NumberedMarkdownTitleNode._parse_title("### 1.1. test") == (
        3,
        [1, 1],
        "test",
    )


def test_numbered_markdown_title_node():
    test_title_node = NumberedMarkdownTitleNode(title="test", level=2, number=[1, 2])
    assert test_title_node.get_title() == "## 1.2. test"
    with pytest.raises(Exception):
        test_title_node.set_text("test text\n### 1.2.2. test2\ntest text2")
    with pytest.raises(Exception):
        test_title_node.set_text("test text\n## 1.3. test2")
    test_title_node.set_text("test text\n### 1.2.1. test2\ntest text2")
    assert isinstance(test_title_node.children[0], PlainTextNode)
    assert test_title_node.children[0].get_text() == "test text"
    assert isinstance(test_title_node.children[1], NumberedMarkdownTitleNode)
    assert test_title_node.children[1].get_title() == "### 1.2.1. test2"


def test_numbered_markdown_text_node():
    test_text_node = NumberedMarkdownTextNode(
        text="test text 0\n# 1. test1\n## 1.1. test2\ntest text\n# 2. test2\n## 2.1. test3\ntest text"
    )
    assert isinstance(test_text_node.children[0], PlainTextNode)
    assert isinstance(test_text_node.children[1], NumberedMarkdownTitleNode)
    with pytest.raises(Exception):
        test_text_node.add_text("# 2. test5")


def test_numbered_markdown_title_node_hierarchy():
    title_node = NumberedMarkdownTitleNode(title="Chapter 1", level=1, number=[1])
    title_node.set_text(
        "## 1.1. Section 1\nContent 1\n## 1.2. Section 2\n### 1.2.1. Subsection\nContent 2"
    )
    assert len(title_node.children) == 2
    assert title_node.children[0].title == "Section 1"
    assert title_node.children[1].title == "Section 2"
    assert title_node.children[1].children[0].title == "Subsection"


def test_numbered_markdown_text_node_get_text():
    test_text_node = NumberedMarkdownTextNode(
        text="# 1. Title\nSome text\n## 1.1. Subtitle\nMore text"
    )
    output = test_text_node.get_text()
    assert "# 1. Title" in output
    assert "Some text" in output
    assert "## 1.1. Subtitle" in output
    assert "More text" in output


def test_numbered_markdown_text_node_recursive_find():
    test_text_node = NumberedMarkdownTextNode(
        text="# 1. Title1\n## 1.1. Subtitle1\n# 2. Title2\n## 2.1. Subtitle2"
    )
    found = test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle1")
    assert found is not None
    assert found.title == "Subtitle1"
    not_found = test_text_node.recursive_find_title_node_by_name("## 3.1. NotExist")
    assert not_found is None


def test_numbered_markdown_text_file_node(fs):
    fs.create_file(
        "/var/data/test.md",
        contents="# 1. Title\nContent here\n## 1.1. Sub\nMore content",
    )
    test_file_node = NumberedMarkdownTextFileNode(file_path=Path("/var/data/test.md"))
    assert test_file_node.file_path == Path("/var/data/test.md")
    assert isinstance(test_file_node.markdown_text_node, NumberedMarkdownTextNode)
    assert "# 1. Title" in test_file_node.get_text()


def test_numbered_markdown_text_file_node_save(fs):
    fs.create_file("/var/data/test.md", contents="# 1. Title\nInitial content")
    test_file_node = NumberedMarkdownTextFileNode(file_path=Path("/var/data/test.md"))
    test_file_node.set_text("# 1. Title\nModified content\n## 1.1. New section")
    test_file_node.save()
    with open("/var/data/test.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "# 1. Title" in content
    assert "Modified content" in content
    assert "## 1.1. New section" in content


def test_numbered_markdown_text_file_node_reload(fs):
    fs.create_file("/var/data/test.md", contents="# 1. Title\nOriginal content")
    test_file_node = NumberedMarkdownTextFileNode(file_path=Path("/var/data/test.md"))
    fs.remove("/var/data/test.md")
    fs.create_file(
        "/var/data/test.md",
        contents="# 1. Title\nReloaded content\n## 1.1. New",
    )
    test_file_node.reload()
    assert "# 1. Title" in test_file_node.get_text()
    assert "Reloaded content" in test_file_node.get_text()


def test_numbered_markdown_title_node_all_children_are_titles():
    title_node = NumberedMarkdownTitleNode(title="Test", level=1, number=[1])
    assert title_node.all_children_are_titles()
    title_node.addchild(PlainTextNode("some text"))
    assert not title_node.all_children_are_titles()
    title_node.children.clear()
    title_node.addchild(
        NumberedMarkdownTitleNode(title="Child", level=2, number=[1, 1])
    )
    assert title_node.all_children_are_titles()
