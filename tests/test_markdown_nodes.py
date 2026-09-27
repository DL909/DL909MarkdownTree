from pathlib import Path

import pytest

from dl909markdowntree import (
    FoldableMarkdownTextFileNode,
    InvalidMarkdownLineError,
    InvalidTitleLevelError,
    MarkdownTextFileNode,
    MarkdownTitleNode,
    PlainTextNode,
)


def test_markdown_title_node_init():
    title_node = MarkdownTitleNode(title="Test Title", level=1)
    assert title_node.title == "Test Title"
    assert title_node.level == 1
    assert title_node.children == []


def test_markdown_title_node_addchild_consecutive_plain_text_merged():
    title_node = MarkdownTitleNode(title="Test", level=1)
    title_node.addchild(PlainTextNode("first line\n"))
    title_node.addchild(PlainTextNode("second line\n"))
    full_text = title_node.get_text()
    assert "first line" in full_text
    assert "second line" in full_text


def test_markdown_title_node_addchild_sets_plain_text_node_parent():
    title_node = MarkdownTitleNode(title="Test", level=1)
    first = PlainTextNode("first line\n")
    second = PlainTextNode("second line\n")
    title_node.addchild(first)
    assert first.parent is title_node
    title_node.addchild(second)
    assert first.parent is title_node
    assert second.parent is None


def test_markdown_title_node_init_with_text():
    title_node = MarkdownTitleNode(title="Test", level=2)
    title_node.set_text("Some content")
    assert title_node.title == "Test"
    assert title_node.level == 2
    assert len(title_node.children) > 0
    assert isinstance(title_node.children[0], PlainTextNode)


def test_markdown_title_node_get_title():
    title_node = MarkdownTitleNode(title="Test", level=3)
    assert title_node.get_title() == "### Test"
    assert title_node.get_title(show_level_sign=False) == "Test"


def test_markdown_title_node_get_title_level_zero():
    title_node = MarkdownTitleNode(level=0)
    assert title_node.get_title() == ""
    assert title_node.get_title(show_level_sign=False) == ""


def test_markdown_title_node_get_text():
    title_node = MarkdownTitleNode(title="Test", level=2)
    title_node.set_text("Content here")
    text = title_node.get_text()
    assert "## Test" in text
    assert "Content here" in text


def test_markdown_title_node_add_text():
    title_node = MarkdownTitleNode(title="Test", level=1)
    title_node.set_text("Initial text")
    title_node.add_text("Additional text")
    text = title_node.get_text()
    assert "Initial text" in text
    assert "Additional text" in text


def test_markdown_title_node_recursive_find_found():
    title_node = MarkdownTitleNode(title="Root", level=1)
    child = MarkdownTitleNode(title="Child", level=2)
    title_node.addchild(child)
    found = title_node.recursive_find_title_node_by_name("## Child")
    assert found is not None
    assert found.title == "Child"


def test_markdown_title_node_recursive_find_not_found():
    title_node = MarkdownTitleNode(title="Root", level=1)
    child = MarkdownTitleNode(title="Child", level=2)
    title_node.addchild(child)
    found = title_node.recursive_find_title_node_by_name("## NotExist")
    assert found is None


def test_markdown_title_node_set_text_with_code_block():
    title_node = MarkdownTitleNode(title="Test", level=1)
    text = """Some text
```python
def hello():
    print("Hello")
```
More text"""
    title_node.set_text(text)
    assert len(title_node.children) > 0
    full_text = title_node.get_text()
    assert "```python" in full_text
    assert "def hello():" in full_text


def test_markdown_title_node_set_text_with_long_fence():
    title_node = MarkdownTitleNode(title="Test", level=1)
    text = """Some text
````python
```
Still inside the block
````
More text"""
    title_node.set_text(text)
    full_text = title_node.get_text()
    assert "````python" in full_text
    assert "```\nStill inside the block" in full_text
    assert full_text.endswith("More text")


def test_markdown_title_node_set_text_longer_closing_fence():
    title_node = MarkdownTitleNode(title="Test", level=1)
    text = """Some text
```
code
````
More text"""
    title_node.set_text(text)
    full_text = title_node.get_text()
    assert "code" in full_text
    assert full_text.endswith("More text")


def test_markdown_title_node_set_text_closing_fence_trailing_spaces():
    title_node = MarkdownTitleNode(title="Test", level=1)
    text = """Some text
```
code
```   
More text"""
    title_node.set_text(text)
    full_text = title_node.get_text()
    assert "code" in full_text
    assert full_text.endswith("More text")


def test_markdown_title_node_set_text_with_tilde_fence():
    title_node = MarkdownTitleNode(title="Test", level=1)
    text = """Some text
~~~
# not a title
~~~
More text"""
    title_node.set_text(text)
    assert (
        len([c for c in title_node.children if isinstance(c, MarkdownTitleNode)]) == 0
    )
    assert "# not a title" in title_node.get_text()
    assert title_node.get_text().endswith("More text")


def test_markdown_title_node_tilde_fence_needs_matching_length_to_close():
    title_node = MarkdownTitleNode(title="Test", level=1)
    text = """~~~~
~~~
# still inside
~~~~
After"""
    title_node.set_text(text)
    assert (
        len([c for c in title_node.children if isinstance(c, MarkdownTitleNode)]) == 0
    )
    assert title_node.get_text().endswith("After")


def test_markdown_title_node_code_block_closing_fence_at_end_of_text():
    title_node = MarkdownTitleNode(title="Test", level=1)
    title_node.set_text("Some text\n```\ncode\n```")
    assert "code" in title_node.get_text()


def test_markdown_title_node_set_text_with_nested_titles():
    title_node = MarkdownTitleNode(title="Root", level=1)
    text = """Introduction
## Child 1
Content 1
## Child 2
Content 2"""
    title_node.set_text(text)
    assert len(title_node.children) == 3
    assert isinstance(title_node.children[0], PlainTextNode)
    assert isinstance(title_node.children[1], MarkdownTitleNode)
    assert title_node.children[1].title == "Child 1"
    assert isinstance(title_node.children[2], MarkdownTitleNode)
    assert title_node.children[2].title == "Child 2"


def test_markdown_title_node_set_text_deep_hierarchy():
    title_node = MarkdownTitleNode(title="Root", level=1)
    text = """## Section 1
### Subsection 1.1
Content
### Subsection 1.2
## Section 2"""
    title_node.set_text(text)
    assert len(title_node.children) == 2
    assert isinstance(title_node.children[0], MarkdownTitleNode)
    assert title_node.children[0].title == "Section 1"
    assert len(title_node.children[0].children) == 2
    assert isinstance(title_node.children[0].children[0], MarkdownTitleNode)
    assert title_node.children[0].children[0].title == "Subsection 1.1"
    assert isinstance(title_node.children[0].children[1], MarkdownTitleNode)
    assert title_node.children[0].children[1].title == "Subsection 1.2"


def test_markdown_title_node_set_text_keeps_malformed_heading_as_text():
    """残缺的标题行（'#' / '# '）应降级为普通文本，而不是打断整篇解析

    早先检测正则 r"^#{1,6} " 认得 '# ' 是标题，解析正则 r"^(#{1,6}) (.+)$" 又不认，
    两者的分歧让一行坏内容把整篇文档变成不可读。
    """
    text = "# Title\nbody\n\n# \nmore\n"
    title_node = MarkdownTitleNode(title="Root", level=1)

    title_node.set_text(text)

    assert title_node.get_text() == text


def test_markdown_title_node_from_line_still_rejects_malformed_heading():
    """单行解析是显式 API，from_line 仍应严格拒绝残缺标题行"""
    for line in ("#", "# ", "##", "#NoSpace", "   # indented"):
        with pytest.raises(InvalidMarkdownLineError):
            MarkdownTitleNode.from_line(line)


def test_markdown_title_node_empty_heading_does_not_abort_document(caplog):
    """文档中间的一行空标题不应让整篇解析失败，且应告警"""
    text = "# Title\nbody\n\n# \n\n## Sub\nmore\n"

    with caplog.at_level("WARNING"):
        node = MarkdownTitleNode.from_text(text)

    assert node.get_text() == text
    top_level = [
        c.get_title() for c in node.children if isinstance(c, MarkdownTitleNode)
    ]
    assert top_level == ["# Title"]
    nested = [
        c.get_title()
        for c in node.children[0].children
        if isinstance(c, MarkdownTitleNode)
    ]
    assert nested == ["## Sub"]
    assert any("empty title line" in r.message for r in caplog.records)


def test_markdown_title_node_from_line_rejects_level_above_six():
    with pytest.raises(InvalidMarkdownLineError):
        MarkdownTitleNode.from_line("####### too deep")
    with pytest.raises(InvalidMarkdownLineError):
        MarkdownTitleNode.from_line("################ very deep")


def test_markdown_title_node_set_text_level_above_six_is_plain_text():
    title_node = MarkdownTitleNode(title="Root", level=1)
    title_node.set_text("####### too deep\ncontent")
    full_text = title_node.get_text()
    assert "####### too deep" in full_text
    assert isinstance(title_node.children[0], PlainTextNode)


def test_markdown_title_node_set_text_invalid_lower_level():
    title_node = MarkdownTitleNode(title="Root", level=2)
    with pytest.raises(InvalidTitleLevelError):
        title_node.set_text("# Lower level")


def test_markdown_text_node_init():
    test_text_node = MarkdownTitleNode.from_text("# Title\nContent")
    assert len(test_text_node.children) > 0
    assert isinstance(test_text_node.children[0], MarkdownTitleNode)


def test_markdown_text_node_get_text():
    test_text_node = MarkdownTitleNode.from_text("# Title\nSome content")
    text = test_text_node.get_text()
    assert "# Title" in text
    assert "Some content" in text


def test_markdown_text_node_set_text():
    test_text_node = MarkdownTitleNode.from_text("# Old Title")
    test_text_node.set_text("# New Title\nNew content")
    text = test_text_node.get_text()
    assert "# New Title" in text
    assert "New content" in text


def test_markdown_text_node_recursive_find_found():
    test_text_node = MarkdownTitleNode.from_text(
        "# Title1\n## Subtitle1\n# Title2\n## Subtitle2"
    )
    found = test_text_node.recursive_find_title_node_by_name("## Subtitle1")
    assert found is not None
    assert found.title == "Subtitle1"


def test_markdown_text_node_recursive_find_not_found():
    test_text_node = MarkdownTitleNode.from_text("# Title1\n## Subtitle1")
    found = test_text_node.recursive_find_title_node_by_name("## NotExist")
    assert found is None


def test_markdown_text_node_with_code_blocks():
    test_text_node = MarkdownTitleNode.from_text(
        """# Title
```python
def test():
    pass
```
Content"""
    )
    text = test_text_node.get_text()
    assert "```python" in text
    assert "def test():" in text


def test_markdown_text_node_complex_structure():
    test_text_node = MarkdownTitleNode.from_text(
        """# Main Title
Introduction text
## Section 1
Content 1
### Subsection 1.1
Detail 1
## Section 2
Content 2"""
    )
    assert len(test_text_node.children) == 1
    assert isinstance(test_text_node.children[0], MarkdownTitleNode)
    assert test_text_node.children[0].title == "Main Title"
    main_title = test_text_node.children[0]
    assert len(main_title.children) == 3
    assert isinstance(main_title.children[0], PlainTextNode)
    assert isinstance(main_title.children[1], MarkdownTitleNode)
    assert main_title.children[1].title == "Section 1"
    assert isinstance(main_title.children[2], MarkdownTitleNode)
    assert main_title.children[2].title == "Section 2"


def test_markdown_text_file_node_init(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Title\nContent")
    test_file_node = MarkdownTextFileNode(file_path=path)
    assert test_file_node.file_path == path
    assert isinstance(test_file_node.markdown_text_node, MarkdownTitleNode)


def test_markdown_text_file_node_get_text(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Title\nSome content here")
    test_file_node = MarkdownTextFileNode(file_path=path)
    text = test_file_node.get_text()
    assert "# Title" in text
    assert "Some content here" in text


def test_markdown_text_file_node_set_text(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Old")
    test_file_node = MarkdownTextFileNode(file_path=path)
    test_file_node.set_text("# New\nNew content")
    assert "# New" in test_file_node.get_text()
    assert "New content" in test_file_node.get_text()


def test_markdown_text_file_node_save(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Original")
    test_file_node = MarkdownTextFileNode(file_path=path)
    test_file_node.set_text("# Modified\nNew content here")
    test_file_node.save()
    content = path.read_text(encoding="utf-8")
    assert "# Modified" in content
    assert "New content here" in content


def test_markdown_text_file_node_reload(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Original\nOriginal content")
    test_file_node = MarkdownTextFileNode(file_path=path)
    path.write_text("# Reloaded\nReloaded content")
    test_file_node.reload()
    text = test_file_node.get_text()
    assert "# Reloaded" in text
    assert "Reloaded content" in text


def test_markdown_text_file_node_save_to_file(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Title")
    test_file_node = MarkdownTextFileNode(file_path=path)
    test_file_node.set_text("# Test\nContent")
    output_path = tmp_path / "output.md"
    test_file_node.save_to_file(output_path)
    content = output_path.read_text(encoding="utf-8")
    assert "# Test" in content
    assert "Content" in content


def test_markdown_text_file_node_recursive_find(tmp_path: Path):
    path = tmp_path / "test.md"
    path.write_text("# Title1\n## Subtitle1\n# Title2\n## Subtitle2")
    test_file_node = MarkdownTextFileNode(file_path=path)
    found = test_file_node.get_root_title().recursive_find_title_node_by_name(
        "## Subtitle1"
    )
    assert found is not None
    assert found.title == "Subtitle1"


def test_markdown_title_node_code_block_in_nested_title():
    title_node = MarkdownTitleNode(title="Root", level=1)
    text = """## Child 1
```
code
```
## Child 2"""
    title_node.set_text(text)
    assert len(title_node.children) == 2
    assert isinstance(title_node.children[0], MarkdownTitleNode)
    assert title_node.children[0].title == "Child 1"
    assert isinstance(title_node.children[1], MarkdownTitleNode)
    assert title_node.children[1].title == "Child 2"


def test_markdown_title_node_trailing_newline_in_search():
    title_node = MarkdownTitleNode(title="Test", level=1)
    child = MarkdownTitleNode(title="Child", level=2)
    title_node.addchild(child)
    found = title_node.recursive_find_title_node_by_name("## Child\n")
    assert found is not None
    assert found.title == "Child"


def test_markdown_text_node_empty_text():
    test_text_node = MarkdownTitleNode.from_text("")
    assert test_text_node.children == []


def test_markdown_text_node_only_text_no_titles():
    test_text_node = MarkdownTitleNode.from_text("Just some plain text")
    assert len(test_text_node.children) == 1
    assert isinstance(test_text_node.children[0], PlainTextNode)


def test_markdown_title_node_set_text_preserves_structure():
    title_node = MarkdownTitleNode(title="Root", level=1)
    original_text = """## Section 1
Paragraph 1

Paragraph 2
## Section 2
- List item 1
- List item 2"""
    title_node.set_text(original_text)
    result = title_node.get_text()
    assert "Paragraph 1" in result
    assert "Paragraph 2" in result
    assert "List item 1" in result
    assert "List item 2" in result


def test_markdown_text_node_recursive_find_trailing_newline():
    test_text_node = MarkdownTitleNode.from_text(
        "# Title\nContent\n## Subtitle\nMore content"
    )
    found = test_text_node.recursive_find_title_node_by_name("## Subtitle\n")
    assert found is not None
    assert found.title == "Subtitle"


def test_set_text_rebuilds_children_as_new_objects():
    title_node = MarkdownTitleNode(title="Root", level=1)
    title_node.set_text("## Section 1\nContent")
    old_child = title_node.children[0]
    assert len(title_node.children) == 1
    title_node.set_text("## Section 1\nNew content")
    new_child = title_node.children[0]
    assert isinstance(new_child, MarkdownTitleNode)
    assert new_child is not old_child
    assert new_child.title == "Section 1"


@pytest.mark.parametrize("ensure_new_line", [True, False])
def test_add_text_on_empty_node_does_not_raise(ensure_new_line):
    """空节点的 get_text() 为 ""，add_text 取下标字符会 IndexError"""
    node = MarkdownTitleNode(level=0)
    assert node.get_text() == ""

    node.add_text("body", ensure_new_line=ensure_new_line)

    assert node.get_text() == "body"


def test_add_text_with_empty_text_is_a_noop():
    """空文本追加不应改动内容，也不应凭 ensure_new_line 补出行尾换行"""
    node = MarkdownTitleNode.from_text("# 1. A\n")

    node.add_text("")

    assert node.get_text() == "# 1. A\n"


def test_add_text_keeps_separating_newline_for_non_empty_node():
    """非空节点仍应保证追加内容另起一行"""
    node = MarkdownTitleNode.from_text("# 1. A\n")

    node.add_text("body")

    assert node.get_text() == "# 1. A\nbody"


def test_foldable_add_text_on_empty_root_does_not_raise(tmp_path):
    """折叠节点的 add_text 走 full_text，空根节点同样会 IndexError"""
    doc_path = tmp_path / "empty.md"
    doc_path.write_text("", encoding="utf-8")
    doc = FoldableMarkdownTextFileNode(doc_path)
    root = doc.get_root_title()
    assert root.get_text(full_text=True) == ""

    root.add_text("body")

    assert root.get_text(full_text=True) == "body"
