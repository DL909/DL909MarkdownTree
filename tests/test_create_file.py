"""test_create_file.py - 测试 create_file 静态方法与 __init__ 自动创建行为"""

from pathlib import Path

from pydantic import BaseModel

from dl909markdowntree import (
    MarkdownTextFileNode,
    NumberedMarkdownTextFileNode,
    FoldableMarkdownTextFileNode,
    AttributedMarkdownTextFileNode,
    NumberedMarkdownFolderNode,
    FoldableMarkdownFolderNode,
    AttributedMarkdownFolderNode,
)


class _SimpleAttr(BaseModel):
    author: str = "default"
    version: str = "1.0.0"


# ─── MarkdownTextFileNode ───────────────────────────────────────────


def test_markdown_text_file_node_create_file(fs):
    path = Path("/tmp/new_doc.md")
    MarkdownTextFileNode.create_file(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_markdown_text_file_node_init_creates_if_missing(fs):
    path = Path("/tmp/auto_created.md")
    assert not path.exists()
    node = MarkdownTextFileNode(file_path=path)
    assert path.exists()
    assert node.get_text() == ""


def test_markdown_text_file_node_init_reads_existing(fs):
    fs.create_file("/tmp/existing.md", contents="# Hello\nContent")
    node = MarkdownTextFileNode(file_path=Path("/tmp/existing.md"))
    assert "# Hello" in node.get_text()
    assert "Content" in node.get_text()


# ─── NumberedMarkdownTextFileNode ───────────────────────────────────


def test_numbered_markdown_text_file_node_create_file(fs):
    path = Path("/tmp/new_numbered.md")
    NumberedMarkdownTextFileNode.create_file(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_numbered_markdown_text_file_node_init_creates_if_missing(fs):
    path = Path("/tmp/auto_created_numbered.md")
    assert not path.exists()
    node = NumberedMarkdownTextFileNode(file_path=path)
    assert path.exists()
    assert node.get_text() == ""


def test_numbered_markdown_text_file_node_init_reads_existing(fs):
    fs.create_file("/tmp/existing_numbered.md", contents="# 1. Chapter\nContent")
    node = NumberedMarkdownTextFileNode(file_path=Path("/tmp/existing_numbered.md"))
    assert "# 1. Chapter" in node.get_text()


# ─── FoldableMarkdownTextFileNode ───────────────────────────────────


def test_foldable_markdown_text_file_node_create_file():
    path = Path("/tmp/new_fold.md")
    FoldableMarkdownTextFileNode.create_file(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_foldable_markdown_text_file_node_init_creates_if_missing():
    path = Path("/tmp/auto_created_fold.md")
    assert not path.exists()
    node = FoldableMarkdownTextFileNode(file_path=path)
    assert path.exists()
    assert node.get_text() == ""


def test_foldable_markdown_text_file_node_init_reads_existing(fs):
    fs.create_file("/tmp/existing_fold.md", contents="# 1. Title\nText")
    node = FoldableMarkdownTextFileNode(file_path=Path("/tmp/existing_fold.md"))
    assert "# 1. Title" in node.get_text()


# ─── AttributedMarkdownTextFileNode ─────────────────────────────────


def test_attributed_markdown_text_file_node_create_file_default():
    path = Path("/tmp/new_attr.md")
    AttributedMarkdownTextFileNode.create_file(path, attribute_type=_SimpleAttr)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "author: default" in content
    assert "version: 1.0.0" in content


def test_attributed_markdown_text_file_node_create_file_with_attribute():
    path = Path("/tmp/new_attr_custom.md")
    custom_attr = _SimpleAttr(author="alice", version="2.0.0")
    AttributedMarkdownTextFileNode.create_file(
        path, attribute_type=_SimpleAttr, attribute=custom_attr
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "author: alice" in content
    assert "version: 2.0.0" in content


def test_attributed_markdown_text_file_node_init_creates_if_missing():
    path = Path("/tmp/auto_created_attr.md")
    assert not path.exists()
    node = AttributedMarkdownTextFileNode(file_path=path, attribute_type=_SimpleAttr)
    assert path.exists()
    assert node.attribute.author == "default"
    assert node.get_text() == ""


def test_attributed_markdown_text_file_node_init_creates_with_attribute():
    path = Path("/tmp/auto_created_attr_custom.md")
    custom_attr = _SimpleAttr(author="bob", version="3.0.0")
    node = AttributedMarkdownTextFileNode(
        file_path=path,
        attribute_type=_SimpleAttr,
        attribute=custom_attr,
    )
    assert path.exists()
    assert node.attribute.author == "bob"
    assert node.attribute.version == "3.0.0"


def test_attributed_markdown_text_file_node_init_reads_existing(fs):
    content = "---\nauthor: existing\nversion: 9.0.0\n---\n# 1. Title\nBody"
    fs.create_file("/tmp/existing_attr.md", contents=content)
    node = AttributedMarkdownTextFileNode(
        file_path=Path("/tmp/existing_attr.md"), attribute_type=_SimpleAttr
    )
    assert node.attribute.author == "existing"
    assert node.attribute.version == "9.0.0"
    assert "# 1. Title" in node.get_text()


# ─── MarkdownFolderNode ─────────────────────────────────────────────


def test_markdown_folder_node_create_file():
    path = Path("/tmp/new_folder")
    NumberedMarkdownFolderNode.create_file(path)
    assert path.exists()
    assert path.is_dir()


def test_markdown_folder_node_init_creates_if_missing():
    path = Path("/tmp/auto_created_folder")
    assert not path.exists()
    _ = NumberedMarkdownFolderNode(file_path=path)
    assert path.exists()
    assert path.is_dir()


def test_markdown_folder_node_init_reads_existing(fs):
    fs.create_dir("/tmp/existing_folder")
    fs.create_file(
        "/tmp/existing_folder/1_Chapter.mdp", contents="## 1.1 Section\nContent"
    )
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/existing_folder"))
    assert "Chapter" in node.get_text()


# ─── FoldableMarkdownFolderNode ─────────────────────────────────────


def test_foldable_markdown_folder_node_create_file():
    path = Path("/tmp/new_fold_folder")
    FoldableMarkdownFolderNode.create_file(path)
    assert path.exists()
    assert path.is_dir()


def test_foldable_markdown_folder_node_init_creates_if_missing():
    path = Path("/tmp/auto_created_fold_folder")
    assert not path.exists()
    _ = FoldableMarkdownFolderNode(file_path=path)
    assert path.exists()
    assert path.is_dir()


def test_foldable_markdown_folder_node_init_reads_existing(fs):
    fs.create_dir("/tmp/existing_fold_folder")
    fs.create_file("/tmp/existing_fold_folder/1_Chapter.mdp", contents="## 1.1 Section")
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/existing_fold_folder"))
    assert "Chapter" in node.get_text()


# ─── AttributedMarkdownFolderNode ───────────────────────────────────


def test_attributed_markdown_folder_node_create_file_default():
    path = Path("/tmp/new_attr_folder")
    AttributedMarkdownFolderNode.create_file(path, attribute_type=_SimpleAttr)
    assert path.exists()
    assert path.is_dir()
    yaml_path = path / "FrontMatter.yaml"
    assert yaml_path.exists()
    assert "author: default" in yaml_path.read_text(encoding="utf-8")


def test_attributed_markdown_folder_node_create_file_with_attribute():
    path = Path("/tmp/new_attr_folder_custom")
    custom_attr = _SimpleAttr(author="carol", version="5.0.0")
    AttributedMarkdownFolderNode.create_file(
        path, attribute_type=_SimpleAttr, attribute=custom_attr
    )
    assert path.exists()
    yaml_path = path / "FrontMatter.yaml"
    assert "author: carol" in yaml_path.read_text(encoding="utf-8")
    assert "version: 5.0.0" in yaml_path.read_text(encoding="utf-8")


def test_attributed_markdown_folder_node_init_creates_if_missing():
    path = Path("/tmp/auto_created_attr_folder")
    assert not path.exists()
    node = AttributedMarkdownFolderNode(file_path=path, attribute_type=_SimpleAttr)
    assert path.exists()
    assert path.is_dir()
    assert node.attribute.author == "default"


def test_attributed_markdown_folder_node_init_creates_with_attribute():
    path = Path("/tmp/auto_created_attr_folder_custom")
    custom_attr = _SimpleAttr(author="dave", version="7.0.0")
    node = AttributedMarkdownFolderNode(
        file_path=path,
        attribute_type=_SimpleAttr,
        attribute=custom_attr,
    )
    assert path.exists()
    assert node.attribute.author == "dave"
    assert node.attribute.version == "7.0.0"


def test_attributed_markdown_folder_node_init_reads_existing(fs):
    fs.create_dir("/tmp/existing_attr_folder")
    fs.create_file(
        "/tmp/existing_attr_folder/FrontMatter.yaml",
        contents="author: folder_author\nversion: 4.0.0\n",
    )
    fs.create_file("/tmp/existing_attr_folder/1_Chapter.mdp", contents="## 1.1 Content")
    node = AttributedMarkdownFolderNode(
        file_path=Path("/tmp/existing_attr_folder"), attribute_type=_SimpleAttr
    )
    assert node.attribute.author == "folder_author"
    assert "Chapter" in node.get_text()
