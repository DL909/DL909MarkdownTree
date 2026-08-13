"""attributed_markdown_folder_nodes.py - 属性化 Markdown 文件夹节点"""

from pathlib import Path
from typing import override

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from dl909markdowntree.interface import (
    AttributedMarkdownTextFileBase,
    FoldableMarkdownTitleBase,
)

from .foldable_markdown_folder_nodes import FoldableMarkdownFolderNode
from .foldable_markdown_nodes import FoldableMarkdownTitleNode


class AttributedMarkdownFolderNode[T: BaseModel](
    FoldableMarkdownFolderNode,
    AttributedMarkdownTextFileBase,
):
    markdown_text_node: FoldableMarkdownTitleNode  # pyright: ignore[reportIncompatibleVariableOverride] - children type is intentionally narrowed from base class
    attribute: T

    @override
    @staticmethod
    def create_file(  # pyright: ignore[reportIncompatibleMethodOverride]
        file_path: Path, attribute_type: type[T], attribute: T | None = None
    ) -> None:
        file_path = Path(file_path)
        file_path.mkdir(parents=True, exist_ok=True)
        if attribute is None:
            attribute = attribute_type()
        yaml_path = file_path / "FrontMatter.yaml"
        yaml_path.write_text(to_yaml_str(attribute), encoding="utf-8")

    def __init__(
        self,
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
        auto_correct: bool = True,
        markdown_text_node: FoldableMarkdownTitleNode | None = None,
    ):
        file_path = Path(file_path)
        if not file_path.exists():
            self.create_file(file_path, attribute_type, attribute)
        yaml_path = file_path / "FrontMatter.yaml"
        self.attribute = (
            attribute
            if attribute
            else (
                parse_yaml_raw_as(attribute_type, yaml_path.read_text(encoding="utf-8"))
                if yaml_path.exists()
                else attribute_type()
            )
        )
        super().__init__(
            file_path=file_path,
            auto_correct=auto_correct,
            markdown_text_node=markdown_text_node,
        )

    @override
    def save_to_file(self, file_path: Path):
        super().save_to_file(file_path)
        yaml_path = Path(file_path) / "FrontMatter.yaml"
        yaml_path.write_text(to_yaml_str(self.attribute), encoding="utf-8")

    @override
    def reload(self, auto_correct: bool | None = None):
        yaml_path = Path(self.file_path) / "FrontMatter.yaml"
        if yaml_path.exists():
            yaml_data = yaml_path.read_text(encoding="utf-8")
            self.attribute = parse_yaml_raw_as(type(self.attribute), yaml_data)
        super().reload(auto_correct=auto_correct)

    @override
    def get_root_title(self) -> FoldableMarkdownTitleBase:
        return super().get_root_title()
