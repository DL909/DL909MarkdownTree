"""ToolContext 资源存取行为测试（覆盖历史上会 RecursionError 的路径）。"""

import pytest

from dl909agentframework.llm.tools.context import ToolContext


def test_extra_resources_via_constructor():
    ctx = ToolContext(foo=1, bar="two")
    assert ctx.get_resource("foo") == 1
    assert ctx.foo == 1
    assert ctx.bar == "two"
    assert "foo" in ctx.available_resources
    assert "bar" in ctx.available_resources


def test_add_and_get_resource():
    ctx = ToolContext()
    ctx.add_resource("x", 42)
    assert ctx.get_resource("x") == 42
    assert ctx.x == 42
    assert "x" in ctx.available_resources


def test_get_resource_default():
    ctx = ToolContext()
    assert ctx.get_resource("missing", "fallback") == "fallback"
    assert ctx.get_resource("missing") is None


def test_missing_attribute_raises_attribute_error_not_recursion():
    ctx = ToolContext()
    with pytest.raises(AttributeError):
        _ = ctx.definitely_missing


def test_markdown_file_node_available():
    sentinel = object()
    ctx = ToolContext(markdown_file_node=sentinel)  # type: ignore[arg-type]
    assert ctx.markdown_file_node is sentinel
    assert "markdown_file_node" in ctx.available_resources
