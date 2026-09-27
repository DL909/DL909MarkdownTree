from pathlib import Path
from typing import Self, override

from .exceptions import InvalidNodeOperationError
from .interface import (
    FoldableMarkdownTextFileBase,
    FoldableMarkdownTitleBase,
    FoldMode,
)
from .markdown_nodes import MarkdownTitleNode
from .numbered_markdown_nodes import (
    NumberedMarkdownTextFileNode,
    NumberedMarkdownTitleNode,
)
from .plain_text_nodes import PlainTextNode


class FoldableMarkdownTitleNode(NumberedMarkdownTitleNode, FoldableMarkdownTitleBase):
    children: list[PlainTextNode | FoldableMarkdownTitleBase]  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
    fold_mode: FoldMode

    def __init__(
        self,
        level: int,
        title: str = "",
        number: list[int] | None = None,
        auto_correct: bool = True,
        fold_mode: FoldMode = FoldMode.SHOW_TITLE,
    ) -> None:
        self.fold_mode = fold_mode if level > 0 else FoldMode.SHOW_CHILD
        super().__init__(level, title, number, auto_correct)

    @override
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str:
        text = self.get_title() if self.level > 0 else ""
        if full_text or self.fold_mode == FoldMode.SHOW_CHILD:
            if self.level > 0:
                text += "\n"
            for child in self.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    text += child.get_text(
                        with_fold_info=with_fold_info, full_text=full_text
                    )
                else:
                    text += child.get_text()
        else:
            if with_fold_info:
                have_text = False
                child_title_number = 0
                for child in self.children:
                    if isinstance(child, PlainTextNode):
                        have_text = True
                    if isinstance(child, MarkdownTitleNode):
                        child_title_number += 1
                if have_text:
                    text += " [text folded]"
                if child_title_number > 0:
                    text += f" [{child_title_number if child_title_number <= 10 else '10+'} child title folded]"
            text += "\n"
        return text

    @override
    def add_text(self, text: str, ensure_new_line: bool = True) -> None:
        """基于完整文本追加，避免把折叠视图与折叠标记写回节点"""
        if not text:
            return
        current_text = self.get_text(full_text=True)
        # 空节点的 get_text(full_text=True) 为 ""，下标取字符会 IndexError
        if (
            ensure_new_line
            and current_text
            and not current_text.endswith("\n")
            and not text.startswith("\n")
        ):
            current_text += "\n"
        self.set_text(current_text + text)

    def _collect_descendant_fold_states(
        self,
    ) -> dict[tuple[int, ...], FoldMode]:
        """收集后代折叠状态，键为 (level, *number)"""
        states: dict[tuple[int, ...], FoldMode] = {}

        def _walk(node: FoldableMarkdownTitleNode) -> None:
            for child in node.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    states[(child.level, *child.number)] = child.fold_mode
                    _walk(child)

        _walk(self)
        return states

    def _apply_descendant_fold_states(
        self, states: dict[tuple[int, ...], FoldMode]
    ) -> None:
        def _walk(node: FoldableMarkdownTitleNode) -> None:
            for child in node.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    key = (child.level, *child.number)
                    if key in states:
                        child.fold_mode = states[key]
                    _walk(child)

        _walk(self)

    @override
    def set_text(self, text: str) -> None:
        """重建子节点后恢复后代折叠状态"""
        fold_states = self._collect_descendant_fold_states()
        super().set_text(text)
        self._apply_descendant_fold_states(fold_states)

    def recursive_up_unfold(self) -> None:
        """递归的展开自身与自身的父级标题"""
        self.fold_mode = FoldMode.SHOW_CHILD
        if isinstance(self.parent, FoldableMarkdownTitleNode):
            self.parent.recursive_up_unfold()

    def unfold(self) -> str:
        if (
            self.parent is not None
            and isinstance(self.parent, FoldableMarkdownTitleNode)
            and self.parent.fold_mode not in [FoldMode.SHOW_CHILD]
        ):
            raise InvalidNodeOperationError("parent must be unfolded before unfold")
        self.fold_mode = FoldMode.SHOW_CHILD
        return self.get_text()

    def recursive_unfold(self) -> None:
        """递归的展开自身与自身的子标题"""
        self.fold_mode = FoldMode.SHOW_CHILD
        for child in self.children:
            if isinstance(child, FoldableMarkdownTitleNode):
                child.recursive_unfold()

    def unfold_by_depth(self, depth: int) -> None:
        if depth >= 1:
            if self.fold_mode is FoldMode.SHOW_TITLE:
                self.fold_mode = FoldMode.SHOW_CHILD
            for child in self.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    child.unfold_by_depth(depth - 1)
        elif depth == 0:
            pass
        else:
            raise RuntimeError(f"invalid depth: {depth}")

    @override
    def recursive_find_title_node_by_name(
        self, title_name: str, within_shown: bool = False
    ) -> Self | None:
        """
        recursively find title by name in this title and its children
        params:
            title_name: title name with level sign and no new line before.
            within_shown: if True, only search within shown (unfolded) descendants.
        return:
            title node if found, None if failed
        """
        if title_name and title_name[-1] == "\n":
            title_name = title_name[:-1]
        if self.get_title() == title_name:
            return self
        else:
            if (not within_shown) or (
                within_shown and self.fold_mode == FoldMode.SHOW_CHILD
            ):
                for child in self.children:
                    if (
                        isinstance(child, type(self))
                        and (
                            result := child.recursive_find_title_node_by_name(
                                title_name, within_shown=within_shown
                            )
                        )
                        is not None
                    ):
                        return result
        return None


class FoldableMarkdownTextFileNode(
    NumberedMarkdownTextFileNode, FoldableMarkdownTextFileBase
):
    markdown_text_node: FoldableMarkdownTitleNode  # type: ignore - children type is intentionally narrowed from base class
    markdown_text_node_type = FoldableMarkdownTitleNode

    @override
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str:
        return self.get_root_title().get_text(with_fold_info, full_text)

    @override
    def save_to_file(self, file_path: Path) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.get_text(full_text=True))

    @override
    def get_root_title(self) -> FoldableMarkdownTitleBase:
        return self.markdown_text_node
