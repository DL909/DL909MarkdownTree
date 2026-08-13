
import pytest
from pydantic import BaseModel

from dl909markdowntree import (
    AttributedMarkdownTextFileNode,
    FoldableMarkdownTitleNode,
    InvalidNumberedTitleLineError,
)


class _TestAttribute(BaseModel):
    """测试用的属性类"""

    author: str = "default_author"
    version: str = "1.0.0"
    tags: list[str] = []


def test_attributed_markdown_text_file_node_init(tmp_path):
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
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    assert test_file_node.file_path == file_path
    assert isinstance(test_file_node.attribute, _TestAttribute)
    assert test_file_node.attribute.author == "test_author"
    assert test_file_node.attribute.version == "2.0.0"
    assert test_file_node.attribute.tags == ["test", "example"]
    assert isinstance(test_file_node.markdown_text_node, FoldableMarkdownTitleNode)
    assert "# 1. Title" in test_file_node.get_text()


def test_attributed_markdown_text_file_node_default_attributes(tmp_path):
    """测试默认属性值"""
    content = """---
author: default_user
---
# 1. Title"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "default_user"
    assert test_file_node.attribute.version == "1.0.0"
    assert test_file_node.attribute.tags == []


def test_attributed_markdown_text_file_node_save_to_file(tmp_path):
    """测试保存到文件"""
    content = """---
author: original
version: 1.0.0
---
# 1. Title
Original content"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    test_file_node.attribute.author = "modified"
    test_file_node.set_text("# 1. Title\nModified content")
    output_path = tmp_path / "output.md"
    test_file_node.save_to_file(output_path)
    saved_content = output_path.read_text(encoding="utf-8")
    assert saved_content.startswith("---\n")
    assert "author: modified" in saved_content
    assert "---\n# 1. Title\nModified content" in saved_content


def test_attributed_markdown_text_file_node_save(tmp_path):
    """测试保存方法"""
    content = """---
author: original
---
# 1. Title
Original content"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    test_file_node.attribute.author = "saved_author"
    test_file_node.set_text("# 1. Title\nSaved content")
    test_file_node.save()
    saved_content = file_path.read_text(encoding="utf-8")
    assert "author: saved_author" in saved_content
    assert "Saved content" in saved_content


def test_attributed_markdown_text_file_node_reload(tmp_path):
    """测试重新加载"""
    content = """---
author: first
version: 1.0.0
---
# 1. Title
First content"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "first"
    file_path.write_text(
        """---
author: second
version: 2.0.0
tags:
  - reloaded
---
# 1. Reloaded Title
Reloaded content""",
        encoding="utf-8",
    )
    test_file_node.reload()
    assert test_file_node.attribute.author == "second"
    assert test_file_node.attribute.version == "2.0.0"
    assert test_file_node.attribute.tags == ["reloaded"]
    assert "# 1. Reloaded Title" in test_file_node.get_text()


def test_attributed_markdown_text_file_node_get_text(tmp_path):
    """测试获取文本"""
    content = """---
author: test
---
# 1. Title
Some text here
## 1.1. Subtitle
More text"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    text = test_file_node.get_text(full_text=True)
    assert "# 1. Title" in text
    assert "Some text here" in text
    assert "## 1.1. Subtitle" in text


def test_attributed_markdown_text_file_node_set_text(tmp_path):
    """测试设置文本"""
    content = """---
author: test
---
# 1. Old Title"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    test_file_node.set_text("# 1. New Title\nNew content\n## 1.1. New Subtitle")
    full_text = test_file_node.get_text(full_text=True)
    assert "# 1. New Title" in full_text
    assert "New content" in full_text
    assert "## 1.1. New Subtitle" in full_text


def test_attributed_markdown_text_file_node_recursive_find(tmp_path):
    """测试递归查找标题节点"""
    content = """---
author: test
---
# 1. Title1
## 1.1. Subtitle1
# 2. Title2
## 2.1. Subtitle2"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    found = test_file_node.get_root_title().recursive_find_title_node_by_name(
        "## 1.1. Subtitle1"
    )
    assert found is not None
    assert found.title == "Subtitle1"
    assert isinstance(found, FoldableMarkdownTitleNode)
    not_found = test_file_node.get_root_title().recursive_find_title_node_by_name(
        "## 3.1. NotExist"
    )
    assert not_found is None


def test_attributed_markdown_text_file_node_with_complex_yaml(tmp_path):
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
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "complex_author"
    assert len(test_file_node.attribute.tags) == 3
    assert "sci-fi" in test_file_node.attribute.tags


def test_attributed_markdown_text_file_node_str_method(tmp_path):
    """测试__str__方法继承"""
    content = """---
author: test
---
# 1. Title
Content"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    str_repr = str(test_file_node)
    assert "# 1. Title" in str_repr


def test_attributed_markdown_text_file_node_markdown_text_node_override(tmp_path):
    """测试 markdown_text_node 参数覆盖"""
    content = """---
author: test
---
# 1. Original Title"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    override_node = FoldableMarkdownTitleNode.from_text(
        "# 1. Overridden Title\nOverride content"
    )
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path,
        attribute_type=_TestAttribute,
        markdown_text_node=override_node,
    )
    full_text = test_file_node.get_text(full_text=True)
    assert "# 1. Overridden Title" in full_text
    assert "Override content" in full_text


def test_attributed_markdown_text_file_node_empty_tags(tmp_path):
    """测试空标签列表"""
    content = """---
author: test
tags: []
---
# 1. Title"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.tags == []


def test_attributed_markdown_text_file_node_unicode_content(tmp_path):
    """测试 Unicode 内容"""
    content = """---
author: 测试作者
version: 1.0.0
---
# 1. 测试标题
这是一些中文内容
🎉 Emoji 测试"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )
    assert test_file_node.attribute.author == "测试作者"
    full_text = test_file_node.get_text(full_text=True)
    assert "这是一些中文内容" in full_text
    assert "🎉" in full_text


def test_attributed_markdown_text_file_node_assertion_invalid_format(tmp_path):
    """测试无效格式的断言"""
    content = """This is not valid YAML frontmatter
# 1. Title"""
    file_path = tmp_path / "invalid.md"
    file_path.write_text(content, encoding="utf-8")
    with pytest.raises(Exception, match="FrontMatter"):
        AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=file_path, attribute_type=_TestAttribute
        )


def test_attributed_markdown_text_file_node_multiple_save_reload_cycles(tmp_path):
    """测试多次保存和重新加载循环"""
    content = """---
author: initial
version: 1.0.0
---
# 1. Title
Initial content"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
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

    def test_attributed_auto_correct_wrong_number(self, tmp_path):
        """测试 AttributedMarkdownTextFileNode 错误编号自动纠正"""
        content = """---
author: test
---
# 1. Title"""
        file_path = tmp_path / "auto_correct.md"
        file_path.write_text(content, encoding="utf-8")
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=file_path, attribute_type=_TestAttribute
        )
        test_file_node.markdown_text_node.auto_correct = True
        test_file_node.set_text("# 5. Wrong\n# 3. Also Wrong")
        assert test_file_node.markdown_text_node.children[0].number == [1]
        assert test_file_node.markdown_text_node.children[1].number == [2]

    def test_attributed_auto_correct_get_text(self, tmp_path):
        """测试自动纠正后 get_text() 输出正确编号"""
        content = """---
author: test
---
# 1. Title"""
        file_path = tmp_path / "auto_correct.md"
        file_path.write_text(content, encoding="utf-8")
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=file_path, attribute_type=_TestAttribute
        )
        test_file_node.markdown_text_node.auto_correct = True
        test_file_node.set_text("# 8. Wrong\n## 9.9. Sub\n# 5. Wrong2")
        output = test_file_node.get_text(full_text=True)
        assert "# 1. Wrong" in output
        assert "## 1.1. Sub" in output
        assert "# 2. Wrong2" in output

    def test_attributed_auto_correct_disabled(self, tmp_path):
        """测试关闭自纠正时保持原有行为"""
        content = """---
author: test
---
# 1. Title"""
        file_path = tmp_path / "auto_correct.md"
        file_path.write_text(content, encoding="utf-8")
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=file_path, attribute_type=_TestAttribute
        )
        test_file_node.markdown_text_node.auto_correct = False
        with pytest.raises(InvalidNumberedTitleLineError):
            test_file_node.set_text("# Wrong Number")

    def test_attributed_auto_correct_default_enabled(self, tmp_path):
        """测试默认自纠正是开启的"""
        content = """---
author: test
---
# 1. Title"""
        file_path = tmp_path / "auto_correct.md"
        file_path.write_text(content, encoding="utf-8")
        test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
            file_path=file_path, attribute_type=_TestAttribute
        )
        assert test_file_node.markdown_text_node.auto_correct is True
        test_file_node.set_text("# 2. Wrong\n# 3. Another")
        assert test_file_node.markdown_text_node.children[0].number == [1]
        assert test_file_node.markdown_text_node.children[1].number == [2]


def test_attributed_markdown_text_file_node_fold(tmp_path):
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
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path, attribute_type=_TestAttribute
    )

    assert "Some content here" not in test_file_node.get_text()
    assert "Some content here" in test_file_node.get_text(full_text=True)


def test_attributed_markdown_text_file_node_attribute_constructor(tmp_path):
    """测试通过 attribute 参数直接传入属性"""
    content = """---
author: test_author
---
# 1. Title"""
    file_path = tmp_path / "attributed.md"
    file_path.write_text(content, encoding="utf-8")
    test_file_node = AttributedMarkdownTextFileNode[_TestAttribute](
        file_path=file_path,
        attribute_type=_TestAttribute,
        attribute=_TestAttribute(author="direct_author", version="9.0.0"),
    )
    assert test_file_node.attribute.author == "direct_author"
    assert test_file_node.attribute.version == "9.0.0"


def test_attributed_markdown_folder_node_missing_frontmatter_fallback(tmp_path):
    """测试缺少 FrontMatter.yaml 时使用属性默认值"""
    from dl909markdowntree.attributed_markdown_folder_nodes import (
        AttributedMarkdownFolderNode,
    )

    folder_path = tmp_path / "attributed_folder"
    folder_path.mkdir(parents=True)
    (folder_path / "1_Section.mdp").write_text(
        "## 1.1. Sub\nContent", encoding="utf-8"
    )
    node = AttributedMarkdownFolderNode[_TestAttribute](
        file_path=folder_path, attribute_type=_TestAttribute
    )
    assert isinstance(node.attribute, _TestAttribute)
    assert node.attribute.author == "default_author"