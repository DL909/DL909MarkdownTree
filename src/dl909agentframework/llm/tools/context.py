#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
context.py - 工具执行上下文

提供 ToolContext 类，封装工具执行所需的各种资源。
"""

from typing import Any

from dl909agentframework.tree_doc.protocols import AttributedMarkdownTextFileProtocol


class ToolContext:
    """工具执行上下文，提供工具函数可访问的资源

    Attributes:
        markdown_file_node: Markdown 文件节点（可选）
        extra_resources: 额外资源字典
    """

    def __init__(
        self,
        markdown_file_node: AttributedMarkdownTextFileProtocol | None = None,
        **extra_resources: Any,
    ):
        self.markdown_file_node = markdown_file_node
        self.resources: dict[str, Any] = dict(extra_resources)

        self._available_resource_names: list[str] = []
        if markdown_file_node is not None:
            self._available_resource_names.append("markdown_file_node")
        self._available_resource_names.extend(extra_resources.keys())

    @property
    def available_resources(self) -> list[str]:
        """获取所有可用资源名称列表"""
        return self._available_resource_names

    def __getattr__(self, name: str) -> Any:
        # __getattr__ 仅在常规属性查找失败时被调用。直接读 self.__dict__ 取
        # resources，避免访问 self.resources 时（若尚未初始化）再次触发 __getattr__
        # 造成无限递归。
        resources = self.__dict__.get("resources", {})
        if name in resources:
            return resources[name]
        raise AttributeError(f"Resource '{name}' not available in context")

    def add_resource(self, name: str, value: Any) -> None:
        """添加资源到上下文"""
        self.resources[name] = value
        if name not in self._available_resource_names:
            self._available_resource_names.append(name)

    def get_resource(self, name: str, default: Any = None) -> Any:
        """获取资源，如果不存在则返回默认值"""
        return self.resources.get(name, default)
