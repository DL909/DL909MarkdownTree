from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

if TYPE_CHECKING:
    from commitizen.question import CzQuestion

    class DL909Commitizen:
        """类型检查期的占位声明；运行时的类由模块级 __getattr__ 惰性构造

        故意不继承 ConventionalCommitsCz：基类只在运行时才导入，
        占位声明只需暴露本模块自己使用的成员。
        """

        commit_parser: str
        change_type_map: ClassVar[dict[str, str] | None]

        def questions(self) -> list[CzQuestion]: ...


_COMMIT_PARSER = (
    r"^((?P<change_type>BREAKING CHANGE|build|chore|ci|docs|feat|fix|perf|"
    r"refactor|revert|style|test)(?:\((?P<scope>[^()\r\n]*)\))?"
    r"(?P<breaking>!)?):\s(?P<message>.*)?"
)

_CHANGE_TYPE_MAP: dict[str, str] = {
    "feat": "Feat",
    "fix": "Fix",
    "refactor": "Refactor",
    "perf": "Perf",
    "docs": "Docs",
    "chore": "Chore",
    "ci": "Ci",
    "style": "Style",
    "test": "Test",
    "build": "Build",
    "revert": "Revert",
}

_CHORE_CHOICE = {
    "value": "chore",
    "name": "chore: Other changes that don't modify src or test",
    "key": "h",
}


def __getattr__(name: str) -> object:
    """惰性构造 DL909Commitizen

    直接 ``import dl909markdowntree.cz_plugin`` 原本必然失败：定义这个类需要先
    import commitizen，而 commitizen 的包初始化会调用 discover_plugins()，后者
    对每个 commitizen.plugin 入口点执行 ep.load()，最终 getattr(模块, 类名)。
    若本模块正处在执行中间态（还没定义到类名），这一步就抛
    "partially initialized module ... has no attribute 'DL909Commitizen'"。
    commitizen 命令行没暴露这个问题，只因为它总是先加载好自身再加载插件。

    把类挪到属性访问时才构造，模块就能先顺利执行完毕，入口点再取属性时
    才去 import commitizen，此时已不在中间态。
    """
    if name != "DL909Commitizen":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from commitizen.cz.conventional_commits.conventional_commits import (
        ConventionalCommitsCz,
    )
    from commitizen.question import ListQuestion

    class DL909Commitizen(ConventionalCommitsCz):
        commit_parser = _COMMIT_PARSER
        change_type_map: ClassVar[dict[str, str] | None] = _CHANGE_TYPE_MAP

        def questions(self) -> list[CzQuestion]:
            questions = super().questions()
            for question in questions:
                if question.get("type") == "list" and question.get("name") == "prefix":
                    prefix = cast(ListQuestion, question)
                    prefix["choices"] = [
                        *(prefix.get("choices") or []),
                        _CHORE_CHOICE,
                    ]
            return questions

    globals()["DL909Commitizen"] = DL909Commitizen
    return DL909Commitizen
