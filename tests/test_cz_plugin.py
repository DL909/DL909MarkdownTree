"""test_cz_plugin.py - commitizen 插件：提交信息解析与交互式前缀选择"""

import logging
import logging.config
import pathlib
import re
import subprocess
import sys

# commitizen 的包初始化会执行 logging.config.dictConfig(..., disable_existing_loggers=True)，
# 把本进程里已存在的 logger 全部置为 disabled。若不恢复，本文件之后所有依赖
# caplog 的测试都会静默失效（commitizen 只在自己的名字下配了 handler）。
import commitizen  # noqa: F401
import pytest
from commitizen.config import BaseConfig

from dl909markdowntree.cz_plugin import _COMMIT_PARSER, DL909Commitizen

for _existing in logging.root.manager.loggerDict.values():
    if isinstance(_existing, logging.Logger):
        _existing.disabled = False
logging.disable(logging.NOTSET)


@pytest.fixture
def cz() -> DL909Commitizen:
    return DL909Commitizen(BaseConfig())


def _parse(message: str) -> dict[str, str] | None:
    match = re.match(_COMMIT_PARSER, message)
    return match.groupdict() if match else None


def test_module_is_importable_before_commitizen():
    """本模块可作为第一个 commitizen 相关导入被加载

    早先类在模块执行期就定义，而 import commitizen 会触发入口点发现并 getattr
    本模块尚未定义的名字，直接 import 必然抛 partially initialized 错误。
    类改为惰性构造后这条路径才通得过。
    """
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from dl909markdowntree.cz_plugin import DL909Commitizen as C;"
                "print(C.__name__)"
            ),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "DL909Commitizen"


def test_unknown_module_attribute_still_raises_attribute_error():
    import dl909markdowntree.cz_plugin as module

    with pytest.raises(AttributeError, match="no attribute 'nope'"):
        _ = module.nope


def test_commit_parser_accepts_every_allowed_type():
    """项目约定的 11 种 type 都要被识别"""
    for change_type in (
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
    ):
        parsed = _parse(f"{change_type}: 描述")
        assert parsed is not None, change_type
        assert parsed["change_type"] == change_type
        assert parsed["message"] == "描述"


def test_commit_parser_rejects_unknown_type():
    """约定外的 type 不得被放行"""
    assert _parse("wip: 随便改改") is None


def test_commit_parser_extracts_scope_and_breaking_marker():
    """scope 允许 CamelCase 类名与模块名，! 表示破坏性变更"""
    parsed = _parse("fix(FolderNode)!: 破坏性改动")
    assert parsed["change_type"] == "fix"
    assert parsed["scope"] == "FolderNode"
    assert parsed["breaking"] == "!"
    assert parsed["message"] == "破坏性改动"


def test_commit_parser_allows_empty_and_dotted_scope():
    """空 scope（带括号）与含点的 scope 都应可用"""
    assert _parse("ci(): 冒烟")["scope"] == ""
    assert _parse("docs(TODO): 记录")["scope"] == "TODO"
    assert _parse("docs(a.b.c): 记录")["scope"] == "a.b.c"


def test_commit_parser_scope_excludes_brackets_and_newlines():
    """scope 内不允许括号或换行，否则正则会跨行误匹配"""
    assert _parse("fix(a(b): x") is None
    assert _parse("fix(a\nb): x") is None


def test_commit_parser_requires_space_after_colon():
    """冒号后必须有空格"""
    assert _parse("fix:紧贴冒号") is None


def test_commit_parser_recognises_breaking_change_type():
    """BREAKING CHANGE 作为独立 type 被支持"""
    assert _parse("BREAKING CHANGE: 接口变了")["change_type"] == "BREAKING CHANGE"


def _prefix_values(cz: DL909Commitizen) -> list[str]:
    prefix = next(q for q in cz.questions() if q.get("name") == "prefix")
    return [c["value"] for c in prefix["choices"]]


def test_questions_injects_chore_choice(cz):
    """插件应在 prefix 列表里补上 chore，且不覆盖原有选项"""
    values = _prefix_values(cz)
    assert "chore" in values
    assert "feat" in values
    assert "fix" in values


def test_questions_does_not_accumulate_across_calls(cz):
    """questions() 每次基于 super() 重建，重复调用不应追加重复项"""
    first = _prefix_values(cz)
    assert first == _prefix_values(cz)
    assert first.count("chore") == 1


def test_change_type_map_covers_every_parser_type(cz):
    """change_type_map 的键应与解析器接受的 type 一致，避免类型缺失映射"""
    parsed_types = {
        "build",
        "chore",
        "ci",
        "docs",
        "feat",
        "fix",
        "perf",
        "refactor",
        "revert",
        "style",
        "test",
    }
    assert set(cz.change_type_map) == parsed_types
