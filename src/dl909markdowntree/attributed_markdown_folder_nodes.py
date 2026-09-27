"""attributed_markdown_folder_nodes.py - 属性化 Markdown 文件夹节点"""

from pathlib import Path
from typing import override

from pydantic import BaseModel
from pydantic_yaml import to_yaml_str

from .attributed_markdown_nodes import AttributedMarkdownTextFileNode
from .foldable_markdown_folder_nodes import FoldableMarkdownFolderNode
from .foldable_markdown_nodes import (
    FoldableMarkdownTitleBase,
    FoldableMarkdownTitleNode,
)
from .interface import AttributedMarkdownTextFileBase


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
        # 显式传入 attribute 时先就地赋值，不要去读 FrontMatter.yaml：
        # 一来省掉一次磁盘读取，二来 super().__init__() 内部的 reload() 需要
        # 用 type(self.attribute) 确定解析目标，此处是它唯一的类型锚点。
        if attribute is not None:
            self.attribute = attribute
        else:
            self.attribute = self._load_attribute(attribute_type, file_path)
        super().__init__(
            file_path=file_path,
            auto_correct=auto_correct,
            markdown_text_node=markdown_text_node,
        )
        # reload() 会用 FrontMatter.yaml 覆盖 attribute，因此显式传入的值
        # 必须在 super().__init__() 之后再放回去一次。
        if attribute is not None:
            self.attribute = attribute

    def _load_attribute(self, attribute_type: type[T], folder: Path) -> T:
        """从 FrontMatter.yaml 读取属性；文件缺失或为空则用默认值"""
        yaml_path = folder / "FrontMatter.yaml"
        if not yaml_path.exists():
            return attribute_type()
        yaml_data = yaml_path.read_text(encoding="utf-8")
        return AttributedMarkdownTextFileNode._parse_attribute(
            attribute_type, yaml_data, yaml_path
        )

    @override
    def save_to_file(self, file_path: Path):
        super().save_to_file(file_path)
        yaml_path = Path(file_path) / "FrontMatter.yaml"
        yaml_path.write_text(to_yaml_str(self.attribute), encoding="utf-8")

    @override
    def reload(self, auto_correct: bool | None = None):
        if (self.file_path / "FrontMatter.yaml").exists():
            self.attribute = self._load_attribute(
                type(self.attribute), Path(self.file_path)
            )
        super().reload(auto_correct=auto_correct)

    @override
    def get_root_title(self) -> FoldableMarkdownTitleBase:
        return super().get_root_title()
