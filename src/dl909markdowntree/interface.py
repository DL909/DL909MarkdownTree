"""interface.py - Protocol hierarchy for markdown file/folder node types"""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Self, override

from pydantic import BaseModel

from .file_node import FileNode
from .text_node import TextNode


class FoldMode(Enum):
    SHOW_TITLE = "show_title"
    SHOW_CHILD = "show_child_title"


class MarkdownTitleBase(TextNode):
    level: int
    title: str

    @classmethod
    @abstractmethod
    def from_line(cls, line: str) -> Self: ...

    @classmethod
    @abstractmethod
    def from_text(cls, text: str) -> Self: ...

    @abstractmethod
    def get_text(self) -> str: ...

    @abstractmethod
    def set_text(self, text: str) -> None: ...

    @abstractmethod
    def add_text(self, text: str) -> None: ...

    @abstractmethod
    def get_title(self, show_level_sign: bool = True) -> str: ...

    @abstractmethod
    def recursive_find_title_node_by_name(self, title_name: str) -> Self | None: ...


class MarkdownTextFileBase(FileNode, TextNode):
    """基础 Markdown 文件协议"""

    @staticmethod
    @abstractmethod
    def create_file(file_path: Path) -> None: ...

    @abstractmethod
    def get_text(self) -> str: ...

    @abstractmethod
    def set_text(self, text: str) -> None: ...

    @abstractmethod
    def save(self) -> None: ...

    @abstractmethod
    def save_to_file(self, file_path: Path) -> None: ...

    @abstractmethod
    def reload(self) -> None: ...

    @abstractmethod
    def get_root_title(self) -> MarkdownTitleBase: ...


class NumberedMarkdownTitleBase(MarkdownTitleBase):
    number: list[int]
    auto_correct: bool


class NumberedMarkdownTextFileBase(MarkdownTextFileBase):
    """带编号的 Markdown 文件协议"""

    @abstractmethod
    def get_root_title(self) -> NumberedMarkdownTitleBase: ...


class FoldableMarkdownTitleBase(NumberedMarkdownTitleBase):
    fold_mode: FoldMode

    @abstractmethod
    @override
    def get_text(self, with_fold_info: bool = True, full_text=False) -> str: ...

    @abstractmethod
    def unfold(self) -> str: ...

    @abstractmethod
    def recursive_up_unfold(self) -> None: ...

    @abstractmethod
    def recursive_unfold(self) -> None: ...

    @abstractmethod
    def unfold_by_depth(self, depth: int) -> None: ...

    @abstractmethod
    @override
    def recursive_find_title_node_by_name(
        self, title_name: str, within_shown: bool = False
    ) -> Self | None: ...


class FoldableMarkdownTextFileBase(NumberedMarkdownTextFileBase):
    """可折叠的 Markdown 文件协议"""

    @abstractmethod
    def get_root_title(self) -> FoldableMarkdownTitleBase: ...

    @abstractmethod
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str: ...


class AttributedMarkdownTextFileBase[T: BaseModel](FoldableMarkdownTextFileBase):
    """带属性的 Markdown 文件协议"""

    attribute: T

    @staticmethod
    @abstractmethod
    def create_file(  # pyright: ignore[reportIncompatibleMethodOverride] - intentionally added attribute_type
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
    ) -> None: ...
