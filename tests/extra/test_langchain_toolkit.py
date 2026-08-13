"""Tests for dl909markdowntree.extra.langchain.toolkit"""

import pytest

pytest.importorskip("langchain_core")

from dl909markdowntree import (
    FoldableMarkdownTextFileNode,
    FoldMode,
    MarkdownTextFileNode,
    Permission,
)
from dl909markdowntree.extra.langchain import MarkdownTreeToolkit


def _make_node(tmp_path) -> MarkdownTextFileNode:
    (tmp_path / "doc.md").write_text("# Hello\n\nWorld content.\n")
    return MarkdownTextFileNode(tmp_path / "doc.md")


def test_toolkit_creation(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    assert toolkit is not None


def test_toolkit_get_tools_returns_six(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    assert len(tools) == 6
    tool_names = {t.name for t in tools}
    assert tool_names == {
        "read",
        "replace",
        "append",
        "unfold",
        "replace_lines",
        "rename_title",
    }


def test_toolkit_read_tool_run(tmp_path):
    from langchain_core.tools import BaseTool

    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    read_tool = next(t for t in tools if t.name == "read")
    assert isinstance(read_tool, BaseTool)

    result = read_tool.invoke({"target": None})
    assert "# Hello" in result
    assert "World content." in result


def test_toolkit_tool_schemas(tmp_path):
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


def test_toolkit_read_tool_full_document_permission_denied(tmp_path):
    node = _make_node(tmp_path)
    title_node = node.get_root_title().recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    toolkit = MarkdownTreeToolkit(
        node,
        permissions=[(title_node, Permission.READ_WRITE)],
    )
    tools = toolkit.get_tools()
    read_tool = next(t for t in tools if t.name == "read")
    result = read_tool.invoke({"target": None})
    assert "权限不足" in result


def test_toolkit_replace_tool_auto_saves(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Hello\n\nWorld content.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    replace_tool = next(t for t in tools if t.name == "replace")
    replace_tool.invoke({"target": "# Hello", "replace_text": "# Goodbye\n\nFarewell."})
    assert doc.read_text(encoding="utf-8") == "# Goodbye\n\nFarewell."


def test_toolkit_permission_denied(tmp_path):
    node = _make_node(tmp_path)
    title_node = node.get_root_title().recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    toolkit = MarkdownTreeToolkit(
        node,
        permissions=[(title_node, Permission.DENY)],
    )
    tools = toolkit.get_tools()
    replace_tool = next(t for t in tools if t.name == "replace")

    result = replace_tool.invoke({"target": "# Hello", "replace_text": "# Hacked"})
    assert "权限不足" in result


def test_toolkit_read_tool_target_not_found(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    read_tool = next(t for t in tools if t.name == "read")

    result = read_tool.invoke({"target": "# Nonexistent"})
    assert "read failed" in result


def test_toolkit_replace_tool_run(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    replace_tool = next(t for t in tools if t.name == "replace")

    result = replace_tool.invoke(
        {"target": "# Hello", "replace_text": "# Hi\n\nGreeting."}
    )
    assert "replace succeeded" in result
    assert "# Hi" in node.get_text()
    assert "# Hello" not in node.get_text()


def test_toolkit_replace_tool_target_not_found(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    replace_tool = next(t for t in tools if t.name == "replace")

    result = replace_tool.invoke({"target": "# Nonexistent", "replace_text": "# X"})
    assert "replace failed" in result


def test_toolkit_append_tool_run(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    append_tool = next(t for t in tools if t.name == "append")

    result = append_tool.invoke({"target": "# Hello", "append_text": "Appended."})
    assert "append succeeded" in result
    assert "Appended." in node.get_text()


def test_toolkit_append_tool_target_not_found(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    append_tool = next(t for t in tools if t.name == "append")

    result = append_tool.invoke({"target": "# Nonexistent", "append_text": "X"})
    assert "append failed" in result


def test_toolkit_unfold_tool_run(tmp_path):
    (tmp_path / "fold.md").write_text("# 1. Parent\n## 1.1. Child\nChild content.\n")
    node = FoldableMarkdownTextFileNode(tmp_path / "fold.md")
    root = node.get_root_title()
    parent_title = root.recursive_find_title_node_by_name("# 1. Parent")
    child_title = root.recursive_find_title_node_by_name("## 1.1. Child")
    assert child_title is not None
    child_title.fold_mode = FoldMode.SHOW_TITLE
    if parent_title is not None:
        parent_title.fold_mode = FoldMode.SHOW_CHILD

    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    unfold_tool = next(t for t in tools if t.name == "unfold")

    result = unfold_tool.invoke({"target": "## 1.1. Child"})
    assert "Child content." in result


def test_toolkit_unfold_tool_target_not_found(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    unfold_tool = next(t for t in tools if t.name == "unfold")

    result = unfold_tool.invoke({"target": "# Nonexistent"})
    assert "unfold failed" in result


def test_toolkit_replace_lines_tool_exact_match(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    rl_tool = next(t for t in tools if t.name == "replace_lines")

    result = rl_tool.invoke(
        {
            "target": "# Hello",
            "old_lines": "World content.",
            "new_lines": "Replaced content.",
        }
    )
    assert "replace_lines succeeded" in result
    assert "Replaced content." in node.get_text()


def test_toolkit_replace_lines_tool_fuzzy_match(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    rl_tool = next(t for t in tools if t.name == "replace_lines")

    result = rl_tool.invoke(
        {
            "target": "# Hello",
            "old_lines": "Wrld content.",  # fuzzy: missing 'o'
            "new_lines": "Replaced content.",
        }
    )
    assert "fuzzy match" in result
    assert "Replaced content." in node.get_text()


def test_toolkit_replace_lines_tool_multiple_matches(tmp_path):
    (tmp_path / "dup.md").write_text("# Hello\n\nSame.\nSame.\n")
    node = MarkdownTextFileNode(tmp_path / "dup.md")
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    rl_tool = next(t for t in tools if t.name == "replace_lines")

    result = rl_tool.invoke(
        {
            "target": "# Hello",
            "old_lines": "Same.",
            "new_lines": "X.",
        }
    )
    assert "matches found" in result


def test_toolkit_replace_lines_tool_no_match(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    rl_tool = next(t for t in tools if t.name == "replace_lines")

    result = rl_tool.invoke(
        {
            "target": "# Hello",
            "old_lines": "zzzz_not_there",
            "new_lines": "X.",
        }
    )
    assert "no match found" in result


def test_toolkit_replace_lines_tool_empty_old_lines(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    rl_tool = next(t for t in tools if t.name == "replace_lines")

    result = rl_tool.invoke(
        {
            "target": "# Hello",
            "old_lines": "",
            "new_lines": "X.",
        }
    )
    assert "matches found" in result


def test_toolkit_rename_title_tool_run(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    rename_tool = next(t for t in tools if t.name == "rename_title")

    result = rename_tool.invoke({"target": "# Hello", "new_title_name": "Hi"})
    assert "rename_title succeeded" in result
    assert "# Hi" in node.get_text()
    assert "# Hello" not in node.get_text()


def test_toolkit_rename_title_tool_target_not_found(tmp_path):
    node = _make_node(tmp_path)
    toolkit = MarkdownTreeToolkit(node)
    tools = toolkit.get_tools()
    rename_tool = next(t for t in tools if t.name == "rename_title")

    result = rename_tool.invoke({"target": "# Nonexistent", "new_title_name": "X"})
    assert "rename_title failed" in result


def test_toolkit_append_permission_denied(tmp_path):
    node = _make_node(tmp_path)
    title_node = node.get_root_title().recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    toolkit = MarkdownTreeToolkit(
        node,
        permissions=[(title_node, Permission.READ)],
    )
    tools = toolkit.get_tools()
    append_tool = next(t for t in tools if t.name == "append")

    result = append_tool.invoke({"target": "# Hello", "append_text": "X"})
    assert "权限不足" in result


def test_toolkit_unfold_permission_denied(tmp_path):
    (tmp_path / "fold.md").write_text("# 1. Parent\n## 1.1. Child\nChild content.\n")
    node = FoldableMarkdownTextFileNode(tmp_path / "fold.md")
    child_title = node.get_root_title().recursive_find_title_node_by_name("## 1.1. Child")
    assert child_title is not None
    child_title.fold_mode = FoldMode.SHOW_TITLE

    toolkit = MarkdownTreeToolkit(
        node,
        permissions=[(child_title, Permission.DENY)],
    )
    tools = toolkit.get_tools()
    unfold_tool = next(t for t in tools if t.name == "unfold")

    result = unfold_tool.invoke({"target": "## 1.1. Child"})
    assert "权限不足" in result


def test_toolkit_replace_lines_permission_denied(tmp_path):
    node = _make_node(tmp_path)
    title_node = node.get_root_title().recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    toolkit = MarkdownTreeToolkit(
        node,
        permissions=[(title_node, Permission.DENY)],
    )
    tools = toolkit.get_tools()
    rl_tool = next(t for t in tools if t.name == "replace_lines")

    result = rl_tool.invoke(
        {
            "target": "# Hello",
            "old_lines": "World content.",
            "new_lines": "X.",
        }
    )
    assert "权限不足" in result


def test_toolkit_rename_title_permission_denied(tmp_path):
    node = _make_node(tmp_path)
    title_node = node.get_root_title().recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    toolkit = MarkdownTreeToolkit(
        node,
        permissions=[(title_node, Permission.DENY)],
    )
    tools = toolkit.get_tools()
    rename_tool = next(t for t in tools if t.name == "rename_title")

    result = rename_tool.invoke({"target": "# Hello", "new_title_name": "X"})
    assert "权限不足" in result