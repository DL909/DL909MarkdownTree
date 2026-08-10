from abc import ABC, abstractmethod
from typing import override

from .node import Node


class TextNode(Node, ABC):
    """
    一个文本节点是可以被转化为字符串和设置其存储的字符串的节点。
    """

    @abstractmethod
    def get_text(self) -> str:
        pass

    @abstractmethod
    def set_text(self, text) -> None:
        pass

    @override
    def __str__(self) -> str:
        return self.get_text()
