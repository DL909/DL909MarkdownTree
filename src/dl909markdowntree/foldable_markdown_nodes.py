from enum import Enum
from typing import Self, override

from dl909markdowntree.interface import (
    FoldableMarkdownTextFileBase,
    FoldableMarkdownTitleBase,
)
from dl909markdowntree.markdown_nodes import MarkdownTitleNode

from .numbered_markdown_nodes import (
    NumberedMarkdownTextFileNode,
    NumberedMarkdownTitleNode,
)
from .plain_text_nodes import PlainTextNode


class FoldMode(Enum):
    SHOW_TITLE = ("show_title",)
    SHOW_CHILD = ("show_child_title",)


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

    def recursive_up_unfold(self) -> None:
        """递归的展开自身与自身的父级标题"""
        if self.fold_mode == FoldMode.SHOW_TITLE:
            self.fold_mode = FoldMode.SHOW_CHILD
            if isinstance(self.parent, FoldableMarkdownTitleNode):
                self.parent.recursive_up_unfold()

    def unfold(self) -> str:
        if self.parent is not None and isinstance(
            self.parent, FoldableMarkdownTitleNode
        ):
            assert self.parent.fold_mode in [
                FoldMode.SHOW_CHILD,
            ]
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
                        isinstance(child, FoldableMarkdownTitleNode)
                        and (
                            result := child.recursive_find_title_node_by_name(
                                title_name, within_shown=within_shown
                            )
                        )
                        is not None
                    ):
                        return result  # pyright: ignore[reportReturnType] - children will be override and fit Self
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
    def get_root_title(self) -> FoldableMarkdownTitleBase:
        return self.markdown_text_node
