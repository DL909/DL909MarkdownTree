"""Tests for dl909markdowntree.extra.tools"""

from dl909markdowntree import FoldableMarkdownTextFileNode, MarkdownTextFileNode
from dl909markdowntree.extra.tools import replace_lines_tool, unfold_tool


def test_unfold_tool_returns_error_for_non_foldable_node(tmp_path):
    """非折叠节点调用 unfold 应返回失败信息而不是抛 AttributeError"""
    doc_path = tmp_path / "plain.md"
    doc_path.write_text("# Hello\ncontent\n", encoding="utf-8")
    doc = MarkdownTextFileNode(doc_path)

    result = unfold_tool(doc, None, "# Hello")

    assert result == "unfold failed: node '# Hello' is not foldable"


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
