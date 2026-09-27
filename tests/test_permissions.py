"""Tests for dl909markdowntree.permissions"""

from pathlib import Path

import pytest

from dl909markdowntree import (
    FoldableMarkdownTextFileNode,
    MarkdownTextFileNode,
    NodePermissionChecker,
    NumberedMarkdownTextFileNode,
    Permission,
    TitlePathPermissionChecker,
)
from dl909markdowntree.extra.tools import rename_title_tool


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

    checker = NodePermissionChecker(
        [
            (parent_title, Permission.READ_WRITE),
            (child_title, Permission.DENY),
        ]
    )
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

    checker = NodePermissionChecker(
        [
            (parent_title, Permission.DENY),
            (child_title, Permission.READ_WRITE),
        ]
    )
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
    parent_title = node.get_root_title().recursive_find_title_node_by_name(
        "# 1. Parent"
    )
    child_title = node.get_root_title().recursive_find_title_node_by_name(
        "## 1.1. Child"
    )
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

    checker = TitlePathPermissionChecker(
        [
            (parent_title, Permission.READ_WRITE),
            (child_title, Permission.DENY),
        ]
    )
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is False


def test_path_checker_explicit_path_registration(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert child_title is not None

    checker = TitlePathPermissionChecker(
        [
            (("# Parent",), Permission.READ),
            (("# Parent", "## Child"), Permission.READ_WRITE),
        ]
    )
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
    new_child_title = node.get_root_title().recursive_find_title_node_by_name(
        "## Child"
    )
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
    checker = TitlePathPermissionChecker(
        [
            (("# Parent", "## Child"), Permission.READ),
        ]
    )

    node.reload()
    new_child_title = node.get_root_title().recursive_find_title_node_by_name(
        "## Child"
    )
    assert new_child_title is not None
    ok, _ = checker.check_permission(new_child_title, Permission.READ)
    assert ok is True


def test_path_checker_deny_at_parent_overrides_child(tmp_path: Path):
    doc = tmp_path / "doc.md"
    doc.write_text("# Parent\n## Child\n\nContent.\n", encoding="utf-8")
    node = MarkdownTextFileNode(doc)
    child_title = node.get_root_title().recursive_find_title_node_by_name("## Child")
    assert child_title is not None

    checker = TitlePathPermissionChecker(
        [
            (("# Parent",), Permission.DENY),
            (("# Parent", "## Child"), Permission.READ_WRITE),
        ]
    )
    ok, _ = checker.check_permission(child_title, Permission.READ)
    assert ok is False


def test_title_path_checker_survives_rename_via_tool(tmp_path):
    """改名祖先后，受保护后代的 DENY 条目必须仍生效，不得退化成祖先的放行"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody\n\n## 1.1. Secret\nhidden\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()
    secret = root.recursive_find_title_node_by_name("## 1.1. Secret")
    checker = TitlePathPermissionChecker(
        [(secret, Permission.DENY), (root, Permission.READ_WRITE)]
    )
    assert checker.check_permission(secret, Permission.READ)[0] is False

    # A 自身继承 root 的 READ_WRITE，因此改名是允许的
    assert rename_title_tool(doc, checker, "# 1. A", "Renamed") == (
        "rename_title succeeded"
    )

    ok, msg = checker.check_permission(secret, Permission.READ)
    assert ok is False, f"后代 DENY 条目在祖先改名后失效: {msg}"


def test_title_path_checker_rename_still_checks_permission(tmp_path):
    """改名需要写权限：被 DENY 的节点不得被改名"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()
    a = root.recursive_find_title_node_by_name("# 1. A")
    checker = TitlePathPermissionChecker(
        [(a, Permission.DENY), (root, Permission.READ_WRITE)]
    )

    with pytest.raises(PermissionError):
        rename_title_tool(doc, checker, "# 1. A", "A2")

    assert doc_path.read_text(encoding="utf-8") == "# 1. A\nbody\n"


def test_title_path_checker_rebinds_on_manual_title_change(tmp_path):
    """绕过工具直接改 title 时，手动调用 on_node_renamed 也能重绑"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()
    a = root.recursive_find_title_node_by_name("# 1. A")
    checker = TitlePathPermissionChecker(
        [(a, Permission.DENY), (root, Permission.READ_WRITE)]
    )

    a.title = "Renamed"
    checker.on_node_renamed(a)

    assert checker.check_permission(a, Permission.READ)[0] is False


def test_title_path_checker_rebinds_descendant_on_manual_change(tmp_path):
    """直接改写祖先标题时，后代登记的条目也必须一并重绑"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody\n\n## 1.1. Secret\nhidden\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()
    a = root.recursive_find_title_node_by_name("# 1. A")
    secret = root.recursive_find_title_node_by_name("## 1.1. Secret")
    checker = TitlePathPermissionChecker(
        [(secret, Permission.DENY), (root, Permission.READ_WRITE)]
    )

    a.title = "Renamed"
    checker.on_node_renamed(a)

    ok, msg = checker.check_permission(secret, Permission.READ)
    assert ok is False, f"后代 DENY 条目在祖先改名后失效: {msg}"


def test_title_path_checker_entries_registered_by_path_are_unaffected(tmp_path):
    """直接传路径元组登记的条目不含节点引用，不应被 on_node_renamed 破坏"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()
    a = root.recursive_find_title_node_by_name("# 1. A")
    checker = TitlePathPermissionChecker([(("# 1. A",), Permission.DENY)])

    checker.on_node_renamed(a)

    # 路径元组登记的条目不跟踪节点，改名后仍按原路径匹配
    assert checker.check_permission(root, Permission.READ)[0] is False


def test_title_path_checker_still_survives_reload(tmp_path):
    """on_node_renamed 的引入不能破坏原有的 reload 后路径可解析能力"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    a = doc.get_root_title().recursive_find_title_node_by_name("# 1. A")
    checker = TitlePathPermissionChecker([(a, Permission.DENY)])

    doc.reload()
    a2 = doc.get_root_title().recursive_find_title_node_by_name("# 1. A")

    assert checker.check_permission(a2, Permission.READ)[0] is False


def test_node_checker_on_node_renamed_is_noop(tmp_path):
    """以身份为键的检查器无需处理改名"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# 1. A\nbody\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    a = doc.get_root_title().recursive_find_title_node_by_name("# 1. A")
    checker = NodePermissionChecker([(a, Permission.DENY)])

    a.title = "Renamed"
    checker.on_node_renamed(a)

    assert checker.check_permission(a, Permission.READ)[0] is False


def test_permission_none_cannot_be_registered_as_a_grant(tmp_path):
    """Permission.NONE 数值最高，登记为授权值等于无条件放行，必须拒绝"""
    doc = _make_node(tmp_path)
    node = doc.get_root_title()
    root = node.children[0]

    for checker_cls in (NodePermissionChecker, TitlePathPermissionChecker):
        with pytest.raises(ValueError, match="NONE"):
            checker_cls([(root, Permission.NONE)])


def test_permission_none_still_short_circuits_as_required_value(tmp_path):
    """作为 required 传入时 NONE 仍表示"跳过检查"，语义未被改动"""
    doc = _make_node(tmp_path)
    root = doc.get_root_title()
    checker = NodePermissionChecker([(root, Permission.DENY)])

    assert checker.check_permission(root, Permission.NONE) == (True, "")


def test_node_checker_scales_with_many_permissions(tmp_path):
    """条目数很大时查找仍是 O(深度)，不能退化成逐层线性扫描"""
    body = []
    for i in range(1, 40):
        body.append(f"# {i}. T{i}\n")
        for j in range(1, 40):
            body.append(f"## {i}.{j}. S\nx\n")
    doc_path = tmp_path / "big.md"
    doc_path.write_text("\n".join(body), encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()

    def walk(node):
        for child in node.children:
            if hasattr(child, "children"):
                yield child
                yield from walk(child)

    nodes = [root, *walk(root)]
    checker = NodePermissionChecker([(n, Permission.READ) for n in nodes])

    assert len(nodes) > 1500
    for n in nodes[:400]:
        assert checker.check_permission(n, Permission.READ)[0] is True


def test_node_checker_set_permissions_rebuilds_index(tmp_path):
    """set_permissions 后索引必须同步重建，否则改权限不生效"""
    doc = _make_node(tmp_path)
    root = doc.get_root_title()
    target = root.children[0]
    checker = NodePermissionChecker([(target, Permission.DENY)])
    assert checker.check_permission(target, Permission.READ)[0] is False

    checker.set_permissions([(target, Permission.READ_WRITE)])

    assert checker.check_permission(target, Permission.READ_WRITE)[0] is True


def test_node_checker_default_deny_preserved_with_index(tmp_path):
    """默认拒绝与 DENY 绝对生效的语义在改用索引后不能变"""
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("# One\nbody one\n\n# Two\nbody two\n", encoding="utf-8")
    doc = NumberedMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()
    target = root.recursive_find_title_node_by_name("# One")
    other = root.recursive_find_title_node_by_name("# Two")
    checker = NodePermissionChecker([(target, Permission.DENY)])

    # 未登记的节点向上找不到任何条目 -> DENY
    assert checker.check_permission(other, Permission.READ)[0] is False
    # DENY 绝对生效，胜过祖先的放行
    checker.set_permissions([(target, Permission.DENY), (root, Permission.READ_WRITE)])
    assert checker.check_permission(target, Permission.READ)[0] is False
