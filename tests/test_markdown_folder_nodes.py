"""test_markdown_folder_nodes.py - 测试 Markdown 文件夹节点"""

from pathlib import Path

import pytest

from dl909markdowntree.markdown_folder_nodes import NumberedMarkdownFolderNode
from dl909markdowntree.numbered_markdown_nodes import (
    NumberedMarkdownTextNode,
    NumberedMarkdownTitleNode,
)
from dl909markdowntree.plain_text_nodes import PlainTextNode


def test_numbered_markdown_folder_node_reload_basic(fs):
    """测试 reload：两个 .mdp 文件正确解析为树结构"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent\n## 1.2 Thesis\nArgument",
    )
    fs.create_file(
        "/tmp/test.mdf/2_Body.mdp",
        contents="## 2.1 History\nText\n## 2.2 Prior Work\nResearch",
    )
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert isinstance(node.markdown_text_node, NumberedMarkdownTextNode)
    assert len(node.markdown_text_node.children) == 2
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    assert isinstance(node.markdown_text_node.children[1], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Intro"
    assert node.markdown_text_node.children[0].number == [1]
    assert node.markdown_text_node.children[1].title == "Body"
    assert node.markdown_text_node.children[1].number == [2]


def test_numbered_markdown_folder_node_reload_with_preamble(fs):
    """测试 reload：包含 0.mdp 时 preamble 被正确解析"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/0.mdp", contents="Preamble paragraph\n\nMore preamble"
    )
    fs.create_file("/tmp/test.mdf/1_Chapter.mdp", contents="## 1.1 Section\nContent")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert isinstance(node.markdown_text_node.children[0], PlainTextNode)
    assert "Preamble paragraph" in node.markdown_text_node.children[0].get_text()
    assert isinstance(node.markdown_text_node.children[1], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[1].title == "Chapter"
    assert node.markdown_text_node.children[1].number == [1]


def test_numbered_markdown_folder_node_reload_invalid_filename_raises(fs):
    """测试 reload：不符合 N_[Title].mdp 命名模式的 .mdp 文件抛出异常"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Valid.mdp", contents="## Content")
    fs.create_file("/tmp/test.mdf/invalid_name.mdp", contents="## Content")
    with pytest.raises(Exception, match="Invalid .mdp filename format"):
        NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))


def test_numbered_markdown_folder_node_reload_ignores_non_mdp(fs):
    """测试 reload：非 .mdp 文件被忽略"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Section.mdp", contents="## 1.1 Content")
    fs.create_file("/tmp/test.mdf/notes.txt", contents="Some notes")
    fs.create_file("/tmp/test.mdf/.DS_Store", contents="")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert len(node.markdown_text_node.children) == 1
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Section"


def test_numbered_markdown_folder_node_get_text(fs):
    """测试 get_text 返回跨文件的完整合成文本"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Opening\nContent")
    fs.create_file("/tmp/test.mdf/2_Body.mdp", contents="## 2.1 History\nText")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    text = node.get_text()
    assert "# 1. Intro" in text
    assert "## 1.1. Opening" in text
    assert "# 2. Body" in text
    assert "## 2.1. History" in text


def test_numbered_markdown_folder_node_set_text(fs):
    """测试 set_text 修改内部树结构"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Opening\nContent")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.set_text(
        "# 1. Intro\n## 1.1 Subsection\nMore content\n# 2. NewChapter\n## 2.1 Details"
    )
    assert len(node.markdown_text_node.children) == 2
    assert isinstance(node.markdown_text_node.children[1], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[1].title == "NewChapter"
    assert node.markdown_text_node.children[1].number == [2]


def test_numbered_markdown_folder_node_save_creates_file(fs):
    """测试 save：新增节点时创建对应的 .mdp 文件"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Content")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    new_section = NumberedMarkdownTitleNode(title="NewChapter", level=1, number=[2])
    node.markdown_text_node.addchild(new_section)
    node.save()
    assert Path("/tmp/test.mdf/2_NewChapter.mdp").exists()


def test_numbered_markdown_folder_node_save_renames_file(fs):
    """测试 save：标题变化时重命名 .mdp 文件"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_OldName.mdp", contents="## 1.1 Content")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    node.markdown_text_node.children[0].title = "NewName"
    node.save()
    assert not Path("/tmp/test.mdf/1_OldName.mdp").exists()
    assert Path("/tmp/test.mdf/1_NewName.mdp").exists()


def test_numbered_markdown_folder_node_save_deletes_file(fs):
    """测试 save：移除节点时删除对应的 .mdp 文件"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Content")
    fs.create_file("/tmp/test.mdf/2_Body.mdp", contents="## 2.1 Content")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.markdown_text_node.children[-1].deprecated = True
    node.markdown_text_node.update()
    node.save()
    assert Path("/tmp/test.mdf/1_Intro.mdp").exists()
    assert not Path("/tmp/test.mdf/2_Body.mdp").exists()


def test_numbered_markdown_folder_node_save_preamble(fs):
    """测试 save：有 preamble 内容时创建 0.mdp"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Content")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.markdown_text_node.children.insert(0, PlainTextNode("Preamble text"))
    node.save()
    assert Path("/tmp/test.mdf/0.mdp").exists()
    with open("/tmp/test.mdf/0.mdp", "r", encoding="utf-8") as f:
        assert "Preamble text" in f.read()


def test_numbered_markdown_folder_node_save_no_preamble_deletes_0(fs):
    """测试 save：无 preamble 时删除既有 0.mdp"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/0.mdp", contents="Old preamble")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Content")
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.markdown_text_node.children[0].deprecated = True
    node.markdown_text_node.update()
    node.save()
    assert not Path("/tmp/test.mdf/0.mdp").exists()


def test_numbered_markdown_folder_node_save_rewrites_existing(fs):
    """测试 save：重写既有文件的内容"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Original\nOld content",
    )
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.markdown_text_node.children[0].set_text("## 1.1 Updated\nNew content")
    node.save()
    with open("/tmp/test.mdf/1_Intro.mdp", "r", encoding="utf-8") as f:
        content = f.read()
    assert "## 1.1. Updated" in content
    assert "New content" in content
    assert "Original" not in content


def test_numbered_markdown_folder_node_reload_after_modification(fs):
    """测试 reload：重新加载反映外部文件变化"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent",
    )
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Intro"
    fs.remove("/tmp/test.mdf/1_Intro.mdp")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Modified\nNew preamble",
    )
    node.reload()
    assert "# 1. Intro" in node.get_text()
    assert "Modified" in node.get_text()


def test_numbered_markdown_folder_node_round_trip(fs):
    """测试 save 后 reload 保持数据一致"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent\n## 1.2 Thesis\nArgument",
    )
    fs.create_file(
        "/tmp/test.mdf/2_Body.mdp",
        contents="## 2.1 History\nText",
    )
    node = NumberedMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    original = node.get_text()
    node.save()
    node.reload()
    assert node.get_text() == original
