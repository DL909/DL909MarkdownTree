from pathlib import Path
from typing import Self, override

from pydantic import Field

from .file_node import FileNode
from .plain_text_file_node import PlainTextNode
from .text_node import TextNode
from .markdown_parser_core import _MarkdownParserCore


class MarkdownTitleNode(TextNode, _MarkdownParserCore):
    children: list[PlainTextNode | Self] = Field(default_factory=list)  # type: ignore - children type is intentionally narrowed from base class
    level: int = Field(default=1, le=6, ge=1)
    title: str = Field(default="")

    # 当所有子节点都是标题节点时返回真
    # 注意当没有子节点时也返回真
    def all_children_are_titles(self) -> bool:
        for child in self.children:
            if isinstance(child, PlainTextNode):
                return False
        return True

    def _get_info(self) -> tuple[bool, int]:
        """
        return
            have_text:bool
            child_title_number:int
        """
        return (self._have_text(), self._child_title_number())

    def _have_text(self) -> bool:
        for i in self.children:
            if isinstance(i, PlainTextNode):
                return True
        return False

    def _child_title_number(self) -> int:
        number = 0
        for i in self.children:
            if isinstance(i, MarkdownTitleNode):
                number += 1
        return number

    def __init__(self, title: str, level: int, text: str | None = None, **kargs):
        super().__init__(level=level, title=title, **kargs)
        if text is not None:
            self.set_text(text)

    def set_text(self, text: str) -> None:
        _MarkdownParserCore.set_text(self, text)

    def _get_root_level(self) -> int:
        return self.level

    def _get_root_title(self) -> str | None:
        return self.title

    def _should_consume_first_line(self) -> bool:
        return True

    def _process_first_line_if_needed(self, first_line: str) -> None:
        if first_line.startswith("#" * self.level + " "):
            self.title = first_line[self.level + 1 :]

    def _validate_title_level(self, title_level: int) -> None:
        if title_level <= self.level:
            raise Exception(f"过低等级的标题：{title_level} <= {self.level}")

    def _create_title_node(
        self, level: int, number: list[int] | None, title: str
    ) -> "MarkdownTitleNode":
        return MarkdownTitleNode(title=title, level=level)  # type: ignore[reportAbstractUsage]

    @override
    def get_text(self) -> str:
        text = self.get_title() + "\n" * 2
        for child in self.children:
            text += child.get_text() + "\n" * 2
        text = text[:-2]
        return text

    def get_title(self, show_level_sign: bool = True) -> str:
        return (("#" * self.level + " ") if show_level_sign else "") + self.title

    def recursive_find_title_node_by_name(self, title_name: str) -> Self | None:
        """
        recursively find title by name in this title and its children
        params:
            title_name: title name with level sign and no new line before.
        return:
            title node if found, None if failed
        """
        if title_name[-1] == "\n":
            title_name = title_name[:-1]
        if self.get_title() == title_name:
            return self
        else:
            for child in self.children:
                if isinstance(child, MarkdownTitleNode):
                    if (
                        result := child.recursive_find_title_node_by_name(title_name)
                    ) is not None:
                        return result
        return None

    def add_text(self, text: str) -> None:
        self.set_text(self.get_text() + "\n" + text)


class MarkdownTextNode(TextNode, _MarkdownParserCore):
    children: list[PlainTextNode | MarkdownTitleNode] = Field(default_factory=list)  # type: ignore - children type is intentionally narrowed from base class

    # 当所有子节点都是标题节点时返回真
    # 注意当没有子节点时也返回真
    def all_children_are_titles(self) -> bool:
        for child in self.children:
            if isinstance(child, PlainTextNode):
                return False
        return True

    def recursive_find_title_node_by_name(
        self, title_name: str
    ) -> MarkdownTitleNode | None:
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
                if isinstance(child, MarkdownTitleNode):
                    if (
                        result := child.recursive_find_title_node_by_name(title_name)
                    ) is not None:
                        return result
        return None

    @override
    def get_text(self) -> str:
        text = ""
        for child in self.children:
            text += child.get_text() + "\n" * 2
        if text != "":
            text = text[:-2]
        return text

    @override
    def set_text(self, text) -> None:
        _MarkdownParserCore.set_text(self, text)

    def __init__(self, text: str, **kargs):
        super().__init__(**kargs)
        self.parse_markdown(text)

    def _get_root_level(self) -> int:
        return 0

    def _should_consume_first_line(self) -> bool:
        return False

    def _validate_title_level(self, title_level: int) -> None:
        if title_level < 1:
            raise Exception(f"无效的标题级别：{title_level}")

    def _create_title_node(
        self, level: int, number: list[int] | None, title: str
    ) -> MarkdownTitleNode:
        return MarkdownTitleNode(title=title, level=level)

    def parse_markdown(self, text: str) -> None:
        self._parse_markdown_core(text)


class MarkdownTextFileNode(FileNode, TextNode):
    markdown_text_node: MarkdownTextNode

    def recursive_find_title_node_by_name(self, title_name) -> MarkdownTitleNode | None:
        return self.markdown_text_node.recursive_find_title_node_by_name(
            title_name=title_name
        )

    @override
    def get_text(self) -> str:
        return self.markdown_text_node.get_text()

    @override
    def set_text(self, text) -> None:
        self.markdown_text_node.set_text(text)

    def save_to_file(self, file_path: Path) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.get_text())

    @override
    def save(self):
        self.save_to_file(file_path=self.file_path)

    @override
    def reload(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.markdown_text_node = MarkdownTextNode(f.read())

    def __init__(self, file_path: Path, **kargs):
        with open(file_path, "r", encoding="utf-8") as f:
            markdown_text_node = MarkdownTextNode(f.read())
        if kargs.get("markdown_text_node"):
            markdown_text_node = kargs.pop("markdown_text_node")
        super().__init__(
            file_path=file_path, markdown_text_node=markdown_text_node, **kargs
        )


if __name__ == "__main__":
    pass
