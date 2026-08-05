"""test_attributed_markdown_folder_nodes.py - 测试属性化 Markdown 文件夹节点"""

from pathlib import Path

from pydantic import BaseModel

from dl909markdowntree.attributed_markdown_folder_nodes import (
    AttributedMarkdownFolderNode,
)
from dl909markdowntree.foldable_markdown_nodes import (
    FoldableMarkdownTextNode,
    FoldableMarkdownTitleNode,
)


class _ChapterMeta(BaseModel):
    """测试用的文件夹属性类"""

    author: str = "default_author"
    status: str = "draft"
    word_count: int = 0


def test_attributed_markdown_folder_node_init(fs):
    """测试基本初始化：加载 FrontMatter.yaml 和 .mdp 文件"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: test_author\nstatus: completed\nword_count: 5000\n",
    )
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    assert node.attribute.author == "test_author"
    assert node.attribute.status == "completed"
    assert node.attribute.word_count == 5000
    assert isinstance(node.markdown_text_node, FoldableMarkdownTextNode)
    assert isinstance(node.markdown_text_node.children[0], FoldableMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Chapter"


def test_attributed_markdown_folder_node_default_attributes(fs):
    """测试默认属性值"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: custom_author\n",
    )
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Content")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    assert node.attribute.author == "custom_author"
    assert node.attribute.status == "draft"
    assert node.attribute.word_count == 0


def test_attributed_markdown_folder_node_save(fs):
    """测试 save：写入 FrontMatter.yaml"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: original\nstatus: draft\nword_count: 0\n",
    )
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Content")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    node.attribute.author = "modified"
    node.attribute.word_count = 3000
    node.save()
    with open("/tmp/test.mdf/FrontMatter.yaml", "r", encoding="utf-8") as f:
        content = f.read()
    assert "author: modified" in content
    assert "word_count: 3000" in content
    assert "status: draft" in content


def test_attributed_markdown_folder_node_reload(fs):
    """测试 reload：重新加载 FrontMatter.yaml"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: first\nstatus: draft\nword_count: 100\n",
    )
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Content")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    assert node.attribute.author == "first"
    fs.remove("/tmp/test.mdf/FrontMatter.yaml")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: second\nstatus: completed\nword_count: 500\n",
    )
    node.reload()
    assert node.attribute.author == "second"
    assert node.attribute.status == "completed"
    assert node.attribute.word_count == 500


def test_attributed_markdown_folder_node_save_and_reload_mdp(fs):
    """测试 save/reload：.mdp 文件与 FrontMatter.yaml 同时保持"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: test\nstatus: draft\nword_count: 0\n",
    )
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent",
    )
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    node.attribute.word_count = 1000
    node.set_text(
        "# 1. Intro\n## 1.1 Opening\nModified content\n## 1.2 NewSection\nNew"
    )
    node.save()
    node.reload()
    assert node.attribute.word_count == 1000
    assert "Modified content" in node.get_text(full_text=True)
    assert "NewSection" in node.get_text(full_text=True)


def test_attributed_markdown_folder_node_get_text_folded(fs):
    """测试 get_text：属性化文件夹节点支持折叠"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: test\nstatus: draft\nword_count: 0\n",
    )
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent",
    )
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    assert "Content" not in node.get_text()
    assert "Content" in node.get_text(full_text=True)


def test_attributed_markdown_folder_node_find_title(fs):
    """测试递归查找标题节点"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: test\nstatus: draft\nword_count: 0\n",
    )
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent\n## 1.2 Thesis\nArgument",
    )
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    found = node.recursive_find_title_node_by_name("## 1.2. Thesis")
    assert found is not None
    assert found.title == "Thesis"
    assert isinstance(found, FoldableMarkdownTitleNode)
    not_found = node.recursive_find_title_node_by_name("## 9.9. NotExist")
    assert not_found is None


def test_attributed_markdown_folder_node_with_preamble(fs):
    """测试包含 preamble 的属性化文件夹节点"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/FrontMatter.yaml",
        contents="author: test\nstatus: draft\nword_count: 0\n",
    )
    fs.create_file("/tmp/test.mdf/0.mdp", contents="Preamble text before sections")
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = AttributedMarkdownFolderNode[_ChapterMeta](
        file_path=Path("/tmp/test.mdf"), attribute_type=_ChapterMeta
    )
    assert "Preamble text before sections" in node.get_text()
    assert "# 1. Chapter" in node.get_text()
