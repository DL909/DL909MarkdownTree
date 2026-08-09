"""protocols.py - Protocol hierarchy for markdown file/folder node types"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable, TypeVar

from .foldable_markdown_nodes import FoldableMarkdownTextNode, FoldableMarkdownTitleNode
from .markdown_nodes import MarkdownTextNode, MarkdownTitleNode
from .numbered_markdown_nodes import NumberedMarkdownTextNode, NumberedMarkdownTitleNode

from pydantic import BaseModel


@runtime_checkable
class MarkdownTextFileProtocol(Protocol):
    """基础 Markdown 文件协议：读取、写入、保存、重载、标题搜索"""

    @staticmethod
    def create_file(file_path: Path) -> None: ...

    def get_text(self) -> str: ...

    def set_text(self, text: str) -> None: ...

    def save(self) -> None: ...

    def reload(self) -> None: ...

    def get_markdown_text_node(self) -> MarkdownTextNode: ...

    def recursive_find_title_node_by_name(
        self, title_name: str
    ) -> MarkdownTitleNode | None: ...


@runtime_checkable
class NumberedMarkdownTextFileProtocol(MarkdownTextFileProtocol, Protocol):
    """带编号的 Markdown 文件协议"""

    def get_markdown_text_node(self) -> NumberedMarkdownTextNode: ...

    def recursive_find_title_node_by_name(
        self, title_name: str
    ) -> NumberedMarkdownTitleNode | None: ...


@runtime_checkable
class FoldableMarkdownTextFileProtocol(NumberedMarkdownTextFileProtocol, Protocol):
    """可折叠的 Markdown 文件协议"""

    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str: ...

    def get_markdown_text_node(self) -> FoldableMarkdownTextNode: ...

    def recursive_find_title_node_by_name(
        self, title_name: str, within_shown: bool = False
    ) -> FoldableMarkdownTitleNode | None: ...


T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class AttributedMarkdownTextFileProtocol(FoldableMarkdownTextFileProtocol, Protocol[T]):
    """带属性的 Markdown 文件协议"""

    attribute: T

    @staticmethod
    def create_file(
        file_path: Path, attribute_type: type[T], attribute: T | None = None, **kwargs
    ) -> None: ...
