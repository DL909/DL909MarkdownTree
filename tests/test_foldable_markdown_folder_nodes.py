"""test_foldable_markdown_folder_nodes.py - 测试可折叠 Markdown 文件夹节点"""

from pathlib import Path


from dl909markdowntree.foldable_markdown_folder_nodes import (
    FoldableMarkdownFolderNode,
)
from dl909markdowntree.foldable_markdown_nodes import (
    FoldMode,
    FoldableMarkdownTextNode,
    FoldableMarkdownTitleNode,
)


def test_foldable_markdown_folder_node_reload_basic(fs):
    """测试 reload：内部树使用 FoldableMarkdownTextNode"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent\n## 1.2 Thesis\nArgument",
    )
    fs.create_file(
        "/tmp/test.mdf/2_Body.mdp",
        contents="## 2.1 History\nText",
    )
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert isinstance(node.markdown_text_node, FoldableMarkdownTextNode)
    assert isinstance(node.markdown_text_node.children[0], FoldableMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Intro"
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_TITLE


def test_foldable_markdown_folder_node_get_text_folded(fs):
    """测试 get_text：折叠模式下显示折叠信息"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent\n## 1.2 Thesis\nArgument",
    )
    fs.create_file(
        "/tmp/test.mdf/2_Body.mdp",
        contents="## 2.1 History\nText",
    )
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    text = node.get_text()
    assert "# 1. Intro" in text
    assert "# 2. Body" in text
    assert "[2 child title folded]" in text
    assert "[text folded]"


def test_foldable_markdown_folder_node_unfold(fs):
    """测试 unfold：展开后显示子标题内容"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent",
    )
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    assert (t := node.recursive_find_title_node_by_name("# 1. Intro"))
    t.unfold()
    assert (t := node.recursive_find_title_node_by_name("## 1.1. Opening"))
    text = t.unfold()
    assert "Opening" in node.get_text()
    assert "Content" in text


def test_foldable_markdown_folder_node_recursive_unfold(fs):
    """测试 recursive_unfold：展开所有层级"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent\n### 1.1.1 Detail\nDeep",
    )
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.markdown_text_node.children[0].recursive_unfold()
    text = node.get_text()
    assert "Opening" in text
    assert "Detail" in text
    assert "Deep" in text


def test_foldable_markdown_folder_node_set_load_depth(fs):
    """测试 set_load_depth：控制展开深度"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\n### 1.1.1 Deep\nContent",
    )
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.markdown_text_node.set_load_depth(1)
    assert "# 1. Intro" in node.get_text()
    assert "## 1.1. Opening" in node.get_text()


def test_foldable_markdown_folder_node_save_full_text(fs):
    """测试 save：始终写入完整文本，无视折叠状态"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent",
    )
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    node.save()
    with open("/tmp/test.mdf/1_Intro.mdp", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Content" in content


def test_foldable_markdown_folder_node_fold_and_save_round_trip(fs):
    """测试 save/reload 周期保持折叠状态"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file(
        "/tmp/test.mdf/1_Intro.mdp",
        contents="## 1.1 Opening\nContent",
    )
    node = FoldableMarkdownFolderNode(
        file_path=Path("/tmp/test.mdf"), use_fold_states=True
    )
    assert node.use_fold_states
    node.markdown_text_node.children[0].fold_mode = FoldMode.SHOW_CHILD
    node.markdown_text_node.children[0].children[0].fold_mode = FoldMode.SHOW_TITLE
    node.save()
    node.reload()
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_CHILD
    assert "Opening" in node.get_text()
    node = FoldableMarkdownFolderNode(
        file_path=Path("/tmp/test.mdf"), use_fold_states=True
    )
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_TITLE
    assert "# 1. Intro" in node.get_text()
    assert "Content" not in node.get_text()


def test_foldable_markdown_folder_node_fold_mode_default(fs):
    """测试默认折叠模式为 SHOW_TITLE"""
    fs.create_dir("/tmp/test.mdf")
    fs.create_file("/tmp/test.mdf/1_Intro.mdp", contents="## 1.1 Opening\nContent")
    node = FoldableMarkdownFolderNode(file_path=Path("/tmp/test.mdf"))
    for child in node.markdown_text_node.children:
        if isinstance(child, FoldableMarkdownTitleNode):
            assert child.fold_mode is FoldMode.SHOW_TITLE
