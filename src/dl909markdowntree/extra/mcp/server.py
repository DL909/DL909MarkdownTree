"""extra/mcp/server.py - MCP server for Dl909MarkdownTree"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from dl909markdowntree import (
    AttributedMarkdownTextFileBase,
    Permission,
    PermissionChecker,
)
from dl909markdowntree.models.exceptions import MarkdownTreeError
from dl909markdowntree.node import Node

if TYPE_CHECKING:
    from fastmcp import FastMCP


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
        if target:
            node = markdown_node.get_root_title().recursive_find_title_node_by_name(
                target
            )
            if node is None:
                return f"read failed: no title matching '{target}'"
            if checker:
                ok, msg = checker.check_permission(node, Permission.READ)
                if not ok:
                    raise PermissionError(msg)
            return node.get_text()
        return markdown_node.get_text()

    @mcp.tool()
    def replace(target: str, replace_text: str) -> str:
        """Replace the content of a specific title (including its descendants).

        Args:
            target: Markdown title including level sign.
            replace_text: Replacement text. May contain one title line matching target's level,
                or omit it to keep the original title.
        """
        node = markdown_node.get_root_title().recursive_find_title_node_by_name(target)
        if node is None:
            return f"replace failed: no title matching '{target}'"
        if checker:
            ok, msg = checker.check_permission(node, Permission.READ_WRITE)
            if not ok:
                raise PermissionError(msg)
        try:
            node.set_text(replace_text)
            return "replace succeeded"
        except MarkdownTreeError as e:
            return f"replace failed: {e}"

    @mcp.tool()
    def append(target: str, append_text: str) -> str:
        """Append text to a specific title section.

        Args:
            target: Markdown title including level sign.
            append_text: Text to append. Must not contain titles at or above target's level.
        """
        node = markdown_node.get_root_title().recursive_find_title_node_by_name(target)
        if node is None:
            return f"append failed: no title matching '{target}'"
        if checker:
            ok, msg = checker.check_permission(node, Permission.READ_WRITE)
            if not ok:
                raise PermissionError(msg)
        try:
            node.add_text(append_text)
            return "append succeeded"
        except MarkdownTreeError as e:
            return f"append failed: {e}"

    @mcp.tool()
    def unfold(target: str) -> str:
        """Unfold a foldable title and return its full content.

        Args:
            target: Markdown title including level sign.
        """
        node = markdown_node.get_root_title().recursive_find_title_node_by_name(target)
        if node is None:
            return f"unfold failed: no title matching '{target}'"
        if checker:
            ok, msg = checker.check_permission(node, Permission.READ)
            if not ok:
                raise PermissionError(msg)
        try:
            return node.unfold()
        except MarkdownTreeError as e:
            return f"unfold failed: {e}"

    @mcp.tool()
    def replace_lines(target: str, old_lines: str, new_lines: str) -> str:
        """Replace specific lines within a title section (fuzzy match supported).

        Args:
            target: Markdown title including level sign.
            old_lines: Original text to replace (must match exactly or >=80% similarity).
            new_lines: Replacement text.
        """
        from difflib import SequenceMatcher

        node = markdown_node.get_root_title().recursive_find_title_node_by_name(target)
        if node is None:
            return f"replace_lines failed: no title matching '{target}'"
        if checker:
            ok, msg = checker.check_permission(node, Permission.READ_WRITE)
            if not ok:
                raise PermissionError(msg)

        current_text = node.get_text()
        match_count = current_text.count(old_lines)

        if match_count == 0:
            best_ratio = 0.0
            best_start = -1
            best_end = -1
            current_lines = current_text.splitlines(keepends=True)
            old_lines_list = old_lines.splitlines(keepends=True)
            old_count = len(old_lines_list)

            if old_count == 0:
                return "replace_lines failed: old_lines is empty"

            for i in range(len(current_lines) - old_count + 1):
                candidate = "".join(current_lines[i : i + old_count])
                ratio = SequenceMatcher(None, old_lines, candidate).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_start = i
                    best_end = i + old_count

            if best_ratio >= 0.8:
                matched = "".join(current_lines[best_start:best_end])
                try:
                    node.set_text(current_text.replace(matched, new_lines, 1))
                    return "replace_lines succeeded (fuzzy match)"
                except MarkdownTreeError as e:
                    return f"replace_lines failed: {e}"
            else:
                return (
                    "replace_lines failed: no match found (best similarity below 80%)"
                )
        elif match_count > 1:
            return f"replace_lines failed: {match_count} matches found, provide more context"

        try:
            node.set_text(current_text.replace(old_lines, new_lines, 1))
            return "replace_lines succeeded"
        except MarkdownTreeError as e:
            return f"replace_lines failed: {e}"

    @mcp.tool()
    def rename_title(target: str, new_title_name: str) -> str:
        """Rename a markdown title (keep level sign and number).

        Args:
            target: Markdown title including level sign.
            new_title_name: New title text (no level sign or number prefix).
        """
        node = markdown_node.get_root_title().recursive_find_title_node_by_name(target)
        if node is None:
            return f"rename_title failed: no title matching '{target}'"
        if checker:
            ok, msg = checker.check_permission(node, Permission.READ_WRITE)
            if not ok:
                raise PermissionError(msg)
        try:
            node.title = new_title_name
            return "rename_title succeeded"
        except MarkdownTreeError as e:
            return f"rename_title failed: {e}"

    return mcp
