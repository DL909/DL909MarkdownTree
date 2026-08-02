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
