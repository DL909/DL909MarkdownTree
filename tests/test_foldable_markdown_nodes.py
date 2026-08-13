
import pytest

from dl909markdowntree import (
    FoldableMarkdownTextFileNode,
    FoldableMarkdownTitleNode,
    FoldMode,
    IncorrectNumberError,
    InvalidNodeOperationError,
    InvalidNumberedTitleLineError,
    InvalidTitleLevelError,
    PlainTextNode,
)


def test_foldable_markdown_title_node():
    test_title_node = FoldableMarkdownTitleNode(
        level=2, title="test", number=[1, 2], auto_correct=False
    )
    assert test_title_node.get_title() == "## 1.2. test"
    with pytest.raises(IncorrectNumberError, match="error number"):
        test_title_node.set_text("test text\n### 1.2.2. test2\ntest text2")
    with pytest.raises(InvalidTitleLevelError, match="too high title level"):
        test_title_node.set_text("test text\n## 1.3. test2")
    test_title_node.set_text("test text\n### 1.2.1. test2\ntest text2")
    assert isinstance(test_title_node.children[0], PlainTextNode)
    assert test_title_node.children[0].get_text() == "test text\n"
    assert isinstance(test_title_node.children[1], FoldableMarkdownTitleNode)
    assert test_title_node.children[1].get_title() == "### 1.2.1. test2"
    assert test_title_node.fold_mode is FoldMode.SHOW_TITLE
    assert (
        test_title_node.get_text()
        == "## 1.2. test [text folded] [1 child title folded]\n"
    )
    test_title_node.unfold_by_depth(1)
    assert test_title_node.fold_mode is FoldMode.SHOW_CHILD
    assert (
        test_title_node.get_text()
        == "## 1.2. test\ntest text\n### 1.2.1. test2 [text folded]\n"
    )
    assert test_title_node.children[1].unfold() == "### 1.2.1. test2\ntest text2"
    assert (
        test_title_node.get_text()
        == "## 1.2. test\ntest text\n### 1.2.1. test2\ntest text2"
    )


def test_foldable_markdown_text_node():
    test_text_node = FoldableMarkdownTitleNode.from_text(
        "# 1. test\n## 1.1. test2\ntest text\n## 1.2. test3\ntest text2"
    )
    assert test_text_node.get_text() == "# 1. test [2 child title folded]\n"
    title_node = test_text_node.recursive_find_title_node_by_name("# 1. test")
    assert title_node
    assert (
        title_node.unfold()
        == "# 1. test\n## 1.1. test2 [text folded]\n## 1.2. test3 [text folded]\n"
    )


def test_foldable_markdown_title_node_fold_modes():
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    title_node.set_text(
        "## 1.1. Child 1\nContent 1\n## 1.2. Child 2\n### 1.2.1. Grandchild\nContent 2"
    )
    assert title_node.fold_mode is FoldMode.SHOW_TITLE
    text = title_node.get_text()
    assert "# 1. Root" in text
    assert "[2 child title folded]" in text


def test_foldable_markdown_title_node_unfold():
    title_node = FoldableMarkdownTitleNode(level=1, title="Parent", number=[1])
    child = FoldableMarkdownTitleNode(level=2, title="Child", number=[1, 1])
    child.set_text("Grandchild content")
    title_node.addchild(child)
    title_node.fold_mode = FoldMode.SHOW_CHILD
    unfolded = child.unfold()
    assert unfolded == "## 1.1. Child\nGrandchild content"


def test_foldable_markdown_title_node_unfold_folded_parent_raises():
    title_node = FoldableMarkdownTitleNode(level=1, title="Parent", number=[1])
    child = FoldableMarkdownTitleNode(level=2, title="Child", number=[1, 1])
    title_node.addchild(child)
    title_node.fold_mode = FoldMode.SHOW_TITLE
    with pytest.raises(InvalidNodeOperationError):
        child.unfold()


def test_foldable_markdown_title_node_recursive_up_unfold():
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    child = FoldableMarkdownTitleNode(level=2, title="Child", number=[1, 1])
    child.set_text("Grandchild content")
    title_node.addchild(child)
    assert title_node.fold_mode is FoldMode.SHOW_TITLE
    assert child.fold_mode is FoldMode.SHOW_TITLE
    child.recursive_up_unfold()
    assert child.fold_mode is FoldMode.SHOW_CHILD
    assert title_node.fold_mode is FoldMode.SHOW_CHILD


def test_foldable_markdown_title_node_recursive_up_unfold_nested_chain():
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    mid = FoldableMarkdownTitleNode(level=2, title="Mid", number=[1, 1])
    leaf = FoldableMarkdownTitleNode(level=3, title="Leaf", number=[1, 1, 1])
    leaf.set_text("content")
    title_node.addchild(mid)
    mid.addchild(leaf)
    leaf.recursive_up_unfold()
    assert leaf.fold_mode is FoldMode.SHOW_CHILD
    assert mid.fold_mode is FoldMode.SHOW_CHILD
    assert title_node.fold_mode is FoldMode.SHOW_CHILD


def test_foldable_markdown_title_node_recursive_up_unfold_no_parent():
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    title_node.recursive_up_unfold()
    assert title_node.fold_mode is FoldMode.SHOW_CHILD


def test_foldable_markdown_title_node_unfold_by_depth():
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    title_node.set_text("## 1.1. Level1\n### 1.1.1. Level2\n#### 1.1.1.1. Level3")
    title_node.unfold_by_depth(2)
    text = title_node.get_text()
    assert text == "# 1. Root\n## 1.1. Level1\n### 1.1.1. Level2 [1 child title folded]\n"


def test_foldable_markdown_title_node_unfold_by_depth_zero_is_noop():
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    title_node.set_text("## 1.1. Level1\n### 1.1.1. Level2")
    title_node.unfold_by_depth(0)
    text = title_node.get_text()
    assert text == "# 1. Root [1 child title folded]\n"
    assert title_node.fold_mode is FoldMode.SHOW_TITLE


def test_foldable_markdown_title_node_unfold_by_depth_negative_raises():
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    title_node.set_text("## 1.1. Level1")
    with pytest.raises(RuntimeError, match="invalid depth: -1"):
        title_node.unfold_by_depth(-1)


def test_foldable_markdown_text_node_unfold_by_depth_negative_raises():
    test_text_node = FoldableMarkdownTitleNode.from_text(
        "# 1. Title1\n## 1.1. Subtitle1"
    )
    with pytest.raises(RuntimeError, match="invalid depth: -1"):
        test_text_node.unfold_by_depth(-1)


def test_foldable_markdown_text_node_recursive_find():
    test_text_node = FoldableMarkdownTitleNode.from_text(
        "# 1. Title1\n## 1.1. Subtitle1\n# 2. Title2\n## 2.1. Subtitle2"
    )
    found = test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle1")
    assert found is not None
    assert found.title == "Subtitle1"
    assert found.number == [1, 1]
    not_found = test_text_node.recursive_find_title_node_by_name("## 3.1. NotExist")
    assert not_found is None


def test_foldable_markdown_text_node_recursive_find_within_shown():
    test_text_node = FoldableMarkdownTitleNode.from_text(
        "# 1. Title1\n## 1.1. Subtitle1\n# 2. Title2\n## 2.1. Subtitle2"
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
    test_text_node = FoldableMarkdownTitleNode.from_text(
        "# 1. Title\nSome text\n## 1.1. Subtitle\nMore text"
    )
    assert "# 1. Title" in test_text_node.get_text()
    assert "[text folded]" in test_text_node.get_text()


def test_foldable_markdown_text_file_node(tmp_path):
    file_path = tmp_path / "foldable.md"
    file_path.write_text("# 1. Title\nContent here\n## 1.1. Sub\nMore content")
    test_file_node = FoldableMarkdownTextFileNode(file_path=file_path)
    assert test_file_node.file_path == file_path
    assert isinstance(test_file_node.markdown_text_node, FoldableMarkdownTitleNode)
    assert "# 1. Title" in test_file_node.get_text()


def test_foldable_markdown_text_file_node_save(tmp_path):
    file_path = tmp_path / "foldable.md"
    file_path.write_text("# 1. Title\nInitial content")
    test_file_node = FoldableMarkdownTextFileNode(file_path=file_path)
    test_file_node.set_text(
        "# 1. Title\nModified content\n## 1.1. New section\nContent here"
    )
    test_file_node.get_root_title().recursive_unfold()
    test_file_node.save()
    content = file_path.read_text()
    assert "# 1. Title" in content
    assert "Modified content" in content
    assert "## 1.1. New section" in content


def test_foldable_markdown_text_file_node_reload(tmp_path):
    file_path = tmp_path / "foldable.md"
    file_path.write_text("# 1. Title\nOriginal content")
    test_file_node = FoldableMarkdownTextFileNode(file_path=file_path)
    file_path.write_text("# 1. Title\nReloaded content\n## 1.1. New")
    test_file_node.reload()
    assert (
        test_file_node.get_text(with_fold_info=False, full_text=False) == "# 1. Title\n"
    )
    assert (
        test_file_node.get_text(full_text=True)
        == "# 1. Title\nReloaded content\n## 1.1. New\n"
    )


def test_foldable_markdown_title_node_multiple_children():
    title_node = FoldableMarkdownTitleNode(level=1, title="Parent", number=[1])
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
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    title_node.set_text(
        "## 1.1. L2a\n### 1.1.1. L3a\n#### 1.1.1.1. L4a\n## 1.2. L2b\n### 1.2.1. L3b"
    )
    assert len(title_node.children) == 2
    assert len(title_node.children[0].children) == 1
    assert len(title_node.children[0].children[0].children) == 1


class TestFoldableMarkdownAutoCorrect:
    """FoldableMarkdown 自纠正模式测试"""

    def test_foldable_auto_correct_wrong_number(self):
        """测试 FoldableMarkdownTitleNode 错误编号自动纠正"""
        title_node = FoldableMarkdownTitleNode(
            level=1, title="Chapter", number=[1], auto_correct=True
        )
        title_node.set_text("## 1.5. Wrong\n## 1.3. Also Wrong")
        assert len(title_node.children) == 2
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]

    def test_foldable_auto_correct_text_node(self):
        """测试 FoldableMarkdownTitleNode 自动纠正"""
        text_node = FoldableMarkdownTitleNode.from_text(
            "# 9. Title\n## 8.8. Subtitle", auto_correct=True
        )
        assert len(text_node.children) == 1
        assert text_node.children[0].number == [1]
        assert text_node.children[0].children[0].number == [1, 1]

    def test_foldable_auto_correct_get_text(self):
        """测试自动纠正后 get_text() 输出正确编号"""
        text_node = FoldableMarkdownTitleNode.from_text(
            "# 8. Wrong\n## 9.9. Sub\n# 5. Wrong2", auto_correct=True
        )
        output = text_node.get_text(full_text=True)
        assert output == "# 1. Wrong\n## 1.1. Sub\n# 2. Wrong2\n"

    def test_foldable_auto_correct_disabled(self):
        """测试关闭自纠正时保持原有行为"""
        title_node = FoldableMarkdownTitleNode(
            level=1, title="Test", number=[1], auto_correct=False
        )
        with pytest.raises(InvalidNumberedTitleLineError):
            title_node.set_text("## Wrong Number")

    def test_foldable_auto_correct_default_enabled(self):
        """测试默认自纠正是开启的"""
        title_node = FoldableMarkdownTitleNode(level=1, title="Test", number=[1])
        assert title_node.auto_correct is True
        title_node.set_text("## 9.9. Section")
        assert title_node.children[0].number == [1, 1]

    def test_foldable_auto_correct_nested_titles(self):
        """测试嵌套标题自动纠正"""
        title_node = FoldableMarkdownTitleNode(
            level=1, title="Root", number=[1], auto_correct=True
        )
        title_node.set_text(
            "## 3.1. Section 1\n### 3.1.5. Sub 1\n## 3.2. Section 2\n### 3.2.5. Sub 2"
        )
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[0].children[0].number == [1, 1, 1]
        assert title_node.children[1].number == [1, 2]
        assert title_node.children[1].children[0].number == [1, 2, 1]

    def test_foldable_auto_correct_with_fold_mode(self):
        """测试自动纠正与折叠模式共存"""
        title_node = FoldableMarkdownTitleNode(
            level=1, title="Chapter", number=[1], auto_correct=True
        )
        title_node.set_text("## 8.1. Section 1\nContent\n## 8.2. Section 2")
        assert title_node.fold_mode == FoldMode.SHOW_TITLE
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]
        text = title_node.get_text()
        assert "[2 child title folded]" in text


def test_foldable_markdown_text_node_recursive_find_trailing_newline():
    test_text_node = FoldableMarkdownTitleNode.from_text(
        "# 1. Title\n## 1.1. Subtitle\nContent"
    )
    found = test_text_node.recursive_find_title_node_by_name("## 1.1. Subtitle\n")
    assert found is not None
    assert found.title == "Subtitle"
    assert found.number == [1, 1]


def test_foldable_markdown_title_node_within_shown_does_not_leak_folded():
    """折叠的子标题不应在 within_shown=True 时泄露"""
    title_node = FoldableMarkdownTitleNode(level=1, title="Root", number=[1])
    child = FoldableMarkdownTitleNode(level=2, title="Child", number=[1, 1])
    grandchild = FoldableMarkdownTitleNode(
        level=3, title="Grandchild", number=[1, 1, 1]
    )
    child.addchild(grandchild)
    title_node.addchild(child)
    title_node.fold_mode = FoldMode.SHOW_CHILD
    child.fold_mode = FoldMode.SHOW_TITLE
    found = title_node.recursive_find_title_node_by_name(
        "### 1.1.1. Grandchild", within_shown=True
    )
    assert found is None
    found_unrestricted = title_node.recursive_find_title_node_by_name(
        "### 1.1.1. Grandchild", within_shown=False
    )
    assert found_unrestricted is not None