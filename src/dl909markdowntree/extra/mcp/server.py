"""extra/mcp/server.py - MCP server for Dl909MarkdownTree"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ...node import Node
from ...permissions import Permission, PermissionChecker
from ..tools import (
    append_tool,
    read_tool,
    rename_title_tool,
    replace_lines_tool,
    replace_tool,
    unfold_tool,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from ...interface import AttributedMarkdownTextFileBase


def create_mcp_server(
    markdown_node: AttributedMarkdownTextFileBase,
    permissions: Sequence[tuple[Node, Permission]] | None = None,
) -> FastMCP:
    """Create an MCP server exposing 6 markdown editing tools.

    Args:
        markdown_node: Any node implementing AttributedMarkdownTextFileProtocol.
        permissions: Optional permission list forwarded to PermissionChecker.
    """
    from fastmcp import FastMCP

    checker = PermissionChecker(permissions) if permissions else None

    mcp = FastMCP("dl909-markdowntree")

    @mcp.tool()
    def read(target: str | None = None) -> str:
        """Read the full document or a specific title section.

        Args:
            target: Markdown title including level sign (e.g. '# Hello'). Omit for full document.
        """
        return read_tool(markdown_node, checker, target)

    @mcp.tool()
    def replace(target: str, replace_text: str) -> str:
        """Replace the content of a specific title (including its descendants).

        Args:
            target: Markdown title including level sign.
            replace_text: Replacement text. May contain one title line matching target's level
                (which renames the title), or no title line to keep the original title.
                Must not contain title lines at a higher level (fewer # signs) than target's level.
        """
        return replace_tool(markdown_node, checker, target, replace_text)

    @mcp.tool()
    def append(target: str, append_text: str) -> str:
        """Append text to a specific title section.

        Args:
            target: Markdown title including level sign.
            append_text: Text to append. Must not contain titles at or above target's level.
        """
        return append_tool(markdown_node, checker, target, append_text)

    @mcp.tool()
    def unfold(target: str) -> str:
        """Unfold a foldable title and return its full content.

        Args:
            target: Markdown title including level sign.
        """
        return unfold_tool(markdown_node, checker, target)

    @mcp.tool()
    def replace_lines(target: str, old_lines: str, new_lines: str) -> str:
        """Replace specific lines within a title section (fuzzy match supported).

        Args:
            target: Markdown title including level sign.
            old_lines: Original text to replace (must match exactly or >=80% similarity).
            new_lines: Replacement text.
        """
        return replace_lines_tool(markdown_node, checker, target, old_lines, new_lines)

    @mcp.tool()
    def rename_title(target: str, new_title_name: str) -> str:
        """Rename a markdown title (keep level sign and number).

        Args:
            target: Markdown title including level sign.
            new_title_name: New title text (no level sign or number prefix).
        """
        return rename_title_tool(markdown_node, checker, target, new_title_name)

    return mcp