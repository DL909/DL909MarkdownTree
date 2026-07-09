from __future__ import annotations
from abc import ABC
from typing import Self
from pydantic import BaseModel, Field


class MyMeta(type(BaseModel), type(ABC)):
    pass


# 确保 Node 使用正确的元类
class Node(BaseModel, metaclass=MyMeta):
    parent: Node | None = None
    children: list[Node] = Field(default_factory=list)
    deprecated: bool = False  # 使用较消极的更新策略。一个节点被注销时，只需要将deprecated属性设为真，之后父节点更新时将移除该节点。

    def update(self) -> Self:
        for i, child in enumerate(self.children):
            child.update()
            if child.deprecated:
                del self.children[i]
        return self

    def addchild(self, child: Node):  # 只能加入孤儿节点
        assert child.parent is None
        self.children.append(child)
        child.parent = self

    def dispatch(self):  # 脱离父节点变为孤儿节点
        if self.parent is not None:
            for i, child in enumerate(self.parent.children):
                if child is self:
                    del self.parent.children[i]
                    break
            self.parent = None
