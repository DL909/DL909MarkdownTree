"""extra/tools.py - MCP 与 LangChain 共用的 Markdown 编辑工具实现"""

from __future__ import annotations

import logging
from collections.abc import Callable
from difflib import SequenceMatcher

from ..exceptions import MarkdownTreeError
from ..interface import AttributedMarkdownTextFileBase, FoldableMarkdownTitleBase
from ..permissions import Permission, PermissionChecker

logger = logging.getLogger(__name__)

# set_text 解析失败（MarkdownTreeError）或保存失败（OSError / RuntimeError）时回滚内存修改
_TOOL_OPERATION_ERRORS = (MarkdownTreeError, OSError, RuntimeError)

# 模糊匹配的相似度下限
_FUZZY_MATCH_THRESHOLD = 0.8


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


def _commit(
    markdown_node: AttributedMarkdownTextFileBase,
    action: Callable[[], str],
    restore: Callable[[], object],
    failure_prefix: str,
) -> str:
    """执行 action() 修改节点并落盘，失败时回滚并返回错误信息

    action 负责改动内存状态并返回成功时给调用方的字符串。回滚本身也必须
    兜住：早先各工具里的 ``except: node.set_text(old_text)`` 是裸调，一旦
    它自己再抛，异常会穿透工具函数，且此时节点已处于半改状态。
    """
    try:
        result = action()
        markdown_node.save()
        return result
    except _TOOL_OPERATION_ERRORS as e:
        try:
            restore()
        except Exception as rollback_error:  # noqa: BLE001 - 回滚失败不能盖掉原始错误
            logger.error(
                "%s failed (%s) and rollback also failed (%s); "
                "the node may be left in a modified state",
                failure_prefix,
                e,
                rollback_error,
            )
        return f"{failure_prefix} failed: {e}"


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
    return _commit(
        markdown_node,
        lambda: node.set_text(replace_text) or "replace succeeded",
        lambda: node.set_text(old_text),
        "replace",
    )


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

    def _append() -> str:
        node.add_text(append_text)
        return "append succeeded"

    return _commit(markdown_node, _append, lambda: node.set_text(old_text), "append")


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
    return _commit(
        markdown_node,
        node.unfold,
        lambda: setattr(node, "fold_mode", old_mode),
        "unfold",
    )


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

    # 必须先于精确匹配判断：非空文本里 "...".count("") 恒大于 1，
    # 否则会落进下面的"多处匹配"分支，报出与真实原因无关的错误
    if not old_lines:
        return "replace_lines failed: old_lines is empty"

    current_text = _get_full_text(node)
    match_count = current_text.count(old_lines)

    def restore() -> None:
        node.set_text(current_text)

    if match_count == 0:
        current_lines = current_text.splitlines(keepends=True)
        old_count = len(old_lines.splitlines(keepends=True))
        best_ratio = 0.0
        best_start = -1
        for i in range(len(current_lines) - old_count + 1):
            candidate = "".join(current_lines[i : i + old_count])
            ratio = SequenceMatcher(None, old_lines, candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i

        if best_ratio < _FUZZY_MATCH_THRESHOLD:
            return "replace_lines failed: no match found (best similarity below 80%)"
        best_end = best_start + old_count
        # 按行号切片替换。早先用 current_text.replace(matched, new_lines, 1)，
        # 替换的是首次出现的位置，而 best_start 是逐行扫描选出的最佳位置，
        # 两者不一定一致——正文含重复行时会改错地方。
        updated = "".join(
            current_lines[:best_start] + [new_lines] + current_lines[best_end:]
        )

        def _fuzzy_replace() -> str:
            node.set_text(updated)
            return "replace_lines succeeded (fuzzy match)"

        return _commit(markdown_node, _fuzzy_replace, restore, "replace_lines")

    if match_count > 1:
        return (
            f"replace_lines failed: {match_count} matches found, provide more context"
        )

    def _exact_replace() -> str:
        node.set_text(current_text.replace(old_lines, new_lines, 1))
        return "replace_lines succeeded"

    return _commit(markdown_node, _exact_replace, restore, "replace_lines")


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

    def _rename() -> str:
        node.title = new_title_name
        if checker is not None:
            # 以标题路径为键的权限条目必须跟着改名重新解析，
            # 否则 DENY 会因路径失配而静默退化成祖先的放行。
            checker.on_node_renamed(node)
        return "rename_title succeeded"

    def _restore_title() -> None:
        node.title = old_title
        if checker is not None:
            # 回滚同样要重绑，否则权限条目会停在一个已不存在的标题上
            checker.on_node_renamed(node)

    return _commit(markdown_node, _rename, _restore_title, "rename_title")
