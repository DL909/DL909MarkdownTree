"""test_markdown_nodes_error_recovery.py - 测试解析失败时的内容恢复功能"""

import pytest

from dl909agentframework.tree_doc.markdown_nodes import (
    MarkdownTextNode,
    MarkdownTitleNode,
)


def test_title_node_set_text_invalid_level_recovers_content():
    """测试当设置文本因标题级别过低失败时，恢复原有内容"""
    title_node = MarkdownTitleNode(title="Root", level=2, text="Original content")
    original_text = title_node.get_text()
    original_children_count = len(title_node.children)

    # 尝试设置包含低级别标题的文本（应该失败）
    with pytest.raises(Exception) as exc_info:
        title_node.set_text("# Lower level title")

    assert "过低等级的标题" in str(exc_info.value)

    # 验证内容已恢复
    assert title_node.get_text() == original_text
    assert len(title_node.children) == original_children_count
    assert title_node.children[0].get_text() == "Original content"


def test_title_node_set_text_empty_title_recovers_content():
    """测试当设置文本因空标题失败时，恢复原有内容"""
    title_node = MarkdownTitleNode(title="Root", level=1, text="Original content")
    original_text = title_node.get_text()
    original_children_count = len(title_node.children)

    # 尝试设置包含空标题的文本（应该失败）
    with pytest.raises(Exception) as exc_info:
        title_node.set_text("#")

    assert "无内容的标题" in str(exc_info.value)

    # 验证内容已恢复
    assert title_node.get_text() == original_text
    assert len(title_node.children) == original_children_count


def test_text_node_set_text_invalid_title_recovers_content():
    """测试 MarkdownTextNode 在解析失败时恢复原有内容"""
    text_node = MarkdownTextNode(text="# Title\nSome content")
    original_text = text_node.get_text()
    original_children_count = len(text_node.children)

    # 尝试设置包含空标题的文本（应该失败）
    with pytest.raises(Exception) as exc_info:
        text_node.set_text("#")

    assert "无内容的标题" in str(exc_info.value)

    # 验证内容已恢复
    assert text_node.get_text() == original_text
    assert len(text_node.children) == original_children_count


def test_text_node_set_text_mid_parse_failure_recovers_content():
    """测试 MarkdownTextNode 解析中途失败时恢复原有内容"""
    text_node = MarkdownTextNode(text="# Title\nSome content")
    original_text = text_node.get_text()

    # 创建 MarkdownTitleNode 并尝试设置包含低级别标题的文本
    # 对于 MarkdownTextNode，所有级别>=1 的标题都合法
    # 所以我们需要测试其他类型的解析错误
    # 使用无内容的标题作为测试用例
    invalid_text = """# Valid Title
Content
#"""

    with pytest.raises(Exception) as exc_info:
        text_node.set_text(invalid_text)

    assert "无内容的标题" in str(exc_info.value)

    # 验证内容已恢复
    assert text_node.get_text() == original_text


def test_title_node_set_text_success_no_recovery_needed():
    """测试成功设置文本时不触发恢复逻辑"""
    title_node = MarkdownTitleNode(title="Root", level=1)

    # 设置合法文本应该成功
    title_node.set_text("## Child Title\nChild content")

    assert len(title_node.children) == 1
    assert isinstance(title_node.children[0], MarkdownTitleNode)
    assert title_node.children[0].title == "Child Title"


def test_text_node_set_text_complex_structure_recovery():
    """测试复杂结构解析失败时的恢复"""
    text_node = MarkdownTextNode(
        text="""# Title 1
Content 1
## Subtitle 1.1
Subcontent"""
    )
    original_text = text_node.get_text()
    original_children_count = len(text_node.children)

    # 尝试设置包含空标题的复杂文本
    invalid_text = """# Valid Title
Content
## Valid Subtitle
#"""

    with pytest.raises(Exception) as exc_info:
        text_node.set_text(invalid_text)

    assert "无内容的标题" in str(exc_info.value)

    # 验证内容已恢复
    assert text_node.get_text() == original_text
    assert len(text_node.children) == original_children_count
