"""foldable_markdown_folder_nodes.py - 可折叠 Markdown 文件夹节点"""

from pathlib import Path
import json
from typing import override

from .foldable_markdown_nodes import (
    FoldMode,
    FoldableMarkdownTextNode,
    FoldableMarkdownTitleNode,
)
from .markdown_folder_nodes import MarkdownFolderNode
from .numbered_markdown_nodes import NumberedMarkdownTitleNode


class FoldableMarkdownFolderNode(MarkdownFolderNode):
    markdown_text_node: FoldableMarkdownTextNode  # type: ignore
    use_fold_states: bool = False

    def _create_text_node(
        self, text: str, auto_correct: bool = True
    ) -> FoldableMarkdownTextNode:
        return FoldableMarkdownTextNode(text=text, auto_correct=auto_correct)

    def _get_mdp_content(self, title_node: NumberedMarkdownTitleNode) -> str:
        text = ""
        for child in title_node.children:
            if isinstance(child, FoldableMarkdownTitleNode):
                text += child.get_text(full_text=True) + "\n" * 2
            else:
                text += child.get_text() + "\n" * 2
        if text != "":
            text = text[:-2]
        return text

    def _collect_fold_states(self) -> dict[str, str]:
        states = {}

        def _walk(node):
            for child in node.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    key = json.dumps(child.number)
                    if child.fold_mode is not FoldMode.SHOW_TITLE:
                        states[key] = child.fold_mode.name
                    _walk(child)

        _walk(self.markdown_text_node)
        return states

    def _apply_fold_states(self, states: dict[str, str]) -> None:
        def _walk(node):
            for child in node.children:
                if isinstance(child, FoldableMarkdownTitleNode):
                    key = json.dumps(child.number)
                    if key in states:
                        child.fold_mode = FoldMode[states[key]]
                    _walk(child)

        _walk(self.markdown_text_node)

    @override
    def reload(self):
        super().reload()
        fold_states_path = Path(self.file_path) / "fold_state.json"
        if fold_states_path.exists():
            raw = fold_states_path.read_text(encoding="utf-8")
            if raw:
                states = json.loads(raw)
                self._apply_fold_states(states)

    @override
    def save(self):
        super().save()
        states = self._collect_fold_states()
        if states:
            fold_states_path = Path(self.file_path) / "fold_state.json"
            fold_states_path.write_text(json.dumps(states, indent=2), encoding="utf-8")
        else:
            fold_states_path = Path(self.file_path) / "fold_state.json"
            if fold_states_path.exists():
                fold_states_path.unlink()

    @override
    def get_text(self, with_fold_info: bool = True, full_text: bool = False) -> str:
        return self.markdown_text_node.get_text(
            with_fold_info=with_fold_info, full_text=full_text
        )

    @override
    def recursive_find_title_node_by_name(
        self, title_name: str, within_shown: bool = False
    ) -> FoldableMarkdownTitleNode | None:
        return self.markdown_text_node.recursive_find_title_node_by_name(
            title_name, within_shown=within_shown
        )
