from __future__ import annotations

import copy
from abc import ABC
from typing import Self

from .exceptions import InvalidNodeOperationError


# 确保 Node 使用正确的元类
class Node(ABC):
    parent: Node | None = None
    children: list[Node]
    deprecated: bool = False  # 使用较消极的更新策略。一个节点被注销时，只需要将deprecated属性设为真，之后父节点更新时将移除该节点。

    def __init__(self) -> None:
        super().__init__()
        self.children = []

    @classmethod
    def from_self(cls, origin: Self, **overrides: object) -> Self:
        """从自身实例重建一个复制版本，overrides 中的键值覆盖相应属性

        注意：children 列表是新建的，但其中的子节点对象与 origin 共享，因此
        副本接管这些子节点（parent 改指副本）。origin 之后再操作这些子节点
        （例如 dispatch()）会影响副本。若需要与 origin 完全无关的空壳，
        传 ``children=[]``——解析路径正是这么用的。

        早先没有重挂 parent，副本里的子节点仍指向 origin，于是副本是一棵
        "反向"的树：对副本的孩子调用 dispatch() 会把 origin 的孩子摘掉。
        """
        result = copy.copy(origin)
        result.children = list(origin.children)
        result.parent = None
        for key, value in overrides.items():
            setattr(result, key, value)
        # 重挂必须放在 overrides 之后：overrides 可能整体替换了 children
        # （解析路径传的就是 children=[]），此时不该再去动 origin 的孩子。
        for child in result.children:
            child.parent = result
        return result

    def update(self) -> Self:
        for child in self.children:
            child.update()
        # 反向遍历删除，避免在正向遍历中删除元素导致跳过后一个节点
        for i in range(len(self.children) - 1, -1, -1):
            if self.children[i].deprecated:
                child = self.children[i]
                child.parent = None
                del self.children[i]
        return self

    def addchild(self, child: Node) -> None:  # 只能加入孤儿节点
        if child.parent is not None:
            raise InvalidNodeOperationError("child already has a parent")
        self.children.append(child)
        child.parent = self

    def dispatch(self) -> None:  # 脱离父节点变为孤儿节点
        if self.parent is not None:
            for i, child in enumerate(self.parent.children):
                if child is self:
                    del self.parent.children[i]
                    break
            self.parent = None
