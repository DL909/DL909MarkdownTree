"""test_markdown_folder_nodes.py - 测试 Markdown 文件夹节点"""

from pathlib import Path

import pytest

from dl909markdowntree import (
    InvalidMdpFilenameError,
    NumberedMarkdownFolderNode,
    NumberedMarkdownTitleNode,
    PlainTextNode,
)


def test_numbered_markdown_folder_node_reload_basic(tmp_path):
    """测试 reload：两个 .mdp 文件正确解析为树结构"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent\n## 1.2. Thesis\nArgument", encoding="utf-8"
    )
    (folder / "2_Body.mdp").write_text(
        "## 2.1. History\nText\n## 2.2. Prior Work\nResearch", encoding="utf-8"
    )
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node, NumberedMarkdownTitleNode)
    assert len(node.markdown_text_node.children) == 2
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    assert isinstance(node.markdown_text_node.children[1], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Intro"
    assert node.markdown_text_node.children[0].number == [1]
    assert node.markdown_text_node.children[1].title == "Body"
    assert node.markdown_text_node.children[1].number == [2]


def test_numbered_markdown_folder_node_reload_with_preamble(tmp_path):
    """测试 reload：包含 0.mdp 时 preamble 被正确解析"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "0.mdp").write_text(
        "Preamble paragraph\n\nMore preamble", encoding="utf-8"
    )
    (folder / "1_Chapter.mdp").write_text(
        "## 1.1. Section\nContent", encoding="utf-8"
    )
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node.children[0], PlainTextNode)
    assert "Preamble paragraph" in node.markdown_text_node.children[0].get_text()
    assert isinstance(node.markdown_text_node.children[1], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[1].title == "Chapter"
    assert node.markdown_text_node.children[1].number == [1]


def test_numbered_markdown_folder_node_reload_invalid_filename_raises(tmp_path):
    """测试 reload：不符合 N_[Title].mdp 命名模式的 .mdp 文件抛出异常"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Valid.mdp").write_text("## Content", encoding="utf-8")
    (folder / "invalid_name.mdp").write_text("## Content", encoding="utf-8")
    with pytest.raises(InvalidMdpFilenameError, match="Invalid .mdp filename format"):
        NumberedMarkdownFolderNode(file_path=Path(folder))


def test_numbered_markdown_folder_node_reload_ignores_non_mdp(tmp_path):
    """测试 reload：非 .mdp 文件被忽略"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Section.mdp").write_text("## 1.1. Content", encoding="utf-8")
    (folder / "notes.txt").write_text("Some notes", encoding="utf-8")
    (folder / ".DS_Store").write_text("", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert len(node.markdown_text_node.children) == 1
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Section"


def test_numbered_markdown_folder_node_get_text(tmp_path):
    """测试 get_text 返回跨文件的完整合成文本"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    (folder / "2_Body.mdp").write_text("## 2.1. History\nText", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    text = node.get_text()
    assert "# 1. Intro" in text
    assert "## 1.1. Opening" in text
    assert "# 2. Body" in text
    assert "## 2.1. History" in text


def test_numbered_markdown_folder_node_set_text(tmp_path):
    """测试 set_text 修改内部树结构"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    node.set_text(
        "# 1. Intro\n## 1.1. Subsection\nMore content\n# 2. NewChapter\n## 2.1. Details"
    )
    assert len(node.markdown_text_node.children) == 2
    assert isinstance(node.markdown_text_node.children[1], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[1].title == "NewChapter"
    assert node.markdown_text_node.children[1].number == [2]


def test_numbered_markdown_folder_node_save_creates_file(tmp_path):
    """测试 save：新增节点时创建对应的 .mdp 文件"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    new_section = NumberedMarkdownTitleNode(title="NewChapter", level=1, number=[2])
    node.markdown_text_node.addchild(new_section)
    node.save()
    assert Path(folder / "2_NewChapter.mdp").exists()


def test_numbered_markdown_folder_node_save_renames_file(tmp_path):
    """测试 save：标题变化时重命名 .mdp 文件"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_OldName.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    node.markdown_text_node.children[0].title = "NewName"
    node.save()
    assert not Path(folder / "1_OldName.mdp").exists()
    assert Path(folder / "1_NewName.mdp").exists()


def test_numbered_markdown_folder_node_save_deletes_file(tmp_path):
    """测试 save：移除节点时删除对应的 .mdp 文件"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Content", encoding="utf-8")
    (folder / "2_Body.mdp").write_text("## 2.1. Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    node.markdown_text_node.children[-1].deprecated = True
    node.markdown_text_node.update()
    node.save()
    assert Path(folder / "1_Intro.mdp").exists()
    assert not Path(folder / "2_Body.mdp").exists()


def test_numbered_markdown_folder_node_save_preamble(tmp_path):
    """测试 save：有 preamble 内容时创建 0.mdp"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    node.markdown_text_node.children.insert(0, PlainTextNode("Preamble text"))
    node.save()
    assert Path(folder / "0.mdp").exists()
    with open(folder / "0.mdp", "r", encoding="utf-8") as f:
        assert "Preamble text" in f.read()


def test_numbered_markdown_folder_node_save_no_preamble_deletes_0(tmp_path):
    """测试 save：无 preamble 时删除既有 0.mdp"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "0.mdp").write_text("Old preamble", encoding="utf-8")
    (folder / "1_Intro.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    node.markdown_text_node.children[0].deprecated = True
    node.markdown_text_node.update()
    node.save()
    assert not Path(folder / "0.mdp").exists()


def test_numbered_markdown_folder_node_save_rewrites_existing(tmp_path):
    """测试 save：重写既有文件的内容"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Original\nOld content", encoding="utf-8"
    )
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    node.markdown_text_node.children[0].set_text("## 1.1. Updated\nNew content")
    node.save()
    with open(folder / "1_Intro.mdp", "r", encoding="utf-8") as f:
        content = f.read()
    assert "## 1.1. Updated" in content
    assert "New content" in content
    assert "Original" not in content


def test_numbered_markdown_folder_node_reload_after_modification(tmp_path):
    """测试 reload：重新加载反映外部文件变化"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent", encoding="utf-8"
    )
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Intro"
    (folder / "1_Intro.mdp").unlink()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Modified\nNew preamble", encoding="utf-8"
    )
    node.reload()
    assert "# 1. Intro" in node.get_text()
    assert "Modified" in node.get_text()


def test_numbered_markdown_folder_node_round_trip(tmp_path):
    """测试 save 后 reload 保持数据一致"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent\n## 1.2. Thesis\nArgument", encoding="utf-8"
    )
    (folder / "2_Body.mdp").write_text("## 2.1. History\nText", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    original = node.get_text()
    node.save()
    node.reload()
    assert node.get_text() == original


def test_numbered_markdown_folder_node_reload_auto_correct_false(tmp_path):
    """测试 reload(auto_correct=False) 时显式传入的 False 不被旧值覆盖"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder), auto_correct=True)
    node.reload(auto_correct=False)
    assert node.markdown_text_node.auto_correct is False
    node2 = NumberedMarkdownFolderNode(file_path=Path(folder), auto_correct=False)
    node2.reload()
    assert node2.markdown_text_node.auto_correct is False


def test_numbered_markdown_folder_node_save_sanitizes_title(tmp_path):
    """测试 save：标题含非法文件名字符时消毒后再写入文件名"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    node.markdown_text_node.children[0].title = "a/b:c"
    node.save()
    assert Path(folder / "1_a_b_c.mdp").exists()
    assert not (folder / "1_a").exists()


def test_numbered_markdown_folder_node_save_sanitizes_to_untitled(tmp_path):
    """测试 save：标题全为非法字符时回退为 untitled"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    node.markdown_text_node.children[0].title = "."
    node.save()
    assert Path(folder / "1_untitled.mdp").exists()


def test_numbered_markdown_folder_node_save_removes_duplicate_number(tmp_path):
    """测试 save：同一编号的重复 .mdp 文件被清理"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_a.mdp").write_text("## 1.1. A content", encoding="utf-8")
    (folder / "1_b.mdp").write_text("## 2.1. B content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    node.save()
    assert Path(folder / "1_a.mdp").exists()
    assert Path(folder / "2_b.mdp").exists()
    assert not Path(folder / "1_b.mdp").exists()


def test_numbered_markdown_folder_node_save_rename_over_existing(tmp_path):
    """测试 save：重命名目标已被占用时不静默覆盖丢失数据"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_a.mdp").write_text("## 1.1. A content", encoding="utf-8")
    (folder / "1_b.mdp").write_text("## 2.1. B content", encoding="utf-8")
    node = NumberedMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node.children[0], NumberedMarkdownTitleNode)
    node.markdown_text_node.children[0].title = "b"
    node.save()
    assert Path(folder / "1_b.mdp").exists()
    assert Path(folder / "2_b.mdp").exists()
    assert not Path(folder / "1_a.mdp").exists()
