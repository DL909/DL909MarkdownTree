"""
permissions.py - 权限管理核心

提供基于树形结构继承的细粒度权限控制。

PermissionChecker 为抽象基类，具体实现有两种策略：
- NodePermissionChecker：以节点对象身份（is 比较）为键，直接追踪节点。
  注意：调用 reload() 会重建节点树，旧节点对象被替换，已有权限条目随之失效。
- TitlePathPermissionChecker：以标题路径（从根标题到节点的标题元组）为键，
  基于节点间关系定位，reload() 后权限条目仍然有效。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import Enum

from .interface import MarkdownTitleBase
from .node import Node


class Permission(Enum):
    """权限级别枚举

    数值越大权限越高，比较时使用数值大小。
    """

    DENY = 0  # 不可读写
    READ = 1  # 可读不可写
    READ_WRITE = 2  # 可读可写
    NONE = 3  # 跳过权限检查（仅用于工具声明）


class PermissionChecker[T](ABC):
    """权限检查器抽象基类

    子类负责以各自的方式登记权限条目并查找节点的有效权限。
    """

    @abstractmethod
    def set_permissions(self, permissions: Sequence[tuple[T, Permission]]) -> None:
        """设置权限列表"""
        ...

    @abstractmethod
    def _find_effective_permission(self, node: Node | None) -> Permission:
        """查找节点的有效权限（向上遍历继承）"""
        ...

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
                (
                    f"权限不足：节点{node_desc}需要{required.name}权限，"
                    f"但当前对该节点的权限为{effective.name}"
                ),
            )

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


class NodePermissionChecker(PermissionChecker[Node | None]):
    """基于节点身份的权限检查器

    权限条目以节点对象身份（is 比较）为键，直接追踪节点。
    调用 reload() 会重建节点树，旧节点对象被替换，已有权限条目随之失效，
    需要重新登记权限条目。
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

    def _find_effective_permission(self, node: Node | None) -> Permission:
        """
        查找节点的有效权限（向上遍历继承）

        规则：
        - 权限列表为空 → 返回 READ_WRITE（默认允许）
        - 权限列表非空 → 从节点向上遍历；遇到 DENY 立即返回 DENY（绝对生效），
          否则取最近的有效权限
        - 如果到根节点仍未找到 → 返回 DENY（默认拒绝）
        """
        if not self._permissions:
            return Permission.READ_WRITE

        nearest: Permission | None = None
        current: Node | None = node
        while True:
            for perm_node, perm in self._permissions:
                if perm_node is current:
                    if perm is Permission.DENY:
                        return Permission.DENY
                    if nearest is None:
                        nearest = perm
            if current is None:
                break
            current = getattr(current, "parent", None)

        if nearest is not None:
            return nearest
        return Permission.DENY


class TitlePathPermissionChecker(PermissionChecker[tuple[str, ...] | None]):
    """基于标题路径关系的权限检查器

    权限条目以标题路径为键：从根标题到节点的完整标题元组
    （每个元素为带级别符号的完整标题，如 ("# Parent", "## Child")）。
    reload() 重建节点树后路径仍然可解析，权限条目不失效。

    登记方式二选一：
    - 传入节点对象（含 None 表示根节点），登记时立即解析为标题路径
    - 直接传入标题路径元组（() 或 None 表示根节点），可在节点尚不存在时配置
    """

    def __init__(
        self,
        permissions: Sequence[tuple[tuple[str, ...] | Node | None, Permission]]
        | None = None,
    ):
        self._permissions: list[tuple[tuple[str, ...] | None, Permission]] = []
        if permissions:
            self.set_permissions(permissions)

    def set_permissions(
        self, permissions: Sequence[tuple[tuple[str, ...] | Node | None, Permission]]
    ) -> None:
        """设置权限列表（节点对象立即解析为标题路径）"""
        self._permissions = [
            (self._resolve_key(entry), perm) for entry, perm in permissions
        ]

    def _resolve_key(
        self, entry: tuple[str, ...] | Node | None
    ) -> tuple[str, ...] | None:
        """将登记条目解析为标题路径键（根统一表示为 None）"""
        if isinstance(entry, Node):
            return self._node_to_path(entry)
        if not entry:
            return None
        return entry

    def _find_effective_permission(self, node: Node | None) -> Permission:
        """
        查找节点的有效权限（沿标题路径前缀向上匹配继承）

        规则：
        - 权限列表为空 → 返回 READ_WRITE（默认允许）
        - 权限列表非空 → 依次匹配节点路径、逐级去尾的祖先路径直至根；
          遇到 DENY 立即返回 DENY（绝对生效），否则取最近的匹配
        - 如果到根仍未匹配 → 返回 DENY（默认拒绝）
        """
        if not self._permissions:
            return Permission.READ_WRITE

        path = self._node_to_path(node)
        nearest: Permission | None = None
        current_path: tuple[str, ...] | None = path
        while True:
            for perm_path, perm in self._permissions:
                if perm_path == current_path:
                    if perm is Permission.DENY:
                        return Permission.DENY
                    if nearest is None:
                        nearest = perm
            if current_path is None:
                break
            current_path = current_path[:-1] or None

        if nearest is not None:
            return nearest
        return Permission.DENY

    @staticmethod
    def _node_to_path(node: Node | None) -> tuple[str, ...] | None:
        """
        将节点解析为标题路径：沿 parent 链向上收集各层标题，跳过 level 为 0 的
        根标题占位节点，遇到无 title 属性的节点（文件节点）停止。
        传入 None、根标题节点或非标题节点 → 返回 None（表示根节点）。
        """
        if node is None:
            return None
        titles: list[str] = []
        current: Node | None = node
        while current is not None:
            if not isinstance(current, MarkdownTitleBase):
                break
            if current.level != 0:
                titles.append(current.get_title())
            current = getattr(current, "parent", None)
        if not titles:
            return None
        titles.reverse()
        return tuple(titles)
