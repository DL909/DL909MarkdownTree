from abc import ABC, abstractmethod
from typing import override

from .node import Node


class TextNode(Node, ABC):
    @abstractmethod
    def get_text(self, **kwargs) -> str:
        pass

    @abstractmethod
    def set_text(self, text, **kwargs) -> None:
        pass

    @override
    def __str__(self) -> str:
        return self.get_text()
