import pathlib
from typing import override

from pydantic import Field

from .file_node import FileNode
from .text_node import TextNode


class PlainTextNode(TextNode):
    # 使用私有属性和属性装饰器
    text: str = ""

    def __init__(self, text: str = ""):
        super().__init__()
        self.text = text

    @override
    def get_text(self) -> str:
        return self.text

    @override
    def set_text(self, text: str) -> None:
        self.text = text


class PlainTextFileNode(FileNode, TextNode):
    textNode: TextNode = Field(default_factory=PlainTextNode)

    @override
    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(self.textNode.get_text())

    @override
    def reload(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.textNode.set_text(f.read())

    @override
    def get_text(self):
        return self.textNode.get_text()

    @override
    def set_text(self, text):
        self.textNode.set_text(text)

    def __init__(self, file_path: pathlib.Path):
        super().__init__(file_path=file_path)
        self.file_path = file_path
        with open(file_path, "r", encoding="utf-8") as f:
            text_node = PlainTextNode(text=f.read())
        self.textNode = text_node
