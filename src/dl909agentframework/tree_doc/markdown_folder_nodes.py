"""markdown_folder_nodes.py - Markdown 文件夹节点，管理 .mdp 文件目录"""

from pathlib import Path
import re
from typing import override

from pydantic import Field

from .file_node import FileNode
from .text_node import TextNode
from .numbered_markdown_nodes import (
    NumberedMarkdownTextNode,
    NumberedMarkdownTitleNode,
)

MDP_FILE_PATTERN = re.compile(r"^(\d+)_(.+)\.mdp$")


class MarkdownFolderNode(FileNode, TextNode):
    markdown_text_node: NumberedMarkdownTextNode = Field(
        default_factory=lambda: NumberedMarkdownTextNode("")
    )
    auto_correct: bool = Field(default=True)

    def __init__(self, file_path: Path, **kargs):
        auto_correct = kargs.pop("auto_correct", True)
        if kargs.get("markdown_text_node"):
            markdown_text_node = kargs.pop("markdown_text_node")
        else:
            mdf_dir = Path(file_path)
            if mdf_dir.is_dir():
                synthetic_text = self._build_synthetic_text_from_dir(mdf_dir)
            else:
                synthetic_text = ""
            markdown_text_node = self._create_text_node(synthetic_text, auto_correct)
        super().__init__(
            file_path=file_path,
            markdown_text_node=markdown_text_node,
            auto_correct=auto_correct,
            **kargs,
        )

    @staticmethod
    def _build_synthetic_text_from_dir(mdf_dir: Path) -> str:
        if not mdf_dir.is_dir():
            return ""

        file_entries = []
        preamble = None
        for entry in sorted(mdf_dir.iterdir()):
            if not entry.name.endswith(".mdp"):
                continue
            if entry.name == "0.mdp":
                preamble = entry.read_text(encoding="utf-8")
                continue
            match = MDP_FILE_PATTERN.match(entry.name)
            if not match:
                raise Exception(f"Invalid .mdp filename format: {entry.name}")
            N = int(match.group(1))
            title = match.group(2)
            content = entry.read_text(encoding="utf-8")
            file_entries.append((N, title, content))

        Ns = [e[0] for e in file_entries]
        if len(Ns) != len(set(Ns)):
            raise Exception(f"Duplicate section numbers in {mdf_dir}")

        file_entries.sort(key=lambda x: x[0])

        parts = []
        if preamble:
            parts.append(preamble)
        for N, title, content in file_entries:
            parts.append(f"# {N}. {title}\n{content}")

        return "\n\n".join(parts)

    def _create_text_node(
        self, text: str, auto_correct: bool = True
    ) -> NumberedMarkdownTextNode:
        return NumberedMarkdownTextNode(text=text, auto_correct=auto_correct)

    @override
    def reload(self):
        synthetic_text = self._build_synthetic_text_from_dir(Path(self.file_path))
        self.markdown_text_node = self._create_text_node(
            synthetic_text, self.auto_correct
        )

    def _get_mdp_content(self, title_node: NumberedMarkdownTitleNode) -> str:
        text = ""
        for child in title_node.children:
            text += child.get_text() + "\n" * 2
        if text != "":
            text = text[:-2]
        return text

    @override
    def save(self):
        mdf_dir = Path(self.file_path)
        if not mdf_dir.exists():
            mdf_dir.mkdir(parents=True)

        preamble_parts = []
        sections = []

        found_first_level1 = False
        for child in self.markdown_text_node.children:
            if (
                isinstance(child, NumberedMarkdownTitleNode)
                and child.level == 1
                and len(child.number) == 1
            ):
                found_first_level1 = True
                N = child.number[0]
                title = child.title
                content = self._get_mdp_content(child)
                sections.append((N, title, content))
            elif not found_first_level1:
                preamble_parts.append(child)
            else:
                preamble_parts.append(child)

        preamble_content = None
        if preamble_parts:
            preamble_content = ""
            for part in preamble_parts:
                preamble_content += part.get_text() + "\n" * 2
            if preamble_content != "":
                preamble_content = preamble_content[:-2]

        existing_mapping = {}
        for entry in mdf_dir.iterdir():
            if not entry.name.endswith(".mdp"):
                continue
            if entry.name == "0.mdp":
                continue
            match = MDP_FILE_PATTERN.match(entry.name)
            if match:
                N = int(match.group(1))
                existing_mapping[N] = (match.group(2), entry)

        new_numbers = {N for N, _, _ in sections}
        existing_numbers = set(existing_mapping.keys())
        for N in existing_numbers - new_numbers:
            _, path = existing_mapping[N]
            path.unlink()

        for N, title, content in sections:
            target_name = f"{N}_{title}.mdp"
            target_path = mdf_dir / target_name
            if N in existing_mapping:
                _, old_path = existing_mapping[N]
                if old_path != target_path:
                    old_path.rename(target_path)
            target_path.write_text(content, encoding="utf-8")

        zero_path = mdf_dir / "0.mdp"
        if preamble_content is not None:
            zero_path.write_text(preamble_content, encoding="utf-8")
        elif zero_path.exists():
            zero_path.unlink()

    @override
    def get_text(self) -> str:
        return self.markdown_text_node.get_text()

    @override
    def set_text(self, text) -> None:
        self.markdown_text_node.set_text(text)

    def recursive_find_title_node_by_name(
        self, title_name: str
    ) -> NumberedMarkdownTitleNode | None:
        return self.markdown_text_node.recursive_find_title_node_by_name(title_name)
