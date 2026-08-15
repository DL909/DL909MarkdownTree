from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from commitizen.cz.conventional_commits.conventional_commits import (
    ConventionalCommitsCz,
)
from commitizen.question import ListQuestion

if TYPE_CHECKING:
    from commitizen.question import CzQuestion

_COMMIT_PARSER = (
    r"^((?P<change_type>BREAKING CHANGE|build|chore|ci|docs|feat|fix|perf|"
    r"refactor|revert|style|test)(?:\((?P<scope>[^()\r\n]*)\))?"
    r"(?P<breaking>!)?):\s(?P<message>.*)?"
)


class DL909Commitizen(ConventionalCommitsCz):
    commit_parser = _COMMIT_PARSER
    change_type_map: ClassVar[dict[str, str] | None] = {
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

    def questions(self) -> list[CzQuestion]:
        questions = super().questions()
        for question in questions:
            if question.get("type") == "list" and question.get("name") == "prefix":
                prefix = cast(ListQuestion, question)
                prefix["choices"] = [
                    *(prefix.get("choices") or []),
                    {
                        "value": "chore",
                        "name": "chore: Other changes that don't modify src or test",
                        "key": "h",
                    },
                ]
        return questions
