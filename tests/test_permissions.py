"""权限系统测试：PermissionChecker 继承规则 + PermissionToolRegistry 实际强制。"""

from dl909agentframework.llm.tools.context import ToolContext
from dl909agentframework.llm.tools.permissions import Permission, PermissionChecker
from dl909agentframework.llm.tools.registry import (
    PermissionTool,
    PermissionToolRegistry,
)


class FakeNode:
    """最小节点：仅提供权限检查所需的 title / parent。"""

    def __init__(self, title: str, parent=None):
        self.title = title
        self.parent = parent


class FakeFileNode:
    def __init__(self, nodes_by_name):
        self._nodes = nodes_by_name

    def recursive_find_title_node_by_name(self, name):
        return self._nodes.get(name)


# ---- PermissionChecker 单元 ----


def test_empty_permissions_defaults_to_read_write():
    checker = PermissionChecker([])
    ok, _ = checker.check_permission(FakeNode("n"), Permission.READ_WRITE)
    assert ok


def test_unlisted_node_defaults_to_deny_when_list_nonempty():
    root = FakeNode("root")
    other = FakeNode("other")
    checker = PermissionChecker([(root, Permission.READ_WRITE)])
    ok, msg = checker.check_permission(other, Permission.READ)
    assert not ok and msg


def test_permission_inherits_from_ancestor():
    root = FakeNode("root")
    child = FakeNode("child", parent=root)
    checker = PermissionChecker([(root, Permission.READ)])
    # 继承到 READ：READ 请求通过，READ_WRITE 请求被拒
    assert checker.check_permission(child, Permission.READ)[0]
    assert not checker.check_permission(child, Permission.READ_WRITE)[0]


# ---- PermissionToolRegistry 集成 ----


def _make_edit_tool(permission: Permission) -> PermissionTool:
    return PermissionTool(
        name="edit",
        description="demo edit tool",
        parameters_schema={},
        func=lambda **kwargs: "edited",
        permission=permission,
    )


def _context():
    root = FakeNode("root")
    child = FakeNode("child", parent=root)
    fnode = FakeFileNode({"root": root, "child": child})
    return root, child, ToolContext(markdown_file_node=fnode)


def test_registry_denies_write_on_read_only_node():
    root, _child, ctx = _context()
    reg = PermissionToolRegistry(permissions=[(root, Permission.READ)])
    reg.register(_make_edit_tool(Permission.READ_WRITE))

    result, success, _ = reg.execute("edit", ctx, {"target": "child"})
    assert success is False
    assert "权限不足" in result


def test_registry_allows_write_when_permitted():
    root, _child, ctx = _context()
    reg = PermissionToolRegistry(permissions=[(root, Permission.READ_WRITE)])
    reg.register(_make_edit_tool(Permission.READ_WRITE))

    result, success, _ = reg.execute("edit", ctx, {"target": "child"})
    assert success is True and result == "edited"


def test_none_permission_tool_skips_check():
    _root, _child, ctx = _context()
    # 权限列表非空且不含目标 -> 若被检查会 DENY；但工具声明 NONE 应跳过检查
    reg = PermissionToolRegistry(permissions=[(FakeNode("x"), Permission.DENY)])
    reg.register(_make_edit_tool(Permission.NONE))
    result, success, _ = reg.execute("edit", ctx, {"target": "child"})
    assert success is True and result == "edited"
