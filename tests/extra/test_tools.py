"""Tests for dl909markdowntree.extra.tools"""

from dl909markdowntree import FoldableMarkdownTextFileNode, MarkdownTextFileNode
from dl909markdowntree.extra.tools import (
    append_tool,
    replace_lines_tool,
    replace_tool,
    unfold_tool,
)


def _make_folded_doc(tmp_path):
    doc_path = tmp_path / "folded.md"
    doc_path.write_text(
        "# 1. Title\nsecret hidden line\n## 1.1. Sub\nhidden sub",
        encoding="utf-8",
    )
    return FoldableMarkdownTextFileNode(doc_path)


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


def test_replace_tool_failure_rollback_preserves_folded_content(tmp_path):
    """replace 失败回滚时不应丢失折叠隐藏内容"""
    doc = _make_folded_doc(tmp_path)
    original = doc.get_text(full_text=True)

    result = replace_tool(doc, None, "# 1. Title", "## wrong level\nx")

    assert "replace failed" in result
    assert doc.get_text(full_text=True) == original


def test_replace_lines_tool_failure_rollback_preserves_folded_content(tmp_path):
    """replace_lines 失败回滚时不应丢失折叠隐藏内容"""
    doc = _make_folded_doc(tmp_path)
    original = doc.get_text(full_text=True)

    result = replace_lines_tool(
        doc,
        None,
        "# 1. Title",
        "secret hidden line\n## 1.1. Sub\nhidden sub",
        "## wrong level\nx",
    )

    assert "replace_lines failed" in result
    assert doc.get_text(full_text=True) == original


def test_append_tool_failure_rollback_preserves_folded_content(tmp_path, monkeypatch):
    """append 保存失败回滚时不应丢失折叠隐藏内容"""
    doc = _make_folded_doc(tmp_path)
    original = doc.get_text(full_text=True)

    def failing_save():
        raise OSError("disk full")

    monkeypatch.setattr(doc, "save", failing_save)
    result = append_tool(doc, None, "# 1. Title", "appended")

    assert "append failed" in result
    assert doc.get_text(full_text=True) == original
