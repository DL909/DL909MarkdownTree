"""markdown_folder_nodes.py - Markdown 文件夹节点，管理 .mdp 文件目录"""

import logging
import re
from pathlib import Path
from typing import override

from .exceptions import InvalidMdpFilenameError
from .interface import (
    NumberedMarkdownTextFileBase,
    NumberedMarkdownTitleBase,
)
from .numbered_markdown_nodes import (
    NumberedMarkdownTitleNode,
)
from .text_node import TextNode

MDP_FILE_PATTERN = re.compile(r"^(\d+)_(.+)\.mdp$")

_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')

logger = logging.getLogger(__name__)


def _sanitize_mdp_title(title: str) -> str:
    return _UNSAFE_FILENAME_CHARS.sub("_", title).strip(". ") or "untitled"


def _mdp_filename(section_number: int, title: str) -> str:
    """生成 .mdp 文件名；标题被改写时告警（消毒不可逆，原标题将永久丢失）"""
    safe = _sanitize_mdp_title(title)
    if safe != title:
        logger.warning(
            f"section {section_number} title {title!r} contains characters that "
            f"are unsafe for a filename; the .mdp file is named {safe!r} and the "
            f"title will read back as {safe!r} after reload"
        )
    return f"{section_number}_{safe}.mdp"


def _as_text_file_content(text: str) -> str:
    """归一化为 POSIX 文本文件形态：非空内容恰好一个结尾换行，空内容则空文件

    早期实现对每个 section 都 rstrip 掉结尾换行，导致每次保存都会产生一次
    与用户无关的 diff（"body\\n" -> "body"）。现在写盘保留结尾换行，读盘时
    再统一归一化，保证 reload -> save 往返幂等。
    """
    stripped = text.rstrip("\n")
    return stripped + "\n" if stripped else ""


class NumberedMarkdownFolderNode(NumberedMarkdownTextFileBase):
    @staticmethod
    def create_file(file_path: Path) -> None:
        Path(file_path).mkdir(parents=True, exist_ok=True)

    def __init__(
        self,
        file_path: Path,
        auto_correct: bool = True,
        markdown_text_node: NumberedMarkdownTitleNode | None = None,
    ):
        file_path = Path(file_path)
        # 必须走 FileNode.__init__：它负责初始化 Node.children。早先这里直接
        # 赋值 self.file_path 而跳过 super().__init__()，导致 children 属性缺失，
        # node.children 与基类的 Node.update() 都会抛 AttributeError。
        # 文件节点的 children 约定为空列表（内容挂在 markdown_text_node 上），
        # 与 PlainTextFileNode 等保持一致。
        super().__init__(file_path=file_path)
        self.auto_correct = auto_correct
        self.markdown_text_node = (
            markdown_text_node
            if markdown_text_node
            else (
                self._create_text_node(
                    self._build_synthetic_text_from_dir(file_path),
                    auto_correct=auto_correct,
                )
                if file_path.exists()
                else NumberedMarkdownTitleNode(level=0)
            )
        )
        if markdown_text_node:
            # 传入的节点就是调用方期望的状态：落盘后直接返回。早先这里仍会
            # 无条件 reload()，而 reload() 用磁盘内容重建节点树，会把调用方
            # 刚拿到的节点整个替换掉——内容写进去了，对象身份却悄悄丢失。
            self.save()
            return
        if not file_path.exists():
            self.create_file(file_path)
        self.reload()

    @staticmethod
    def _build_synthetic_text_from_dir(mdf_dir: Path) -> str:
        file_entries = []
        preamble = None
        for entry in sorted(mdf_dir.iterdir()):
            if not entry.name.endswith(".mdp"):
                continue
            if entry.name == "0.mdp":
                # 归一化：0.mdp 的结尾换行由 save 统一补，读盘时先剥掉，
                # 否则每次 reload 都会在段落之间多插一个空行并逐轮累积
                preamble = _as_text_file_content(
                    entry.read_text(encoding="utf-8")
                ).rstrip("\n")
                continue
            match = MDP_FILE_PATTERN.match(entry.name)
            if not match:
                raise InvalidMdpFilenameError(
                    f"Invalid .mdp filename format: {entry.name}"
                )
            N = int(match.group(1))
            title = match.group(2)
            content = entry.read_text(encoding="utf-8").rstrip("\n")
            file_entries.append((N, title, content))

        file_entries.sort(key=lambda x: x[0])

        parts = []
        if preamble:
            parts.append(preamble)
        for N, title, content in file_entries:
            section = f"# {N}. {title}"
            if content:
                section += "\n" + content
            parts.append(section)

        return _as_text_file_content("\n\n".join(parts))

    def _create_text_node(
        self, text: str, auto_correct: bool = True
    ) -> NumberedMarkdownTitleNode:
        return NumberedMarkdownTitleNode.from_text(text=text, auto_correct=auto_correct)

    def _get_section_content(self, child: NumberedMarkdownTitleNode) -> str:
        return _as_text_file_content(
            "".join(child.get_text().splitlines(keepends=True)[1:])
        )

    def _get_preamble_part_content(self, part: TextNode) -> str:
        return part.get_text()

    @override
    def reload(self):
        synthetic_text = self._build_synthetic_text_from_dir(self.file_path)
        self.markdown_text_node = self._create_text_node(
            synthetic_text, auto_correct=self.auto_correct
        )

    def reload_with(self, auto_correct: bool) -> None:
        """以指定的 auto_correct 重新加载，并记住该设置供后续 reload() 使用

        单独提供而非给 reload() 加参数：FileNode.reload() 不带参数，文件夹节点
        给它加一个带默认值的参数既违反里氏替换，也让"用哪个值"变得含糊。
        """
        self.auto_correct = auto_correct
        self.reload()

    @override
    def save_to_file(self, file_path: Path):
        file_path = Path(file_path)
        # exist_ok=True：exists() 与 mkdir() 之间存在竞态，缺了会在并发
        # 创建同一目录时抛 FileExistsError
        file_path.mkdir(parents=True, exist_ok=True)

        if not file_path.is_dir():
            raise NotADirectoryError(f"{file_path} isn't a directory")

        preamble_parts = []
        sections = []

        found_first_level1 = False
        for child in self.get_root_title().children:
            if (
                isinstance(child, NumberedMarkdownTitleNode)
                and child.level == 1
                and len(child.number) == 1
            ):
                found_first_level1 = True
                N = child.number[0]
                title = child.title
                content = self._get_section_content(child)
                sections.append((N, title, content))
            elif not found_first_level1:
                preamble_parts.append(child)
            else:
                raise RuntimeError(
                    f"unexpected content after first level-1 section: {type(child).__name__}"
                )

        # preamble_content 为 None 表示"本次没有前言"，与"前言为空串"区分开：
        # 前者删除 0.mdp，后者写出空文件。纯空白段落归一化为空，避免
        # "只含换行的 0.mdp" 在往返中被改写成空串造成漂移。
        preamble_content: str | None = None
        if preamble_parts:
            body = "\n\n".join(
                text
                for text in (
                    self._get_preamble_part_content(part).rstrip("\n")
                    for part in preamble_parts
                )
                if text.strip()
            )
            preamble_content = _as_text_file_content(body)

        existing_files: dict[int, list[tuple[str, Path]]] = {}
        for entry in file_path.iterdir():
            if not entry.name.endswith(".mdp"):
                continue
            if entry.name == "0.mdp":
                continue
            match = MDP_FILE_PATTERN.match(entry.name)
            if match:
                N = int(match.group(1))
                existing_files.setdefault(N, []).append((match.group(2), entry))

        new_numbers = {N for N, _, _ in sections}
        for N, files in existing_files.items():
            if N not in new_numbers:
                for _, path in files:
                    path.unlink()

        for N, title, content in sections:
            # 同一编号下的旧文件先全部删掉，再按新名字写一个。早先是
            # "找到第一个旧文件 -> 删掉同名目标 -> rename 过去 -> 再删剩下的"，
            # 三段循环才凑齐一个结果：文件名由本节的标题决定，内容永远来自本节，
            # rename 纯属多余。删完再写让"标题改名""同编号多文件"走同一条路径。
            for _, old_path in existing_files.get(N, ()):
                old_path.unlink()
            (file_path / _mdp_filename(N, title)).write_text(content, encoding="utf-8")

        zero_path = file_path / "0.mdp"
        if preamble_content is not None:
            zero_path.write_text(preamble_content, encoding="utf-8")
        elif zero_path.exists():
            zero_path.unlink()

    @override
    def save(self) -> None:
        self.save_to_file(self.file_path)

    @override
    def get_text(self) -> str:
        return self.markdown_text_node.get_text()

    @override
    def set_text(self, text: str) -> None:
        self.markdown_text_node.set_text(text)

    @override
    def get_root_title(self) -> NumberedMarkdownTitleBase:
        return self.markdown_text_node

    @override
    def get_markdown_text_node(self) -> NumberedMarkdownTitleBase:
        return self.markdown_text_node
