from pathlib import Path

import pytest

from dl909agentframework.tree_doc.markdown_nodes import (
    MarkdownTextNode,
    MarkdownTitleNode,
    MarkdownTextFileNode,
)
from dl909agentframework.tree_doc.plain_text_file_node import PlainTextNode


def test_markdown_title_node_init():
    title_node = MarkdownTitleNode(title="Test Title", level=1)
    assert title_node.title == "Test Title"
    assert title_node.level == 1
    assert title_node.children == []


def test_markdown_title_node_init_with_text():
    title_node = MarkdownTitleNode(title="Test", level=2, text="Some content")
    assert title_node.title == "Test"
    assert title_node.level == 2
    assert len(title_node.children) > 0
    assert isinstance(title_node.children[0], PlainTextNode)


def test_markdown_title_node_get_title():
    title_node = MarkdownTitleNode(title="Test", level=3)
    assert title_node.get_title() == "### Test"
    assert title_node.get_title(show_level_sign=False) == "Test"


def test_markdown_title_node_all_children_are_titles_empty():
    title_node = MarkdownTitleNode(title="Test", level=1)
    assert title_node.all_children_are_titles()


def test_markdown_title_node_all_children_are_titles_with_text():
    title_node = MarkdownTitleNode(title="Test", level=1)
    title_node.addchild(PlainTextNode("some text"))
    assert not title_node.all_children_are_titles()


def test_markdown_title_node_all_children_are_titles_with_titles():
    title_node = MarkdownTitleNode(title="Test", level=1)
    child_title = MarkdownTitleNode(title="Child", level=2)
    title_node.addchild(child_title)
    assert title_node.all_children_are_titles()


def test_markdown_title_node_get_text():
    title_node = MarkdownTitleNode(title="Test", level=2, text="Content here")
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


def test_markdown_title_node_set_text_invalid_empty_title():
    title_node = MarkdownTitleNode(title="Root", level=1)
    with pytest.raises(Exception) as exc_info:
        title_node.set_text("#")
    assert "无内容的标题" in str(exc_info.value)


def test_markdown_title_node_set_text_invalid_lower_level():
    title_node = MarkdownTitleNode(title="Root", level=2)
    with pytest.raises(Exception) as exc_info:
        title_node.set_text("# Lower level")
    assert "过低等级的标题" in str(exc_info.value)


def test_markdown_title_node_child_title_number():
    title_node = MarkdownTitleNode(title="Root", level=1)
    assert title_node._child_title_number() == 0
    title_node.addchild(MarkdownTitleNode(title="Child 1", level=2))
    title_node.addchild(MarkdownTitleNode(title="Child 2", level=2))
    title_node.addchild(PlainTextNode("text"))
    assert title_node._child_title_number() == 2


def test_markdown_title_node_have_text():
    title_node = MarkdownTitleNode(title="Root", level=1)
    assert not title_node._have_text()
    title_node.addchild(PlainTextNode("some text"))
    assert title_node._have_text()


def test_markdown_text_node_init():
    test_text_node = MarkdownTextNode(text="# Title\nContent")
    assert len(test_text_node.children) > 0
    assert isinstance(test_text_node.children[0], MarkdownTitleNode)


def test_markdown_text_node_get_text():
    test_text_node = MarkdownTextNode(text="# Title\nSome content")
    text = test_text_node.get_text()
    assert "# Title" in text
    assert "Some content" in text


def test_markdown_text_node_set_text():
    test_text_node = MarkdownTextNode(text="# Old Title")
    test_text_node.set_text("# New Title\nNew content")
    text = test_text_node.get_text()
    assert "# New Title" in text
    assert "New content" in text


def test_markdown_text_node_all_children_are_titles():
    test_text_node = MarkdownTextNode(text="# Title 1\n## Title 2")
    assert test_text_node.all_children_are_titles()
    assert isinstance(test_text_node.children[0], MarkdownTitleNode)
    assert test_text_node.children[0].all_children_are_titles()
    assert isinstance(test_text_node.children[0].children[0], MarkdownTitleNode)
    test_text_node.children[0].children[0].addchild(PlainTextNode("content"))
    assert not test_text_node.children[0].children[0].all_children_are_titles()


def test_markdown_text_node_recursive_find_found():
    test_text_node = MarkdownTextNode(
        text="# Title1\n## Subtitle1\n# Title2\n## Subtitle2"
    )
    found = test_text_node.recursive_find_title_node_by_name("## Subtitle1")
    assert found is not None
    assert found.title == "Subtitle1"


def test_markdown_text_node_recursive_find_not_found():
    test_text_node = MarkdownTextNode(text="# Title1\n## Subtitle1")
    found = test_text_node.recursive_find_title_node_by_name("## NotExist")
    assert found is None


def test_markdown_text_node_with_code_blocks():
    test_text_node = MarkdownTextNode(
        text="""# Title
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
    test_text_node = MarkdownTextNode(
        text="""# Main Title
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


def test_markdown_text_file_node_init(fs):
    fs.create_file("/tmp/test.md", contents="# Title\nContent")
    test_file_node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    assert test_file_node.file_path == Path("/tmp/test.md")
    assert isinstance(test_file_node.markdown_text_node, MarkdownTextNode)


def test_markdown_text_file_node_get_text(fs):
    fs.create_file("/tmp/test.md", contents="# Title\nSome content here")
    test_file_node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    text = test_file_node.get_text()
    assert "# Title" in text
    assert "Some content here" in text


def test_markdown_text_file_node_set_text(fs):
    fs.create_file("/tmp/test.md", contents="# Old")
    test_file_node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    test_file_node.set_text("# New\nNew content")
    assert "# New" in test_file_node.get_text()
    assert "New content" in test_file_node.get_text()


def test_markdown_text_file_node_save(fs):
    fs.create_file("/tmp/test.md", contents="# Original")
    test_file_node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    test_file_node.set_text("# Modified\nNew content here")
    test_file_node.save()
    with open("/tmp/test.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert "# Modified" in content
    assert "New content here" in content


def test_markdown_text_file_node_reload(fs):
    fs.create_file("/tmp/test.md", contents="# Original\nOriginal content")
    test_file_node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    fs.remove("/tmp/test.md")
    fs.create_file("/tmp/test.md", contents="# Reloaded\nReloaded content")
    test_file_node.reload()
    text = test_file_node.get_text()
    assert "# Reloaded" in text
    assert "Reloaded content" in text


def test_markdown_text_file_node_save_to_file(fs):
    fs.create_file("/tmp/test.md", contents="# Title")
    test_file_node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    test_file_node.set_text("# Test\nContent")
    output_path = Path("/tmp/output.md")
    test_file_node.save_to_file(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "# Test" in content
    assert "Content" in content


def test_markdown_text_file_node_recursive_find(fs):
    fs.create_file(
        "/tmp/test.md",
        contents="# Title1\n## Subtitle1\n# Title2\n## Subtitle2",
    )
    test_file_node = MarkdownTextFileNode(file_path=Path("/tmp/test.md"))
    found = test_file_node.recursive_find_title_node_by_name("## Subtitle1")
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
    test_text_node = MarkdownTextNode(text="")
    assert test_text_node.children == []


def test_markdown_text_node_only_text_no_titles():
    test_text_node = MarkdownTextNode(text="Just some plain text")
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
