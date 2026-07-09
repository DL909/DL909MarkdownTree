"""markdown_parser_core.py - Markdown 解析器核心 Mixin 基类"""

from typing import Any

from .plain_text_file_node import PlainTextNode


class _MarkdownParserCore:
    """
    Markdown 解析器核心 Mixin 基类

    提供细粒度的钩子方法用于解析 Markdown 文本。子类通过重写钩子方法
    来定制解析行为，而无需重复主循环逻辑。

    解析流程:
    1. _get_root_level() - 获取根节点级别
    2. _process_first_line_if_needed() - 处理首行（如果需要）
    3. 遍历每一行:
       - _is_code_block_boundary() - 检测代码块边界
       - _handle_code_block_line() - 处理代码块内的行
       - _is_title_line() - 检测标题行
       - _parse_title_line() - 解析标题行（子类重写）
       - _validate_title_level() - 验证标题级别
       - _create_title_node() - 创建标题节点（子类重写）
       - _handle_text_line() - 处理普通文本行
    4. _flush_cached_text() - 提交缓存文本

    注意：本 Mixin 依赖子类提供 `children: list` 和 `addchild()` 方法
    """

    def _get_root_level(self) -> int:
        """
        获取根节点的标题级别

        MarkdownTitleNode: 返回 self.level
        MarkdownTextNode: 返回 0
        """
        raise NotImplementedError()

    def _get_root_title(self) -> str | None:
        """
        获取根节点的标题文本（如果有）

        MarkdownTitleNode: 返回 self.title
        MarkdownTextNode: 返回 None
        """
        return None

    def _should_consume_first_line(self) -> bool:
        """
        是否需要在解析前消费第一行（作为自身标题）

        MarkdownTitleNode: True
        MarkdownTextNode: False
        """
        return False

    def _process_first_line_if_needed(self, first_line: str) -> None:
        """
        处理第一行（如果需要）

        MarkdownTitleNode: 提取标题文本
        MarkdownTextNode: 无操作
        """
        pass

    def _is_code_block_boundary(self, line: str) -> bool:
        """检测行是否为代码块边界（```）"""
        return line.startswith("```")

    def _parse_code_block_start(self, line: str) -> bool:
        """
        解析代码块开始行，返回是否确实是代码块

        规则：``` 后可以跟一个单词（语言标识），多个单词则视为普通文本
        """
        index = 3
        if len(line) == 3:
            return True
        while index < len(line) and line[index] != " ":
            index += 1
        return len(line) == index

    def _is_title_line(self, line: str) -> bool:
        """检测行是否为标题行（以 # 开头）"""
        return line.startswith("#")

    def _parse_title_line(self, line: str) -> tuple[int, list[int] | None, str]:
        """
        解析标题行

        Returns:
            (level, number_list, title_text)
            - level: 标题级别（# 的数量）
            - number_list: 编号列表（编号标题）或 None（普通标题）
            - title_text: 标题文本

        MarkdownTitleNode: 解析 "# Title" → (1, None, "Title")
        NumberedMarkdownTitleNode: 解析 "# 1.2.3 Title" → (1, [1, 2, 3], "Title")
        """
        index = 1
        while index < len(line) and line[index] == "#":
            index += 1
        level = index

        if len(line) <= index or len(line) <= index + 1:
            raise Exception(f"无内容的标题：{line}")

        title_text = line[index + 1 :]
        return (level, None, title_text)

    def _validate_title_level(self, title_level: int) -> None:
        """
        验证标题级别是否合法

        MarkdownTitleNode: title_level > self.level
        MarkdownTextNode: 始终合法（title_level >= 1）
        """
        root_level = self._get_root_level()
        if title_level <= root_level:
            raise Exception(f"过低等级的标题：{title_level} <= {root_level}")

    def _create_title_node(self, level: int, number: list[int] | None, title: str):
        """
        创建标题节点实例

        MarkdownTitleNode: 返回 MarkdownTitleNode
        NumberedMarkdownTitleNode: 返回 NumberedMarkdownTitleNode
        FoldableMarkdownTitleNode: 返回 FoldableMarkdownTitleNode
        """
        raise NotImplementedError()

    def _validate_title_number(
        self,
        level: int,
        number: list[int] | None,
        titles: list[Any],
        line_index: int,
        full_text: str,
    ) -> list[int]:
        """
        验证并计算正确的标题编号

        基类默认实现：返回传入的 number（普通标题不需要验证）
        编号标题子类：根据上一个同级标题推导正确的编号并验证

        Args:
            level: 标题级别
            number: 解析得到的编号
            titles: 各级别最后标题的追踪数组
            line_index: 当前行索引
            full_text: 完整文本

        Returns:
            正确的编号列表

        Raises:
            Exception: 当编号不正确时
        """
        if number is None:
            return []
        return number

    def _add_title_to_hierarchy(
        self,
        new_title,
        level: int,
        titles: list[Any],
        last_title,
    ) -> tuple[list[Any], Any]:
        """
        将新标题添加到层级结构中

        Args:
            new_title: 新创建的标题节点
            level: 标题级别
            titles: 各级别最后标题的追踪数组
            last_title: 上一个标题节点

        Returns:
            (updated_titles, updated_last_title)
        """
        for i in range(level - 1, -1, -1):
            if titles[i] is not None:
                titles[i].addchild(new_title)
                titles[level] = new_title
                return (titles, new_title)
        return (titles, last_title)

    def _flush_cached_text(
        self, cached_text: str, last_title, clear_cache: bool = True
    ) -> str:
        """
        提交缓存的文本到最后一个标题节点

        Args:
            cached_text: 缓存的文本
            last_title: 最后一个标题节点
            clear_cache: 是否清空缓存

        Returns:
            清空后的缓存（通常为空字符串）
        """
        if cached_text != "":
            if clear_cache:
                cached_text = (
                    cached_text[:-1] if cached_text.endswith("\n") else cached_text
                )
            last_title.addchild(PlainTextNode(cached_text))
            return ""
        return cached_text

    def _handle_code_block_line(
        self, line: str, cached_text: str, in_code_block: bool
    ) -> tuple[str, bool]:
        """
        处理代码块内的行

        Returns:
            (updated_cached_text, still_in_code_block)
        """
        if line == "```":
            return (cached_text + line + "\n", False)
        return (cached_text + line + "\n", True)

    def _handle_title_line(
        self,
        line: str,
        cached_text: str,
        last_title,
        titles: list[Any],
        line_index: int,
        full_text: str,
    ) -> tuple[str, Any, list[Any]]:
        """
        处理标题行

        Returns:
            (updated_cached_text, updated_last_title, updated_titles)
        """
        level, number, title_text = self._parse_title_line(line)
        self._validate_title_level(level)

        correct_number = self._validate_title_number(
            level, number, titles, line_index, full_text
        )

        if cached_text != "":
            cached_text = self._flush_cached_text(cached_text, last_title)

        new_title = self._create_title_node(level, correct_number, title_text)
        titles, last_title = self._add_title_to_hierarchy(
            new_title, level, titles, last_title
        )

        for j in range(level + 1, 7):
            titles[j] = None

        return (cached_text, last_title, titles)

    def _handle_text_line(self, line: str, cached_text: str) -> str:
        """
        处理普通文本行

        Returns:
            updated_cached_text
        """
        if line != "":
            return cached_text + line + "\n"
        return cached_text

    def _parse_markdown_core(self, text: str) -> None:
        """
        核心解析方法 - 模板方法模式

        主循环流程：
        1. 初始化状态（titles 数组、缓存等）
        2. 可选：处理第一行
        3. 遍历每一行：
           - 代码块处理
           - 标题行处理
           - 普通文本行处理
        4. 提交剩余缓存
        """
        self.children.clear()  # type: ignore - children provided by parent class (Node)

        code_block_flag = False
        cached_text = ""
        root_level = self._get_root_level()

        titles: list[Any | None] = [None] * 7
        titles[root_level] = self
        last_title = self

        lines = text.splitlines()

        if self._should_consume_first_line() and lines:
            first_line = lines[0]
            if first_line.startswith("#" * root_level + " "):
                self._process_first_line_if_needed(first_line)
                lines = lines[1:]

        for line_index, line in enumerate(lines):
            if code_block_flag:
                cached_text, code_block_flag = self._handle_code_block_line(
                    line, cached_text, code_block_flag
                )
                continue

            if self._is_code_block_boundary(line):
                if self._parse_code_block_start(line):
                    code_block_flag = True
                cached_text = self._handle_text_line(line, cached_text)
                continue

            if self._is_title_line(line):
                cached_text, last_title, titles = self._handle_title_line(
                    line, cached_text, last_title, titles, line_index, text
                )
                continue

            cached_text = self._handle_text_line(line, cached_text)

        if cached_text != "":
            self._flush_cached_text(cached_text, last_title)

    def parse_markdown(self, text: str) -> None:
        """
        解析 Markdown 文本的公共入口

        子类可以重写此方法添加额外逻辑，或调用 _parse_markdown_core()
        """
        self._parse_markdown_core(text)

    def set_text(self, text: str) -> None:
        """
        设置文本的公共入口

        默认实现：备份 children 后调用 parse_markdown()，失败时恢复
        子类可重写
        """
        # 备份当前 children 以便解析失败时恢复
        original_children = list(self.children)  # type: ignore - children provided by parent class (Node)

        try:
            self.parse_markdown(text)
        except Exception:
            # 解析失败时恢复原有 children
            self.children.clear()  # type: ignore - children provided by parent class (Node)
            for child in original_children:
                child.parent = None  # 重置父节点引用
                self.children.append(child)  # type: ignore - children provided by parent class (Node)
                child.parent = self  # type: ignore - children provided by parent class (Node)
            raise  # 重新抛出原始异常
