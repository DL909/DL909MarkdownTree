from pathlib import Path
from typing import TypeVar, override

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from dl909markdowntree.interface import AttributedMarkdownTextFileBase

from .file_node import FileNode
from .foldable_markdown_nodes import (
    FoldableMarkdownTitleNode,
)
from .text_node import TextNode

T = TypeVar("T", bound=BaseModel)


class AttributedMarkdownTextFileNode[T: BaseModel](
    AttributedMarkdownTextFileBase, FileNode, TextNode
):
    markdown_text_node: FoldableMarkdownTitleNode
    attribute: T

    @override
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str:
        return self.markdown_text_node.get_text(
            with_fold_info=with_fold_info, full_text=full_text
        )

    def get_root_title(self) -> FoldableMarkdownTitleNode:
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
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
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
        self.markdown_text_node = FoldableMarkdownTitleNode.from_text(
            text=markdown_content
        )
        self.attribute = parse_yaml_raw_as(type(self.attribute), yaml_data)

    def __init__(
        self,
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
        auto_correct: bool = True,
        markdown_text_node: FoldableMarkdownTitleNode | None = None,
    ):
        file_path = Path(file_path)
        super().__init__(file_path=file_path)
        if not file_path.exists():
            self.create_file(file_path, attribute_type, attribute)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = (
            markdown_text_node
            if markdown_text_node
            else FoldableMarkdownTitleNode.from_text(
                text=markdown_content, auto_correct=auto_correct
            )
        )
        self.attribute = (
            attribute if attribute else parse_yaml_raw_as(attribute_type, yaml_data)
        )
