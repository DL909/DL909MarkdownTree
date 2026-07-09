from typing import Self

from pydantic import Field

from pathlib import Path

from .markdown_nodes import (
    MarkdownTextNode,
    MarkdownTitleNode,
    MarkdownTextFileNode,
)
from .plain_text_file_node import PlainTextNode


class NumberedMarkdownTitleNode(MarkdownTitleNode):
    children: list[PlainTextNode | Self] = Field(default_factory=list)  # type: ignore - children type is intentionally narrowed from base class
    level: int = Field(le=6, ge=1)
    title: str = Field()
    number: list[int] = Field()
    auto_correct: bool = Field(default=False)

    # 当所有子节点都是标题节点时返回真
    # 注意当没有子节点时也返回真
    def all_children_are_titles(self) -> bool:
        for child in self.children:
            if isinstance(child, PlainTextNode):
                return False
        return True

    def _get_root_level(self) -> int:
        return self.level

    def _should_consume_first_line(self) -> bool:
        return True

    def _process_first_line_if_needed(self, first_line: str) -> None:
        if first_line.startswith("#" * self.level + " "):
            (_, number, title) = self._parse_title_line(first_line)
            if number is not None and number != self.number:
                raise Exception(f"标题编号不匹配：期望 {self.number}, 得到 {number}")
            self.title = title

    def _parse_title_line(self, line: str) -> tuple[int, list[int] | None, str]:
        level: int = 0
        while line[level] == "#":
            level += 1
        if line[level] != " ":
            raise Exception(f"标题格式错误：{line}")
        index = level + 1

        if len(line) <= index:
            return (level, None, "")

        if line[index] == " ":
            return (level, None, line[index + 1 :])

        while index < len(line) and line[index] != " ":
            index += 1
        number_str = line[level + 1 : index]

        if index >= len(line):
            return (level, None, number_str)

        number_str_list = number_str.split(".")
        if number_str_list[-1] == "":
            number_str_list = number_str_list[:-1]

        try:
            number_list = [int(i) for i in number_str_list]
            return (level, number_list, line[index + 1 :])
        except ValueError:
            return (level, None, line[level + 1 :])

    @staticmethod
    def _parse_title(title_str: str) -> tuple[int, list[int], str]:
        """保持向后兼容的静态方法"""
        level: int = 0
        while title_str[level] == "#":
            level += 1
        if title_str[level] != " ":
            raise Exception(f"标题格式错误：{title_str}")
        index = level + 1
        while title_str[index] != " ":
            index += 1
        number_str = title_str[level + 1 : index]
        number_str_list = number_str.split(".")
        if number_str_list[-1] == "":
            number_str_list = number_str_list[:-1]
        number_list = [int(i) for i in number_str_list]
        return (level, number_list, title_str[index + 1 :])

    def _validate_title_level(self, title_level: int) -> None:
        if title_level <= self.level:
            raise Exception(f"过低等级的标题：{title_level} <= {self.level}")

    def _validate_title_number(
        self,
        level: int,
        number: list[int] | None,
        titles: list,
        line_index: int,
        full_text: str,
    ) -> list[int]:
        temp = titles[level]
        if temp is None:
            sub = 1
            temp = titles[level - sub]
            while temp is None and sub <= level:
                sub += 1
                temp = titles[level - sub]
            if temp is None:
                correct_number = []
                for _ in range(level):
                    correct_number.append(1)
            else:
                if isinstance(temp, NumberedMarkdownTitleNode):
                    correct_number = temp.number.copy()
                else:
                    correct_number = []
                for _ in range(sub):
                    correct_number.append(1)
        else:
            if isinstance(temp, NumberedMarkdownTitleNode):
                correct_number = temp.number.copy()
                correct_number[-1] += 1
            else:
                correct_number = []
                for _ in range(level):
                    correct_number.append(1)
                correct_number[-1] = 1

        if number is None:
            if self.auto_correct:
                return correct_number
            else:
                raise Exception(
                    f"编号标题解析失败：{full_text.splitlines()[line_index]}"
                )

        if number != correct_number:
            if self.auto_correct:
                return correct_number
            else:
                raise Exception(f"{number} isn't {correct_number}")

        return number

    def _create_title_node(
        self, level: int, number: list[int] | None, title: str
    ) -> "NumberedMarkdownTitleNode":
        assert number is not None
        return NumberedMarkdownTitleNode(
            level=level, number=number, title=title, auto_correct=self.auto_correct
        )

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


class NumberedMarkdownTextNode(MarkdownTextNode):
    children: list[PlainTextNode | NumberedMarkdownTitleNode] = Field(  # type: ignore - children type is intentionally narrowed from base class
        default_factory=list
    )
    auto_correct: bool = Field(default=False)

    def recursive_find_title_node_by_name(
        self, title_name: str
    ) -> NumberedMarkdownTitleNode | None:
        """
        recursively find title by name in this title and its children
        params:
            title_name: title name with level sign and no new line before.
        return:
            title node if found, None if failed
        """
        if title_name[-1] == "\n":
            title_name = title_name[:-1]
        else:
            for child in self.children:
                if isinstance(child, NumberedMarkdownTitleNode):
                    if (
                        result := child.recursive_find_title_node_by_name(title_name)
                    ) is not None:
                        return result
        return None

    def add_text(self, text: str) -> None:
        self.set_text(self.get_text() + "\n" + text)

    def _parse_title_line(self, line: str) -> tuple[int, list[int] | None, str]:
        level: int = 0
        while line[level] == "#":
            level += 1
        if line[level] != " ":
            raise Exception(f"标题格式错误：{line}")
        index = level + 1

        if len(line) <= index:
            return (level, None, "")

        if line[index] == " ":
            return (level, None, line[index + 1 :])

        while index < len(line) and line[index] != " ":
            index += 1
        number_str = line[level + 1 : index]

        if index >= len(line):
            return (level, None, number_str)

        number_str_list = number_str.split(".")
        if number_str_list[-1] == "":
            number_str_list = number_str_list[:-1]

        try:
            number_list = [int(i) for i in number_str_list]
            return (level, number_list, line[index + 1 :])
        except ValueError:
            return (level, None, line[level + 1 :])

    def _validate_title_number(
        self,
        level: int,
        number: list[int] | None,
        titles: list,
        line_index: int,
        full_text: str,
    ) -> list[int]:
        temp = titles[level]
        if temp is None:
            sub = 1
            temp = titles[level - sub]
            while temp is None and sub <= level:
                sub += 1
                temp = titles[level - sub]
            if temp is None:
                correct_number = []
                for _ in range(level):
                    correct_number.append(1)
            else:
                if isinstance(temp, NumberedMarkdownTitleNode):
                    correct_number = temp.number.copy()
                else:
                    assert isinstance(temp, NumberedMarkdownTextNode)
                    correct_number = []
                for _ in range(sub):
                    correct_number.append(1)
        else:
            if isinstance(temp, NumberedMarkdownTitleNode):
                correct_number = temp.number.copy()
                correct_number[-1] += 1
            else:
                correct_number = []
                for _ in range(level):
                    correct_number.append(1)
                correct_number[-1] = 1

        if number is None:
            if self.auto_correct:
                return correct_number
            else:
                raise Exception(
                    f"编号标题解析失败：{full_text.splitlines()[line_index]}"
                )

        if number != correct_number:
            if self.auto_correct:
                return correct_number
            else:
                raise Exception(f"{number} isn't {correct_number}")

        return number

    def _create_title_node(
        self, level: int, number: list[int] | None, title: str
    ) -> NumberedMarkdownTitleNode:
        assert number is not None
        return NumberedMarkdownTitleNode(
            level=level, number=number, title=title, auto_correct=self.auto_correct
        )

    def parse_markdown(self, text) -> None:
        self._parse_markdown_core(text)


class NumberedMarkdownTextFileNode(MarkdownTextFileNode):
    markdown_text_node: NumberedMarkdownTextNode = Field()  # type: ignore - children type is intentionally narrowed from base class

    def recursive_find_title_node_by_name(
        self, title_name
    ) -> NumberedMarkdownTitleNode | None:
        return self.markdown_text_node.recursive_find_title_node_by_name(
            title_name=title_name
        )

    def __init__(self, file_path: Path, **kargs):
        with open(file_path, "r", encoding="utf-8") as f:
            markdown_text_node = NumberedMarkdownTextNode(f.read())
        if kargs.get("markdown_text_node"):
            markdown_text_node = kargs.pop("markdown_text_node")
        super().__init__(
            file_path=file_path, markdown_text_node=markdown_text_node, **kargs
        )
