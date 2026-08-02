"""extra/langchain/toolkit.py - LangChain BaseToolKit for Dl909MarkdownTree"""

from __future__ import annotations

from typing import Sequence

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from dl909markdowntree import (
    AttributedMarkdownTextFileProtocol,
    Permission,
    PermissionChecker,
)


class _ReadArgs(BaseModel):
    target: str | None = Field(
        None,
        description="Markdown title including level sign (e.g. '# Hello'). Omit for full document.",
    )


class _ReplaceArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    replace_text: str = Field(..., description="Replacement text.")


class _AppendArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    append_text: str = Field(..., description="Text to append.")


class _UnfoldArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")


class _ReplaceLinesArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    old_lines: str = Field(..., description="Original text to replace.")
    new_lines: str = Field(..., description="Replacement text.")


class _RenameTitleArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    new_title_name: str = Field(..., description="New title text (no level sign).")


class _MarkdownReadTool(BaseTool):
    name: str = "read"
    description: str = "Read the full document or a specific title section."
    args_schema: type[BaseModel] | None = _ReadArgs

    def __init__(self, node: AttributedMarkdownTextFileProtocol, checker: PermissionChecker | None = None):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str | None = None) -> str:
        if self._checker and target:
            t = self._node.recursive_find_title_node_by_name(target)
            if t is None:
                return f"read failed: no title matching '{target}'"
            ok, msg = self._checker.check_permission(t, Permission.READ)
            if not ok:
                return msg

        if target:
            node = self._node.recursive_find_title_node_by_name(target)
            if node is None:
                return f"read failed: no title matching '{target}'"
            return node.get_text()
        return self._node.get_text()


class _MarkdownReplaceTool(BaseTool):
    name: str = "replace"
    description: str = "Replace the content of a specific title."
    args_schema: type[BaseModel] | None = _ReplaceArgs

    def __init__(self, node: AttributedMarkdownTextFileProtocol, checker: PermissionChecker | None = None):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, replace_text: str) -> str:
        if self._checker:
            t = self._node.recursive_find_title_node_by_name(target)
            if t is None:
                return f"replace failed: no title matching '{target}'"
            ok, msg = self._checker.check_permission(t, Permission.READ_WRITE)
            if not ok:
                return msg

        node = self._node.recursive_find_title_node_by_name(target)
        if node is None:
            return f"replace failed: no title matching '{target}'"
        try:
            node.set_text(replace_text)
            return "replace succeeded"
        except Exception as e:
            return f"replace failed: {e}"


class _MarkdownAppendTool(BaseTool):
    name: str = "append"
    description: str = "Append text to a specific title section."
    args_schema: type[BaseModel] | None = _AppendArgs

    def __init__(self, node: AttributedMarkdownTextFileProtocol, checker: PermissionChecker | None = None):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, append_text: str) -> str:
        if self._checker:
            t = self._node.recursive_find_title_node_by_name(target)
            if t is None:
                return f"append failed: no title matching '{target}'"
            ok, msg = self._checker.check_permission(t, Permission.READ_WRITE)
            if not ok:
                return msg

        node = self._node.recursive_find_title_node_by_name(target)
        if node is None:
            return f"append failed: no title matching '{target}'"
        try:
            node.add_text(append_text)
            return "append succeeded"
        except Exception as e:
            return f"append failed: {e}"


class _MarkdownUnfoldTool(BaseTool):
    name: str = "unfold"
    description: str = "Unfold a foldable title and return its full content."
    args_schema: type[BaseModel] | None = _UnfoldArgs

    def __init__(self, node: AttributedMarkdownTextFileProtocol, checker: PermissionChecker | None = None):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str) -> str:
        if self._checker:
            t = self._node.recursive_find_title_node_by_name(target)
            if t is None:
                return f"unfold failed: no title matching '{target}'"
            ok, msg = self._checker.check_permission(t, Permission.READ)
            if not ok:
                return msg

        node = self._node.recursive_find_title_node_by_name(target)
        if node is None:
            return f"unfold failed: no title matching '{target}'"
        try:
            return node.unfold()
        except Exception as e:
            return f"unfold failed: {e}"


class _MarkdownReplaceLinesTool(BaseTool):
    name: str = "replace_lines"
    description: str = "Replace specific lines within a title section (fuzzy match supported)."
    args_schema: type[BaseModel] | None = _ReplaceLinesArgs

    def __init__(self, node: AttributedMarkdownTextFileProtocol, checker: PermissionChecker | None = None):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, old_lines: str, new_lines: str) -> str:
        if self._checker:
            t = self._node.recursive_find_title_node_by_name(target)
            if t is None:
                return f"replace_lines failed: no title matching '{target}'"
            ok, msg = self._checker.check_permission(t, Permission.READ_WRITE)
            if not ok:
                return msg

        from difflib import SequenceMatcher

        node = self._node.recursive_find_title_node_by_name(target)
        if node is None:
            return f"replace_lines failed: no title matching '{target}'"

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
                except Exception as e:
                    return f"replace_lines failed: {e}"
            else:
                return "replace_lines failed: no match found (best similarity below 80%)"
        elif match_count > 1:
            return f"replace_lines failed: {match_count} matches found, provide more context"

        try:
            node.set_text(current_text.replace(old_lines, new_lines, 1))
            return "replace_lines succeeded"
        except Exception as e:
            return f"replace_lines failed: {e}"


class _MarkdownRenameTitleTool(BaseTool):
    name: str = "rename_title"
    description: str = "Rename a markdown title (keep level sign and number)."
    args_schema: type[BaseModel] | None = _RenameTitleArgs

    def __init__(self, node: AttributedMarkdownTextFileProtocol, checker: PermissionChecker | None = None):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, new_title_name: str) -> str:
        if self._checker:
            t = self._node.recursive_find_title_node_by_name(target)
            if t is None:
                return f"rename_title failed: no title matching '{target}'"
            ok, msg = self._checker.check_permission(t, Permission.READ_WRITE)
            if not ok:
                return msg

        node = self._node.recursive_find_title_node_by_name(target)
        if node is None:
            return f"rename_title failed: no title matching '{target}'"
        try:
            node.title = new_title_name
            return "rename_title succeeded"
        except Exception as e:
            return f"rename_title failed: {e}"


class MarkdownTreeToolkit:
    """LangChain toolkit wrapping 6 markdown editing tools."""

    def __init__(
        self,
        markdown_node: AttributedMarkdownTextFileProtocol,
        permissions: Sequence[tuple[object, Permission]] | None = None,
    ):
        self._node = markdown_node
        self._checker = PermissionChecker(permissions) if permissions else None

    def get_tools(self) -> list[BaseTool]:
        return [
            _MarkdownReadTool(self._node, self._checker),
            _MarkdownReplaceTool(self._node, self._checker),
            _MarkdownAppendTool(self._node, self._checker),
            _MarkdownUnfoldTool(self._node, self._checker),
            _MarkdownReplaceLinesTool(self._node, self._checker),
            _MarkdownRenameTitleTool(self._node, self._checker),
        ]
