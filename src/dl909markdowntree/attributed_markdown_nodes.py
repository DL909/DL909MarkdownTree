from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str

from .exceptions import (
    InvalidFrontMatterError,
    MarkdownFileError,
)
from .file_node import FileNode
from .foldable_markdown_nodes import FoldableMarkdownTextFileNode
from .interface import AttributedMarkdownTextFileBase
from .markdown_nodes import MarkdownTextFileNode, MarkdownTitleNode


class AttributedMixin[T: BaseModel]:
    """FrontMatter 能力的内核：属性字段与 YAML 解析。

    与正文的落盘形态无关——.md 把 FrontMatter 写成正文前缀，.mdp 文件夹写成
    独立的 FrontMatter.yaml，两者真正共享的只有 attribute 与 YAML 解析，
    所以内核必须比两种形态都窄。
    """

    attribute: T
    file_path: Path
    # 具体类会把它窄化到自己的标题节点类型，与文件节点基类里的做法一致
    markdown_text_node: MarkdownTitleNode

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


class FrontMatterTextFileMixin[T: BaseModel](AttributedMixin[T]):
    """把 FrontMatter 以 '---' 前缀写进 .md 正文的形态。

    只依赖基类提供的 markdown_text_node / file_path / _create_text_node，
    对标题节点是否编号、是否可折叠一无所知——因此可以直接拼在
    MarkdownTextFileNode 上，得到"非编号、非折叠、有属性"的节点。
    """

    # 下面两个是本 mixin 依赖、由被混入的文件节点基类提供的能力。声明放在
    # TYPE_CHECKING 里：写方法体会让 mixin 自己"提供"它们，而 mixin 在 MRO 中
    # 排在基类前面，一遮蔽基类的真实实现（get_text 恒返回 None）；标
    # @abstractmethod 也一样坏——抽象桩盖住具体实现后，ABC 反过来判定整个
    # 具体类是抽象的、拒绝实例化。只在类型检查时声明，两头都不吃亏。
    if TYPE_CHECKING:

        def get_text(self) -> str: ...

        def _create_text_node(
            self, text: str, auto_correct: bool = True
        ) -> MarkdownTitleNode: ...

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[str, str]:
        """将 ``---\\n<yaml>\\n---\\n<markdown>`` 拆分为 (yaml_data, markdown_content)"""
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
    def create_file(
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
    ) -> None:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if attribute is None:
            attribute = attribute_type()
        file_path.write_text(f"---\n{to_yaml_str(attribute)}---\n", encoding="utf-8")

    def to_markdown(self) -> str:
        """完整文件内容：FrontMatter 前缀 + 正文。

        正文恒为完整内容——文件节点只在内容层工作，折叠不影响落盘。
        """
        return f"---\n{to_yaml_str(self.attribute)}---\n{self.get_text()}"

    def save_to_file(self, file_path: Path) -> None:
        Path(file_path).write_text(self.to_markdown(), encoding="utf-8")

    def reload(self) -> None:
        content = self._read_file(self.file_path)
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = self._create_text_node(markdown_content)
        self.attribute = self._parse_attribute(
            type(self.attribute), yaml_data, self.file_path
        )

    def __init__(
        self,
        file_path: Path,
        attribute_type: type[T],
        attribute: T | None = None,
        auto_correct: bool = True,
        markdown_text_node: MarkdownTitleNode | None = None,
    ):
        file_path = Path(file_path)
        # 从 FileNode 而不是 super() 起链：本 mixin 取代了文件节点基类的整个
        # __init__（建档、切 FrontMatter、构造标题节点都在下面自己做）。
        # 若走 super()，会先执行 MarkdownTextFileNode.__init__ 而它末尾调用
        # self.reload()——此刻 self.attribute 还没赋值，直接 AttributeError。
        # pyright 不知道本 mixin 只会被混入 FileNode 子类，故在此显式收窄。
        FileNode.__init__(self, file_path=file_path)  # pyright: ignore[reportArgumentType]
        if not file_path.exists():
            self.create_file(file_path, attribute_type, attribute)
        content = self._read_file(file_path)
        yaml_data, markdown_content = self._split_frontmatter(content)
        self.markdown_text_node = (
            markdown_text_node
            if markdown_text_node
            else self._create_text_node(markdown_content, auto_correct)
        )
        self.attribute = (
            attribute
            if attribute
            else self._parse_attribute(attribute_type, yaml_data, file_path)
        )


class AttributedMarkdownTextFileNode[T: BaseModel](  # pyright: ignore[reportIncompatibleVariableOverride, reportIncompatibleMethodOverride] - 带属性形态必然收窄：create_file 多要 attribute_type，_create_text_node 复用折叠侧的窄化
    FrontMatterTextFileMixin[T],
    AttributedMarkdownTextFileBase[T],
    FoldableMarkdownTextFileNode,
):
    """带属性的可折叠 Markdown 文件。

    早先直接继承 AttributedMarkdownTextFileBase 而非 MarkdownTextFileNode，
    拿不到基类的 markdown_text_node_type，reload() 等走基类的代码路径会
    AttributeError，于是不得不把 get_text / set_text / get_markdown_text_node
    全部重写一遍。改为继承真正的实现基类后，这些重复覆写全部消失。
    """


class BasicAttributedMarkdownTextFileNode[T: BaseModel](  # pyright: ignore[reportIncompatibleMethodOverride] - 带属性形态的 create_file 必然多要 attribute_type 与 attribute
    FrontMatterTextFileMixin[T],
    AttributedMarkdownTextFileBase[T],
    MarkdownTextFileNode,
):
    """非编号、非折叠、有 FrontMatter 的 Markdown 文件。

    早先这类文档无法表达：文件侧继承链严格单调，想要属性就连编号和折叠
    一起要。现在属性是横切关注点，编号与折叠交给用户自己拼。
    """
