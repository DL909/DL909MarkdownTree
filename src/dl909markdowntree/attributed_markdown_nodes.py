from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str
from .foldable_markdown_nodes import (
    FoldableMarkdownTextNode,
    FoldableMarkdownTitleNode,
)

from .text_node import TextNode
from .file_node import FileNode

from typing import override, TypeVar, Generic
from pathlib import Path


T = TypeVar("T", bound=BaseModel)


class AttributedMarkdownTextFileNode(FileNode, TextNode, Generic[T]):
    markdown_text_node: FoldableMarkdownTextNode
    attribute: T

    def recursive_find_title_node_by_name(
        self, title_name: str, within_shown: bool = False
    ) -> FoldableMarkdownTitleNode | None:
        return self.markdown_text_node.recursive_find_title_node_by_name(
            title_name=title_name, within_shown=within_shown
        )

    @override
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str:
        return self.markdown_text_node.get_text(
            with_fold_info=with_fold_info, full_text=full_text
        )

    def get_markdown_text_node(self) -> FoldableMarkdownTextNode:
        return self.markdown_text_node

    @override
    def set_text(self, text) -> None:
        self.markdown_text_node.set_text(text)

    def save_to_file(self, file_path: Path) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                f"---\n{to_yaml_str(self.attribute)}\n---\n{self.get_text(full_text=True)}"
            )

    @override
    def save(self):
        self.save_to_file(file_path=Path(self.file_path))

    @staticmethod
    def create_file(
        file_path: Path, attribute_type: type[T], attribute: T | None = None
    ) -> None:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if attribute is None:
            attribute = attribute_type()
        content = f"---\n{to_yaml_str(attribute)}\n---\n"
        file_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[str, str]:
        """将 ``---\n<yaml>\n---\n<markdown>`` 拆分为 (yaml_data, markdown_content)"""
        if not content.startswith("---\n"):
            raise ValueError("文件缺少 FrontMatter 起始标记 '---'")
        i = content.find("\n---\n", 4)
        if i == -1:
            raise ValueError("文件缺少 FrontMatter 结束标记 '---'")
        i += 1
        return content[4 : i - 1], content[i + 4 :]

    @override
    def reload(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = FoldableMarkdownTextNode(text=markdown_content)
        self.attribute = parse_yaml_raw_as(type(self.attribute), yaml_data)

    def __init__(self, file_path: Path, attribute_type: type[T], **kwargs):
        file_path = Path(file_path)
        explicit_attribute = kwargs.pop("attribute", None)
        if not file_path.exists():
            self.create_file(file_path, attribute_type, explicit_attribute)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        yaml_data, markdown_content = self._split_frontmatter(content)
        auto_correct = kwargs.pop("auto_correct", True)
        markdown_text_node = FoldableMarkdownTextNode(
            text=markdown_content, auto_correct=auto_correct
        )
        attribute = (
            explicit_attribute
            if explicit_attribute is not None
            else parse_yaml_raw_as(attribute_type, yaml_data)
        )
        if kwargs.get("markdown_text_node"):
            markdown_text_node = kwargs.pop("markdown_text_node")

        super().__init__(
            file_path=file_path,
            markdown_text_node=markdown_text_node,
            attribute=attribute,
            **kwargs,
        )
