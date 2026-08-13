"""test_create_file.py - 测试 create_file 静态方法与 __init__ 自动创建行为"""

from pathlib import Path

from pydantic import BaseModel

from dl909markdowntree import (
    AttributedMarkdownFolderNode,
    AttributedMarkdownTextFileNode,
    FoldableMarkdownFolderNode,
    FoldableMarkdownTextFileNode,
    MarkdownTextFileNode,
    NumberedMarkdownFolderNode,
    NumberedMarkdownTextFileNode,
)


class _SimpleAttr(BaseModel):
    author: str = "default"
    version: str = "1.0.0"


# ─── MarkdownTextFileNode ───────────────────────────────────────────


def test_markdown_text_file_node_create_file(tmp_path: Path):
    path = tmp_path / "createed.md"
    MarkdownTextFileNode.create_file(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_markdown_text_file_node_init_creates_if_missing(tmp_path: Path):
    path = tmp_path / "auto_created.md"
    assert not path.exists()
    node = MarkdownTextFileNode(file_path=path)
    assert path.exists()
    assert node.get_text() == ""


def test_markdown_text_file_node_init_reads_existing(tmp_path: Path):
    path = tmp_path / "existing.md"
    path.write_text("# Hello\nContent")
    node = MarkdownTextFileNode(file_path=path)
    assert "# Hello" in node.get_text()
    assert "Content" in node.get_text()


# ─── NumberedMarkdownTextFileNode ───────────────────────────────────


def test_numbered_markdown_text_file_node_create_file(tmp_path: Path):
    path = tmp_path / "new_numbered.md"
    NumberedMarkdownTextFileNode.create_file(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_numbered_markdown_text_file_node_init_creates_if_missing(tmp_path: Path):
    path = tmp_path / "auto_created_numbered.md"
    assert not path.exists()
    node = NumberedMarkdownTextFileNode(file_path=path)
    assert path.exists()
    assert node.get_text() == ""


def test_numbered_markdown_text_file_node_init_reads_existing(tmp_path: Path):
    path = tmp_path / "existing_numbered.md"
    path.write_text("# 1. Chapter\nContent")
    node = NumberedMarkdownTextFileNode(file_path=path)
    assert "# 1. Chapter" in node.get_text()


# ─── FoldableMarkdownTextFileNode ───────────────────────────────────


def test_foldable_markdown_text_file_node_create_file(tmp_path: Path):
    path = tmp_path / "new_fold.md"
    FoldableMarkdownTextFileNode.create_file(path)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_foldable_markdown_text_file_node_init_creates_if_missing(tmp_path: Path):
    path = tmp_path / "auto_created_fold.md"
    assert not path.exists()
    node = FoldableMarkdownTextFileNode(file_path=path)
    assert path.exists()
    assert node.get_text() == ""


def test_foldable_markdown_text_file_node_init_reads_existing(tmp_path: Path):
    path = tmp_path / "existing_fold.md"
    path.write_text("# 1. Title\nText")
    node = FoldableMarkdownTextFileNode(file_path=path)
    assert "# 1. Title" in node.get_text()


# ─── AttributedMarkdownTextFileNode ─────────────────────────────────


def test_attributed_markdown_text_file_node_create_file_default(tmp_path: Path):
    path = tmp_path / "new_attr.md"
    AttributedMarkdownTextFileNode.create_file(path, attribute_type=_SimpleAttr)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "author: default" in content
    assert "version: 1.0.0" in content


def test_attributed_markdown_text_file_node_create_file_with_attribute(tmp_path: Path):
    path = tmp_path / "new_attr_custom.md"
    custom_attr = _SimpleAttr(author="alice", version="2.0.0")
    AttributedMarkdownTextFileNode.create_file(
        path, attribute_type=_SimpleAttr, attribute=custom_attr
    )
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "author: alice" in content
    assert "version: 2.0.0" in content


def test_attributed_markdown_text_file_node_init_creates_if_missing(tmp_path: Path):
    path = tmp_path / "auto_created_attr.md"
    assert not path.exists()
    node = AttributedMarkdownTextFileNode(file_path=path, attribute_type=_SimpleAttr)
    assert path.exists()
    assert node.attribute.author == "default"
    assert node.get_text() == ""


def test_attributed_markdown_text_file_node_init_creates_with_attribute(tmp_path: Path):
    path = tmp_path / "auto_created_attr_custom.md"
    custom_attr = _SimpleAttr(author="bob", version="3.0.0")
    node = AttributedMarkdownTextFileNode(
        file_path=path,
        attribute_type=_SimpleAttr,
        attribute=custom_attr,
    )
    assert path.exists()
    assert node.attribute.author == "bob"
    assert node.attribute.version == "3.0.0"


def test_attributed_markdown_text_file_node_init_reads_existing(tmp_path: Path):
    content = "---\nauthor: existing\nversion: 9.0.0\n---\n# 1. Title\nBody"
    path = tmp_path / "existing_attr.md"
    path.write_text(content)
    node = AttributedMarkdownTextFileNode(file_path=path, attribute_type=_SimpleAttr)
    assert node.attribute.author == "existing"
    assert node.attribute.version == "9.0.0"
    assert "# 1. Title" in node.get_text()


# ─── MarkdownFolderNode ─────────────────────────────────────────────


def test_markdown_folder_node_create_file(tmp_path: Path):
    path = tmp_path / "new_folder"
    NumberedMarkdownFolderNode.create_file(path)
    assert path.exists()
    assert path.is_dir()


def test_markdown_folder_node_init_creates_if_missing(tmp_path: Path):
    path = tmp_path / "auto_created_folder"
    assert not path.exists()
    _ = NumberedMarkdownFolderNode(file_path=path)
    assert path.exists()
    assert path.is_dir()


def test_markdown_folder_node_init_reads_existing(tmp_path: Path):
    path = tmp_path / "existing_folder.mdf"
    path.mkdir()
    (path / "1_Chapter.mdp").write_text("## 1.1. Section\nContent")
    node = NumberedMarkdownFolderNode(file_path=path)
    assert "Chapter" in node.get_text()


# ─── FoldableMarkdownFolderNode ─────────────────────────────────────


def test_foldable_markdown_folder_node_create_file(tmp_path: Path):
    path = tmp_path / "new_fold_folder"
    FoldableMarkdownFolderNode.create_file(path)
    assert path.exists()
    assert path.is_dir()


def test_foldable_markdown_folder_node_init_creates_if_missing(tmp_path: Path):
    path = tmp_path / "auto_created_fold_folder"
    assert not path.exists()
    _ = FoldableMarkdownFolderNode(file_path=path)
    assert path.exists()
    assert path.is_dir()


def test_foldable_markdown_folder_node_init_reads_existing(tmp_path: Path):
    path = tmp_path / "existing_fold_folder"
    path.mkdir()
    (path / "1_Chapter.mdp").write_text("## 1.1. Section")
    node = FoldableMarkdownFolderNode(file_path=path)
    assert "Chapter" in node.get_text()


# ─── AttributedMarkdownFolderNode ───────────────────────────────────


def test_attributed_markdown_folder_node_create_file_default(tmp_path: Path):
    path = tmp_path / "new_attr_folder"
    AttributedMarkdownFolderNode.create_file(path, attribute_type=_SimpleAttr)
    assert path.exists()
    assert path.is_dir()
    yaml_path = path / "FrontMatter.yaml"
    assert yaml_path.exists()
    assert "author: default" in yaml_path.read_text(encoding="utf-8")


def test_attributed_markdown_folder_node_create_file_with_attribute(tmp_path: Path):
    path = tmp_path / "new_attr_folder_custom"
    custom_attr = _SimpleAttr(author="carol", version="5.0.0")
    AttributedMarkdownFolderNode.create_file(
        path, attribute_type=_SimpleAttr, attribute=custom_attr
    )
    assert path.exists()
    yaml_path = path / "FrontMatter.yaml"
    assert "author: carol" in yaml_path.read_text(encoding="utf-8")
    assert "version: 5.0.0" in yaml_path.read_text(encoding="utf-8")


def test_attributed_markdown_folder_node_init_creates_if_missing(tmp_path: Path):
    path = tmp_path / "auto_created_attr_folder"
    assert not path.exists()
    node = AttributedMarkdownFolderNode(file_path=path, attribute_type=_SimpleAttr)
    assert path.exists()
    assert path.is_dir()
    assert node.attribute.author == "default"


def test_attributed_markdown_folder_node_init_creates_with_attribute(tmp_path: Path):
    path = tmp_path / "auto_created_attr_folder_custom"
    custom_attr = _SimpleAttr(author="dave", version="7.0.0")
    node = AttributedMarkdownFolderNode(
        file_path=path,
        attribute_type=_SimpleAttr,
        attribute=custom_attr,
    )
    assert path.exists()
    assert node.attribute.author == "dave"
    assert node.attribute.version == "7.0.0"


def test_attributed_markdown_folder_node_init_reads_existing(tmp_path: Path):
    path = tmp_path / "existing_attr_folder"
    path.mkdir()
    (path / "FrontMatter.yaml").write_text("author: folder_author\nversion: 4.0.0\n")
    (path / "1_Chapter.mdp").write_text("## 1.1. Content")
    node = AttributedMarkdownFolderNode(file_path=path, attribute_type=_SimpleAttr)
    assert node.attribute.author == "folder_author"
    assert "Chapter" in node.get_text()


# ─── create_file 边界：父目录缺失 ─────────────────────────────────────


def test_markdown_text_file_node_create_file_missing_parent_dir(tmp_path: Path):
    path = tmp_path / "nested/one/two/doc.md"
    MarkdownTextFileNode.create_file(path)
    assert path.parent.exists()
    assert path.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_numbered_markdown_text_file_node_create_file_missing_parent_dir(
    tmp_path: Path,
):
    path = tmp_path / "nested/one/two/num.md"
    NumberedMarkdownTextFileNode.create_file(path)
    assert path.parent.exists()
    assert path.read_text(encoding="utf-8") == ""


def test_attributed_markdown_text_file_node_create_file_missing_parent_dir(
    tmp_path: Path,
):
    path = tmp_path / "nested/one/two/attr.md"
    AttributedMarkdownTextFileNode.create_file(path, attribute_type=_SimpleAttr)
    assert path.parent.exists()
    assert "author: default" in path.read_text(encoding="utf-8")


def test_foldable_markdown_folder_node_create_file_missing_parent_dir(tmp_path: Path):
    path = tmp_path / "nested/one/two/new_folder"
    FoldableMarkdownFolderNode.create_file(path)
    assert path.parent.exists()
    assert path.exists()
    assert path.is_dir()


def test_attributed_markdown_folder_node_create_file_missing_parent_dir(tmp_path: Path):
    path = tmp_path / "nested/one/two/new_attr_folder"
    AttributedMarkdownFolderNode.create_file(path, attribute_type=_SimpleAttr)
    assert path.parent.exists()
    assert path.is_dir()
    assert (path / "FrontMatter.yaml").exists()


# ─── create_file 边界：目标已存在 ─────────────────────────────────────


def test_markdown_text_file_node_create_file_existing_truncates(tmp_path: Path):
    path = tmp_path / "with_old_content.md"
    path.write_text("# Old\ncontent")
    MarkdownTextFileNode.create_file(path)
    assert path.read_text(encoding="utf-8") == ""


def test_foldable_markdown_text_file_node_create_file_existing_truncates(
    tmp_path: Path,
):
    path = tmp_path / "with_old_content_fold.md"
    path.write_text("# Old\ncontent")
    FoldableMarkdownTextFileNode.create_file(path)
    assert path.read_text(encoding="utf-8") == ""


def test_attributed_markdown_text_file_node_create_file_existing_overwrites(
    tmp_path: Path,
):
    path = tmp_path / "attr_with_old_content.md"
    path.write_text("---\nauthor: old\nversion: 0.0.1\n---\n# T\nbody")
    AttributedMarkdownTextFileNode.create_file(path, attribute_type=_SimpleAttr)
    content = path.read_text(encoding="utf-8")
    assert "author: old" not in content
    assert "author: default" in content
    assert "version: 1.0.0" in content


def test_foldable_markdown_folder_node_create_file_existing_preserves(tmp_path: Path):
    path = tmp_path / "existing_dir_with_content"
    path.mkdir()
    (path / "1_Chapter.mdp").write_text("## 1.1 Section")
    FoldableMarkdownFolderNode.create_file(path)
    assert path.is_dir()
    assert (path / "1_Chapter.mdp").exists()


def test_attributed_markdown_folder_node_create_file_existing_overwrites_yaml(
    tmp_path: Path,
):
    path = tmp_path / "attr_folder_with_old_yaml"
    path.mkdir()
    (path / "FrontMatter.yaml").write_text("author: old\n")
    AttributedMarkdownFolderNode.create_file(path, attribute_type=_SimpleAttr)
    assert "author: old" not in (path / "FrontMatter.yaml").read_text(encoding="utf-8")
    assert "author: default" in (path / "FrontMatter.yaml").read_text(encoding="utf-8")
