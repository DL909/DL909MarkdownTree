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

    @override
    def reload(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---\n")
        i = content.find("---", 4)
        assert content[i : i + 4] == "---\n"
        yaml_data = content[4 : i - 1]
        markdown_content = content[i + 4 :]
        self.markdown_text_node = FoldableMarkdownTextNode(text=markdown_content)
        self.attribute = parse_yaml_raw_as(type(self.attribute), yaml_data)

    def __init__(self, file_path: Path, attribute_type: type[T], **kargs):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("---\n")
        i = content.find("\n---\n", 4) + 1
        assert content[i : i + 4] == "---\n"
        yaml_data = content[4 : i - 1]
        markdown_content = content[i + 4 :]
        auto_correct = kargs.pop("auto_correct", True)
        markdown_text_node = FoldableMarkdownTextNode(
            text=markdown_content, auto_correct=auto_correct
        )
        attribute = parse_yaml_raw_as(attribute_type, yaml_data)
        if kargs.get("markdown_text_node"):
            markdown_text_node = kargs.pop("markdown_text_node")

        super().__init__(
            file_path=file_path,
            markdown_text_node=markdown_text_node,
            attribute=attribute,
            **kargs,
        )
