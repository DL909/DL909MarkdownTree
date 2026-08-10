import pathlib
from abc import ABC, abstractmethod
from .node import Node


class FileNode(Node, ABC):
    """
    一个文件节点对应文件系统中的一个文件或文件夹，并可以将自身数据保存到该文件/文件夹或从对应的文件/文件夹重新加载数据。
    """

    file_path: pathlib.Path

    @abstractmethod
    def save(self, **kwargs):
        pass

    @abstractmethod
    def reload(self, **kwargs):
        pass
