#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
registry.py - 工具注册表和装饰器

提供 @tool 装饰器和 ToolRegistry 类，支持从函数签名自动生成 JSON schema。
"""

from __future__ import annotations

import inspect
import logging
from functools import wraps
from typing import (
    Any,
    Callable,
    Self,
    Sequence,
    get_args,
    get_origin,
    overload,
)

from pydantic import BaseModel

from dl909agentframework.tree_doc.node import Node
from dl909agentframework.tree_doc.markdown_nodes import MarkdownTitleNode

from dl909agentframework.llm.tools.permissions import Permission

from dl909agentframework.llm.tools.context import ToolContext

logger = logging.getLogger(__name__)

type ToolCheck = Callable[[ToolRegistry, ToolContext], str | None]


class FatalToolException(Exception):
    pass


class Tool:
    """表示一个可被 LLM 调用的工具"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        func: Callable,
        param_model: type[BaseModel] | None = None,
        must_use_time: int = 0,
        end_after_use: bool = False,
    ):
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.func = func
        self.param_model = param_model
        self.must_use_time = must_use_time
        self.use_time = 0
        self.end_after_use = end_after_use

    def to_openai_tool(self) -> dict[str, Any]:
        """转换为 OpenAI API 所需的工具定义格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def execute(
        self, context: Any, arguments: dict[str, Any]
    ) -> tuple[str, bool, bool]:
        """执行工具函数

        Args:
            context: 工具执行上下文
            arguments: LLM 传入的参数

        Returns:
            (执行结果字符串，是否成功，应当终止 llm 工具调用循环)
        """
        try:
            kwargs = {}

            if self.param_model:
                validated_args = self.param_model(**arguments)
                kwargs["arguments"] = validated_args
            else:
                kwargs["arguments"] = arguments

            sig = inspect.signature(self.func)
            for param_name, _ in sig.parameters.items():
                if param_name == "arguments":
                    continue
                if param_name in context.available_resources:
                    kwargs[param_name] = getattr(context, param_name)

            result = self.func(**kwargs)

            self.use_time += 1

            if not isinstance(result, str):
                result = str(result)

            return result, True, self.end_after_use

        except FatalToolException as e:
            raise e

        except Exception as e:
            logger.warning("Tool '%s' execution failed: %s", self.name, e)
            return f"工具 '{self.name}' 执行失败：{e}", False, False


class PermissionTool(Tool):
    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        func: Callable,
        param_model: type[BaseModel] | None = None,
        must_use_time: int = 0,
        end_after_use: bool = False,
        permission: Permission = Permission.NONE,
    ):
        super.__init__(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            func=func,
            param_model=param_model,
            must_use_time=must_use_time,
            end_after_use=end_after_use,
        )
        self.permission = permission


class ToolRegistry:
    """工具注册表，管理所有可用工具"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, *tools: Tool) -> Self:
        """注册一个工具"""
        for tool in tools:
            if tool.name in self._tools:
                logger.warning("Tool '%s' already registered, overriding", tool.name)
            self._tools[tool.name] = tool
            logger.debug("Tool '%s' registered", tool.name)
        return self

    def get(self, name: str) -> Tool | None:
        """获取指定名称的工具"""
        return self._tools.get(name)

    def get_all(self) -> list[Tool]:
        """获取所有注册的工具"""
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """转换为 OpenAI API 所需的工具列表格式"""
        return [tool.to_openai_tool() for tool in self._tools.values()]

    def reset(self) -> None:
        for tool in self._tools.values():
            tool.use_time = 0

    def execute(
        self, name: str, context: Any, arguments: dict[str, Any]
    ) -> tuple[str, bool, bool]:
        """执行指定名称的工具

        Returns:
            (执行结果字符串，是否成功，应当终止 llm 工具调用循环)
        """
        tool = self.get(name)
        if tool is None:
            return f"工具调用失败：没有名为 '{name}' 的工具", False, False

        return tool.execute(context, arguments)

    def merge(self, *registries: ToolRegistry) -> Self:
        """合并多个注册表，返回新注册表"""
        new_registry = Self()
        for tool in self._tools.values():
            new_registry.register(tool)
        for registry in registries:
            for tool in registry._tools.values():
                new_registry.register(tool)
        return new_registry


def default_must_use_check(registry: ToolRegistry, _context: ToolContext) -> str | None:
    """默认 must_use 检查函数：检查所有 Tool 的 must_use_time 是否达标"""
    still_need_use: list[tuple[str, int]] = []
    for tool in registry._tools.values():
        left = tool.must_use_time - tool.use_time
        if left > 0:
            still_need_use.append((tool.name, left))
    if still_need_use:
        details = "\n".join(
            f"{name}: 需要再使用 {count} 次" for name, count in still_need_use
        )
        return f"仍有一些需要的工具调用没有完成，需要调用的工具和剩余的需要调用次数如下：\n{details}"
    return None


class PermissionToolRegistry(ToolRegistry):
    """
    扩展的 ToolRegistry，专门用于带权限控制的工具

    与普通 ToolRegistry 的区别：
    - 强制要求设置权限列表
    - 提供更细粒度的权限管理方法
    - 执行工具前会自动检查权限
    """

    def __init__(
        self,
        permissions: Sequence[tuple[Node | None, Permission]] | None = None,
    ):
        super().__init__()
        from dl909agentframework.llm.tools.permissions import PermissionChecker

        self._permission_checker: PermissionChecker | None = None
        if permissions:
            self.set_permissions(permissions)

    def set_permissions(
        self, permissions: Sequence[tuple[Node | None, Permission]]
    ) -> None:
        """设置权限列表"""
        from dl909agentframework.llm.tools.permissions import PermissionChecker

        if self._permission_checker is None:
            self._permission_checker = PermissionChecker(permissions)
        else:
            self._permission_checker.set_permissions(permissions)

    def execute(
        self, name: str, context: Any, arguments: dict[str, Any]
    ) -> tuple[str, bool, bool]:
        """执行指定名称的工具，执行前检查权限

        Returns:
            (执行结果字符串，是否成功，应当终止 llm 工具调用循环)
        """
        from dl909agentframework.llm.tools.permissions import Permission

        tool = self.get(name)
        if tool is None:
            return f"工具调用失败：没有名为 '{name}' 的工具", False, False

        if isinstance(tool, PermissionTool) and tool.permission != Permission.NONE:
            target_node = self._extract_target_node(arguments, context)
            if self._permission_checker:
                success, error_msg = self._permission_checker.check_permission(
                    target_node, tool.permission
                )
                if not success:
                    return error_msg, False, False

        return tool.execute(context, arguments)

    def _extract_target_node(
        self, arguments: dict[str, Any], context: Any
    ) -> MarkdownTitleNode | None:
        """从参数中提取目标节点（用于权限检查）"""
        if arguments and "target" in arguments:
            target_name = arguments["target"]
            markdown_file_node = getattr(context, "markdown_file_node", None)
            if markdown_file_node:
                return markdown_file_node.recursive_find_title_node_by_name(target_name)
        return None

    def add_permission(self, node: Node | None, permission: Permission) -> None:
        """添加单个节点的权限"""
        from dl909agentframework.llm.tools.permissions import PermissionChecker

        if self._permission_checker is None:
            self._permission_checker = PermissionChecker([])

        current = self._permission_checker._permissions
        for i, (perm_node, _) in enumerate(current):
            if perm_node is node:
                current[i] = (node, permission)
                return
        current.append((node, permission))
        self._permission_checker.set_permissions(current)

    def remove_permission(self, node: Node | None) -> None:
        """移除指定节点的权限（恢复继承）"""
        if self._permission_checker is None:
            return

        self._permission_checker._permissions = [
            (n, p) for n, p in self._permission_checker._permissions if n is not node
        ]


def _python_type_to_json_schema(
    type_hint: Any, _visited: set[type[BaseModel]] | None = None
) -> dict[str, Any]:
    """将 Python 类型注解转换为 JSON schema

    支持：
    - 基础类型：str, int, float, bool
    - 容器类型：list[T], dict[K, V]
    - 可选类型：T | None
    - Pydantic BaseModel
    """
    if _visited is None:
        _visited = set()

    if type_hint is None:
        return {"type": "null"}

    if type_hint is str:
        return {"type": "string"}
    elif type_hint is int:
        return {"type": "integer"}
    elif type_hint is float:
        return {"type": "number"}
    elif type_hint is bool:
        return {"type": "boolean"}
    elif type_hint is dict:
        return {"type": "object"}
    elif type_hint is list:
        return {"type": "array"}

    origin = get_origin(type_hint)
    args = get_args(type_hint)

    if origin is list:
        if args:
            item_schema = _python_type_to_json_schema(args[0], _visited)
            return {"type": "array", "items": item_schema}
        return {"type": "array"}

    elif origin is dict:
        if len(args) >= 2:
            value_schema = _python_type_to_json_schema(args[1], _visited)
            return {"type": "object", "additionalProperties": value_schema}
        return {"type": "object"}

    elif origin is type(None):
        return {"type": "null"}

    import types

    if origin is types.UnionType or str(origin) == "~typing.Union":
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _python_type_to_json_schema(non_none_args[0], _visited)
        elif len(non_none_args) > 1:
            types_schemas = [
                _python_type_to_json_schema(arg, _visited) for arg in non_none_args
            ]
            return {"oneOf": types_schemas}
        return {"type": "null"}

    elif isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
        if type_hint in _visited:
            return {
                "type": "object",
                "description": f"(循环引用：{type_hint.__name__})",
            }
        _visited.add(type_hint)
        return _model_to_parameters_schema(type_hint, _visited)

    return {"type": "string"}


def _model_to_parameters_schema(
    model: type[BaseModel], _visited: set[type[BaseModel]] | None = None
) -> dict[str, Any]:
    """从 Pydantic 模型生成 JSON schema"""

    properties = {}
    required = []

    for field_name, field_info in model.model_fields.items():
        field_type = field_info.annotation
        properties[field_name] = _python_type_to_json_schema(field_type, _visited)

        if field_info.is_required():
            required.append(field_name)

        if field_info.description:
            properties[field_name]["description"] = field_info.description

    result = {
        "type": "object",
        "properties": properties,
    }

    if required:
        result["required"] = required

    return result


def _extract_description(func: Callable) -> str:
    """从函数 docstring 提取描述"""
    docstring = inspect.getdoc(func)
    if not docstring:
        return ""

    first_line = docstring.split("\n")[0].strip()
    if first_line.endswith('"""') or first_line.endswith("'''"):
        first_line = first_line[:-3].strip()
    if first_line.startswith('"""') or first_line.startswith("'''"):
        first_line = first_line[3:].strip()

    return first_line


@overload
def tool(
    func: Callable,
    *,
    name: str | None = None,
    description: str | None = None,
    param_model: type[BaseModel] | None = None,
    must_use_time: int = 0,
    end_after_use: bool = False,
    required_permission: Permission = Permission.NONE,
) -> Tool: ...


@overload
def tool(
    *,
    name: str | None = None,
    description: str | None = None,
    param_model: type[BaseModel] | None = None,
    must_use_time: int = 0,
    end_after_use: bool = False,
    required_permission: Permission = Permission.NONE,
) -> Callable[[Callable], Tool]: ...


def tool(
    func: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    param_model: type[BaseModel] | None = None,
    must_use_time: int = 0,
    end_after_use: bool = False,
    required_permission: Permission = Permission.NONE,
) -> Tool | Callable[[Callable], Tool]:
    """装饰器：将函数注册为工具

    Args:
        func: 被装饰的函数（当不使用括号时）
        name: 工具名称，默认使用函数名
        description: 工具描述，默认从 docstring 第一行提取
        param_model: Pydantic 模型用于参数验证，默认从函数签名推断
        required_permission: 工具所需的权限级别（仅用于 PermissionToolRegistry）

    用法:
        @tool
        def my_tool(arguments: dict) -> str:
            '''工具描述'''
            return "结果"

        @tool(name="custom_name", description="自定义描述")
        def my_tool(arguments: MyParams) -> str:
            return "结果"
    """

    def _create_tool(f: Callable) -> Tool:
        tool_name = name or f.__name__
        tool_description = description or _extract_description(f)

        if param_model:
            params_schema = _model_to_parameters_schema(param_model, set())
            actual_param_model = param_model
        else:
            sig = inspect.signature(f)
            params_schema = {"type": "object", "properties": {}, "required": []}
            actual_param_model = None

            for param_name, param in sig.parameters.items():
                if param_name == "arguments":
                    if param.annotation is not inspect.Parameter.empty:
                        if isinstance(param.annotation, type) and issubclass(
                            param.annotation, BaseModel
                        ):
                            params_schema = _model_to_parameters_schema(
                                param.annotation, set()
                            )
                            actual_param_model = param.annotation
                    continue

                if param.annotation is not inspect.Parameter.empty:
                    params_schema["properties"][param_name] = (
                        _python_type_to_json_schema(param.annotation, set())
                    )
                    if param.default is inspect.Parameter.empty:
                        params_schema.setdefault("required", []).append(param_name)

        tool_instance = Tool(
            name=tool_name,
            description=tool_description,
            parameters_schema=params_schema,
            func=f,
            param_model=actual_param_model,
            must_use_time=must_use_time,
            end_after_use=end_after_use,
        )

        if required_permission is not None:
            tool_instance.required_permission = required_permission

        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        wrapper._tool = tool_instance
        return tool_instance

    if func is None:
        return _create_tool
    else:
        return _create_tool(func)
