"""test_attributed_markdown_nodes_error_recovery.py - 测试属性化 Markdown 文件节点解析失败时的内容恢复功能"""

from pathlib import Path

import pytest
from pydantic import BaseModel

from dl909markdowntree.attributed_markdown_nodes import (
    AttributedMarkdownTextFileNode,
)
from dl909markdowntree.foldable_markdown_nodes import (
    FoldableMarkdownTitleNode,
)


class ExampleAttribute(BaseModel):
    """测试用的属性类"""

    title: str = "Test"
    tags: list[str] = []


def test_attributed_file_node_set_text_invalid_level_recovers_content(tmp_path):
    """测试属性化文件节点设置文本因编号错误失败时，恢复原有内容"""
    file_path = tmp_path / "test.md"
    file_path.write_text(
        """---
title: Test
tags: []
---
# 1. Title
Content""",
        encoding="utf-8",
    )
    file_node = AttributedMarkdownTextFileNode(
        file_path=file_path,
        attribute_type=ExampleAttribute,
        auto_correct=False,
    )
    # 设置一个合法的子标题
    file_node.set_text("## 1.1. Child Title\nChild content")
    original_text = file_node.get_text()

    # 尝试设置包含错误编号的文本
    invalid_text = """## 1.1. Valid Child
Content
## 999.2. Wrong Number"""

    with pytest.raises(Exception, match="error number"):
        file_node.set_text(invalid_text)

    # 验证内容已恢复
    assert file_node.get_text() == original_text


def test_attributed_file_node_set_text_invalid_number_recovers_content(tmp_path):
    """测试属性化文件节点设置文本因编号错误失败时，恢复原有内容"""
    file_path = tmp_path / "test.md"
    file_path.write_text(
        """---
title: Test
tags: []
---
# 1. Title
Content""",
        encoding="utf-8",
    )
    file_node = AttributedMarkdownTextFileNode(
        file_path=file_path,
        attribute_type=ExampleAttribute,
        auto_correct=False,
    )
    original_text = file_node.get_text()

    # 尝试设置包含错误编号的文本
    invalid_text = """# 1. Valid Title
Content
## 999.1. Wrong Number"""

    with pytest.raises(Exception, match="error number"):
        file_node.set_text(invalid_text)

    # 验证内容已恢复
    assert file_node.get_text() == original_text


def test_attributed_file_node_set_text_empty_title_recovers_content(tmp_path):
    """测试属性化文件节点设置空标题失败时恢复原有内容"""
    file_path = tmp_path / "test.md"
    file_path.write_text(
        """---
title: Test
tags: []
---
# 1. Title
Content""",
        encoding="utf-8",
    )
    file_node = AttributedMarkdownTextFileNode(
        file_path=file_path, attribute_type=ExampleAttribute
    )
    original_text = file_node.get_text()

    # 尝试设置空标题（应该失败）
    with pytest.raises(Exception):
        file_node.set_text("# ")

    # 验证内容已恢复
    assert file_node.get_text() == original_text


def test_attributed_file_node_set_text_mid_parse_failure_recovers_content(tmp_path):
    """测试属性化文件节点解析中途失败时恢复原有内容"""
    file_path = tmp_path / "test.md"
    file_path.write_text(
        """---
title: Test
tags: []
---
# 1. Title
Content
## 1.1. Subtitle
Subcontent""",
        encoding="utf-8",
    )
    file_node = AttributedMarkdownTextFileNode(
        file_path=file_path,
        attribute_type=ExampleAttribute,
        auto_correct=False,
    )
    original_text = file_node.get_text()

    # 尝试设置包含错误编号的复杂文本
    invalid_text = """# 1. Valid Title
Content
## 1.1. Valid Subtitle
Subcontent
## 999.2. Invalid Number"""

    with pytest.raises(Exception, match="error number"):
        file_node.set_text(invalid_text)

    # 验证内容已恢复
    assert file_node.get_text() == original_text


def test_attributed_file_node_set_text_success_no_recovery_needed(tmp_path):
    """测试成功设置文本时不触发恢复逻辑"""
    file_path = tmp_path / "test.md"
    file_path.write_text(
        """---
title: Test
tags: []
---
# 1. Title
Content""",
        encoding="utf-8",
    )
    file_node = AttributedMarkdownTextFileNode(
        file_path=file_path,
        attribute_type=ExampleAttribute,
        auto_correct=True,
    )

    # 设置合法文本应该成功
    file_node.set_text("## 1.1. Child Title\nChild content")

    assert len(file_node.markdown_text_node.children) == 1
    child = file_node.markdown_text_node.children[0]
    assert isinstance(child, FoldableMarkdownTitleNode)
    assert child.title == "Child Title"


def test_attributed_file_node_markdown_text_node_direct_error_recovery(tmp_path):
    """测试属性化文件节点的 markdown_text_node 直接调用 set_text 时的错误恢复"""
    file_path = tmp_path / "test.md"
    file_path.write_text(
        """---
title: Test
tags: []
---
# 1. Title
Content""",
        encoding="utf-8",
    )
    file_node = AttributedMarkdownTextFileNode(
        file_path=file_path, attribute_type=ExampleAttribute
    )
    original_text = file_node.markdown_text_node.get_text()

    # 直接调用 markdown_text_node 的 set_text
    with pytest.raises(Exception):
        file_node.markdown_text_node.set_text("# ")

    # 验证内容已恢复
    assert file_node.markdown_text_node.get_text() == original_text