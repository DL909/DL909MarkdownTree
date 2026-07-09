import pathlib
from abc import ABC, abstractmethod
from .node import Node


class FileNode(Node, ABC):
    file_path: pathlib.Path

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def reload(self):
        pass
