"""attributed_markdown_folder_nodes.py - 属性化 Markdown 文件夹节点"""

from pathlib import Path
from typing import override, TypeVar, Generic

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from .foldable_markdown_nodes import (
    FoldableMarkdownTextNode,
)
from .foldable_markdown_folder_nodes import FoldableMarkdownFolderNode

T = TypeVar("T", bound=BaseModel)


class AttributedMarkdownFolderNode(FoldableMarkdownFolderNode, Generic[T]):
    markdown_text_node: FoldableMarkdownTextNode  # type: ignore
    attribute: T

    def __init__(self, file_path: Path, attribute_type: type[T], **kargs):
        yaml_path = Path(file_path) / "FrontMatter.yaml"
        if yaml_path.exists():
            yaml_data = yaml_path.read_text(encoding="utf-8")
            attribute = parse_yaml_raw_as(attribute_type, yaml_data)
        else:
            attribute = attribute_type()

        super().__init__(
            file_path=file_path,
            attribute=attribute,
            **kargs,
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
