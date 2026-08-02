"""Tests for dl909markdowntree.extra.langchain.toolkit"""

import pytest

pytest.importorskip("langchain_core")

from pathlib import Path

from dl909markdowntree import (
    MarkdownTextFileNode,
    FoldableMarkdownTextFileNode,
    FoldMode,
    Permission,
    PermissionChecker,
)
from dl909markdowntree.extra.langchain import MarkdownTreeToolkit


def _make_node(tmp_path: Path) -> MarkdownTextFileNode:
    doc = tmp_path / "doc.md"
    doc.write_text("# Hello\n\nWorld content.\n", encoding="utf-8")
    return MarkdownTextFileNode(doc)


def test_toolkit_creation(tmp_path: Path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    assert toolkit is not None


def test_toolkit_get_tools_returns_six(tmp_path: Path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    assert len(tools) == 6
    tool_names = {t.name for t in tools}
    assert tool_names == {"read", "replace", "append", "unfold", "replace_lines", "rename_title"}


def test_toolkit_read_tool_run(tmp_path: Path):
    from langchain_core.tools import BaseTool

    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    read_tool = next(t for t in tools if t.name == "read")
    assert isinstance(read_tool, BaseTool)

    result = read_tool.invoke({"target": None})
    assert "# Hello" in result
    assert "World content." in result


def test_toolkit_tool_schemas(tmp_path: Path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()

    read_tool = next(t for t in tools if t.name == "read")
    schema = read_tool.get_input_schema()
    assert "target" in schema.model_fields

    replace_tool = next(t for t in tools if t.name == "replace")
    schema = replace_tool.get_input_schema()
    assert "target" in schema.model_fields
    assert "replace_text" in schema.model_fields


def test_toolkit_permission_denied(tmp_path: Path):
    node = _make_node(tmp_path)
    title_node = node.recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    toolkit = MarkdownTreeToolkit(
        node,
        permissions=[(title_node, Permission.DENY)],
    )
    tools = toolkit.get_tools()
    replace_tool = next(t for t in tools if t.name == "replace")

    result = replace_tool.invoke({"target": "# Hello", "replace_text": "# Hacked"})
    assert "权限不足" in result
