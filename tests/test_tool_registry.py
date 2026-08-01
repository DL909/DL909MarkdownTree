"""ToolRegistry / @tool / merge / must_use 检查测试。"""

from dl909agentframework.llm.tools.registry import (
    PermissionTool,
    Tool,
    ToolRegistry,
    default_must_use_check,
    tool,
)
from dl909agentframework.llm.tools.context import ToolContext
from dl909agentframework.llm.tools.permissions import Permission


def test_tool_decorator_builds_schema_from_signature():
    @tool
    def sample(arguments: dict, count: int, flag: bool = False) -> str:
        """示例工具"""
        return "ok"

    assert isinstance(sample, Tool)
    assert sample.name == "sample"
    assert sample.description == "示例工具"
    props = sample.parameters_schema["properties"]
    assert props["count"] == {"type": "integer"}
    assert props["flag"] == {"type": "boolean"}
    # count 无默认值 -> required；flag 有默认值 -> 非 required
    assert "count" in sample.parameters_schema["required"]
    assert "flag" not in sample.parameters_schema.get("required", [])


def test_tool_without_permission_is_plain_tool():
    @tool
    def t(arguments: dict) -> str:
        """d"""
        return "ok"

    assert isinstance(t, Tool)
    assert not isinstance(t, PermissionTool)


def test_tool_with_permission_is_permission_tool():
    @tool(required_permission=Permission.READ_WRITE)
    def t(arguments: dict) -> str:
        """d"""
        return "ok"

    assert isinstance(t, PermissionTool)
    assert t.permission == Permission.READ_WRITE


def test_register_and_execute():
    @tool
    def echo(arguments: dict) -> str:
        """echo"""
        return "hi"

    reg = ToolRegistry().register(echo)
    result, success, end = reg.execute("echo", ToolContext(), {})
    assert success and result == "hi" and end is False


def test_execute_unknown_tool():
    reg = ToolRegistry()
    result, success, _ = reg.execute("nope", ToolContext(), {})
    assert success is False and "nope" in result


def test_merge_returns_new_registry_with_all_tools():
    @tool
    def a(arguments: dict) -> str:
        """a"""
        return "a"

    @tool
    def b(arguments: dict) -> str:
        """b"""
        return "b"

    r1 = ToolRegistry().register(a)
    r2 = ToolRegistry().register(b)
    merged = r1.merge(r2)

    assert isinstance(merged, ToolRegistry)
    assert merged is not r1 and merged is not r2
    names = {t.name for t in merged.get_all()}
    assert names == {"a", "b"}
    # 原注册表不受影响
    assert {t.name for t in r1.get_all()} == {"a"}


def test_default_must_use_check():
    @tool(must_use_time=1)
    def needed(arguments: dict) -> str:
        """needed"""
        return "x"

    reg = ToolRegistry().register(needed)
    # 尚未调用 -> 应提示还需调用
    msg = default_must_use_check(reg, ToolContext())
    assert msg is not None and "needed" in msg

    reg.execute("needed", ToolContext(), {})
    # 调用一次后达标 -> None
    assert default_must_use_check(reg, ToolContext()) is None
