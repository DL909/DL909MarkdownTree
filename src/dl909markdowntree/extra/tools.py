"""extra/tools.py - MCP 与 LangChain 共用的 Markdown 编辑工具实现"""

from __future__ import annotations

from difflib import SequenceMatcher

from ..exceptions import MarkdownTreeError
from ..interface import AttributedMarkdownTextFileBase
from ..permissions import Permission, PermissionChecker


def _find_title_node(
    markdown_node: AttributedMarkdownTextFileBase, target: str
):
    return markdown_node.get_root_title().recursive_find_title_node_by_name(target)


def _check_permission_or_raise(
    checker: PermissionChecker | None, node, required: Permission
) -> None:
    if checker is None:
        return
    ok, msg = checker.check_permission(node, required)
    if not ok:
        raise PermissionError(msg)


def read_tool(
    markdown_node: AttributedMarkdownTextFileBase,
    checker: PermissionChecker | None,
    target: str | None = None,
) -> str:
    """读取全文或指定标题段落。"""
    if target:
        node = _find_title_node(markdown_node, target)
        if node is None:
            return f"read failed: no title matching '{target}'"
        _check_permission_or_raise(checker, node, Permission.READ)
        return node.get_text()
    root = markdown_node.get_root_title()
    _check_permission_or_raise(checker, root, Permission.READ)
    return markdown_node.get_text()


def replace_tool(
    markdown_node: AttributedMarkdownTextFileBase,
    checker: PermissionChecker | None,
    target: str,
    replace_text: str,
) -> str:
    node = _find_title_node(markdown_node, target)
    if node is None:
        return f"replace failed: no title matching '{target}'"
    _check_permission_or_raise(checker, node, Permission.READ_WRITE)
    try:
        node.set_text(replace_text)
        markdown_node.save()
        return "replace succeeded"
    except MarkdownTreeError as e:
        return f"replace failed: {e}"


def append_tool(
    markdown_node: AttributedMarkdownTextFileBase,
    checker: PermissionChecker | None,
    target: str,
    append_text: str,
) -> str:
    node = _find_title_node(markdown_node, target)
    if node is None:
        return f"append failed: no title matching '{target}'"
    _check_permission_or_raise(checker, node, Permission.READ_WRITE)
    try:
        node.add_text(append_text)
        markdown_node.save()
        return "append succeeded"
    except MarkdownTreeError as e:
        return f"append failed: {e}"


def unfold_tool(
    markdown_node: AttributedMarkdownTextFileBase,
    checker: PermissionChecker | None,
    target: str,
) -> str:
    node = _find_title_node(markdown_node, target)
    if node is None:
        return f"unfold failed: no title matching '{target}'"
    _check_permission_or_raise(checker, node, Permission.READ)
    try:
        text = node.unfold()
        markdown_node.save()
        return text
    except MarkdownTreeError as e:
        return f"unfold failed: {e}"


def replace_lines_tool(
    markdown_node: AttributedMarkdownTextFileBase,
    checker: PermissionChecker | None,
    target: str,
    old_lines: str,
    new_lines: str,
) -> str:
    node = _find_title_node(markdown_node, target)
    if node is None:
        return f"replace_lines failed: no title matching '{target}'"
    _check_permission_or_raise(checker, node, Permission.READ_WRITE)

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
                markdown_node.save()
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
        markdown_node.save()
        return "replace_lines succeeded"
    except MarkdownTreeError as e:
        return f"replace_lines failed: {e}"


def rename_title_tool(
    markdown_node: AttributedMarkdownTextFileBase,
    checker: PermissionChecker | None,
    target: str,
    new_title_name: str,
) -> str:
    node = _find_title_node(markdown_node, target)
    if node is None:
        return f"rename_title failed: no title matching '{target}'"
    _check_permission_or_raise(checker, node, Permission.READ_WRITE)
    try:
        node.title = new_title_name
        markdown_node.save()
        return "rename_title succeeded"
    except MarkdownTreeError as e:
        return f"rename_title failed: {e}"