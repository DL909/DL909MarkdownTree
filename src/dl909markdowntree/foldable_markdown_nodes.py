from enum import Enum
from pathlib import Path
from typing import override, Self

from pydantic import Field

from .numbered_markdown_nodes import (
    NumberedMarkdownTextNode,
    NumberedMarkdownTitleNode,
    NumberedMarkdownTextFileNode,
)
from .plain_text_nodes import PlainTextNode


class FoldMode(Enum):
    SHOW_TITLE = ("show_title",)
    SHOW_CHILD = ("show_child_title",)


class FoldableMarkdownTitleNode(NumberedMarkdownTitleNode):
    fold_mode: FoldMode = Field(default=FoldMode.SHOW_TITLE)
    auto_correct: bool = Field(default=True)

    @override
    def add_text(self, text: str, **kwargs) -> None:
        self.set_text(self.get_text(full_text=True, **kwargs) + "\n" + text, **kwargs)

    @override
    def get_text(self, with_fold_info: bool = True, full_text=False, **kwargs) -> str:
        if full_text:
            text = self.get_title() + "\n" * 2
            for child in self.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    text += child.get_text(full_text=True, **kwargs) + "\n" * 2
                else:
                    text += child.get_text(**kwargs) + "\n" * 2
        else:
            match self.fold_mode:
                case FoldMode.SHOW_TITLE:
                    text = self.get_title()
                    if with_fold_info:
                        (have_text, child_title_number) = self._get_info()
                        if have_text:
                            text += " [text folded]"
                        if child_title_number > 0:
                            text += f" [{child_title_number if child_title_number <= 10 else '10+'} child title folded]"
                    text += "\n" * 2
                case FoldMode.SHOW_CHILD:
                    text = self.get_title() + "\n" * 2
                    for child in self.children:
                        if isinstance(child, FoldableMarkdownTitleNode):
                            text += (
                                child.get_text(with_fold_info=with_fold_info, **kwargs)
                                + "\n" * 2
                            )
                        else:
                            text += child.get_text(**kwargs) + "\n" * 2

        text = text[:-2]
        return text

    def recursive_up_unfold(self, **kwargs) -> None:
        """递归的展开自身与自身的父级标题"""
        if self.fold_mode == FoldMode.SHOW_TITLE:
            self.fold_mode = FoldMode.SHOW_CHILD
            if isinstance(self.parent, FoldableMarkdownTitleNode):
                self.parent.recursive_up_unfold(**kwargs)

    def unfold(self, **kwargs) -> str:
        if self.parent is not None and isinstance(
            self.parent, FoldableMarkdownTitleNode
        ):
            assert self.parent.fold_mode in [
                FoldMode.SHOW_CHILD,
            ]
        self.fold_mode = FoldMode.SHOW_CHILD
        return self.get_text(**kwargs)

    def recursive_unfold(self, **kwargs) -> None:
        """递归的展开自身与自身的子标题"""
        self.fold_mode = FoldMode.SHOW_CHILD
        for child in self.children:
            if isinstance(child, FoldableMarkdownTitleNode):
                child.recursive_unfold(**kwargs)

    def set_load_depth(self, depth: int, **kwargs) -> None:
        if depth >= 1:
            if self.fold_mode is FoldMode.SHOW_TITLE:
                self.fold_mode = FoldMode.SHOW_CHILD
            for child in self.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    child.set_load_depth(depth - 1)
        elif depth == 0:
            pass
        else:
            raise Exception(f"无效的加载深度：{depth}")

    @override
    def _create_title_node(
        self, level: int, number: list[int] | None, title: str, **kwargs
    ) -> "FoldableMarkdownTitleNode":
        assert number is not None
        return FoldableMarkdownTitleNode(
            level=level,
            number=number,
            title=title,
            auto_correct=self.auto_correct,
            **kwargs,
        )

    @override
    def recursive_find_title_node_by_name(
        self, title_name: str, within_shown: bool = False, **kwargs
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
        if self.get_title(**kwargs) == title_name:
            return self
        else:
            if (not within_shown) or (
                within_shown and self.fold_mode == FoldMode.SHOW_CHILD
            ):
                for child in self.children:
                    if isinstance(child, FoldableMarkdownTitleNode):
                        if (
                            result := child.recursive_find_title_node_by_name(
                                title_name, within_shown=within_shown, **kwargs
                            )
                        ) is not None:
                            return result
        return None


class FoldableMarkdownTextNode(NumberedMarkdownTextNode):
    children: list[PlainTextNode | FoldableMarkdownTitleNode] = Field(  # type: ignore - children type is intentionally narrowed from base class
        default_factory=list
    )
    auto_correct: bool = Field(default=True)

    @override
    def recursive_find_title_node_by_name(
        self, title_name: str, within_shown: bool = False, **kwargs
    ) -> FoldableMarkdownTitleNode | None:
        """
        recursively find title by name in this text node's children
        params:
            title_name: title name with level sign and no new line before.
        return:
            title node if found, None if failed
        """
        if title_name and title_name[-1] == "\n":
            title_name = title_name[:-1]
        for child in self.children:
            if isinstance(child, FoldableMarkdownTitleNode):
                if (
                    result := child.recursive_find_title_node_by_name(
                        title_name, within_shown=within_shown, **kwargs
                    )
                ) is not None:
                    return result
        return None

    @override
    def add_text(self, text: str, **kwargs) -> None:
        self.set_text(self.get_text(full_text=True, **kwargs) + "\n" + text, **kwargs)

    @override
    def _create_title_node(
        self, level: int, number: list[int] | None, title: str, **kwargs
    ) -> FoldableMarkdownTitleNode:
        assert number is not None
        return FoldableMarkdownTitleNode(
            level=level,
            number=number,
            title=title,
            auto_correct=self.auto_correct,
            **kwargs,
        )

    def set_load_depth(self, depth: int, **kwargs) -> None:
        for child in self.children:
            if isinstance(child, FoldableMarkdownTitleNode):
                child.set_load_depth(depth, **kwargs)

    @override
    def get_text(
        self, with_fold_info: bool = True, full_text: bool = False, **kwargs
    ) -> str:
        text = ""
        for child in self.children:
            if isinstance(child, FoldableMarkdownTitleNode):
                text += (
                    child.get_text(
                        with_fold_info=with_fold_info, full_text=full_text, **kwargs
                    )
                    + "\n"
                )
            else:
                text += child.get_text(**kwargs) + "\n"
        if text != "":
            text = text[:-1]
        return text


class FoldableMarkdownTextFileNode(NumberedMarkdownTextFileNode):
    markdown_text_node: FoldableMarkdownTextNode = Field()

    def recursive_find_title_node_by_name(
        self, title_name, within_shown: bool = False, **kwargs
    ) -> FoldableMarkdownTitleNode | None:
        return self.markdown_text_node.recursive_find_title_node_by_name(
            title_name, within_shown=within_shown, **kwargs
        )

    @override
    def get_text(
        self, with_fold_info: bool = True, full_text: bool = False, **kwargs
    ) -> str:
        return self.markdown_text_node.get_text(
            with_fold_info=with_fold_info, full_text=full_text, **kwargs
        )

    @staticmethod
    def create_file(file_path: Path, **kwargs) -> None:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")

    def __init__(self, file_path: Path, **kargs):
        file_path = Path(file_path)
        auto_correct = kargs.pop("auto_correct", True)
        if not file_path.exists():
            self.create_file(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            markdown_text_node = FoldableMarkdownTextNode(
                f.read(), auto_correct=auto_correct
            )
        if kargs.get("markdown_text_node"):
            markdown_text_node = kargs.pop("markdown_text_node")
        super().__init__(
            file_path=file_path, markdown_text_node=markdown_text_node, **kargs
        )

    @override
    def reload(self, **kwargs):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.markdown_text_node = FoldableMarkdownTextNode(f.read())  # type:ignore[override]

    @override
    def save_to_file(self, file_path: Path, **kwargs) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.markdown_text_node.get_text(full_text=True, **kwargs))
