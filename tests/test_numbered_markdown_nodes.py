from pathlib import Path

import pytest

from dl909markdowntree.models.exceptions import (
    IncorrectNumberError,
    InvalidTitleLevelError,
)
from dl909markdowntree.numbered_markdown_nodes import (
    NumberedMarkdownTextFileNode,
    NumberedMarkdownTitleNode,
)
from dl909markdowntree.plain_text_nodes import PlainTextNode


def test_numbered_markdown_title_node():
    test_title_node = NumberedMarkdownTitleNode(
        title="test", level=2, number=[1, 2], auto_correct=False
    )
    assert test_title_node.get_title() == "## 1.2. test"
    with pytest.raises(IncorrectNumberError, match="error number"):
        test_title_node.set_text("test text\n### 1.2.2. test2\ntest text2")
    with pytest.raises(InvalidTitleLevelError, match="too high title level"):
        test_title_node.set_text("test text\n## 1.3. test2")
    test_title_node.set_text("test text\n### 1.2.1. test2\ntest text2")
    assert isinstance(test_title_node.children[0], PlainTextNode)
    assert test_title_node.children[0].get_text() == "test text\n"
    assert isinstance(test_title_node.children[1], NumberedMarkdownTitleNode)
    assert test_title_node.children[1].get_title() == "### 1.2.1. test2"


def test_numbered_markdown_text_node():
    test_text_node = NumberedMarkdownTitleNode.from_text(
        "test text 0\n# 1. test1\n## 1.1. test2\ntest text\n# 2. test2\n## 2.1. test3\ntest text",
        auto_correct=False,
    )
    assert isinstance(test_text_node.children[0], PlainTextNode)
    assert isinstance(test_text_node.children[1], NumberedMarkdownTitleNode)
    with pytest.raises(IncorrectNumberError, match="error number"):
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
    test_text_node = NumberedMarkdownTitleNode.from_text(
        "# 1. Title\nSome text\n## 1.1. Subtitle\nMore text"
    )
    output = test_text_node.get_text()
    assert "# 1. Title" in output
    assert "Some text" in output
    assert "## 1.1. Subtitle" in output
    assert "More text" in output


def test_numbered_markdown_text_node_recursive_find():
    test_text_node = NumberedMarkdownTitleNode.from_text(
        "# 1. Title1\n## 1.1. Subtitle1\n# 2. Title2\n## 2.1. Subtitle2"
    )
    found = test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle1")
    assert found is not None
    assert found.title == "Subtitle1"
    not_found = test_text_node.recursive_find_title_node_by_name("## 3.1. NotExist")
    assert not_found is None


def test_numbered_markdown_text_file_node(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\nContent here\n## 1.1. Sub\nMore content")
    test_file_node = NumberedMarkdownTextFileNode(file_path=path)
    assert test_file_node.file_path == path
    assert isinstance(test_file_node.markdown_text_node, NumberedMarkdownTitleNode)
    assert "# 1. Title" in test_file_node.get_text()


def test_numbered_markdown_text_file_node_save(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\nInitial content")
    test_file_node = NumberedMarkdownTextFileNode(file_path=path)
    test_file_node.set_text("# 1. Title\nModified content\n## 1.1. New section")
    test_file_node.save()
    content = path.read_text(encoding="utf-8")
    assert "# 1. Title" in content
    assert "Modified content" in content
    assert "## 1.1. New section" in content


def test_numbered_markdown_text_file_node_reload(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# 1. Title\nOriginal content")
    test_file_node = NumberedMarkdownTextFileNode(file_path=path)
    path.write_text("# 1. Title\nReloaded content\n## 1.1. New")
    test_file_node.reload()
    assert test_file_node.get_text() == "# 1. Title\nReloaded content\n## 1.1. New\n"


def test_numbered_markdown_text_node_recursive_find_trailing_newline():
    test_text_node = NumberedMarkdownTitleNode.from_text(
        "# 1. Title\n## 1.1. Subtitle\nContent"
    )
    found = test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle\n")
    assert found is not None
    assert found.title == "Subtitle"
    assert found.number == [1, 1]