"""test_numbered_markdown_nodes_error_recovery.py - 测试编号标题节点解析失败时的内容恢复功能"""

import pytest

from dl909markdowntree.numbered_markdown_nodes import (
    NumberedMarkdownTextNode,
    NumberedMarkdownTitleNode,
)


def test_numbered_title_node_set_text_invalid_level_recovers_content():
    """测试编号标题节点设置文本因标题级别过低失败时，恢复原有内容"""
    title_node = NumberedMarkdownTitleNode(
        title="Root", level=2, number=[1], text="Original content"
    )
    original_text = title_node.get_text()
    original_children_count = len(title_node.children)

    # 尝试设置包含低级别标题的文本（应该失败）
    with pytest.raises(Exception) as exc_info:
        title_node.set_text("# 1. Lower level title")

    assert "过低等级的标题" in str(exc_info.value)

    # 验证内容已恢复
    assert title_node.get_text() == original_text
    assert len(title_node.children) == original_children_count


def test_numbered_title_node_set_text_invalid_number_recovers_content():
    """测试编号标题节点设置文本因编号错误失败时，恢复原有内容"""
    title_node = NumberedMarkdownTitleNode(
        title="Root", level=1, number=[1], auto_correct=False
    )
    title_node.set_text("## 1.1 Valid Child\nContent")
    original_text = title_node.get_text()

    # 尝试设置包含错误编号的文本
    invalid_text = """## 1.1 Valid
Content
## 999.2 Wrong Number"""

    with pytest.raises(Exception) as exc_info:
        title_node.set_text(invalid_text)

    assert "isn't" in str(exc_info.value)

    # 验证内容已恢复
    assert title_node.get_text() == original_text


def test_numbered_text_node_set_text_invalid_number_recovers_content():
    """测试编号文本节点解析失败时恢复原有内容"""
    text_node = NumberedMarkdownTextNode(text="# 1. Title\nContent", auto_correct=False)
    original_text = text_node.get_text()

    # 尝试设置包含错误编号的文本
    invalid_text = """# 1. Valid Title
Content
## 999.1 Wrong Number"""

    with pytest.raises(Exception):
        text_node.set_text(invalid_text)

    # 验证内容已恢复
    assert text_node.get_text() == original_text


def test_numbered_title_node_set_text_empty_title_recovers_content():
    """测试编号标题节点设置空标题失败时恢复原有内容"""
    title_node = NumberedMarkdownTitleNode(
        title="Root", level=1, number=[1], text="Original content"
    )
    original_text = title_node.get_text()

    # 尝试设置空标题（应该失败）
    with pytest.raises(Exception) as exc_info:
        title_node.set_text("#")

    assert "无内容的标题" in str(exc_info.value)

    # 验证内容已恢复
    assert title_node.get_text() == original_text


def test_numbered_text_node_set_text_mid_parse_failure_recovers_content():
    """测试编号文本节点解析中途失败时恢复原有内容"""
    text_node = NumberedMarkdownTextNode(
        text="# 1. Title\nSome content", auto_correct=False
    )
    original_text = text_node.get_text()

    # 尝试设置文本：第一个子标题合法，但第二个编号错误
    invalid_text = """## 1.1 Valid Child
Some content
## 999.2 Invalid Number"""

    with pytest.raises(Exception) as exc_info:
        text_node.set_text(invalid_text)

    assert "isn't" in str(exc_info.value)

    # 验证内容已恢复
    assert text_node.get_text() == original_text


def test_numbered_title_node_set_text_success_no_recovery_needed():
    """测试成功设置文本时不触发恢复逻辑"""
    title_node = NumberedMarkdownTitleNode(
        title="Root", level=1, number=[1], auto_correct=True
    )

    # 设置合法文本应该成功
    title_node.set_text("## 1.1 Child Title\nChild content")

    assert len(title_node.children) == 1
    assert isinstance(title_node.children[0], NumberedMarkdownTitleNode)
    assert title_node.children[0].title == "Child Title"
