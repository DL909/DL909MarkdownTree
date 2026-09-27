from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Self, override

from .exceptions import (
    InvalidMarkdownLineError,
    InvalidTitleLevelError,
    UnclosedCodeBlockError,
)
from .interface import MarkdownTextFileBase, MarkdownTitleBase
from .node import Node
from .plain_text_nodes import PlainTextNode

# 标题行的唯一权威定义。检测（"这行是不是标题"）与解析（"取出级别和标题文本"）
# 必须用同一条正则：早先检测用 r"^#{1,6} " 而解析用 r"^(#{1,6}) (.+)$"，
# 二者对 "# " 这种空标题的判断不一致，导致一行空标题把整篇文档的解析打断。
_TITLE_LINE_PATTERN = re.compile(r"^(#{1,6}) (.+)$")
# 反引号围栏的 info string 里不允许出现反引号，波浪号围栏则允许——两种围栏
# 必须用各自的字符类，合并成一条会改变波浪号围栏的行为。
_BACKTICK_FENCE_PATTERN = re.compile(r"^(`{3,})([^`]*)$")
_TILDE_FENCE_PATTERN = re.compile(r"^(~{3,})(.*)$")
# 形如 "# " / "## " 的空标题：CommonMark 不认为它是标题，早先会被检测正则
# 认作标题、却过不了解析正则，从而让一行坏内容打断整篇文档的解析。
# 现在降级为普通文本，同时告警，避免问题被静默吞掉。
_EMPTY_TITLE_LINE_PATTERN = re.compile(r"^#{1,6}[ \t]*$")

logger = logging.getLogger(__name__)


class MarkdownTitleNode(MarkdownTitleBase):
    children: list[PlainTextNode | MarkdownTitleNode]  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
    level: int
    title: str

    def __init__(self, level: int, title: str = "") -> None:
        self.children = []  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
        self.level = level
        self.title = title

    @classmethod
    def from_line(cls, line: str) -> Self:
        match = _TITLE_LINE_PATTERN.match(line.rstrip("\n"))
        if not match:
            raise InvalidMarkdownLineError(f"invalid Markdown title line: {line}")
        return cls(level=len(match.group(1)), title=match.group(2))

    def _from_line(self, line: str) -> Self:
        return self.from_line(line)

    @classmethod
    def from_text(cls, text: str) -> Self:
        result = cls(level=0)
        result.set_text(text)
        return result

    @override
    def addchild(self, child: Node) -> None:
        if isinstance(child, PlainTextNode):
            if self.children and isinstance(self.children[-1], PlainTextNode):
                self.children[-1].text += child.text
            elif self.children:
                return self.children[-1].addchild(child)
            else:
                self.children.append(child)
                child.parent = self
        elif isinstance(child, type(self)):
            if child.level <= self.level:
                raise InvalidTitleLevelError("too high title level")
            return self._add_title_child(child)
        else:
            return super().addchild(child)

    def _add_title_child_to_children(self, child: Self) -> None:
        self.children.append(child)
        child.parent = self

    def _add_title_child(self, child: Self) -> None:
        if (
            self.children
            and isinstance(self.children[-1], MarkdownTitleNode)
            and child.level > self.children[-1].level
        ):
            return self.children[-1]._add_title_child(child)
        self._add_title_child_to_children(child)

    def _parse_markdown(self, content: str) -> tuple[Self, bool]:
        """
        return
            new title node: Self
            if override current title: bool
        """
        lines = content.splitlines(keepends=True)
        override_flag = False
        # 覆盖判定同样必须用权威正则：早先用宽松的 r"^(#+)" 会把 "# " 这类
        # 并非标题的行也判成"同级别标题"，随后 _from_line 抛错打断整篇解析。
        if (
            lines
            and self.level > 0
            and (match := _TITLE_LINE_PATTERN.match(lines[0].rstrip("\n")))
            and len(match.group(1)) == self.level
        ):
            result = self._from_line(lines[0])
            lines = lines[1:]
            override_flag = True
        else:
            result = type(self).from_self(self, children=[])
        cached_lines = ""
        code_block_flag = False
        fence_char = ""
        fence_run = 0
        for line in lines:
            stripped_line = line.rstrip("\n")
            if code_block_flag:
                if (
                    re.match(rf"^{fence_char}{{{fence_run},}}\s*$", stripped_line)
                    is not None
                ):
                    code_block_flag = False
                cached_lines += line
            else:
                fence_match = _BACKTICK_FENCE_PATTERN.match(stripped_line)
                if fence_match is None:
                    fence_match = _TILDE_FENCE_PATTERN.match(stripped_line)
                if fence_match is not None:
                    code_block_flag = True
                    fence = fence_match.group(1)
                    fence_char = fence[0]
                    fence_run = len(fence)
                    cached_lines += line
                else:
                    if _TITLE_LINE_PATTERN.match(stripped_line):
                        if cached_lines:
                            result.addchild(PlainTextNode(cached_lines))
                        cached_lines = ""
                        result.addchild(self._from_line(line))
                    else:
                        if _EMPTY_TITLE_LINE_PATTERN.match(stripped_line):
                            logger.warning(
                                f"empty title line kept as plain text: {stripped_line!r}"
                            )
                        cached_lines += line
        if code_block_flag:
            raise UnclosedCodeBlockError("unclosed code block")
        if cached_lines:
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
        self.children.extend(origin.children)
        for child in self.children:
            child.parent = self

    @override
    def set_text(self, text: str) -> None:
        result, override_flag = self._parse_markdown(text)
        if override_flag:
            self._override_self(result)
        else:
            self.children.clear()
            self.children.extend(result.children)
            for child in self.children:
                child.parent = self

    def get_title(self, show_level_sign: bool = True) -> str:
        if self.level <= 0:
            return self.title
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
                    isinstance(child, type(self))
                    and (result := child.recursive_find_title_node_by_name(title_name))
                    is not None
                ):
                    return result
        return None

    def add_text(self, text: str, ensure_new_line: bool = True) -> None:
        if not text:
            return
        current_text = self.get_text()
        # 不能用 current_text[-1] / text[0]：空节点（get_text() == ""）或
        # 空 text 会直接 IndexError。用 endswith/startswith 判空。
        if (
            ensure_new_line
            and current_text
            and not current_text.endswith("\n")
            and not text.startswith("\n")
        ):
            current_text += "\n"
        self.set_text(current_text + text)


class MarkdownTextFileNode(MarkdownTextFileBase):
    markdown_text_node: MarkdownTitleNode
    markdown_text_node_type: type[MarkdownTitleNode] = MarkdownTitleNode

    @override
    def get_text(self) -> str:
        return self.markdown_text_node.get_text()

    @override
    def set_text(self, text: str) -> None:
        self.markdown_text_node.set_text(text)

    @override
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
    def get_root_title(self) -> MarkdownTitleBase:
        return self.markdown_text_node

    @override
    def reload(self):
        self.markdown_text_node = self.markdown_text_node_type.from_text(
            self.file_path.read_text(encoding="utf-8")
        )

    def __init__(
        self, file_path: Path, markdown_text_node: MarkdownTitleNode | None = None
    ):
        file_path = Path(file_path)
        super().__init__(file_path=file_path)
        if not file_path.exists():
            self.create_file(file_path)
        if markdown_text_node:
            self.markdown_text_node = markdown_text_node
            self.save()
        else:
            self.reload()
