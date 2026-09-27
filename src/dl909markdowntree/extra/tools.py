"""extra/tools.py - MCP 与 LangChain 共用的 Markdown 编辑工具实现"""

from __future__ import annotations

from difflib import SequenceMatcher

from ..exceptions import MarkdownTreeError
from ..interface import AttributedMarkdownTextFileBase, FoldableMarkdownTitleBase
from ..permissions import Permission, PermissionChecker

# set_text 解析失败（MarkdownTreeError）或保存失败（OSError / RuntimeError）时回滚内存修改
_TOOL_OPERATION_ERRORS = (MarkdownTreeError, OSError, RuntimeError)


def _find_title_node(markdown_node: AttributedMarkdownTextFileBase, target: str):
    return markdown_node.get_root_title().recursive_find_title_node_by_name(target)


def _get_full_text(node) -> str:
    """获取包含折叠隐藏内容的完整文本；非折叠节点退回普通 get_text()"""
    if isinstance(node, FoldableMarkdownTitleBase):
        return node.get_text(full_text=True)
    return node.get_text()


def _check_permission_or_raise(
    checker: PermissionChecker | None, node, required: Permission
) -> None:
    if checker is None:
        return
    ok, msg = checker.check_permission(node, required)
    if not ok:
        raise PermissionError(msg)


def _validate_title_text(text: str) -> str | None:
    """校验待写入的标题文本，返回拒绝原因（None 表示通过）。

    标题文本会被原样拼进 ``# <number> <title>`` 这一行。只要不含换行，
    它就不可能凭空变成新的标题节点（行首多一个 ``#`` 只会让标题文本本身
    以 ``#`` 开头，仍是同一个节点），所以这里只需挡掉换行与空标题。
    """
    if not text.strip():
        return "new title is empty"
    if "\n" in text or "\r" in text:
        return "new title must not contain line breaks"
    return None


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
        # 目标标题可能处于折叠态，必须取含折叠内容的完整文本，
        # 否则读到的只是 "[text folded]" 之类的占位符而非正文。
        return _get_full_text(node)
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
    old_text = _get_full_text(node)
    try:
        node.set_text(replace_text)
        markdown_node.save()
        return "replace succeeded"
    except _TOOL_OPERATION_ERRORS as e:
        node.set_text(old_text)
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
    old_text = _get_full_text(node)
    try:
        node.add_text(append_text)
        markdown_node.save()
        return "append succeeded"
    except _TOOL_OPERATION_ERRORS as e:
        node.set_text(old_text)
        return f"append failed: {e}"


def unfold_tool(
    markdown_node: AttributedMarkdownTextFileBase,
    checker: PermissionChecker | None,
    target: str,
) -> str:
    node = _find_title_node(markdown_node, target)
    if node is None:
        return f"unfold failed: no title matching '{target}'"
    # unfold 会改写 fold_mode 并 save()，属于写操作；对文件夹节点还会落盘
    # fold_state.json，因此必须要求 READ_WRITE 而不是 READ。
    _check_permission_or_raise(checker, node, Permission.READ_WRITE)
    if not isinstance(node, FoldableMarkdownTitleBase):
        return f"unfold failed: node '{target}' is not foldable"
    old_mode = node.fold_mode
    try:
        text = node.unfold()
        markdown_node.save()
        return text
    except _TOOL_OPERATION_ERRORS as e:
        node.fold_mode = old_mode
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

    current_text = _get_full_text(node)
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
            old_text = _get_full_text(node)
            try:
                node.set_text(current_text.replace(matched, new_lines, 1))
                markdown_node.save()
                return "replace_lines succeeded (fuzzy match)"
            except _TOOL_OPERATION_ERRORS as e:
                node.set_text(old_text)
                return f"replace_lines failed: {e}"
        else:
            return "replace_lines failed: no match found (best similarity below 80%)"
    elif match_count > 1:
        return (
            f"replace_lines failed: {match_count} matches found, provide more context"
        )

    old_text = _get_full_text(node)
    try:
        node.set_text(current_text.replace(old_lines, new_lines, 1))
        markdown_node.save()
        return "replace_lines succeeded"
    except _TOOL_OPERATION_ERRORS as e:
        node.set_text(old_text)
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
    if (reason := _validate_title_text(new_title_name)) is not None:
        return f"rename_title failed: {reason}"
    old_title = node.title
    try:
        node.title = new_title_name
        markdown_node.save()
        return "rename_title succeeded"
    except _TOOL_OPERATION_ERRORS as e:
        node.title = old_title
        return f"rename_title failed: {e}"
