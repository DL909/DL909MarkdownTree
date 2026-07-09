"""test_numbered_markdown_nodes_auto_correct.py - 自纠正模式测试"""

import pytest

from dl909agentframework.tree_doc.numbered_markdown_nodes import (
    NumberedMarkdownTextNode,
    NumberedMarkdownTitleNode,
)
from dl909agentframework.tree_doc.plain_text_file_node import PlainTextNode


class TestNumberedMarkdownTitleNodeAutoCorrect:
    """NumberedMarkdownTitleNode 自纠正模式测试"""

    def test_auto_correct_missing_number_single_level(self):
        """测试单级标题无编号时自动添加"""
        title_node = NumberedMarkdownTitleNode(
            title="Test", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## Title without number")
        assert len(title_node.children) == 1
        assert title_node.children[0].title == "Title without number"
        assert title_node.children[0].number == [1, 1]

    def test_auto_correct_missing_number_nested(self):
        """测试嵌套标题无编号时自动添加"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter 1", level=1, number=[1], auto_correct=True
        )
        title_node.set_text(
            "## Section 1\n### Subsection 1\n## Section 2\n### Subsection 2"
        )
        assert len(title_node.children) == 2
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[0].title == "Section 1"
        assert title_node.children[1].number == [1, 2]
        assert title_node.children[1].title == "Section 2"
        assert title_node.children[0].children[0].number == [1, 1, 1]
        assert title_node.children[1].children[0].number == [1, 2, 1]

    def test_auto_correct_wrong_number(self):
        """测试错误编号自动修正"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter 1", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## 1.5. Wrong Number\n## 1.3. Another Wrong")
        assert len(title_node.children) == 2
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]

    def test_auto_correct_mixed_correct_and_wrong(self):
        """测试混合正确和错误编号时的处理"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter 1", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## 1.1. Correct\n## 1.5. Wrong\n## 1.3. Should be 1.3")
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]
        assert title_node.children[2].number == [1, 3]

    def test_auto_correct_plain_title_format(self):
        """测试普通标题格式（无编号）自动纠正"""
        title_node = NumberedMarkdownTitleNode(
            title="Root", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## Plain Title\n### Another Plain")
        assert len(title_node.children) == 1
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[0].title == "Plain Title"

    def test_auto_correct_get_title_includes_number(self):
        """测试 get_title() 输出包含正确的编号"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## Section")
        assert title_node.children[0].get_title() == "## 1.1. Section"

    def test_auto_correct_disabled_throws_error_missing_number(self):
        """测试关闭自纠正时，无编号标题抛出异常"""
        title_node = NumberedMarkdownTitleNode(
            title="Test", level=1, number=[1], auto_correct=False
        )
        with pytest.raises(Exception):
            title_node.set_text("## Title without number")

    def test_auto_correct_disabled_throws_error_wrong_number(self):
        """测试关闭自纠正时，错误编号抛出异常"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter 1", level=1, number=[1], auto_correct=False
        )
        with pytest.raises(Exception):
            title_node.set_text("## 1.5. Wrong Number")

    def test_auto_correct_default_is_disabled(self):
        """测试默认自纠正功能是关闭的"""
        title_node = NumberedMarkdownTitleNode(title="Test", level=1, number=[1])
        assert title_node.auto_correct is False
        with pytest.raises(Exception):
            title_node.set_text("## Wrong Number")


class TestNumberedMarkdownTextNodeAutoCorrect:
    """NumberedMarkdownTextNode 自纠正模式测试"""

    def test_auto_correct_text_node_missing_number(self):
        """测试 TextNode 级别无编号自动纠正"""
        text_node = NumberedMarkdownTextNode(
            text="# Title without number", auto_correct=True
        )
        assert len(text_node.children) == 1
        assert text_node.children[0].number == [1]
        assert text_node.children[0].title == "Title without number"

    def test_auto_correct_text_node_wrong_number(self):
        """测试 TextNode 级别错误编号自动纠正"""
        text_node = NumberedMarkdownTextNode(
            text="# 5. Wrong\n# 3. Also Wrong", auto_correct=True
        )
        assert len(text_node.children) == 2
        assert text_node.children[0].number == [1]
        assert text_node.children[1].number == [2]

    def test_auto_correct_text_node_nested(self):
        """测试 TextNode 嵌套标题自动纠正"""
        text_node = NumberedMarkdownTextNode(
            text="# Title\n## Subtitle\n# Another Title\n## Another Subtitle",
            auto_correct=True,
        )
        assert len(text_node.children) == 2
        assert text_node.children[0].number == [1]
        assert text_node.children[0].children[0].number == [1, 1]
        assert text_node.children[1].number == [2]
        assert text_node.children[1].children[0].number == [2, 1]

    def test_auto_correct_text_node_mixed_with_text(self):
        """测试 TextNode 混合文本和标题的自动纠正"""
        text_node = NumberedMarkdownTextNode(
            text="Some intro text\n# Title\nContent\n## Subtitle\nMore content",
            auto_correct=True,
        )
        assert isinstance(text_node.children[0], PlainTextNode)
        assert text_node.children[0].get_text() == "Some intro text"
        assert text_node.children[1].number == [1]
        assert text_node.children[1].children[0].get_text() == "Content"
        assert text_node.children[1].children[1].number == [1, 1]

    def test_auto_correct_text_node_disabled(self):
        """测试 TextNode 关闭自纠正时抛出异常"""
        with pytest.raises(Exception):
            NumberedMarkdownTextNode(text="# Wrong Number", auto_correct=False)

    def test_auto_correct_text_node_default_disabled(self):
        """测试 TextNode 默认自纠正是关闭的"""
        text_node = NumberedMarkdownTextNode(text="# 1. Correct")
        assert text_node.auto_correct is False
        with pytest.raises(Exception):
            text_node.add_text("# Wrong Number")


class TestAutoCorrectEdgeCases:
    """边界情况测试"""

    def test_auto_correct_deep_nesting(self):
        """测试深层嵌套的自动纠正"""
        title_node = NumberedMarkdownTitleNode(
            title="Root", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## L2\n### L3\n#### L4\n##### L5\n###### L6")
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[0].children[0].number == [1, 1, 1]
        assert title_node.children[0].children[0].children[0].number == [
            1,
            1,
            1,
            1,
        ]
        assert title_node.children[0].children[0].children[0].children[0].number == [
            1,
            1,
            1,
            1,
            1,
        ]
        assert title_node.children[0].children[0].children[0].children[0].children[
            0
        ].number == [
            1,
            1,
            1,
            1,
            1,
            1,
        ]

    def test_auto_correct_skip_levels(self):
        """测试跳过级别的标题自动纠正"""
        title_node = NumberedMarkdownTitleNode(
            title="Root", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("#### Skip to L4")
        assert len(title_node.children) == 1
        assert title_node.children[0].number == [1, 1, 1, 1]
        assert title_node.children[0].level == 4

    def test_auto_correct_with_code_block(self):
        """测试代码块内的内容不影响编号"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## Section 1\n```\n# This is code\n```\n## Section 2")
        assert len(title_node.children) == 2
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]
        assert "# This is code" in title_node.children[0].children[0].get_text()

    def test_auto_correct_reset_numbering_at_same_level(self):
        """测试同级标题重新编号"""
        title_node = NumberedMarkdownTitleNode(
            title="Root", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## 1.1. First\n## 1.5. Second\n## 1.3. Third")
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[1].number == [1, 2]
        assert title_node.children[2].number == [1, 3]

    def test_auto_correct_get_text_after_correction(self):
        """测试纠正后 get_text() 输出正确的编号"""
        text_node = NumberedMarkdownTextNode(
            text="# Title\n## Sub\n# Wrong\n## Sub2", auto_correct=True
        )
        output = text_node.get_text()
        assert "# 1. Title" in output
        assert "## 1.1. Sub" in output
        assert "# 2. Wrong" in output
        assert "## 2.1. Sub2" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
