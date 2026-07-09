#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
markdown_edit_tools.py - Markdown 文档编辑工具集

提供用于编辑 Markdown 文档的工具：replace, append, unfold, read
"""

from __future__ import annotations

from difflib import SequenceMatcher
import logging
from typing import Sequence, TypeVar

from pydantic import BaseModel, Field

from dl909agentframework.llm.tools.registry import tool
from dl909agentframework.llm.tools.permissions import Permission
from dl909agentframework.tree_doc.node import Node
from dl909agentframework.tree_doc.protocols import AttributedMarkdownTextFileProtocol

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class ReadArguments(BaseModel):
    """read 工具的参数模型"""

    target: str | None = Field(
        None,
        description="目标 Markdown 标题，包括序号和前置井号。不传入则读取整个文档。",
    )


@tool(param_model=ReadArguments, required_permission=Permission.READ)
def read(
    markdown_file_node: AttributedMarkdownTextFileProtocol[T], arguments: ReadArguments
) -> str:
    """读取文档内容

    如果 arguments.target 为 None，读取整个文档（根节点）。
    否则读取指定标题的内容。
    """
    if arguments.target:
        target_node = markdown_file_node.recursive_find_title_node_by_name(
            arguments.target
        )
        if target_node is None:
            return f"read 工具调用失败：没有与{arguments.target}匹配的标题"
        return target_node.get_text(full_text=True)
    else:
        return markdown_file_node.get_text(full_text=False)


class ReplaceArguments(BaseModel):
    """replace 工具的参数模型"""

    target: str = Field(
        ...,
        description="目标 Markdown 标题，包括序号和前置井号，例如：'### 1.2.2 特殊力量/魔法科技体系'。",
    )
    replace_text: str = Field(
        ...,
        description="用于替换的文本，用于替换 Markdown 文档某个标题的内容。"
        "能且只能包含一个与 target 确定的标题同级的 Markdown 在第一行，用于替换原 Markdown 标题，否则将使用原本的标题。"
        "可以包含任意多的比 target 低级（更多井号）的标题。",
    )


@tool(param_model=ReplaceArguments, required_permission=Permission.READ_WRITE)
def replace(
    markdown_file_node: AttributedMarkdownTextFileProtocol[T],
    arguments: ReplaceArguments,
) -> str:
    """用于替换 Markdown 文档某个标题的内容（包括其从属的所有子标题和项目）"""
    target_title_name: str = arguments.target
    target_markdown_title_node = markdown_file_node.recursive_find_title_node_by_name(
        target_title_name
    )
    if target_markdown_title_node is None:
        return f"replace 工具调用失败：没有与{target_title_name}匹配的标题"
    try:
        target_markdown_title_node.set_text(arguments.replace_text)
        return "replace 工具调用成功"
    except Exception as e:
        return f"replace 工具调用失败：{e}"


class ReplaceLinesArguments(BaseModel):
    """replace_lines 工具的参数模型"""

    target: str = Field(
        ...,
        description="目标 Markdown 标题，包括序号和前置井号，例如：'### 5.1.1.1. 第 1 章 正文'。",
    )
    old_lines: str = Field(
        ...,
        description="需要被替换的原始多行文本。必须严格匹配（包括空格和缩进）。",
    )
    new_lines: str = Field(
        ...,
        description="用于替换的新多行文本。",
    )


@tool(param_model=ReplaceLinesArguments, required_permission=Permission.READ_WRITE)
def replace_lines(
    markdown_file_node: AttributedMarkdownTextFileProtocol[T],
    arguments: ReplaceLinesArguments,
) -> str:
    """在指定标题下精确替换特定的多行文本（支持模糊匹配）"""
    target_title_name: str = arguments.target
    old_lines: str = arguments.old_lines
    new_lines: str = arguments.new_lines

    target_markdown_title_node = markdown_file_node.recursive_find_title_node_by_name(
        target_title_name
    )
    if target_markdown_title_node is None:
        return f"replace_lines 工具调用失败：没有与{target_title_name}匹配的标题"

    try:
        current_text = target_markdown_title_node.get_text()
    except Exception as e:
        return f"replace_lines 工具调用失败：读取内容时出错 - {e}"

    match_count = current_text.count(old_lines)

    if match_count == 0:
        best_match_ratio = 0.0
        best_match_start = -1
        best_match_end = -1

        current_lines_list = current_text.splitlines(keepends=True)
        old_lines_list = old_lines.splitlines(keepends=True)
        old_line_count = len(old_lines_list)

        if old_line_count == 0:
            return "replace_lines 工具调用失败：old_lines 为空"

        for i in range(len(current_lines_list) - old_line_count + 1):
            candidate = "".join(current_lines_list[i : i + old_line_count])
            ratio = SequenceMatcher(None, old_lines, candidate).ratio()
            if ratio > best_match_ratio:
                best_match_ratio = ratio
                best_match_start = i
                best_match_end = i + old_line_count

        if best_match_ratio >= 0.8:
            matched_text = "".join(current_lines_list[best_match_start:best_match_end])
            try:
                new_text = current_text.replace(matched_text, new_lines, 1)
                target_markdown_title_node.set_text(new_text)
                return "replace_lines 工具调用成功（使用模糊匹配）"
            except Exception as e:
                return f"replace_lines 工具调用失败：替换时出错 - {e}"
        else:
            return "replace_lines 工具调用失败：未找到匹配的文本。请检查 old_lines 是否完全匹配（包括空格、单双引号和缩进）。"
    elif match_count > 1:
        return f"replace_lines 工具调用失败：找到{match_count}处匹配。请提供更精确的上下文（前后各多几行）以唯一确定位置。"

    try:
        new_text = current_text.replace(old_lines, new_lines, 1)
        target_markdown_title_node.set_text(new_text)
        return "replace_lines 工具调用成功"
    except Exception as e:
        return f"replace_lines 工具调用失败：替换时出错 - {e}"


class AppendArguments(BaseModel):
    """append 工具的参数模型"""

    target: str = Field(
        ...,
        description="目标 Markdown 标题，包括序号和前置井号，例如：'### 1.2.2 特殊力量/魔法科技体系'。",
    )
    append_text: str = Field(
        ...,
        description="用于补充的文本，将附加在 target 指定的标题的所有内容"
        "（从属的文字和递归的所有从属其的子标题及从属这些子标题的文字）。"
        "不得包含与 target 同级或更高级（同等数量或更少井号）的标题，"
        "可以包含任意多的比 target 低级（更多井号）的标题。",
    )


@tool(param_model=AppendArguments, required_permission=Permission.READ_WRITE)
def append(
    markdown_file_node: AttributedMarkdownTextFileProtocol[T],
    arguments: AppendArguments,
) -> str:
    """用于补充 Markdown 文档某个标题的内容"""
    target_title_name: str = arguments.target
    target_markdown_title_node = markdown_file_node.recursive_find_title_node_by_name(
        target_title_name
    )
    if target_markdown_title_node is None:
        return f"append 工具调用失败：没有与{target_title_name}匹配的标题"
    try:
        target_markdown_title_node.add_text(arguments.append_text)
        return "append 工具调用成功"
    except Exception as e:
        return f"append 工具调用失败：{e}"


class UnfoldArguments(BaseModel):
    """unfold 工具的参数模型"""

    target: str = Field(
        ...,
        description="目标 Markdown 标题，包括序号和前置井号，例如：'### 1.2.2 特殊力量/魔法科技体系'。",
    )


@tool(param_model=UnfoldArguments, required_permission=Permission.READ)
def unfold(
    markdown_file_node: AttributedMarkdownTextFileProtocol[T],
    arguments: UnfoldArguments,
) -> str:
    """展开一个折叠的 Markdown 文档标题，查看其折叠的内容，之后该标题保持在展开状态。"""
    target_title_name: str = arguments.target
    target_markdown_title_node = markdown_file_node.recursive_find_title_node_by_name(
        target_title_name
    )
    if target_markdown_title_node is None:
        return f"unfold 工具调用失败：没有与{target_title_name}匹配的标题"
    else:
        try:
            return_content = target_markdown_title_node.unfold()
        except Exception as e:
            return f"unfold 工具调用失败：{e}"
    return f"unfold 工具调用成功，展开内容如下：\n{return_content}"


class RenameTitleArguments(BaseModel):
    """append 工具的参数模型"""

    target: str = Field(
        ...,
        description="目标 Markdown 标题，包括序号和前置井号，例如：'### 1.2.2 特殊力量/魔法科技体系'。",
    )
    new_title_name: str = Field(
        ...,
        description="重命名标题，不包括序号和前置井号，例如：'特殊力量/魔法科技体系'。",
    )


@tool(param_model=RenameTitleArguments, required_permission=Permission.READ_WRITE)
def rename_title(
    markdown_file_node: AttributedMarkdownTextFileProtocol[T],
    arguments: RenameTitleArguments,
) -> str:
    """重命名一个Markdown文档标题"""
    target_title_name: str = arguments.target
    target_markdown_title_node = markdown_file_node.recursive_find_title_node_by_name(
        target_title_name
    )
    if target_markdown_title_node is None:
        return f"rename_title 工具调用失败：没有与{target_title_name}匹配的标题"
    try:
        target_markdown_title_node.title = arguments.new_title_name
    except Exception as e:
        return f"rename_title 工具调用失败：{e}"
    return "rename_title 工具调用成功。"


def create_markdown_edit_tools_registry(
    allow_replace: bool = True,
    allow_append: bool = True,
    allow_unfold: bool = True,
    allow_read: bool = True,
    allow_replace_lines: bool = True,
    allow_rename_title: bool = True,
    permissions: Sequence[tuple[Node | None, Permission]] | None = None,
):
    """创建包含所有 Markdown 编辑工具的注册表

    Args:
        permissions: 权限列表，如果提供则创建 PermissionToolRegistry
    """
    from dl909agentframework.llm.tools.registry import (
        PermissionToolRegistry,
        ToolRegistry,
    )

    if permissions:
        registry = PermissionToolRegistry(permissions)
    else:
        registry = ToolRegistry()

    if allow_replace:
        registry.register(replace)
    if allow_append:
        registry.register(append)
    if allow_unfold:
        registry.register(unfold)
    if allow_read:
        registry.register(read)
    if allow_replace_lines:
        registry.register(replace_lines)
    if allow_rename_title:
        registry.register(rename_title)

    return registry


__all__ = [
    "replace",
    "append",
    "unfold",
    "read",
    "replace_lines",
    "ReplaceArguments",
    "AppendArguments",
    "UnfoldArguments",
    "ReplaceLinesArguments",
    "ReadArguments",
    "create_markdown_edit_tools_registry",
]
