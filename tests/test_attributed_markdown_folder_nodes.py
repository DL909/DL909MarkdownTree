"""test_attributed_markdown_folder_nodes.py - 测试属性化 Markdown 文件夹节点"""

from pathlib import Path

from pydantic import BaseModel

from dl909markdowntree.attributed_markdown_folder_nodes import (
    AttributedMarkdownFolderNode,
)
from dl909markdowntree.foldable_markdown_nodes import (
    FoldableMarkdownTitleNode,
)


class _ChapterMeta(BaseModel):
    """测试用的文件夹属性类"""

    author: str = "default_author"
    status: str = "draft"
    word_count: int = 0


def test_attributed_markdown_folder_node_init(tmp_path):
    """测试基本初始化：加载 FrontMatter.yaml 和 .mdp 文件"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: test_author\nstatus: completed\nword_count: 5000\n",
        encoding="utf-8",
    )
    (folder / "1_Chapter.mdp").write_text("## 1.1. Section\nContent", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    assert node.attribute.author == "test_author"
    assert node.attribute.status == "completed"
    assert node.attribute.word_count == 5000
    assert isinstance(node.markdown_text_node, FoldableMarkdownTitleNode)
    assert isinstance(node.markdown_text_node.children[0], FoldableMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Chapter"


def test_attributed_markdown_folder_node_default_attributes(tmp_path):
    """测试默认属性值"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text("author: custom_author\n", encoding="utf-8")
    (folder / "1_Chapter.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    assert node.attribute.author == "custom_author"
    assert node.attribute.status == "draft"
    assert node.attribute.word_count == 0


def test_attributed_markdown_folder_node_save(tmp_path):
    """测试 save：写入 FrontMatter.yaml"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: original\nstatus: draft\nword_count: 0\n", encoding="utf-8"
    )
    (folder / "1_Chapter.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    node.attribute.author = "modified"
    node.attribute.word_count = 3000
    node.save()
    with open(folder / "FrontMatter.yaml", "r", encoding="utf-8") as f:
        content = f.read()
    assert "author: modified" in content
    assert "word_count: 3000" in content
    assert "status: draft" in content


def test_attributed_markdown_folder_node_reload(tmp_path):
    """测试 reload：重新加载 FrontMatter.yaml"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: first\nstatus: draft\nword_count: 100\n", encoding="utf-8"
    )
    (folder / "1_Chapter.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    assert node.attribute.author == "first"
    (folder / "FrontMatter.yaml").unlink()
    (folder / "FrontMatter.yaml").write_text(
        "author: second\nstatus: completed\nword_count: 500\n", encoding="utf-8"
    )
    node.reload()
    assert node.attribute.author == "second"
    assert node.attribute.status == "completed"
    assert node.attribute.word_count == 500


def test_attributed_markdown_folder_node_save_and_reload_mdp(tmp_path):
    """测试 save/reload：.mdp 文件与 FrontMatter.yaml 同时保持"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: test\nstatus: draft\nword_count: 0\n", encoding="utf-8"
    )
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    node.attribute.word_count = 1000
    node.set_text(
        "# 1. Intro\n## 1.1. Opening\nModified content\n## 1.2. NewSection\nNew"
    )
    node.save()
    node.reload()
    assert node.attribute.word_count == 1000
    assert "Modified content" in node.get_text(full_text=True)
    assert "NewSection" in node.get_text(full_text=True)


def test_attributed_markdown_folder_node_get_text_folded(tmp_path):
    """测试 get_text：属性化文件夹节点支持折叠"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: test\nstatus: draft\nword_count: 0\n", encoding="utf-8"
    )
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    assert "Content" not in node.get_text()
    assert "Content" in node.get_text(full_text=True)


def test_attributed_markdown_folder_node_find_title(tmp_path):
    """测试递归查找标题节点"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: test\nstatus: draft\nword_count: 0\n", encoding="utf-8"
    )
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent\n## 1.2. Thesis\nArgument", encoding="utf-8"
    )
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    found = node.get_root_title().recursive_find_title_node_by_name("## 1.2. Thesis")
    assert found is not None
    assert found.title == "Thesis"
    assert isinstance(found, FoldableMarkdownTitleNode)
    not_found = node.get_root_title().recursive_find_title_node_by_name(
        "## 9.9. NotExist"
    )
    assert not_found is None


def test_attributed_markdown_folder_node_with_preamble(tmp_path):
    """测试包含 preamble 的属性化文件夹节点"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "FrontMatter.yaml").write_text(
        "author: test\nstatus: draft\nword_count: 0\n", encoding="utf-8"
    )
    (folder / "0.mdp").write_text(
        "Preamble text before sections", encoding="utf-8"
    )
    (folder / "1_Chapter.mdp").write_text("## 1.1. Section\nContent", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path(folder), attribute_type=_ChapterMeta
    )
    assert "Preamble text before sections" in node.get_text()
    assert "# 1. Chapter" in node.get_text()