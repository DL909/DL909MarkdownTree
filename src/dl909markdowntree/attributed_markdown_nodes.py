from pathlib import Path
from typing import TypeVar, override

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from .exceptions import (
    InvalidFrontMatterError,
    MarkdownFileError,
)
from .file_node import FileNode
from .foldable_markdown_nodes import (
    FoldableMarkdownTitleNode,
)
from .interface import AttributedMarkdownTextFileBase
from .text_node import TextNode

T = TypeVar("T", bound=BaseModel)


class AttributedMarkdownTextFileNode[T: BaseModel](
    AttributedMarkdownTextFileBase, FileNode, TextNode
):
    markdown_text_node: FoldableMarkdownTitleNode
    # 本类直接继承 AttributedMarkdownTextFileBase 而非 MarkdownTextFileNode，
    # 拿不到基类的 markdown_text_node_type，reload() 等走基类的代码路径会
    # AttributeError。这里显式声明，并让 __init__/reload 真正使用它。
    markdown_text_node_type: type[FoldableMarkdownTitleNode] = FoldableMarkdownTitleNode
    attribute: T

    @override
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str:
        return self.markdown_text_node.get_text(
            with_fold_info=with_fold_info, full_text=full_text
        )

    def get_root_title(self) -> FoldableMarkdownTitleNode:
        return self.markdown_text_node

    @override
    def get_markdown_text_node(self) -> FoldableMarkdownTitleNode:
        return self.markdown_text_node

    @override
    def set_text(self, text) -> None:
        self.markdown_text_node.set_text(text)

    def save_to_file(self, file_path: Path) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                f"---\n{to_yaml_str(self.attribute)}---\n{self.get_text(full_text=True)}"
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
        content = f"---\n{to_yaml_str(attribute)}---\n"
        file_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[str, str]:
        """将 ``---\n<yaml>\n---\n<markdown>`` 拆分为 (yaml_data, markdown_content)"""
        if not content.startswith("---\n"):
            raise InvalidFrontMatterError("文件缺少 FrontMatter 起始标记 '---'")
        # 结束标记既可能是 "\n---\n"（后面还有正文），也可能是文件结尾的
        # "\n---"（无尾换行）。只找前者会把后者误判成"缺少结束标记"。
        index = content.find("\n---\n", 3)
        if index == -1:
            if content.endswith("\n---"):
                index = len(content) - 4
            else:
                raise InvalidFrontMatterError("文件缺少 FrontMatter 结束标记 '---'")
        return content[4:index], content[index + 5 :]

    @staticmethod
    def _read_file(file_path: Path) -> str:
        """读取文件并把 IO / 解码错误收敛为 MarkdownTreeError 家族"""
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise MarkdownFileError(f"无法读取 {file_path}: {e}") from e

    @staticmethod
    def _parse_attribute(
        attribute_type: type[T], yaml_data: str, source: Path | str
    ) -> T:
        """把 FrontMatter 解析为属性对象，解析失败收敛为 MarkdownTreeError"""
        if not yaml_data.strip():
            return attribute_type()
        try:
            return parse_yaml_raw_as(attribute_type, yaml_data)
        except Exception as e:
            # pydantic_yaml 的 ParserError / pydantic 的 ValidationError 都不
            # 属于 MarkdownTreeError，调用方无法用单一类型兜底
            raise InvalidFrontMatterError(
                f"{source} 的 FrontMatter 无法解析为 {attribute_type.__name__}: {e}"
            ) from e

    @override
    def reload(self):
        content = self._read_file(self.file_path)
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = self.markdown_text_node_type.from_text(
            text=markdown_content
        )
        self.attribute = self._parse_attribute(
            type(self.attribute), yaml_data, self.file_path
        )

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
        content = self._read_file(file_path)
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = (
            markdown_text_node
            if markdown_text_node
            else self.markdown_text_node_type.from_text(
                text=markdown_content, auto_correct=auto_correct
            )
        )
        self.attribute = (
            attribute
            if attribute
            else self._parse_attribute(attribute_type, yaml_data, file_path)
        )
