"""extra/langchain/toolkit.py - LangChain BaseToolKit for Dl909MarkdownTree"""

from __future__ import annotations

from langchain_core.tools import ArgsSchema, BaseTool
from pydantic import BaseModel, Field

from ...interface import AttributedMarkdownTextFileBase
from ...permissions import PermissionChecker
from ..tools import (
    append_tool,
    read_tool,
    rename_title_tool,
    replace_lines_tool,
    replace_tool,
    unfold_tool,
)


class _ReadArgs(BaseModel):
    target: str | None = Field(
        None,
        description="Markdown title including level sign (e.g. '# Hello'). Omit for full document.",
    )


class _ReplaceArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    replace_text: str = Field(
        ...,
        description=(
            "Replacement text. May contain one title line matching target's level "
            "(which renames the title), or no title line to keep the original title. "
            "Must not contain title lines at a higher level (fewer # signs) than target's level."
        ),
    )


class _AppendArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    append_text: str = Field(
        ...,
        description="Text to append. Must not contain titles at or above target's level.",
    )


class _UnfoldArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")


class _ReplaceLinesArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    old_lines: str = Field(..., description="Original text to replace.")
    new_lines: str = Field(..., description="Replacement text.")


class _RenameTitleArgs(BaseModel):
    target: str = Field(..., description="Markdown title including level sign.")
    new_title_name: str = Field(..., description="New title text (no level sign).")


def _denied_message(exc: PermissionError) -> str:
    return exc.args[0] if exc.args else "permission denied"


class _MarkdownReadTool(BaseTool):
    name: str = "read"
    description: str = "Read the full document or a specific title section."
    args_schema: ArgsSchema | None = _ReadArgs

    def __init__(
        self,
        node: AttributedMarkdownTextFileBase,
        checker: PermissionChecker | None = None,
    ):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str | None = None) -> str:
        try:
            return read_tool(self._node, self._checker, target)
        except PermissionError as e:
            return _denied_message(e)


class _MarkdownReplaceTool(BaseTool):
    name: str = "replace"
    description: str = "Replace the content of a specific title."
    args_schema: ArgsSchema | None = _ReplaceArgs

    def __init__(
        self,
        node: AttributedMarkdownTextFileBase,
        checker: PermissionChecker | None = None,
    ):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, replace_text: str) -> str:
        try:
            return replace_tool(self._node, self._checker, target, replace_text)
        except PermissionError as e:
            return _denied_message(e)


class _MarkdownAppendTool(BaseTool):
    name: str = "append"
    description: str = "Append text to a specific title section."
    args_schema: ArgsSchema | None = _AppendArgs

    def __init__(
        self,
        node: AttributedMarkdownTextFileBase,
        checker: PermissionChecker | None = None,
    ):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, append_text: str) -> str:
        try:
            return append_tool(self._node, self._checker, target, append_text)
        except PermissionError as e:
            return _denied_message(e)


class _MarkdownUnfoldTool(BaseTool):
    name: str = "unfold"
    description: str = "Unfold a foldable title and return its full content."
    args_schema: ArgsSchema | None = _UnfoldArgs

    def __init__(
        self,
        node: AttributedMarkdownTextFileBase,
        checker: PermissionChecker | None = None,
    ):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str) -> str:
        try:
            return unfold_tool(self._node, self._checker, target)
        except PermissionError as e:
            return _denied_message(e)


class _MarkdownReplaceLinesTool(BaseTool):
    name: str = "replace_lines"
    description: str = (
        "Replace specific lines within a title section (fuzzy match supported)."
    )
    args_schema: ArgsSchema | None = _ReplaceLinesArgs

    def __init__(
        self,
        node: AttributedMarkdownTextFileBase,
        checker: PermissionChecker | None = None,
    ):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, old_lines: str, new_lines: str) -> str:
        try:
            return replace_lines_tool(
                self._node, self._checker, target, old_lines, new_lines
            )
        except PermissionError as e:
            return _denied_message(e)


class _MarkdownRenameTitleTool(BaseTool):
    name: str = "rename_title"
    description: str = "Rename a markdown title (keep level sign and number)."
    args_schema: ArgsSchema | None = _RenameTitleArgs

    def __init__(
        self,
        node: AttributedMarkdownTextFileBase,
        checker: PermissionChecker | None = None,
    ):
        super().__init__()
        self._node = node
        self._checker = checker

    def _run(self, target: str, new_title_name: str) -> str:
        try:
            return rename_title_tool(self._node, self._checker, target, new_title_name)
        except PermissionError as e:
            return _denied_message(e)


class MarkdownTreeToolkit:
    """LangChain toolkit wrapping 6 markdown editing tools."""

    def __init__(
        self,
        markdown_node: AttributedMarkdownTextFileBase,
        checker: PermissionChecker | None = None,
    ):
        """Args:
        markdown_node: Any node implementing AttributedMarkdownTextFileProtocol.
        checker: Permission checker (e.g. NodePermissionChecker or
            TitlePathPermissionChecker). None disables permission checks.
        """
        self._node = markdown_node
        self._checker = checker

    def get_tools(self) -> list[BaseTool]:
        return [
            _MarkdownReadTool(self._node, self._checker),
            _MarkdownReplaceTool(self._node, self._checker),
            _MarkdownAppendTool(self._node, self._checker),
            _MarkdownUnfoldTool(self._node, self._checker),
            _MarkdownReplaceLinesTool(self._node, self._checker),
            _MarkdownRenameTitleTool(self._node, self._checker),
        ]