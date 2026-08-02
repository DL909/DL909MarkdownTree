from pathlib import Path

import pytest

from dl909markdowntree.foldable_markdown_nodes import (
    FoldMode,
    FoldableMarkdownTextNode,
    FoldableMarkdownTitleNode,
    FoldableMarkdownTextFileNode,
)
from dl909markdowntree.plain_text_nodes import PlainTextNode


def test_foldable_markdown_title_node():
    test_title_node = FoldableMarkdownTitleNode(
        title="test", level=2, number=[1, 2], auto_correct=False
    )
    assert test_title_node.get_title() == "## 1.2. test"
    with pytest.raises(Exception):
        test_title_node.set_text("test text\n### 1.2.2. test2\ntest text2")
    with pytest.raises(Exception):
        test_title_node.set_text("test text\n## 1.3. test2")
    test_title_node.set_text("test text\n### 1.2.1. test2\ntest text2")
    assert isinstance(test_title_node.children[0], PlainTextNode)
    assert test_title_node.children[0].get_text() == "test text"
    assert isinstance(test_title_node.children[1], FoldableMarkdownTitleNode)
    assert test_title_node.children[1].get_title() == "### 1.2.1. test2"
    assert test_title_node.fold_mode is FoldMode.SHOW_TITLE
    assert (
        test_title_node.get_text()
        == "## 1.2. test [text folded] [1 child title folded]"
    )
    test_title_node.set_load_depth(1)
    assert test_title_node.fold_mode is FoldMode.SHOW_CHILD
    assert (
        test_title_node.get_text()
        == "## 1.2. test\n\ntest text\n\n### 1.2.1. test2 [text folded]"
    )
    assert test_title_node.children[1].unfold() == "### 1.2.1. test2\n\ntest text2"
    assert (
        test_title_node.get_text()
        == "## 1.2. test\n\ntest text\n\n### 1.2.1. test2\n\ntest text2"
    )


def test_foldable_markdown_text_node():
    test_text_node = FoldableMarkdownTextNode(
        text="# 1. test\n## 1.1. test2\ntest text\n## 1.2. test3\ntest text2"
    )
    assert test_text_node.get_text() == "# 1. test [2 child title folded]"
    title_node = test_text_node.recursive_find_title_node_by_name("# 1. test")
    assert title_node
    assert (
        title_node.unfold()
        == "# 1. test\n\n## 1.1. test2 [text folded]\n\n## 1.2. test3 [text folded]"
    )


def test_foldable_markdown_title_node_fold_modes():
    title_node = FoldableMarkdownTitleNode(title="Root", level=1, number=[1])
    title_node.set_text(
        "## 1.1. Child 1\nContent 1\n## 1.2. Child 2\n### 1.2.1. Grandchild\nContent 2"
    )
    assert title_node.fold_mode is FoldMode.SHOW_TITLE
    text = title_node.get_text()
    assert "# 1. Root" in text
    assert "[2 child title folded]" in text


def test_foldable_markdown_title_node_unfold():
    title_node = FoldableMarkdownTitleNode(title="Parent", level=1, number=[1])
    child = FoldableMarkdownTitleNode(title="Child", level=2, number=[1, 1])
    child.set_text("Grandchild content")
    title_node.addchild(child)
    title_node.fold_mode = FoldMode.SHOW_CHILD
    unfolded = child.unfold()
    assert unfolded == "## 1.1. Child\n\nGrandchild content"


def test_foldable_markdown_title_node_set_load_depth():
    title_node = FoldableMarkdownTitleNode(title="Root", level=1, number=[1])
    title_node.set_text("## 1.1. Level1\n### 1.1.1. Level2\n#### 1.1.1.1. Level3")
    title_node.set_load_depth(2)
    text = title_node.get_text()
    assert "## 1.1. Level1" in text
    assert "### 1.1.1. Level2" in text


def test_foldable_markdown_text_node_recursive_find():
    test_text_node = FoldableMarkdownTextNode(
        text="# 1. Title1\n## 1.1. Subtitle1\n# 2. Title2\n## 2.1. Subtitle2"
    )
    found = test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle1")
    assert found is not None
    assert found.title == "Subtitle1"
    assert found.number == [1, 1]
    not_found = test_text_node.recursive_find_title_node_by_name("## 3.1. NotExist")
    assert not_found is None


def test_foldable_markdown_text_node_recursive_find_within_shown():
    test_text_node = FoldableMarkdownTextNode(
        text="# 1. Title1\n## 1.1. Subtitle1\n# 2. Title2\n## 2.1. Subtitle2"
    )
    assert isinstance(test_text_node.children[0], FoldableMarkdownTitleNode)
    assert test_text_node.children[0].fold_mode == FoldMode.SHOW_TITLE
    assert (
        test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle1", True)
        is None
    )
    assert (
        found := test_text_node.recursive_find_title_node_by_name("# 1. Title1")
    ) is not None
    found.unfold()
    assert (
        test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle1", True)
        is not None
    )


def test_foldable_markdown_text_node_get_text():
    test_text_node = FoldableMarkdownTextNode(
        text="# 1. Title\nSome text\n## 1.1. Subtitle\nMore text"
    )
    assert "# 1. Title" in test_text_node.get_text()
    assert "[text folded]" in test_text_node.get_text()


def test_foldable_markdown_text_file_node(fs):
    fs.create_file(
        "/var/data/foldable.md",
        contents="# 1. Title\nContent here\n## 1.1. Sub\nMore content",
    )
    test_file_node = FoldableMarkdownTextFileNode(
        file_path=Path("/var/data/foldable.md")
    )
    assert test_file_node.file_path == Path("/var/data/foldable.md")
    assert isinstance(test_file_node.markdown_text_node, FoldableMarkdownTextNode)
    assert "# 1. Title" in test_file_node.get_text()


def test_foldable_markdown_text_file_node_save(fs):
    fs.create_file("/var/data/foldable.md", contents="# 1. Title\nInitial content")
    test_file_node = FoldableMarkdownTextFileNode(
        file_path=Path("/var/data/foldable.md")
    )
    test_file_node.set_text(
        "# 1. Title\nModified content\n## 1.1. New section\nContent here"
    )
    test_file_node.save()
    with open("/var/data/foldable.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "# 1. Title" in content
    assert "[text folded]" in content or "Modified content" in content


def test_foldable_markdown_text_file_node_reload(fs):
    fs.create_file("/var/data/foldable.md", contents="# 1. Title\nOriginal content")
    test_file_node = FoldableMarkdownTextFileNode(
        file_path=Path("/var/data/foldable.md")
    )
    fs.remove("/var/data/foldable.md")
    fs.create_file(
        "/var/data/foldable.md",
        contents="# 1. Title\nReloaded content\n## 1.1. New",
    )
    test_file_node.reload()
    assert "# 1. Title" in test_file_node.get_text(
        with_fold_info=False, full_text=False
    )
    assert "Reloaded content" in test_file_node.get_text(full_text=True)
    assert "## 1.1. New" in test_file_node.get_text(full_text=True)


def test_foldable_markdown_title_node_multiple_children():
    title_node = FoldableMarkdownTitleNode(title="Parent", level=1, number=[1])
    title_node.set_text(
        "## 1.1. Child1\nText1\n## 1.2. Child2\nText2\n## 1.3. Child3\nText3"
    )
    assert len(title_node.children) == 3
    assert (
        isinstance(title_node.children[0], FoldableMarkdownTitleNode)
        and isinstance(title_node.children[1], FoldableMarkdownTitleNode)
        and isinstance(title_node.children[2], FoldableMarkdownTitleNode)
    )

    assert title_node.children[0].title == "Child1"
    assert title_node.children[1].title == "Child2"
    assert title_node.children[2].title == "Child3"


def test_foldable_markdown_title_node_deep_hierarchy():
    title_node = FoldableMarkdownTitleNode(title="Root", level=1, number=[1])
    title_node.set_text(
        "## 1.1. L2a\n### 1.1.1. L3a\n#### 1.1.1.1. L4a\n## 1.2. L2b\n### 1.2.1. L3b"
    )
    assert len(title_node.children) == 2
    assert len(title_node.children[0].children) == 1
    assert len(title_node.children[0].children[0].children) == 1


class TestFoldableMarkdownAutoCorrect:
    """FoldableMarkdown 自纠正模式测试"""

    def test_foldable_auto_correct_missing_number(self):
        """测试 FoldableMarkdownTitleNode 无编号自动纠正"""
        title_node = FoldableMarkdownTitleNode(
            title="Chapter", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## Section without number")
        assert len(title_node.children) == 1
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[0].title == "Section without number"

    def test_foldable_auto_correct_wrong_number(self):
        """测试 FoldableMarkdownTitleNode 错误编号自动纠正"""
        title_node = FoldableMarkdownTitleNode(
            title="Chapter", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## 1.5. Wrong\n## 1.3. Also Wrong")
        assert len(title_node.children) == 2
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]

    def test_foldable_auto_correct_text_node(self):
        """测试 FoldableMarkdownTextNode 自动纠正"""
        text_node = FoldableMarkdownTextNode(
            text="# Title without number\n## Subtitle", auto_correct=True
        )
        assert len(text_node.children) == 1
        assert text_node.children[0].number == [1]
        assert text_node.children[0].children[0].number == [1, 1]

    def test_foldable_auto_correct_get_text(self):
        """测试自动纠正后 get_text() 输出正确编号"""
        text_node = FoldableMarkdownTextNode(
            text="# Wrong\n## Sub\n# 5. Wrong2", auto_correct=True
        )
        output = text_node.get_text(full_text=True)
        assert "# 1. Wrong" in output
        assert "## 1.1. Sub" in output
        assert "# 2. Wrong2" in output

    def test_foldable_auto_correct_disabled(self):
        """测试关闭自纠正时保持原有行为"""
        title_node = FoldableMarkdownTitleNode(
            title="Test", level=1, number=[1], auto_correct=False
        )
        with pytest.raises(Exception):
            title_node.set_text("## Wrong Number")

    def test_foldable_auto_correct_default_enabled(self):
        """测试默认自纠正是开启的"""
        title_node = FoldableMarkdownTitleNode(title="Test", level=1, number=[1])
        assert title_node.auto_correct is True
        title_node.set_text("## Section")
        assert title_node.children[0].number == [1, 1]

    def test_foldable_auto_correct_nested_titles(self):
        """测试嵌套标题自动纠正"""
        title_node = FoldableMarkdownTitleNode(
            title="Root", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## Section 1\n### Sub 1\n## Section 2\n### Sub 2")
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[0].children[0].number == [1, 1, 1]
        assert title_node.children[1].number == [1, 2]
        assert title_node.children[1].children[0].number == [1, 2, 1]

    def test_foldable_auto_correct_with_fold_mode(self):
        """测试自动纠正与折叠模式共存"""
        title_node = FoldableMarkdownTitleNode(
            title="Chapter", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## Section 1\nContent\n## Section 2")
        assert title_node.fold_mode == FoldMode.SHOW_TITLE
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]
        text = title_node.get_text()
        assert "[2 child title folded]" in text
