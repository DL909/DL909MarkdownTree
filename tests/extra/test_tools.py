"""Tests for dl909markdowntree.extra.tools"""

from dl909markdowntree import FoldableMarkdownTextFileNode
from dl909markdowntree.extra.tools import replace_lines_tool


def test_replace_lines_matches_hidden_folded_line(tmp_path):
    """折叠视图中隐藏的行也应可被 replace_lines 匹配替换"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. Title\nhidden line\n", encoding="utf-8")
    doc = FoldableMarkdownTextFileNode(doc_path)

    result = replace_lines_tool(
        doc, None, "# 1. Title", "hidden line", "replaced line"
    )

    assert "replace_lines succeeded" in result
    assert doc.get_text(full_text=True) == "# 1. Title\nreplaced line\n"
    assert "hidden line" not in doc_path.read_text(encoding="utf-8")
