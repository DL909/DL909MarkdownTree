"""attributed_markdown_folder_nodes.py - 属性化 Markdown 文件夹节点"""

from pathlib import Path
from typing import override

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from .foldable_markdown_folder_nodes import FoldableMarkdownFolderNode
from .foldable_markdown_nodes import (
    FoldableMarkdownTextNode,
)


class AttributedMarkdownFolderNode[T: BaseModel](FoldableMarkdownFolderNode):
    markdown_text_node: FoldableMarkdownTextNode  # type: ignore
    attribute: T

    @staticmethod
    def create_file(
        file_path: Path, attribute_type: type[T], attribute: T | None = None
    ) -> None:
        file_path = Path(file_path)
        file_path.mkdir(parents=True, exist_ok=True)
        if attribute is None:
            attribute = attribute_type()
        yaml_path = file_path / "FrontMatter.yaml"
        yaml_path.write_text(to_yaml_str(attribute), encoding="utf-8")

    def get_markdown_text_node(self) -> FoldableMarkdownTextNode:
        return self.markdown_text_node

    def __init__(self, file_path: Path, attribute_type: type[T], **kwargs):
        file_path = Path(file_path)
        explicit_attribute = kwargs.pop("attribute", None)
        if not file_path.exists():
            self.create_file(file_path, attribute_type, explicit_attribute)
            if explicit_attribute is None:
                yaml_path = file_path / "FrontMatter.yaml"
                yaml_data = yaml_path.read_text(encoding="utf-8")
                explicit_attribute = parse_yaml_raw_as(attribute_type, yaml_data)
            super().__init__(
                file_path=file_path,
                attribute=explicit_attribute,
                **kwargs,
            )
            return

        yaml_path = Path(file_path) / "FrontMatter.yaml"
        if explicit_attribute is not None:
            attribute = explicit_attribute
        elif yaml_path.exists():
            yaml_data = yaml_path.read_text(encoding="utf-8")
            attribute = parse_yaml_raw_as(attribute_type, yaml_data)
        else:
            attribute = attribute_type()

        super().__init__(
            file_path=file_path,
            attribute=attribute,
            **kwargs,
        )

    @override
    def reload(self):
        yaml_path = Path(self.file_path) / "FrontMatter.yaml"
        if yaml_path.exists():
            yaml_data = yaml_path.read_text(encoding="utf-8")
            self.attribute = parse_yaml_raw_as(type(self.attribute), yaml_data)
        super().reload()

    @override
    def save(self):
        super().save()
        yaml_path = Path(self.file_path) / "FrontMatter.yaml"
        yaml_path.write_text(to_yaml_str(self.attribute), encoding="utf-8")
