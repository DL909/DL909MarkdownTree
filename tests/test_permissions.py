"""Tests for dl909markdowntree.permissions"""

from pathlib import Path

from dl909markdowntree import (
    FoldableMarkdownTextFileNode,
    MarkdownTextFileNode,
    NodePermissionChecker,
    Permission,
    TitlePathPermissionChecker,
)


def _make_node(tmp_path: Path) -> MarkdownTextFileNode:
    tmp_path.mkdir(parents=True, exist_ok=True)
    doc = tmp_path / "doc.md"
    doc.write_text("# Hello\n\nWorld content.\n", encoding="utf-8")
    return MarkdownTextFileNode(doc)


def test_permission_enum_values():
    assert Permission.DENY.value == 0
    assert Permission.READ.value == 1
    assert Permission.READ_WRITE.value == 2
    assert Permission.NONE.value == 3


def test_permission_checker_default_no_permissions(tmp_path: Path):
    node = _make_node(tmp_path)
    checker = NodePermissionChecker()
    ok, msg = checker.check_permission(node, Permission.READ)
    assert ok is True
    assert msg == ""


def test_check_permission_none_always_passes(tmp_path: Path):
    node = _make_node(tmp_path)
    checker = NodePermissionChecker([(node, Permission.DENY)])
    ok, msg = checker.check_permission(node, Permission.NONE)
    assert ok is True
    assert msg == ""


def test_check_permission_granted_when_effective_meets_required(tmp_path: Path):
    node = _make_node(tmp_path)
    checker = NodePermissionChecker([(node, Permission.READ_WRITE)])
    ok, msg = checker.check_permission(node, Permission.READ)
    assert ok is True
    assert msg == ""


def test_check_permission_denied_when_effective_below_required(tmp_path: Path):
    node = _make_node(tmp_path)
    checker = NodePermissionChecker([(node, Permission.READ)])
    ok, msg = checker.check_permission(node, Permission.READ_WRITE)
    assert ok is False
    assert "权限不足" in msg
    assert "READ" in msg
    assert "READ_WRITE" in msg


def test_check_permission_denied_for_root_node(tmp_path: Path):
    checker = NodePermissionChecker([(None, Permission.READ)])
    ok, msg = checker.check_permission(None, Permission.READ_WRITE)
    assert ok is False
    assert "根节点" in msg


def test_set_permissions_replaces_list(tmp_path: Path):
    node = _make_node(tmp_path)
    checker = NodePermissionChecker([(node, Permission.DENY)])
    ok, _ = checker.check_permission(node, Permission.READ)
    assert ok is False

    checker.set_permissions([(node, Permission.READ_WRITE)])
    ok, _ = checker.check_permission(node, Permission.READ_WRITE)
    assert ok is True


def test_find_effective_permission_empty_list_returns_read_write(tmp_path: Path):
    node = _make_node(tmp_path)
    checker = NodePermissionChecker()
    ok, _ = checker.check_permission(node, Permission.READ_WRITE)
    assert ok is True


def test_find_effective_permission_no_match_returns_deny(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Title\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    title = node.get_root_title().recursive_find_title_node_by_name("# Title")
    assert title is not None

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other_doc = other_dir / "doc.md"
    other_doc.write_text("# Other\nContent.\n", encoding="utf-8")
    unrelated_node = MarkdownTextFileNode(other_doc)
    checker = NodePermissionChecker([(unrelated_node, Permission.READ_WRITE)])
    ok, _ = checker.check_permission(title, Permission.READ)
    assert ok is False


def test_find_effective_permission_inherits_from_parent(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    parent_title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert parent_title is not None
    assert child_title is not None
    assert child_title.parent is parent_title

    checker = NodePermissionChecker([(parent_title, Permission.READ)])
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is True

    ok, _ = checker.check_permission(child_title, Permission.READ_WRITE)
    assert ok is False


def test_find_effective_permission_deny_at_child_overrides_parent(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    parent_title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert parent_title is not None
    assert child_title is not None

    checker = NodePermissionChecker([
        (parent_title, Permission.READ_WRITE),
        (child_title, Permission.DENY),
    ])
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is False


def test_find_effective_permission_deny_at_parent_overrides_child(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    parent_title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert parent_title is not None
    assert child_title is not None

    checker = NodePermissionChecker([
        (parent_title, Permission.DENY),
        (child_title, Permission.READ_WRITE),
    ])
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is False


def test_find_effective_permission_root_entry_applies(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    assert title is not None

    checker = NodePermissionChecker([(None, Permission.DENY)])
    ok, _ = checker.check_permission(title, Permission.READ)
    assert ok is False

    checker = NodePermissionChecker([(None, Permission.READ_WRITE)])
    ok, _ = checker.check_permission(title, Permission.READ)
    assert ok is True


def test_get_node_description_with_title(tmp_path: Path):
    node = _make_node(tmp_path)
    title_node = node.get_root_title().recursive_find_title_node_by_name("# Hello")
    assert title_node is not None
    checker = NodePermissionChecker()
    desc = checker._get_node_description(title_node)
    assert desc == "'Hello'"


def test_get_node_description_none_returns_root(tmp_path: Path):
    checker = NodePermissionChecker()
    desc = checker._get_node_description(None)
    assert desc == "根节点"


def test_get_node_description_no_title_no_name(tmp_path: Path):
    node = _make_node(tmp_path)
    checker = NodePermissionChecker()
    desc = checker._get_node_description(node)
    assert desc == f"<{type(node).__name__}>"


def test_check_permission_foldable_node_inherits_parent_permission(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# 1. Parent\n## 1.1. Child\n\nContent.\n", encoding="utf-8")
    node = FoldableMarkdownTextFileNode(doc)
    parent_title = node.get_root_title().recursive_find_title_node_by_name("# 1. Parent")
    child_title = node.get_root_title().recursive_find_title_node_by_name("## 1.1. Child")
    assert parent_title is not None
    assert child_title is not None

    checker = NodePermissionChecker([(parent_title, Permission.READ)])
    ok, _ = checker.check_permission(child_title, Permission.READ_WRITE)
    assert ok is False

    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is True


def test_path_checker_node_registration_inherits(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    parent_title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert parent_title is not None
    assert child_title is not None

    checker = TitlePathPermissionChecker([(parent_title, Permission.READ)])
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is True

    ok, _ = checker.check_permission(child_title, Permission.READ_WRITE)
    assert ok is False


def test_path_checker_node_registration_deny_overrides(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    parent_title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert parent_title is not None
    assert child_title is not None

    checker = TitlePathPermissionChecker([
        (parent_title, Permission.READ_WRITE),
        (child_title, Permission.DENY),
    ])
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is False


def test_path_checker_explicit_path_registration(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert child_title is not None

    checker = TitlePathPermissionChecker([
        (("# Parent",), Permission.READ),
        (("# Parent", "## Child"), Permission.READ_WRITE),
    ])
    ok, _ = checker.check_permission(child_title, Permission.READ_WRITE)
    assert ok is True


def test_path_checker_explicit_path_no_match_returns_deny(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert child_title is not None

    checker = TitlePathPermissionChecker([(("# Other",), Permission.READ_WRITE)])
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is False


def test_path_checker_root_entries_equivalent(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    assert title is not None

    for root_key in (None, ()):
        checker = TitlePathPermissionChecker([(root_key, Permission.DENY)])
        ok, _ = checker.check_permission(title, Permission.READ)
        assert ok is False

    checker = TitlePathPermissionChecker([(None, Permission.READ_WRITE)])
    ok, _ = checker.check_permission(None, Permission.READ)
    assert ok is True


def test_path_checker_root_title_node_treated_as_root(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    root_title = node.get_root_title()

    checker = TitlePathPermissionChecker([(None, Permission.DENY)])
    ok, _ = checker.check_permission(root_title, Permission.READ)
    assert ok is False


def test_path_checker_node_without_title_treated_as_root(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    title = node.get_root_title().recursive_find_title_node_by_name("# Parent")
    assert title is not None

    checker = TitlePathPermissionChecker([(node, Permission.DENY)])
    ok, _ = checker.check_permission(title, Permission.READ)
    assert ok is False


def test_path_checker_survives_reload(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert child_title is not None
    checker = TitlePathPermissionChecker([(child_title, Permission.READ)])

    node.reload()
    new_child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert new_child_title is not None
    assert new_child_title is not child_title

    ok, _ = checker.check_permission(new_child_title, Permission.READ)
    assert ok is True

    ok, _ = checker.check_permission(new_child_title, Permission.READ_WRITE)
    assert ok is False


def test_path_checker_explicit_path_survives_reload(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    checker = TitlePathPermissionChecker([
        (("# Parent", "## Child"), Permission.READ),
    ])

    node.reload()
    new_child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert new_child_title is not None
    ok, _ = checker.check_permission(new_child_title, Permission.READ)
    assert ok is True


def test_path_checker_deny_at_parent_overrides_child(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert child_title is not None

    checker = TitlePathPermissionChecker([
        (("# Parent",), Permission.DENY),
        (("# Parent", "## Child"), Permission.READ_WRITE),
    ])
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is False
