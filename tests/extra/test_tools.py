"""Tests for dl909markdowntree.extra.tools"""

from dl909markdowntree import (
    FoldableMarkdownFolderNode,
    FoldableMarkdownTextFileNode,
    FoldMode,
    MarkdownTextFileNode,
)
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

    result = replace_lines_tool(doc, None, "# 1. Title", "hidden line", "replaced line")

    assert "replace_lines succeeded" in result
    assert doc.get_text(full_text=True) == "# 1. Title\nreplaced line\n"
    assert "hidden line" not in doc_path.read_text(encoding="utf-8")


def test_replace_tool_failure_rollback_preserves_folded_content(tmp_path):
    """replace 失败回滚时不应丢失折叠隐藏内容"""
    doc = _make_folded_doc(tmp_path)
    original = doc.get_text(full_text=True)

    result = replace_tool(doc, None, "## 1.1. sub", "# wrong level\nx")

    assert "replace failed" in result
    assert doc.get_text(full_text=True) == original


def test_replace_lines_tool_failure_rollback_preserves_folded_content(tmp_path):
    """replace_lines 失败回滚时不应丢失折叠隐藏内容"""
    doc = _make_folded_doc(tmp_path)
    original = doc.get_text(full_text=True)

    result = replace_lines_tool(
        doc,
        None,
        "## 1.1. Sub",
        "## 1.1. Sub",
        "# wrong level\nx",
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


def test_replace_lines_tool_does_not_match_folded_marker(tmp_path):
    """折叠标记不应被匹配替换，匹配始终基于完整文本"""
    doc = _make_folded_doc(tmp_path)
    original = doc.get_text(full_text=True)
    disk_before = doc.file_path.read_text(encoding="utf-8")

    result = replace_lines_tool(
        doc, None, "# 1. Title", "[text folded]", "[text hidden]"
    )

    assert "no match found" in result
    assert doc.get_text(full_text=True) == original
    assert doc.file_path.read_text(encoding="utf-8") == disk_before


def test_append_tool_preserves_descendant_fold_states(tmp_path):
    """工具编辑不应重置后代折叠状态"""
    doc = _make_folded_doc(tmp_path)
    title = doc.get_root_title().children[0]
    sub = title.children[1]
    title.fold_mode = FoldMode.SHOW_CHILD
    sub.fold_mode = FoldMode.SHOW_CHILD

    result = append_tool(doc, None, "# 1. Title", "extra")

    assert "append succeeded" in result
    new_title = doc.get_root_title().children[0]
    new_sub = new_title.children[1]
    assert new_title.fold_mode is FoldMode.SHOW_CHILD
    assert new_sub.fold_mode is FoldMode.SHOW_CHILD


def test_folder_tool_edit_persists_descendant_fold_states(tmp_path):
    """文件夹节点工具编辑后折叠状态应持久化，重开不丢失"""
    folder = tmp_path / "book.mdf"
    folder.mkdir()
    (folder / "1_One.mdp").write_text("## 1.1. Sub\ncontent", encoding="utf-8")
    doc = FoldableMarkdownFolderNode(folder)
    title = doc.get_root_title().children[0]
    sub = title.children[0]
    title.fold_mode = FoldMode.SHOW_CHILD
    sub.fold_mode = FoldMode.SHOW_CHILD

    result = append_tool(doc, None, "# 1. One", "extra")
    assert "append succeeded" in result
    doc.save()

    reopened = FoldableMarkdownFolderNode(folder)
    new_title = reopened.get_root_title().children[0]
    new_sub = new_title.children[0]
    assert new_title.fold_mode is FoldMode.SHOW_CHILD
    assert new_sub.fold_mode is FoldMode.SHOW_CHILD
