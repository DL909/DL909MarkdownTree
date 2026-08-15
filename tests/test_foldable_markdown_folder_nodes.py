"""test_foldable_markdown_folder_nodes.py - 测试可折叠 Markdown 文件夹节点"""

from pathlib import Path

from dl909markdowntree import (
    FoldableMarkdownFolderNode,
    FoldableMarkdownTitleNode,
    FoldMode,
)


def test_foldable_markdown_folder_node_reload_basic(tmp_path):
    """测试 reload：内部树使用 FoldableMarkdownTitleNode"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent\n## 1.2. Thesis\nArgument", encoding="utf-8"
    )
    (folder / "2_Body.mdp").write_text("## 2.1. History\nText", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    assert isinstance(node.markdown_text_node, FoldableMarkdownTitleNode)
    assert isinstance(node.markdown_text_node.children[0], FoldableMarkdownTitleNode)
    assert node.markdown_text_node.children[0].title == "Intro"
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_TITLE


def test_foldable_markdown_folder_node_get_text_folded(tmp_path):
    """测试 get_text：折叠模式下显示折叠信息"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent\n## 1.2. Thesis\nArgument", encoding="utf-8"
    )
    (folder / "2_Body.mdp").write_text("## 2.1. History\nText", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    text = node.get_text()
    assert "# 1. Intro" in text
    assert "# 2. Body" in text
    assert "[2 child title folded]" in text
    assert "[1 child title folded]" in text


def test_foldable_markdown_folder_node_unfold(tmp_path):
    """测试 unfold：展开后显示子标题内容"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    t = node.get_root_title().recursive_find_title_node_by_name("# 1. Intro")
    assert t is not None
    t.unfold()
    t = node.get_root_title().recursive_find_title_node_by_name("## 1.1. Opening")
    assert t is not None
    text = t.unfold()
    assert "Opening" in node.get_text()
    assert "Content" in text


def test_foldable_markdown_folder_node_recursive_unfold(tmp_path):
    """测试 recursive_unfold：展开所有层级"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\nContent\n### 1.1.1. Detail\nDeep", encoding="utf-8"
    )
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    node.markdown_text_node.children[0].recursive_unfold()
    text = node.get_text()
    assert "Opening" in text
    assert "Detail" in text
    assert "Deep" in text


def test_foldable_markdown_folder_node_set_load_depth(tmp_path):
    """测试 unfold_by_depth：控制展开深度"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text(
        "## 1.1. Opening\n### 1.1.1. Deep\nContent", encoding="utf-8"
    )
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    node.markdown_text_node.unfold_by_depth(2)
    assert "# 1. Intro" in node.get_text()
    assert "## 1.1. Opening" in node.get_text()


def test_foldable_markdown_folder_node_save_full_text(tmp_path):
    """测试 save：始终写入完整文本，无视折叠状态"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    node.save()
    with open(folder / "1_Intro.mdp", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Content" in content


def test_foldable_markdown_folder_node_save_folded_preamble(tmp_path):
    """测试 save：折叠的 preamble 不把折叠标记写入 0.mdp"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "0.mdp").write_text(
        "## 0.1. PreambleSub\nPre content", encoding="utf-8"
    )
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    preamble = node.markdown_text_node.children[0]
    assert isinstance(preamble, FoldableMarkdownTitleNode)
    preamble.fold_mode = FoldMode.SHOW_TITLE
    node.save()
    content = (folder / "0.mdp").read_text(encoding="utf-8")
    assert "PreambleSub" in content
    assert "Pre content" in content
    assert "folded" not in content


def test_foldable_markdown_folder_node_fold_and_save_round_trip(tmp_path):
    """测试 save/reload 周期保持折叠状态"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    node.markdown_text_node.children[0].fold_mode = FoldMode.SHOW_CHILD
    node.markdown_text_node.children[0].children[0].fold_mode = FoldMode.SHOW_TITLE
    node.save()
    node.reload()
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_CHILD
    assert node.get_text() == "# 1. Intro\n## 1.1. Opening [text folded]\n"
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_CHILD
    assert node.get_text() == "# 1. Intro\n## 1.1. Opening [text folded]\n"


def test_foldable_markdown_folder_node_fold_mode_default(tmp_path):
    """测试默认折叠模式为 SHOW_TITLE"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    for child in node.markdown_text_node.children:
        if isinstance(child, FoldableMarkdownTitleNode):
            assert child.fold_mode is FoldMode.SHOW_TITLE


def test_foldable_markdown_folder_node_reload_corrupt_fold_state(tmp_path):
    """测试 reload：损坏的 fold_state.json 被忽略而不抛异常"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    (folder / "fold_state.json").write_text("{ not valid json", encoding="utf-8")
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_TITLE


def test_foldable_markdown_folder_node_reload_unknown_fold_state(tmp_path):
    """测试 reload：未知折叠状态名被忽略而不抛异常"""
    folder = tmp_path / "test.mdf"
    folder.mkdir()
    (folder / "1_Intro.mdp").write_text("## 1.1. Opening\nContent", encoding="utf-8")
    (folder / "fold_state.json").write_text(
        '{"[1]": "NOT_A_MODE"}', encoding="utf-8"
    )
    node = FoldableMarkdownFolderNode(file_path=Path(folder))
    assert node.markdown_text_node.children[0].fold_mode is FoldMode.SHOW_TITLE