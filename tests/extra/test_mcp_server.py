"""Tests for dl909markdowntree.extra.mcp.server"""

import pytest

pytest.importorskip("fastmcp")

from pathlib import Path
from unittest.mock import patch

from dl909markdowntree import (
    MarkdownTextFileNode,
    FoldableMarkdownTextFileNode,
    FoldMode,
    Permission,
    PermissionChecker,
)
from dl909markdowntree.extra.mcp import create_mcp_server


def _make_node(tmp_path: Path) -> MarkdownTextFileNode:
    doc = tmp_path / "doc.md"
    doc.write_text("# Hello\n\nWorld content.\n", encoding="utf-8")
    return MarkdownTextFileNode(doc)


def test_create_mcp_server_returns_fastmcp(tmp_path: Path):
    from fastmcp import FastMCP

    node = _make_node(tmp_path)
    server = create_mcp_server(node)
    assert isinstance(server, FastMCP)


def test_mcp_server_has_six_tools(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def list_tools():
        return await server.list_tools()

    tools = asyncio.run(list_tools())
    tool_names = {t.name for t in tools}
    assert tool_names == {"read", "replace", "append", "unfold", "replace_lines", "rename_title"}


def test_mcp_read_tool_full_document(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("read", {})

    result = asyncio.run(call())
    text = result.content[0].text
    assert "# Hello" in text
    assert "World content." in text


def test_mcp_read_tool_with_target(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("read", {"target": "# Hello"})

    result = asyncio.run(call())
    text = result.content[0].text
    assert "Hello" in text


def test_mcp_replace_tool(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        await server.call_tool("replace", {
            "target": "# Hello",
            "replace_text": "# Goodbye\n\nFarewell.",
        })
        return node.get_text()

    text = asyncio.run(call())
    assert "# Goodbye" in text
    assert "# Hello" not in text


def test_mcp_permission_denied(tmp_path: Path):
    import asyncio
    from fastmcp.exceptions import ToolError

    node = _make_node(tmp_path)
    title_node = node.recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    server = create_mcp_server(node, permissions=[(title_node, Permission.DENY)])

    async def call():
        return await server.call_tool("replace", {
            "target": "# Hello",
            "replace_text": "# Hacked",
        })

    with pytest.raises(ToolError, match="权限不足"):
        asyncio.run(call())


def test_mcp_read_tool_target_not_found(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("read", {"target": "# Nonexistent"})

    result = asyncio.run(call())
    text = result.content[0].text
    assert "read failed" in text


def test_mcp_read_tool_permission_denied(tmp_path: Path):
    import asyncio
    from fastmcp.exceptions import ToolError

    node = _make_node(tmp_path)
    title_node = node.recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    server = create_mcp_server(node, permissions=[(title_node, Permission.DENY)])

    async def call():
        return await server.call_tool("read", {"target": "# Hello"})

    with pytest.raises(ToolError, match="权限不足"):
        asyncio.run(call())


def test_mcp_replace_tool_target_not_found(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("replace", {
            "target": "# Nonexistent",
            "replace_text": "# X",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "replace failed" in text


def test_mcp_replace_tool_permission_denied(tmp_path: Path):
    import asyncio
    from fastmcp.exceptions import ToolError

    node = _make_node(tmp_path)
    title_node = node.recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    server = create_mcp_server(node, permissions=[(title_node, Permission.READ)])

    async def call():
        return await server.call_tool("replace", {
            "target": "# Hello",
            "replace_text": "# Hacked",
        })

    with pytest.raises(ToolError, match="权限不足"):
        asyncio.run(call())


def test_mcp_append_tool(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        await server.call_tool("append", {
            "target": "# Hello",
            "append_text": "Appended.",
        })
        return node.get_text()

    text = asyncio.run(call())
    assert "Appended." in text


def test_mcp_append_tool_target_not_found(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("append", {
            "target": "# Nonexistent",
            "append_text": "X",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "append failed" in text


def test_mcp_append_tool_permission_denied(tmp_path: Path):
    import asyncio
    from fastmcp.exceptions import ToolError

    node = _make_node(tmp_path)
    title_node = node.recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    server = create_mcp_server(node, permissions=[(title_node, Permission.READ)])

    async def call():
        return await server.call_tool("append", {
            "target": "# Hello",
            "append_text": "X",
        })

    with pytest.raises(ToolError, match="权限不足"):
        asyncio.run(call())


def test_mcp_unfold_tool(tmp_path: Path):
    import asyncio

    doc = tmp_path / "fold.md"
    doc.write_text("# 1. Parent\n## 1.1. Child\nChild content.\n", encoding="utf-8")
    node = FoldableMarkdownTextFileNode(doc)
    child_title = node.recursive_find_title_node_by_name("## 1.1. Child")
    assert child_title is not None
    child_title.fold_mode = FoldMode.SHOW_TITLE
    parent_title = node.recursive_find_title_node_by_name("# 1. Parent")
    if parent_title is not None:
        parent_title.fold_mode = FoldMode.SHOW_CHILD

    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("unfold", {"target": "## 1.1. Child"})

    result = asyncio.run(call())
    text = result.content[0].text
    assert "Child content." in text


def test_mcp_unfold_tool_target_not_found(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("unfold", {"target": "# Nonexistent"})

    result = asyncio.run(call())
    text = result.content[0].text
    assert "unfold failed" in text


def test_mcp_unfold_tool_permission_denied(tmp_path: Path):
    import asyncio
    from fastmcp.exceptions import ToolError

    doc = tmp_path / "fold.md"
    doc.write_text("# 1. Parent\n## 1.1. Child\nChild content.\n", encoding="utf-8")
    node = FoldableMarkdownTextFileNode(doc)
    child_title = node.recursive_find_title_node_by_name("## 1.1. Child")
    assert child_title is not None
    child_title.fold_mode = FoldMode.SHOW_TITLE
    parent_title = node.recursive_find_title_node_by_name("# 1. Parent")
    if parent_title is not None:
        parent_title.fold_mode = FoldMode.SHOW_CHILD

    server = create_mcp_server(node, permissions=[(child_title, Permission.DENY)])

    async def call():
        return await server.call_tool("unfold", {"target": "## 1.1. Child"})

    with pytest.raises(ToolError, match="权限不足"):
        asyncio.run(call())


def test_mcp_replace_lines_tool_exact_match(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("replace_lines", {
            "target": "# Hello",
            "old_lines": "World content.",
            "new_lines": "Replaced.",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "succeeded" in text


def test_mcp_replace_lines_tool_fuzzy_match(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("replace_lines", {
            "target": "# Hello",
            "old_lines": "Wrld content.",
            "new_lines": "Replaced.",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "fuzzy match" in text


def test_mcp_replace_lines_tool_multiple_matches(tmp_path: Path):
    import asyncio

    doc = tmp_path / "dup.md"
    doc.write_text("# Hello\n\nSame.\nSame.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("replace_lines", {
            "target": "# Hello",
            "old_lines": "Same.",
            "new_lines": "X.",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "matches found" in text


def test_mcp_replace_lines_tool_no_match(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("replace_lines", {
            "target": "# Hello",
            "old_lines": "zzzz_not_there",
            "new_lines": "X.",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "no match found" in text


def test_mcp_replace_lines_tool_empty_old_lines(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("replace_lines", {
            "target": "# Hello",
            "old_lines": "",
            "new_lines": "X.",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "matches found" in text


def test_mcp_replace_lines_tool_permission_denied(tmp_path: Path):
    import asyncio
    from fastmcp.exceptions import ToolError

    node = _make_node(tmp_path)
    title_node = node.recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    server = create_mcp_server(node, permissions=[(title_node, Permission.DENY)])

    async def call():
        return await server.call_tool("replace_lines", {
            "target": "# Hello",
            "old_lines": "World content.",
            "new_lines": "X.",
        })

    with pytest.raises(ToolError, match="权限不足"):
        asyncio.run(call())


def test_mcp_rename_title_tool(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        await server.call_tool("rename_title", {
            "target": "# Hello",
            "new_title_name": "Hi",
        })
        return node.get_text()

    text = asyncio.run(call())
    assert "# Hi" in text
    assert "# Hello" not in text


def test_mcp_rename_title_tool_target_not_found(tmp_path: Path):
    import asyncio

    node = _make_node(tmp_path)
    server = create_mcp_server(node)

    async def call():
        return await server.call_tool("rename_title", {
            "target": "# Nonexistent",
            "new_title_name": "X",
        })

    result = asyncio.run(call())
    text = result.content[0].text
    assert "rename_title failed" in text


def test_mcp_rename_title_tool_permission_denied(tmp_path: Path):
    import asyncio
    from fastmcp.exceptions import ToolError

    node = _make_node(tmp_path)
    title_node = node.recursive_find_title_node_by_name("# Hello")
    assert title_node is not None

    server = create_mcp_server(node, permissions=[(title_node, Permission.READ)])

    async def call():
        return await server.call_tool("rename_title", {
            "target": "# Hello",
            "new_title_name": "X",
        })

    with pytest.raises(ToolError, match="权限不足"):
        asyncio.run(call())
