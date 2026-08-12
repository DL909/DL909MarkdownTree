from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Self, override

from dl909markdowntree.protocols import (
    NumberedMarkdownTextFileProtocol,
    NumberedMarkdownTitleProtocol,
)

from .markdown_nodes import (
    MarkdownTextFileNode,
    MarkdownTitleNode,
)
from .plain_text_nodes import PlainTextNode


class NumberedMarkdownTitleNode(MarkdownTitleNode, NumberedMarkdownTitleProtocol):
    children: list[PlainTextNode | NumberedMarkdownTitleNode]  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
    number: list[int]
    auto_correct: bool  # correct incorrect number and warn (otherwise will raise)

    @override
    @classmethod
    def from_line(cls, line: str, auto_correct: bool = True) -> Self:
        match = re.match(r"^(#+) ((\d\.)+) (.+)$", line.rstrip("\n"))
        if not match:
            raise Exception()
        return cls(
            level=len(match.group(1)),
            number=[int(x) for x in match.group(2).rstrip(".").split(".")],
            title=match.group(3),
            auto_correct=auto_correct,
        )

    @override
    @classmethod
    def from_text(cls, text: str, auto_correct: bool = True) -> Self:
        result = super().from_text(text)
        result.auto_correct = auto_correct
        return result

    @override
    def __init__(
        self,
        level: int,
        title: str = "",
        number: list[int] | None = None,
        auto_correct: bool = True,
    ) -> None:
        self.number = number if number else []
        self.auto_correct = auto_correct
        super().__init__(level=level, title=title)

    @override
    def _add_title_child_to_children(self, child: Self) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        if isinstance(self.children[-1], NumberedMarkdownTitleNode):
            correct_number = copy.deepcopy(self.children[-1].number)
        else:
            if self.level == 0:
                correct_number = []
            else:
                correct_number = copy.deepcopy(self.number)
        while len(correct_number) > child.level:
            correct_number.append(1)
        while len(correct_number) < child.level:
            correct_number = correct_number[:-1]
        correct_number[-1] += 1

        if correct_number != child.number:
            if self.auto_correct:
                import logging

                logging.getLogger("NumberedMarkdownTitleNode").warning(
                    f"error number in title: {child.get_title()}, expected: {correct_number}, but got: {child.number}, corrected"
                )
                child.number = correct_number
            else:
                raise Exception("error number")
        child.auto_correct = self.auto_correct
        self.children.append(child)

    @override
    def get_title(self, show_level_sign: bool = True) -> str:
        number_part = ""
        for i in self.number:
            number_part += f"{i}."
        return (
            (("#" * self.level + " ") if show_level_sign else "")
            + number_part
            + " "
            + self.title
        )


class NumberedMarkdownTextFileNode(
    MarkdownTextFileNode, NumberedMarkdownTextFileProtocol
):
    markdown_text_node: NumberedMarkdownTitleNode  # type: ignore - children type is intentionally narrowed from base class

    def get_markdown_text_node(self) -> NumberedMarkdownTitleNode:
        return self.markdown_text_node

    def __init__(
        self,
        file_path: Path,
        markdown_text_node: NumberedMarkdownTitleNode | None = None,
    ):
        super().__init__(file_path, markdown_text_node)
