# 用 cz_customize 配置取代自写 cz 插件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删掉 `src/dl909markdowntree/cz_plugin.py` 这份自写的 commitizen 插件，把它的行为原样搬进 `pyproject.toml` 的 `[tool.commitizen.customize]`。

**Architecture:** commitizen 4.17.0 自带 `cz_customize` 入口点，`CustomizeCommitsCz.__init__` 会把配置段里的 `commit_parser` / `changelog_pattern` / `change_type_map` / `change_type_order` 逐个 `setattr` 到实例上，而 `commands/changelog.py:193` 读的正是 `self.cz.commit_parser` —— 配置值会被采用。插件的三个作用点（chore 进 changelog、菜单里多一项 chore、type→章节名映射）全部落在这些可配置项里。

**Tech Stack:** commitizen 4.17.0、TOML、uv。

**不做什么:** 不装 git hook（无 `tools/hooks/`、不设 `core.hooksPath`）、不加 CI 校验步骤、不改 README / USAGE / release.yml。提交信息校验仍靠手动 `cz check`，与现在一致。

---

## File Structure

| 文件 | 动作 | 职责 |
|---|---|---|
| `pyproject.toml` | 改 | 删入口点；`name` 改 `cz_customize`；新增 `[tool.commitizen.customize]` |
| `src/dl909markdowntree/cz_plugin.py` | 删 | 插件类，89 行 |
| `tests/test_cz_plugin.py` | 删 | 12 个用例 + 顶部恢复 logger 的 workaround |
| `docs/superpowers/plans/2026-09-28-extract-cz-plugin.md` | 删 | 方案两次被改判，已作废 |
| `docs/superpowers/plans/2026-09-28-cz-customize-config.md` | 新增 | 本文件 |

`TODO.md` 里提到 cz_plugin 的几行是走查历史记录，不改写。`src/` 其余代码与其余测试一行不碰。

---

## 配置项与插件代码的对应关系

| 插件里的东西 | 配置项 | 值 |
|---|---|---|
| `DL909Commitizen.commit_parser` | `commit_parser` | 白名单补齐 11 种 type |
| `DL909Commitizen.change_type_map` | `change_type_map` | 11 种 type → 章节名 |
| 继承来的 `ConventionalCommitsCz.changelog_pattern` | `changelog_pattern` | 与 `defaults.BUMP_PATTERN` 逐字相同 |
| 继承来的 `change_type_order` | `change_type_order` | 与 `defaults.CHANGE_TYPE_ORDER` 相同 |
| `questions()` 里 append 的 `_CHORE_CHOICE` | `[[...customize.questions]]` 的 `choices` | 10 项（cz 自带 9 + chore），`key` 保持原值 |
| 继承来的 `message()` | `message_template` | 与 `ConventionalCommitsCz.message()` 在 `breaking_change_exclamation_in_title=false` 下逐字等价 |
| 继承来的 `schema_pattern()` | `schema_pattern` | 与 commitizen 默认值逐字相同 |

---

## 实施步骤

- [ ] **Step 0: 存基线**

  ```bash
  uv run cz changelog --dry-run --start-rev v2.0.2 > /tmp/cz-before.txt
  ```

  改完后重跑同一命令到 `/tmp/cz-after.txt`，`diff` 必须无输出。这是本次改动的
  核心验收：changelog 输出必须逐字节不变。

- [ ] **Step 1: 改 `pyproject.toml`**

  删掉整个 `[project.entry-points."commitizen.plugin"]` 小节；`[tool.commitizen]` 的
  `name` 改成 `cz_customize`，其余三项（`version_provider` / `tag_format` /
  `update_changelog_on_bump`）原样保留；新增 `[tool.commitizen.customize]` 整段。

  **不设** `use_shortcuts` 与 `breaking_change_exclamation_in_title`，两者都用默认值，
  菜单与 `!` 标记行为与改动前完全一致。

- [ ] **Step 2: `uv sync --dev`（必须在删模块之前）**

  ```bash
  uv sync --dev
  uv run python -c "from commitizen.cz import registry; print(sorted(registry))"
  # 期望：['cz_conventional_commits', 'cz_customize', 'cz_jira']，不再有 cz_dl909
  ```

  顺序反了会炸，原因见下面「为什么必须先 sync」。

- [ ] **Step 3: 删文件**

  ```bash
  git rm src/dl909markdowntree/cz_plugin.py tests/test_cz_plugin.py \
         docs/superpowers/plans/2026-09-28-extract-cz-plugin.md
  ```

  顺带清掉 `__pycache__` 里的 `cz_plugin.cpython-312.pyc` 与
  `test_cz_plugin.cpython-312-pytest-*.pyc`（未被 git 跟踪，但要避免误导后续排查）。

- [ ] **Step 4: 验证**

  ```bash
  uv run cz changelog --dry-run --start-rev v2.0.2 > /tmp/cz-after.txt
  diff /tmp/cz-before.txt /tmp/cz-after.txt     # 必须无输出

  uv run pytest -q                                # 期望 457 passed
  uv run ruff check src/ tests/
  uv run ruff format --check src/ tests/
  uv run pyright src/                             # 期望 0 errors
  ```

  `cz check` 四连测（判据：合法 0 / 非法 14 / 空消息加 `--allow-abort` 放行 /
  `Merge …` 放行）：

  ```bash
  printf 'chore(plan): x\n' > /tmp/m.txt && uv run cz check --allow-abort --commit-msg-file /tmp/m.txt; echo $?
  printf 'nope\n'          > /tmp/m.txt && uv run cz check --allow-abort --commit-msg-file /tmp/m.txt; echo $?
  ```

  再确认三个「只在 customize 段取值、缺省静默返回空串」的方法都有输出：
  `uv run cz example` / `uv run cz schema` / `uv run cz info`。

  最后人工走一次 `uv run cz commit`，确认菜单里有 chore、生成的标题格式与改动前一致。

- [ ] **Step 5: 提交**

  ```
  docs(plan): 用 cz_customize 配置取代自写插件
  refactor(cz): 用 cz_customize 配置取代自写插件
  ```

---

## 为什么必须先 `uv sync` 再删模块

当前是 editable 安装，`.venv/…/dl909markdowntree-2.0.3.dist-info/entry_points.txt`
里登记着 `cz_dl909 = dl909markdowntree.cz_plugin:DL909Commitizen`。而
`commitizen/cz/__init__.py` 的 `discover_plugins()` 在 `import commitizen` 的**执行期**
就遍历环境里所有 `commitizen.plugin` 入口点并逐个 `ep.load()`。

先删模块、不同步，就等于让 `ep.load()` 去 import 一个已经不存在的东西 →
`ModuleNotFoundError`，之后任何 `cz` 命令都起不来。

对照：**只改 `[tool.commitizen]` 不需要重装**，因为 cz 是直接读 `pyproject.toml` 的；
只有动 entry point 才必须重装。

---

## 三个静默失败点

**1. `message_template` 的变量名必须与 question 的 `name` 完全一致。**
jinja2 对未定义变量渲染成空串而不报错。照官方示例写 `{{change_type}}` 但问题名叫
`prefix`，结果提交信息变成 `(interface): xxx`——前缀整个消失。

**2. 正则必须用 TOML 单引号字面量串。**
基本串（双引号）会把 `\s` `\r` 当转义处理，`\(` 更是非法转义。

**3. `schema_pattern` / `example` / `schema` / `info` 都不能省。**
`CustomizeCommitsCz` 的这四个是**方法**，只从 `customize` 段取值、缺省返回 `""`。
其中 `schema_pattern` 缺省最危险：空正则匹配一切，`cz check` 会变成**永远通过**，
而且不报任何错。本计划直接照抄 commitizen 的默认值，逐字相同，`cz check` 行为零变化。

---

## 行为差异（有意为之）

| 差异 | 说明 |
|---|---|
| `cz commit` 少问一个问题 | 删掉 `is_breaking_change`。`breaking_change_exclamation_in_title` 为 false 时它的答案本来就被模板丢弃，保留只是多问一句。改为在 footer 提示文案里写明 `BREAKING CHANGE:` 前缀 |
| `cz example` / `cz schema` / 菜单文案变中文 | 纯提示文本，非功能；与仓库文档语言一致 |
| 交互 scope 不再自动把空格转 `-` | 配置里拿不到 `filter` 回调（文档标注为 Work in Progress）。仓库惯例是 CamelCase 类名 / 模块名，本就无空格 |
| subject 为空不再当场报错 | 同上；改由 `schema_pattern` 在 `cz check` 时兜住 |
| 库 wheel 里不再含 changelog 入口点 | 库的用户不再被装上一个跟他们项目无关的 chore 选项——这正是原插件最大的问题 |

## 已知代价

官方文档明确警告 `cz_customize`「很可能在下一个大版本被移除或改名」
（[issue #1385](https://github.com/commitizen-tools/commitizen/issues/1385)），
无公布时间表，4.17.0 代码里也没有对应的运行时告警。真到那天迁移成本 = 写回一个
Python 类，不会比现状更糟；而现状依赖 `ConventionalCommitsCz.questions()` 的内部
结构，同样是内部 API 依赖。

---

## 执行偏差（实施后回填）

**1. `uv sync --dev` 会顺手卸掉可选依赖，计划里这条命令写错了。**

Step 2 写的是 `uv sync --dev`，理由是「只需重建 dist-info」。实测它同时把
`mcp` / `langchain` 两个 optional-dependency 组卸掉了——`uv sync` 不带
`--all-extras` 就是按「声明的依赖」对齐环境，可选组不在其中。后果是三处一起亮红灯：

- `pytest` 从 457 passed 掉到 **398 passed, 2 skipped**（`test_langchain_toolkit.py`
  与 `test_mcp_server.py` 整体 `importorskip`）
- `pyright` 从 0 errors 变成 **3 errors**，全是 `langchain_core` / `fastmcp` 的
  `reportMissingImports`
- 差点被误读成「删除插件引入了回归」

正确命令是 `uv sync --dev --all-extras`，与 `.github/workflows/release.yml` 一致。
教训不是这一条命令，而是**看起来无害的环境命令其实会改环境**：`uv sync`、`pip
install -e .` 都会按声明对齐，之后必须用「装齐了的环境」重跑全部验收数字，
不能沿用改之前那份。

**2. 「人工走一次 `cz commit`」换成了可复现的等价检查。**

交互式菜单没法进自动化。改成直接构造 answers 调 `cz.message()`，与
`ConventionalCommitsCz.message()` 在 `breaking_change_exclamation_in_title=false`
下的期望输出逐组比对（5 组：普通 scope、chore、无 scope 多行 body、docs、破坏性
变更）——全部 OK。顺带断言了菜单 5 个问题、10 个 prefix 选项、`use_shortcuts=False`。
强度比肉眼看菜单更高，且能重跑。

**3. 验证跑了两遍。** 因为偏差 1，第一次那轮的 398 passed / 3 errors 不作数；
`--all-extras` 装回后重跑才是有效数字。

**最终结果：** changelog 输出与改动前逐字节一致；457 passed；ruff check 与
format --check 通过；pyright 0 errors；`cz check` 四连测 0 / 14 / 0 / 0；
`cz example` / `cz schema` / `cz info` 均有输出。

