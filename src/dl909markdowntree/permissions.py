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


def _iter_subtree(node: Node):
    """自底向上遍历节点自身及其全部后代"""
    yield node
    # getattr 兜底：用户自定义的 Node 子类可能没有调用 Node.__init__，
    # 此时 children 属性缺失，不应让权限检查因此崩溃
    for child in getattr(node, "children", []):
        yield from _iter_subtree(child)


class Permission(Enum):
    """权限级别枚举

    数值越大权限越高，比较时使用数值大小。
    """

    DENY = 0  # 不可读写
    READ = 1  # 可读不可写
    READ_WRITE = 2  # 可读可写
    NONE = 3  # 跳过权限检查（仅用于工具声明）


def _reject_none_grants(permissions: Sequence[tuple[object, Permission]]) -> None:
    """拒绝把 Permission.NONE 登记为授权值

    NONE 的数值（3）高于 READ_WRITE，比较又用 >=，因此一旦某节点被授予
    NONE，任何 required 都会通过——等价于无条件放行。它的本意只是"跳过
    权限检查"的工具声明标记，不该出现在授权列表里。
    """
    for _key, perm in permissions:
        if perm is Permission.NONE:
            raise ValueError(
                "Permission.NONE 只能作为工具声明的跳过标记，不能登记为授权值："
                "其数值高于 READ_WRITE，登记后等价于对该节点完全放行"
            )


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

    def on_node_renamed(self, node: Node) -> None:
        """节点标题被改写后的钩子。

        以标题路径为键的检查器需要借此重新解析键，否则条目会因路径失配而
        静默失效（见 TitlePathPermissionChecker）。以节点身份为键的实现
        无需处理。直接绕过工具改写 node.title 时也需手动调用本方法。
        """
        return

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
        self._permissions: list[tuple[Node | None, Permission]] = []
        # 查找用的索引：id(node) -> Permission。
        # 早先每一层向上都把整个列表线性扫一遍，是 O(深度 x 条目数)；大文档上
        # 逐节点校验明显变慢（实测 4721 个节点时单次检查约 0.17ms）。
        self._by_id: dict[int, Permission] = {}
        if permissions:
            self.set_permissions(permissions)

    def set_permissions(
        self, permissions: Sequence[tuple[Node | None, Permission]]
    ) -> None:
        """设置权限列表"""
        _reject_none_grants(permissions)
        self._permissions = list(permissions)
        # 以 id() 为键是安全的：_permissions 持有节点引用，节点在条目存活
        # 期间不会被回收，地址也就不会被复用。id(None) 同理代表根节点条目。
        self._by_id = {id(node): perm for node, perm in self._permissions}

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
            # 用 `is not None` 而非真值判断：Permission.DENY 的值是 0
            perm = self._by_id.get(id(current))
            if perm is not None:
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

    注意：标题是路径键的一部分，改写标题会让已登记的条目失配并静默失效
    （DENY 会退化成祖先的放行）。用节点对象登记的条目会在
    :meth:`on_node_renamed` 时自动重新解析；直接传路径元组登记的条目
    没有节点可供跟踪，改名后需调用 set_permissions 重新登记。
    """

    def __init__(
        self,
        permissions: Sequence[tuple[tuple[str, ...] | Node | None, Permission]]
        | None = None,
    ):
        # 每项为 (标题路径键, 权限, 登记时的节点引用或 None)
        self._permissions: list[
            tuple[tuple[str, ...] | None, Permission, Node | None]
        ] = []
        if permissions:
            self.set_permissions(permissions)

    def set_permissions(
        self, permissions: Sequence[tuple[tuple[str, ...] | Node | None, Permission]]
    ) -> None:
        """设置权限列表（节点对象立即解析为标题路径）"""
        _reject_none_grants(permissions)
        self._permissions = [
            (self._resolve_key(entry), perm, entry if isinstance(entry, Node) else None)
            for entry, perm in permissions
        ]

    def on_node_renamed(self, node: Node) -> None:
        """标题改写后重新解析以该节点及其后代登记的条目，避免条目静默失配

        改名会同时改变整棵子树的标题路径，因此只重绑节点本身不够：
        受保护的后代会以旧祖先标题为键，失配后回落到祖先的放行。
        """
        affected = {id(n) for n in _iter_subtree(node)}
        for index, (_path, perm, origin_node) in enumerate(self._permissions):
            if origin_node is not None and id(origin_node) in affected:
                self._permissions[index] = (
                    self._node_to_path(origin_node),
                    perm,
                    origin_node,
                )

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
            for perm_path, perm, _origin in self._permissions:
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
