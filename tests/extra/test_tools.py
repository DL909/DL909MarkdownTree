"""Tests for dl909markdowntree.extra.tools"""

import unittest.mock

import pytest

from dl909markdowntree import (
    FoldableMarkdownFolderNode,
    FoldableMarkdownTextFileNode,
    FoldMode,
    MarkdownTextFileNode,
    NodePermissionChecker,
    NumberedMarkdownTextFileNode,
    Permission,
)
from dl909markdowntree.extra.tools import (
    append_tool,
    read_tool,
    rename_title_tool,
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


def test_read_tool_returns_full_text_for_folded_target(tmp_path):
    """读折叠中的目标标题应拿到正文，而不是 [text folded] 占位符"""
    doc = _make_folded_doc(tmp_path)
    title = doc.get_root_title().children[0]
    title.fold_mode = FoldMode.SHOW_TITLE

    result = read_tool(doc, None, "# 1. Title")

    assert "secret hidden line" in result
    assert "hidden sub" in result
    assert "folded" not in result


def test_unfold_tool_requires_write_permission(tmp_path):
    """unfold 会改 fold_mode 并落盘，只读权限不得放行"""
    folder = tmp_path / "book.mdf"
    folder.mkdir()
    (folder / "1_One.mdp").write_text("content", encoding="utf-8")
    doc = FoldableMarkdownFolderNode(folder)
    title = doc.get_root_title().children[0]
    checker = NodePermissionChecker([(title, Permission.READ)])

    with pytest.raises(PermissionError):
        unfold_tool(doc, checker, "# 1. One")

    assert not (folder / "fold_state.json").exists()
    assert title.fold_mode is not FoldMode.SHOW_CHILD


def test_unfold_tool_allowed_with_write_permission(tmp_path):
    """持有写权限时 unfold 正常执行"""
    folder = tmp_path / "book.mdf"
    folder.mkdir()
    (folder / "1_One.mdp").write_text("content", encoding="utf-8")
    doc = FoldableMarkdownFolderNode(folder)
    title = doc.get_root_title().children[0]
    checker = NodePermissionChecker([(title, Permission.READ_WRITE)])

    result = unfold_tool(doc, checker, "# 1. One")

    assert "content" in result
    assert title.fold_mode is FoldMode.SHOW_CHILD


@pytest.mark.parametrize(
    "bad_title",
    [
        "Injected\n\n# 9. Sneaky\nowned",  # 换行可伪造新标题
        "Injected\r\n# 9. Sneaky",  # CRLF 同样可伪造
        "   ",
        "",
    ],
)
def test_rename_title_rejects_structure_forging_input(tmp_path, bad_title):
    """标题文本含换行 / 纯空白时必须拒绝，防止伪造文档结构"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody A\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)

    result = rename_title_tool(doc, None, "# 1. A", bad_title)

    assert result.startswith("rename_title failed:")
    assert doc_path.read_text(encoding="utf-8") == "# 1. A\nbody A\n"


def test_rename_title_accepts_hash_inside_title(tmp_path):
    """标题文本里的 # 不是注入向量，不应被误拒（无换行即无法伪造节点）"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody A\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)

    result = rename_title_tool(doc, None, "# 1. A", "#1 retrospective")

    assert result == "rename_title succeeded"
    assert doc_path.read_text(encoding="utf-8") == "# 1. #1 retrospective\nbody A\n"


def test_rename_title_accepts_normal_title(tmp_path):
    """普通标题改名仍应成功"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody A\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)

    assert rename_title_tool(doc, None, "# 1. A", "Renamed") == "rename_title succeeded"
    assert doc_path.read_text(encoding="utf-8") == "# 1. Renamed\nbody A\n"


def test_replace_lines_fuzzy_replaces_at_the_matched_line_not_the_first(tmp_path):
    """模糊匹配只应改写命中的那一行，其余内容保持不变"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nrepeat me\nrepeat me\nrepeat me\n", encoding="utf-8")
    doc = FoldableMarkdownTextFileNode(doc_path)

    result = replace_lines_tool(doc, None, "# 1. A", "repat me", "FIXED\n")

    assert "fuzzy match" in result
    written = doc_path.read_text(encoding="utf-8")
    assert written.count("repeat me") == 2
    assert written.count("FIXED") == 1


def test_replace_lines_fuzzy_preserves_surrounding_lines(tmp_path):
    """模糊替换不得吞掉匹配窗口之外的内容"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nalpha\nbravo\ncharlie\ndelta\n", encoding="utf-8")
    doc = FoldableMarkdownTextFileNode(doc_path)

    # 故意与正文不完全一致，确保走模糊匹配分支
    result = replace_lines_tool(
        doc, None, "# 1. A", "bravoo\ncharlle", "BRAVO\nCHARLIE\n"
    )

    assert "fuzzy match" in result
    written = doc_path.read_text(encoding="utf-8")
    assert "alpha" in written
    assert "delta" in written
    assert "BRAVO" in written
    assert "bravo" not in written


def test_replace_lines_empty_old_lines_reports_real_reason(tmp_path):
    """空 old_lines 应报出真实原因，而不是与"多处匹配"混淆的错误"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody A\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)

    result = replace_lines_tool(doc, None, "# 1. A", "", "INSERTED")

    assert result == "replace_lines failed: old_lines is empty"
    assert "INSERTED" not in doc.get_text()


def test_tool_rollback_failure_is_logged_not_raised(tmp_path, caplog):
    """回滚自身抛错也不得穿透工具函数，应记录日志并返回原始失败信息"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody A\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    title_type = type(doc.get_root_title())
    calls = {"n": 0}

    def flaky_set_text(self, text):
        calls["n"] += 1
        raise RuntimeError(
            "boom during set_text" if calls["n"] == 1 else "boom during rollback"
        )

    with (
        caplog.at_level("ERROR"),
        unittest.mock.patch.object(title_type, "set_text", flaky_set_text),
    ):
        result = replace_tool(doc, None, "# 1. A", "new body\n")

    assert result == "replace failed: boom during set_text"
    assert calls["n"] == 2  # 首次失败 + 回滚也失败
    assert any("rollback also failed" in r.getMessage() for r in caplog.records)
