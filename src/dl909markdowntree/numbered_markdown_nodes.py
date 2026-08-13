from __future__ import annotations

import copy
import logging
import re
from typing import Self, override

from .exceptions import (
    IncorrectNumberError,
    InvalidNumberedTitleLineError,
)
from .interface import (
    NumberedMarkdownTextFileBase,
    NumberedMarkdownTitleBase,
)
from .markdown_nodes import (
    MarkdownTextFileNode,
    MarkdownTitleNode,
)
from .plain_text_nodes import PlainTextNode

logger = logging.getLogger(__name__)


class NumberedMarkdownTitleNode(MarkdownTitleNode, NumberedMarkdownTitleBase):
    children: list[PlainTextNode | NumberedMarkdownTitleNode]  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
    number: list[int]
    auto_correct: bool  # correct incorrect number and warn (otherwise will raise)

    @override
    @classmethod
    def from_line(cls, line: str, auto_correct: bool = True) -> Self:
        match = re.match(r"^(#+) ((?:\d+\.)+) (.+)$", line.rstrip("\n"))
        if not match:
            raise InvalidNumberedTitleLineError(
                f"invalid numbered title line: {line}"
            )
        return cls(
            level=len(match.group(1)),
            number=[int(x) for x in match.group(2).rstrip(".").split(".")],
            title=match.group(3),
            auto_correct=auto_correct,
        )

    @override
    @classmethod
    def from_text(cls, text: str, auto_correct: bool = True) -> Self:
        result = cls(level=0, auto_correct=auto_correct)
        result.set_text(text)
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
        if self.children and isinstance(self.children[-1], NumberedMarkdownTitleNode):
            correct_number = copy.deepcopy(self.children[-1].number)
        else:
            if self.level == 0:
                correct_number = []
            else:
                correct_number = copy.deepcopy(self.number)
        if len(correct_number) < child.level:
            correct_number.extend([1] * (child.level - len(correct_number)))
        else:
            while len(correct_number) > child.level:
                correct_number.pop()
            correct_number[-1] += 1

        if correct_number != child.number:
            if self.auto_correct:
                logger.warning(
                    f"error number in title: {child.get_title()}, expected: {correct_number}, but got: {child.number}, corrected"
                )
                child.number = correct_number
            else:
                raise IncorrectNumberError("error number")
        child.auto_correct = self.auto_correct
        self.children.append(child)
        child.parent = self

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


class NumberedMarkdownTextFileNode(MarkdownTextFileNode, NumberedMarkdownTextFileBase):
    markdown_text_node: NumberedMarkdownTitleNode  # type: ignore - children type is intentionally narrowed from base class
    markdown_text_node_type = NumberedMarkdownTitleNode

    def get_root_title(self) -> NumberedMarkdownTitleBase:
        return self.markdown_text_node
