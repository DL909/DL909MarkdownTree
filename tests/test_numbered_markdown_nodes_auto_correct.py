"""test_numbered_markdown_nodes_auto_correct.py - 自纠正模式测试"""

import pytest

from dl909markdowntree.models.exceptions import IncorrectNumberError
from dl909markdowntree.numbered_markdown_nodes import (
    NumberedMarkdownTitleNode,
)
from dl909markdowntree.plain_text_nodes import PlainTextNode


class TestNumberedMarkdownTitleNodeAutoCorrect:
    """NumberedMarkdownTitleNode 自纠正模式测试"""

    def test_auto_correct_missing_number_single_level(self):
        """测试单级标题错误编号时自动纠正"""
        title_node = NumberedMarkdownTitleNode(
            title="Test", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## 9.9. Title without number")
        assert len(title_node.children) == 1
        assert title_node.children[0].title == "Title without number"
        assert title_node.children[0].number == [1, 1]

    def test_auto_correct_missing_number_nested(self):
        """测试嵌套标题错误编号时自动纠正"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter 1", level=1, number=[1], auto_correct=True
        )
        title_node.set_text(
            "## 9.9. Section 1\n### 9.9.9. Subsection 1\n## 9.8. Section 2\n### 9.8.9. Subsection 2"
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
        """测试普通标题格式（错误编号）自动纠正"""
        title_node = NumberedMarkdownTitleNode(
            title="Root", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## 9.9. Plain Title\n### 9.9.9. Another Plain")
        assert len(title_node.children) == 1
        assert title_node.children[0].number == [1, 1]
        assert title_node.children[0].title == "Plain Title"

    def test_auto_correct_get_title_includes_number(self):
        """测试 get_title() 输出包含正确的编号"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter", level=1, number=[1], auto_correct=True
        )
        title_node.set_text("## 9.9. Section")
        assert title_node.children[0].get_title() == "## 1.1. Section"

    def test_auto_correct_disabled_throws_error_missing_number(self):
        """测试关闭自纠正时，错误编号标题抛出异常"""
        title_node = NumberedMarkdownTitleNode(
            title="Test", level=1, number=[1], auto_correct=False
        )
        with pytest.raises(IncorrectNumberError, match="error number"):
            title_node.set_text("## 9.9. Title without number")

    def test_auto_correct_disabled_throws_error_wrong_number(self):
        """测试关闭自纠正时，错误编号抛出异常"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter 1", level=1, number=[1], auto_correct=False
        )
        with pytest.raises(IncorrectNumberError, match="error number"):
            title_node.set_text("## 1.5. Wrong Number")

    def test_auto_correct_default_enabled(self):
        """测试默认自纠正功能是开启的"""
        title_node = NumberedMarkdownTitleNode(title="Test", level=1, number=[1])
        assert title_node.auto_correct is True
        title_node.set_text("## 9.9. Wrong Number")


class TestNumberedMarkdownTitleNodeFromTextAutoCorrect:
    """NumberedMarkdownTitleNode.from_text 自纠正模式测试"""

    def test_auto_correct_text_node_missing_number(self):
        """测试 from_text 级别错误编号自动纠正"""
        text_node = NumberedMarkdownTitleNode.from_text(
            text="# 5. Title without number", auto_correct=True
        )
        assert len(text_node.children) == 1
        assert text_node.children[0].number == [1]
        assert text_node.children[0].title == "Title without number"

    def test_auto_correct_text_node_wrong_number(self):
        """测试 from_text 级别错误编号自动纠正"""
        text_node = NumberedMarkdownTitleNode.from_text(
            text="# 5. Wrong\n# 3. Also Wrong", auto_correct=True
        )
        assert len(text_node.children) == 2
        assert text_node.children[0].number == [1]
        assert text_node.children[1].number == [2]

    def test_auto_correct_text_node_nested(self):
        """测试 from_text 嵌套标题自动纠正"""
        text_node = NumberedMarkdownTitleNode.from_text(
            text="# 5. Title\n## 5.5. Subtitle\n# 3. Another Title\n## 3.3. Another Subtitle",
            auto_correct=True,
        )
        assert len(text_node.children) == 2
        assert text_node.children[0].number == [1]
        assert text_node.children[0].children[0].number == [1, 1]
        assert text_node.children[1].number == [2]
        assert text_node.children[1].children[0].number == [2, 1]

    def test_auto_correct_text_node_mixed_with_text(self):
        """测试 from_text 混合文本和标题的自动纠正"""
        text_node = NumberedMarkdownTitleNode.from_text(
            text="Some intro text\n# 5. Title\nContent\n## 5.5. Subtitle\nMore content",
            auto_correct=True,
        )
        assert isinstance(text_node.children[0], PlainTextNode)
        assert text_node.children[0].get_text() == "Some intro text\n"
        assert text_node.children[1].number == [1]
        assert text_node.children[1].children[0].get_text() == "Content\n"
        assert text_node.children[1].children[1].number == [1, 1]

    def test_auto_correct_text_node_disabled(self):
        """测试 from_text 关闭自纠正时抛出异常"""
        with pytest.raises(IncorrectNumberError, match="error number"):
            NumberedMarkdownTitleNode.from_text(
                text="# 5. Wrong Number", auto_correct=False
            )

    def test_auto_correct_text_node_default_enabled(self):
        """测试 from_text 默认自纠正是开启的"""
        text_node = NumberedMarkdownTitleNode.from_text(text="# 1. Correct")
        assert text_node.auto_correct is True
        text_node.add_text("# 9.9. Wrong Number")


class TestAutoCorrectEdgeCases:
    """边界情况测试"""

    def test_auto_correct_deep_nesting(self):
        """测试深层嵌套的自动纠正"""
        title_node = NumberedMarkdownTitleNode(
            title="Root", level=1, number=[1], auto_correct=True
        )
        title_node.set_text(
            "## 9.9. L2\n### 9.9.9. L3\n#### 9.9.9.9. L4\n##### 9.9.9.9.9. L5\n###### 9.9.9.9.9.9. L6"
        )
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
        title_node.set_text("#### 9.9.9.9. Skip to L4")
        assert len(title_node.children) == 1
        assert title_node.children[0].number == [1, 1, 1, 1]
        assert title_node.children[0].level == 4

    def test_auto_correct_with_code_block(self):
        """测试代码块内的内容不影响编号"""
        title_node = NumberedMarkdownTitleNode(
            title="Chapter", level=1, number=[1], auto_correct=True
        )
        title_node.set_text(
            "## 9.9. Section 1\n```\n# This is code\n```\n## 9.8. Section 2"
        )
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
        text_node = NumberedMarkdownTitleNode.from_text(
            text="# 5. Title\n## 5.5. Sub\n# 3. Wrong\n## 3.3. Sub2",
            auto_correct=True,
        )
        output = text_node.get_text()
        assert "# 1. Title" in output
        assert "## 1.1. Sub" in output
        assert "# 2. Wrong" in output
        assert "## 2.1. Sub2" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
