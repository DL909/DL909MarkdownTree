#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
permissions.py - 权限管理核心

提供基于树形结构继承的细粒度权限控制。
"""

from __future__ import annotations

from enum import Enum
from typing import Sequence

from dl909agentframework.tree_doc.node import Node


class Permission(Enum):
    """权限级别枚举

    数值越大权限越高，比较时使用数值大小。
    """

    DENY = 0  # 不可读写
    READ = 1  # 可读不可写
    READ_WRITE = 2  # 可读可写
    NONE = 3  # 跳过权限检查（仅用于工具声明）


class PermissionChecker:
    """权限检查器

    负责根据权限列表和继承规则检查节点权限。
    """

    def __init__(
        self, permissions: Sequence[tuple[Node | None, Permission]] | None = None
    ):
        """
        Args:
            permissions: 权限列表 [(node, permission), ...]
                        node 为 MarkdownTitleNode 对象或 None（表示根节点）
        """
        self._permissions: list[tuple[Node | None, Permission]] = (
            list(permissions) if permissions else []
        )

    def set_permissions(
        self, permissions: Sequence[tuple[Node | None, Permission]]
    ) -> None:
        """设置权限列表"""
        self._permissions = list(permissions)

    def check_permission(
        self,
        node: Node | None,
        required: Permission,
    ) -> tuple[bool, str]:
        """
        检查节点是否具有所需权限

        Args:
            node: 要检查的节点（MarkdownTitleNode 或 None 表示根节点）
            required: 工具所需的权限级别

        Returns:
            (是否通过，错误消息)
        """
        if required == Permission.NONE:
            return True, ""

        effective = self._find_effective_permission(node)

        if effective.value >= required.value:
            return True, ""
        else:
            node_desc = self._get_node_description(node)
            return (
                False,
                f"权限不足：节点{node_desc}需要{required.name}权限，"
                f"但当前对该节点的权限为{effective.name}",
            )

    def _find_effective_permission(self, node: Node | None) -> Permission:
        """
        查找节点的有效权限（向上遍历继承）

        规则：
        - 权限列表为空 → 返回 READ_WRITE（默认允许）
        - 权限列表非空 → 从节点向上遍历，找到最近的有效权限
        - 如果到根节点仍未找到 → 返回 DENY（默认拒绝）
        """
        if not self._permissions:
            return Permission.READ_WRITE

        current = node
        while current is not None:
            for perm_node, perm in self._permissions:
                if perm_node is current:
                    return perm
            current = getattr(current, "parent", None)

        return Permission.DENY

    def _get_node_description(self, node: Node | None) -> str:
        """获取节点的描述字符串（用于错误消息）"""
        if node is None:
            return "根节点"
        # title / name 是具体子类才有的字段，Node 基类未声明，用 getattr 探测。
        title = getattr(node, "title", None)
        if title is not None:
            return f"'{title}'"
        name = getattr(node, "name", None)
        if name is not None:
            return f"'{name}'"
        return f"<{type(node).__name__}>"
