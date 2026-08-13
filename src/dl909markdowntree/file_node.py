from abc import ABC, abstractmethod
from pathlib import Path

from .node import Node


class FileNode(Node, ABC):
    """
    一个文件节点对应文件系统中的一个文件或文件夹，并可以将自身数据保存到该文件/文件夹或从对应的文件/文件夹重新加载数据。
    """

    file_path: Path

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def reload(self):
        pass

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        super().__init__()
