"""markdown_folder_nodes.py - Markdown 文件夹节点，管理 .mdp 文件目录"""

import re
from pathlib import Path
from typing import override

from dl909markdowntree.interface import (
    NumberedMarkdownTextFileBase,
    NumberedMarkdownTitleBase,
)

from .models.exceptions import InvalidMdpFilenameError
from .numbered_markdown_nodes import (
    NumberedMarkdownTitleNode,
)

MDP_FILE_PATTERN = re.compile(r"^(\d+)_(.+)\.mdp$")


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
        self.file_path = file_path
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
            self.save()
        if not file_path.exists():
            self.create_file(file_path)
        self.reload(auto_correct)

    @staticmethod
    def _build_synthetic_text_from_dir(mdf_dir: Path) -> str:
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
                raise InvalidMdpFilenameError(
                    f"Invalid .mdp filename format: {entry.name}"
                )
            N = int(match.group(1))
            title = match.group(2)
            content = entry.read_text(encoding="utf-8")
            file_entries.append((N, title, content))

        file_entries.sort(key=lambda x: x[0])

        parts = []
        if preamble:
            parts.append(preamble)
        for N, title, content in file_entries:
            parts.append(f"# {N}. {title}\n{content}")

        return "\n\n".join(parts)

    def _create_text_node(
        self, text: str, auto_correct: bool = True
    ) -> NumberedMarkdownTitleNode:
        return NumberedMarkdownTitleNode.from_text(text=text, auto_correct=auto_correct)

    def _get_section_content(self, child: NumberedMarkdownTitleNode) -> str:
        return "".join(child.get_text().splitlines(keepends=True)[1:]).rstrip("\n")

    @override
    def reload(self, auto_correct: bool | None = None):
        synthetic_text = self._build_synthetic_text_from_dir(self.file_path)
        self.markdown_text_node = self._create_text_node(
            synthetic_text,
            auto_correct if auto_correct else self.markdown_text_node.auto_correct,
        )

    @override
    def save_to_file(self, file_path: Path):
        if not file_path.exists():
            file_path.mkdir(parents=True)

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
                raise RuntimeError()

        preamble_content = None
        if preamble_parts:
            preamble_content = ""
            for part in preamble_parts:
                preamble_content += part.get_text() + "\n" * 2
            if preamble_content != "":
                preamble_content = preamble_content[:-2].rstrip("\n")

        existing_mapping = {}
        for entry in file_path.iterdir():
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
            target_path = file_path / target_name
            if N in existing_mapping:
                _, old_path = existing_mapping[N]
                if old_path != target_path:
                    old_path.rename(target_path)
            target_path.write_text(content, encoding="utf-8")

        zero_path = file_path / "0.mdp"
        if preamble_content is not None:
            zero_path.write_text(preamble_content, encoding="utf-8")
        elif zero_path.exists():
            zero_path.unlink()

    @override
    def save(self):
        self.save_to_file(self.file_path)

    @override
    def get_text(self) -> str:
        return self.markdown_text_node.get_text()

    @override
    def set_text(self, text) -> None:
        self.markdown_text_node.set_text(text)

    @override
    def get_root_title(self) -> NumberedMarkdownTitleBase:
        return self.markdown_text_node
