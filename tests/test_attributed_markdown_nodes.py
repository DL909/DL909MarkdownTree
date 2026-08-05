from pathlib import Path

import pytest
from pydantic import BaseModel

from dl909markdowntree.attributed_markdown_nodes import (
    AttributedMarkdownTextFileNode,
)
from dl909markdowntree.foldable_markdown_nodes import (
    FoldableMarkdownTextNode,
    FoldableMarkdownTitleNode,
)


class _TestAttribute(BaseModel):
    """测试用的属性类"""

    author: str = "default_author"
    version: str = "1.0.0"
    tags: list[str] = []


def test_attributed_markdown_text_file_node_init(fs):
    """测试基本初始化"""
    content = """---
author: test_author
version: 2.0.0
tags:
  - test
  - example
---
# 1. Title
Some content here"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    assert test_file_node.file_path == Path("/tmp/attributed.md")
    assert isinstance(test_file_node.attribute, _TestAttribute)
    assert test_file_node.attribute.author == "test_author"
    assert test_file_node.attribute.version == "2.0.0"
    assert test_file_node.attribute.tags == ["test", "example"]
    assert isinstance(test_file_node.markdown_text_node, FoldableMarkdownTextNode)
    assert "# 1. Title" in test_file_node.get_text()


def test_attributed_markdown_text_file_node_default_attributes(fs):
    """测试默认属性值"""
    content = """---
author: default_user
---
# 1. Title"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "default_user"
    assert test_file_node.attribute.version == "1.0.0"
    assert test_file_node.attribute.tags == []


def test_attributed_markdown_text_file_node_save_to_file(fs):
    """测试保存到文件"""
    content = """---
author: original
version: 1.0.0
---
# 1. Title
Original content"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    test_file_node.attribute.author = "modified"
    test_file_node.set_text("# 1. Title\nModified content")
    output_path = Path("/tmp/output.md")
    test_file_node.save_to_file(output_path)
    with open(output_path, "r", encoding="utf-8") as f:
        saved_content = f.read()
    assert saved_content.startswith("---\n")
    assert "author: modified" in saved_content
    assert "---\n# 1. Title\n\nModified content" in saved_content


def test_attributed_markdown_text_file_node_save(fs):
    """测试保存方法"""
    content = """---
author: original
---
# 1. Title
Original content"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    test_file_node.attribute.author = "saved_author"
    test_file_node.set_text("# 1. Title\nSaved content")
    test_file_node.save()
    with open("/tmp/attributed.md", "r", encoding="utf-8") as f:
        saved_content = f.read()
    assert "author: saved_author" in saved_content
    assert "Saved content" in saved_content


def test_attributed_markdown_text_file_node_reload(fs):
    """测试重新加载"""
    content = """---
author: first
version: 1.0.0
---
# 1. Title
First content"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "first"
    fs.remove("/tmp/attributed.md")
    fs.create_file(
        "/tmp/attributed.md",
        contents="""---
author: second
version: 2.0.0
tags:
  - reloaded
---
# 1. Reloaded Title
Reloaded content""",
    )
    test_file_node.reload()
    assert test_file_node.attribute.author == "second"
    assert test_file_node.attribute.version == "2.0.0"
    assert test_file_node.attribute.tags == ["reloaded"]
    assert "# 1. Reloaded Title" in test_file_node.get_text()


def test_attributed_markdown_text_file_node_get_text(fs):
    """测试获取文本"""
    content = """---
author: test
---
# 1. Title
Some text here
## 1.1. Subtitle
More text"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    text = test_file_node.get_text(full_text=True)
    assert "# 1. Title" in text
    assert "Some text here" in text
    assert "## 1.1. Subtitle" in text


def test_attributed_markdown_text_file_node_set_text(fs):
    """测试设置文本"""
    content = """---
author: test
---
# 1. Old Title"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    test_file_node.set_text("# 1. New Title\nNew content\n## 1.1. New Subtitle")
    assert "# 1. New Title" in test_file_node.get_text(full_text=True)
    assert "New content" in test_file_node.get_text(full_text=True)
    assert "## 1.1. New Subtitle" in test_file_node.get_text(full_text=True)


def test_attributed_markdown_text_file_node_recursive_find(fs):
    """测试递归查找标题节点"""
    content = """---
author: test
---
# 1. Title1
## 1.1. Subtitle1
# 2. Title2
## 2.1. Subtitle2"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    found = test_file_node.recursive_find_title_node_by_name("## 1.1. Subtitle1")
    assert found is not None
    assert found.title == "Subtitle1"
    assert isinstance(found, FoldableMarkdownTitleNode)
    not_found = test_file_node.recursive_find_title_node_by_name("## 3.1. NotExist")
    assert not_found is None


def test_attributed_markdown_text_file_node_with_complex_yaml(fs):
    """测试复杂 YAML 属性"""
    content = """---
author: complex_author
version: 3.5.0
tags:
  - fiction
  - sci-fi
  - adventure
metadata:
  created: 2024-01-01
  modified: 2024-01-02
---
# 1. Complex Title"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "complex_author"
    assert len(test_file_node.attribute.tags) == 3
    assert "sci-fi" in test_file_node.attribute.tags


def test_attributed_markdown_text_file_node_str_method(fs):
    """测试__str__方法继承"""
    content = """---
author: test
---
# 1. Title
Content"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    str_repr = str(test_file_node)
    assert "# 1. Title" in str_repr


def test_attributed_markdown_text_file_node_markdown_text_node_override(fs):
    """测试 markdown_text_node 参数覆盖"""
    content = """---
author: test
---
# 1. Original Title"""
    fs.create_file("/tmp/attributed.md", contents=content)
    override_node = FoldableMarkdownTextNode(
        text="# 1. Overridden Title\nOverride content"
    )
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"),
        attribute_type=_TestAttribute,
        markdown_text_node=override_node,
    )
    assert "# 1. Overridden Title" in test_file_node.get_text(full_text=True)
    assert "Override content" in test_file_node.get_text(full_text=True)


def test_attributed_markdown_text_file_node_empty_tags(fs):
    """测试空标签列表"""
    content = """---
author: test
tags: []
---
# 1. Title"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.tags == []


def test_attributed_markdown_text_file_node_unicode_content(fs):
    """测试 Unicode 内容"""
    content = """---
author: 测试作者
version: 1.0.0
---
# 1. 测试标题
这是一些中文内容
🎉 Emoji 测试"""
    fs.create_file("/tmp/attributed.md", contents=content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "测试作者"
    assert "这是一些中文内容" in test_file_node.get_text(full_text=True)
    assert "🎉" in test_file_node.get_text(full_text=True)


def test_attributed_markdown_text_file_node_assertion_invalid_format(fs):
    """测试无效格式的断言"""
    content = """This is not valid YAML frontmatter
# 1. Title"""
    fs.create_file("/tmp/invalid.md", contents=content)
    with pytest.raises(AssertionError):
        AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=Path("/tmp/invalid.md"), attribute_type=_TestAttribute
        )


def test_attributed_markdown_text_file_node_multiple_save_reload_cycles(fs):
    """测试多次保存和重新加载循环"""
    content = """---
author: initial
version: 1.0.0
---
# 1. Title
Initial content"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )
    for i in range(3):
        test_file_node.attribute.version = f"{i + 2}.0.0"
        test_file_node.set_text(
            test_file_node.get_text(full_text=True)
            + "\n"
            + f"# {i + 2}. Title\nVersion {i + 2} content"
        )
        test_file_node.save()
        test_file_node.reload()
        assert test_file_node.attribute.version == f"{i + 2}.0.0"
        assert f"# {i + 2}. Title" in test_file_node.get_text()


class TestAttributedMarkdownAutoCorrect:
    """AttributedMarkdown 自纠正模式测试"""

    def test_attributed_auto_correct_missing_number(self, fs):
        """测试 AttributedMarkdownTextFileNode 无编号自动纠正"""
        content = """---
author: test
version: 1.0.0
---
# 1. Title"""
        fs.create_file("/tmp/auto_correct.md", contents=content)
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=Path("/tmp/auto_correct.md"), attribute_type=_TestAttribute
        )
        test_file_node.markdown_text_node.auto_correct = True
        test_file_node.set_text("# New Title\nContent\n## Subtitle")
        assert test_file_node.markdown_text_node.children[0].number == [1]
        assert test_file_node.markdown_text_node.children[0].children[1].number == [
            1,
            1,
        ]

    def test_attributed_auto_correct_wrong_number(self, fs):
        """测试 AttributedMarkdownTextFileNode 错误编号自动纠正"""
        content = """---
author: test
---
# 1. Title"""
        fs.create_file("/tmp/auto_correct.md", contents=content)
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=Path("/tmp/auto_correct.md"), attribute_type=_TestAttribute
        )
        test_file_node.markdown_text_node.auto_correct = True
        test_file_node.set_text("# 5. Wrong\n# 3. Also Wrong")
        assert test_file_node.markdown_text_node.children[0].number == [1]
        assert test_file_node.markdown_text_node.children[1].number == [2]

    def test_attributed_auto_correct_get_text(self, fs):
        """测试自动纠正后 get_text() 输出正确编号"""
        content = """---
author: test
---
# 1. Title"""
        fs.create_file("/tmp/auto_correct.md", contents=content)
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=Path("/tmp/auto_correct.md"), attribute_type=_TestAttribute
        )
        test_file_node.markdown_text_node.auto_correct = True
        test_file_node.set_text("# Wrong\n## Sub\n# 5. Wrong2")
        output = test_file_node.get_text(full_text=True)
        assert "# 1. Wrong" in output
        assert "## 1.1. Sub" in output
        assert "# 2. Wrong2" in output

    def test_attributed_auto_correct_disabled(self, fs):
        """测试关闭自纠正时保持原有行为"""
        content = """---
author: test
---
# 1. Title"""
        fs.create_file("/tmp/auto_correct.md", contents=content)
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=Path("/tmp/auto_correct.md"), attribute_type=_TestAttribute
        )
        test_file_node.markdown_text_node.auto_correct = False
        with pytest.raises(Exception, match="编号标题解析失败"):
            test_file_node.set_text("# Wrong Number")

    def test_attributed_auto_correct_default_enabled(self, fs):
        """测试默认自纠正是开启的"""
        content = """---
author: test
---
# 1. Title"""
        fs.create_file("/tmp/auto_correct.md", contents=content)
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=Path("/tmp/auto_correct.md"), attribute_type=_TestAttribute
        )
        assert test_file_node.markdown_text_node.auto_correct is True
        test_file_node.set_text("# 2. Wrong\n# 3. Another")
        assert test_file_node.markdown_text_node.children[0].number == [1]
        assert test_file_node.markdown_text_node.children[1].number == [2]


def test_attributed_markdown_text_file_node_fold(fs):
    """测试折叠"""
    content = """---
author: test_author
version: 2.0.0
tags:
  - test
  - example
---
# 1. Title
Some content here"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"), attribute_type=_TestAttribute
    )

    assert "Some content here" not in test_file_node.get_text()
    assert "Some content here" in test_file_node.get_text(full_text=True)


def test_attributed_markdown_text_file_node_attribute_constructor(fs):
    """测试通过 attribute 参数直接传入属性"""
    content = """---
author: test_author
---
# 1. Title"""
    fs.create_file("/tmp/attributed.md", contents=content)
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=Path("/tmp/attributed.md"),
        attribute_type=_TestAttribute,
        attribute=_TestAttribute(author="direct_author", version="9.0.0"),
    )
    assert test_file_node.attribute.author == "direct_author"
    assert test_file_node.attribute.version == "9.0.0"


def test_attributed_markdown_folder_node_missing_frontmatter_fallback(fs):
    """测试缺少 FrontMatter.yaml 时使用属性默认值"""
    from dl909markdowntree.attributed_markdown_folder_nodes import (
        AttributedMarkdownFolderNode,
    )

    folder_path = Path("/tmp/attributed_folder")
    folder_path.mkdir(parents=True)
    (folder_path / "1_Section.mdp").write_text("## 1.1. Sub\nContent", encoding="utf-8")
    node = AttributedMarkdownFolderNode[_TestAttribute](
        file_path=folder_path, attribute_type=_TestAttribute
    )
    assert isinstance(node.attribute, _TestAttribute)
    assert node.attribute.author == "default_author"


def test_markdown_parser_core_parse_code_block_start_boundary():
    """测试 _parse_code_block_start 边界：多单词视为普通文本"""
    from dl909markdowntree.markdown_parser_core import _MarkdownParserCore

    core = _MarkdownParserCore()
    assert core._parse_code_block_start("```") is True
    assert core._parse_code_block_start("```python") is True
    assert core._parse_code_block_start("```python hello") is False
    assert core._parse_code_block_start("``` ") is False
