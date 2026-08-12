from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Self, override

from .file_node import FileNode
from .node import Node
from .plain_text_nodes import PlainTextNode
from .protocols import MarkdownTextFileProtocol, MarkdownTitleProtocol
from .text_node import TextNode


class MarkdownTitleNode(MarkdownTitleProtocol):
    children: list[PlainTextNode | MarkdownTitleNode]  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
    level: int
    title: str

    def __init__(self, level: int, title: str = "") -> None:
        self.children = []  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
        self.level = level
        self.title = title

    @classmethod
    def from_line(cls, line: str) -> Self:
        match = re.match(r"^(#+) (.+)$", line.rstrip("\n"))
        if not match:
            raise Exception()
        return cls(level=len(match.group(1)), title=match.group(2))

    @classmethod
    def from_text(cls, text: str) -> Self:
        result = cls(level=0)
        result.set_text(text)
        return result

    @override
    def addchild(self, child: Node) -> None:
        if isinstance(child, PlainTextNode):
            if self.children:
                return self.children[-1].addchild(child)
            else:
                self.children.append(child)
        elif isinstance(child, MarkdownTitleNode):
            if child.level >= self.level:  # pyright: ignore[reportAttributeAccessIssue] - a subclass of Self obviously will has level
                raise Exception("too high title level")
            return self.addchild(child)

        return super().addchild(child)

    def _add_title_child_to_children(self, child: Self) -> None:
        self.children.append(child)

    def _add_title_child(self, child: Self) -> None:
        if self.children and isinstance(self.children[-1], MarkdownTitleNode):
            if self.children[-1].level <= child.level:  # pyright: ignore[reportAttributeAccessIssue] - a subclass of Self obviously will has level
                return self._add_title_child_to_children(child)
            else:
                return self.children[-1].addchild(child)

    def _parse_markdown(self, content: str) -> tuple[Self, bool]:
        """
        return
            new title node: Self
            if override current title: bool
        """
        lines = [x + "\n" for x in content.split("\n")]
        override_flag = False
        if lines[0].startswith("#"):
            result = self.from_line(lines[0])
            lines = lines[1:]
            override_flag = True
        else:
            result = copy.deepcopy(self)
        cached_lines = ""
        code_block_flag = False
        for line in lines:
            if code_block_flag:
                if re.match(r"^``` *\n", line):
                    code_block_flag = False
                cached_lines += line
            else:
                if re.match(r"^```\s*\n", line):
                    code_block_flag = True
                    cached_lines += line
                else:
                    if re.match(r"^#{1,6} \s", line):
                        result.addchild(PlainTextNode(cached_lines))
                        result.addchild(self.from_line(line))
                    else:
                        cached_lines += line
        if code_block_flag:
            raise Exception("unclosed code block")
        result.addchild(PlainTextNode(cached_lines))

        return result, override_flag

    @override
    def get_text(self) -> str:
        text = ""
        if self.level > 0:
            text = self.get_title() + "\n"
        for child in self.children:
            text += child.get_text()
        return text

    def _override_self(self, origin: Self) -> None:
        """
        update attribute according to given
        """
        self.title = origin.title
        self.children.clear()
        self.children.append(*origin.children)

    @override
    def set_text(self, text: str) -> None:
        result, override_flag = self._parse_markdown(text)
        if override_flag:
            self._override_self(result)
        else:
            self.children.clear()
            self.children.append(*result.children)

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
        if title_name and title_name[-1] == "\n":
            title_name = title_name[:-1]
        if self.get_title() == title_name:
            return self
        else:
            for child in self.children:
                if (
                    isinstance(child, MarkdownTitleNode)
                    and (result := child.recursive_find_title_node_by_name(title_name))
                    is not None
                ):
                    return result  # pyright: ignore[reportReturnType] - children will be override and fit Self
        return None

    def add_text(self, text: str) -> None:
        self.set_text(self.get_text() + "\n" + text)


class MarkdownTextFileNode(MarkdownTextFileProtocol):
    markdown_text_node: MarkdownTitleNode

    @override
    def get_text(self) -> str:
        return self.markdown_text_node.get_text()

    @override
    def set_text(self, text: str) -> None:
        self.markdown_text_node.set_text(text)

    def get_markdown_text_node(self) -> MarkdownTitleNode:
        return self.markdown_text_node

    def save_to_file(self, file_path: Path) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.get_text())

    @override
    def save(self):
        self.save_to_file(file_path=self.file_path)

    @staticmethod
    def create_file(file_path: Path) -> None:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")

    @override
    def get_root_title(self) -> MarkdownTitleProtocol:
        return self.markdown_text_node

    @override
    def reload(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.markdown_text_node = MarkdownTitleNode.from_text(f.read())

    def __init__(
        self, file_path: Path, markdown_text_node: MarkdownTitleNode | None = None
    ):
        file_path = Path(file_path)
        if not file_path.exists():
            self.create_file(file_path)
        if markdown_text_node:
            self.markdown_text_node = markdown_text_node
            self.save()
        else:
            self.reload()
