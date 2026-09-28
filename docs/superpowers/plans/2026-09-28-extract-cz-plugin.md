# cz 插件独立化 Plan

> **For agentic workers:** 按任务逐条执行。每个 checkbox 是一个 2–5 分钟的动作。

**Goal:** 把 commitizen 插件 `cz_dl909` 从 `dl909markdowntree` 的发布产物里摘出去，改成一个独立分发包，让它不再被安装到库的每一个用户环境里。

**Tech Stack:** Python 3.12、hatchling、commitizen 3.x、uv。

---

## 一、为什么要拆——三条都是查证过的事实，不是推测

**1. 它会污染每一个下游用户的 commitizen。**
`commitizen/cz/__init__.py:16` 的 `discover_plugins()` 在 `import commitizen`
执行期就运行，遍历环境里**所有** `commitizen.plugin` 入口点并逐个 `ep.load()`。
所以任何人 `pip install dl909markdowntree` 之后，他自己项目里的 `cz` 就多出一个
跟他毫无关系的 `chore` 选项。

**2. 它对 commitizen 内部结构有运行时耦合。**
插件子类化 `ConventionalCommitsCz`，并直接改写 `prefix["choices"]` 这个内部
TypedDict。别人环境里的 commitizen 版本只要和我们开发时不同，就可能在用户
敲 `cz` 的过程中抛异常。

**3. 它把开发期的绕行带进了发布产物。**
模块级 `__getattr__` 惰性构造 + `TYPE_CHECKING` 占位类，都是为了对付
「本模块由 `ep.load()` 在 commitizen 自己的 import 中期被加载」这件事。
commitizen 只是 dev 依赖，库的用户根本装不上，这套复杂度对他们是纯负担。

---

## 二、关键约束：决定了"移出去"不能只是"移个文件"

commitizen **只认入口点**，没有按模块路径加载的回退：

```python
# commitizen/factory.py
def committer_factory(config):
    return registry[config.settings["name"]](config)   # KeyError → "Try running 'pip install cz_dl909'"

# commitizen/cz/__init__.py
registry: dict[str, type[BaseCommitizen]] = discover_plugins()
    # == {ep.name: ep.load() for ep in metadata.entry_points(group="commitizen.plugin")}
```

由此推出两条**不能走**的路：

- ❌ 把文件搬到 `src/` 外面、继续用 `pythonpath` 或 `sys.path` 引入 → 插件直接失效。
- ❌ 在 `pyproject.toml` 里保留入口点、但让 wheel 不打包这个模块 → 已发布包的
  元数据里带着一个指向不存在模块的入口点，用户的 `ep.load()` 抛
  `ModuleNotFoundError`，**反而把用户的 commitizen 弄坏**。这是负分，比不拆更糟。

所以「移出去」的最小正确形态是：**它必须成为一个独立的、会被安装的分发包。**

---

## 三、方案对比

| | A. 独立 repo + `uv tool install` | B. 同 repo 第二个 package | C. 不拆，只写进文档 |
|---|---|---|---|
| 库 wheel 干净 | ✅ | ✅ | ❌ |
| 用户环境无污染 | ✅ | ✅ | ❌ |
| 库 repo 需开 workspace | ❌ 不需要 | ✅ 需要，CI 要跟着改 | ❌ |
| 版本独立、commitizen 升级不牵连库 | ✅ | ❌ 锁在同一个 release 节奏 | ❌ |
| 维护成本 | 多一个 85 行的 repo | 单 repo，pyproject 变复杂 | 零 |
| 用户要装一次 | `uv tool install cz-dl909` | `uv sync` 自动带上 | 不用装，但忍受污染 |

**推荐 A。** 决定性理由是这个文件 85 行、已稳定很久，维护成本≈0；而 B 要在库 repo
里引入 uv workspace 这个新机制，正好撞上"少加机制"的取向。代价只是多一个仓库要
记得同步——但它几乎不会再变。

C 不是没成本：它把"你的 commitizen 会被别人的库改掉"这件事留给每个用户自己发现。
如果哪天要退回 C，正确的做法是在 README 的 Known limitations 里写清第 1、2 两条，
而不是什么都不说。

---

## 四、方案 A 的执行步骤

### Task 1: 建包骨架

- [ ] **Step 1: 建目录与 pyproject**

在 `~/` 下（与 MarkdownTree 平级）新建 `cz-dl909/`，内含：

```toml
# cz-dl909/pyproject.toml
[project]
name = "cz-dl909"
version = "0.1.0"
description = "commitizen 插件：让 changelog 正确识别 chore 等 11 种 type"
readme = "README.md"
requires-python = ">=3.12"
dependencies = ["commitizen>=3.0.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/cz_dl909"]

[tool.pytest.ini_options]
pythonpath = ["src"]

[tool.pyright]
pythonVersion = "3.12"
include = ["src"]

[tool.ruff]
target-version = "py312"
```

四个工具配置照抄库里的，`pythonVersion = "3.12"` 那条注释（pyright 不从
`requires-python` 推断）一并带过去。

- [ ] **Step 2: 建包目录**

```
cz-dl909/
├── pyproject.toml
├── README.md
├── src/cz_dl909/__init__.py
└── tests/test_plugin.py
```

做成包而不是单文件模块：`discover_plugins` 里那句
`pkgutil.iter_modules` 会遍历顶层 `cz_` 开头的模块名，包和单文件都会被扫到，
两者没有差别；包的好处是以后能放 `__version__` 和别的文件。

- [ ] **Step 3: 入口点声明**

```toml
[project.entry-points."commitizen.plugin"]
cz_dl909 = "cz_dl909:DL909Commitizen"
```

键名 `cz_dl909` 必须与库 repo 里 `[tool.commitizen] name` 一致——那只是个
注册表查表的 key，库 repo 那边不用改代码。

### Task 2: 搬代码

- [ ] **Step 4: 把 `cz_plugin.py` 搬到 `src/cz_dl909/__init__.py`**

内容原样搬，模块文档字符串里的 `dl909markdowntree` 措辞改成 `cz_dl909`。
**惰性构造的 `__getattr__` 必须一起搬，不能因为"独立包可能不需要"就删掉。**
理由：那个测试（`test_module_is_importable_before_commitizen`）断言的是
「把本模块作为第一个 commitizen 相关导入直接 import」这条路径，这条路径在
独立包里同样存在。将来真想简化，需要先证明入口点加载路径不再经过本模块的
import 中期，而不是凭感觉删。

- [ ] **Step 5: 搬测试**

`tests/test_cz_plugin.py` → `cz-dl909/tests/test_plugin.py`，改两处：
- `from dl909markdowntree.cz_plugin import ...` → `from cz_dl909 import ...`
- 子进程测试里的 `cwd` 指向 `cz-dl909/` 而不是库 repo

那个 `logging.disable(NOTSET)` 的恢复 workaround 也要一起搬——它的成因是
commitizen 的包初始化会 `disable_existing_loggers=True`，在哪个仓库都一样发生。

- [ ] **Step 6: 补一条 README**

三句话即可：它做什么（给 changelog 正确识别 chore 等 11 种 type）、怎么装
（`uv tool install cz-dl909`）、怎么用（在目标 repo 的 pyproject 里写
`[tool.commitizen] name = "cz_dl909"`）。

### Task 3: 装上并验证插件本身

- [ ] **Step 7: 本地安装并验证**

```bash
cd ~/cz-dl909 && uv sync --dev && uv run pytest -q
```

Expected: 全部 passed（约 14 个测试，与库里现有的数量一致）

- [ ] **Step 8: 装成工具，确认库 repo 里不再被自动发现**

```bash
uv tool install ~/cz-dl909
cd ~/MarkdownTree && uv run python -c "
from commitizen.cz import registry
print('cz_dl909' in registry)
"
```

Expected: `False` —— 此时库 repo 的入口点已经删掉了（Task 4 先做），
所以 registry 里不该再有它。

### Task 4: 从库 repo 摘出去

- [ ] **Step 9: 删文件**

删除 `src/dl909markdowntree/cz_plugin.py` 与 `tests/test_cz_plugin.py`。

- [ ] **Step 10: 删入口点声明**

`pyproject.toml` 删掉整个 `[project.entry-points."commitizen.plugin"]` 小节。
`[tool.commitizen]` 那一节**全部保留**（`name` / `version_provider` /
`tag_format` / `update_changelog_on_bump`）——它只是查表配置，不含代码。

- [ ] **Step 11: 把 commitizen 从 dev 依赖组移出**

```toml
[dependency-groups]
dev = [
  "pdbpp>=0.12.1",
  "pyright>=1.1.410",
  "pytest>=9.1.1",
  "pytest-cov>=7.1.0",
  "ruff>=0.15.18",
  "twine>=7.0.0",
]
```

**这一步不能省。** 留着它，`.venv/bin/cz` 就会继续存在，而 `uv run` 把项目
venv 的 bin 放在 PATH 最前，于是 `uv run cz bump` 会挑中那个**没有插件**的
cz，报 "The committer has not been found in the system"。移出之后
`uv run cz` 会沿 PATH 回退到 `uv tool install` 装的那个。

- [ ] **Step 12: 验证库侧干净**

```bash
uv sync --dev && uv run pytest -q && uv run ruff check src/ tests/ \
  && uv run ruff format --check src/ tests/ && uv run pyright src/
```

Expected: 测试从 469 降到约 455（少掉 cz 插件那 14 个），ruff 与 pyright 全过，
且 **pyright 现在是 0 errors 而不是 8**——本地 venv 缺 pydantic_yaml 等可选依赖
造成的 `reportMissingImports` 会随之减少。

- [ ] **Step 13: 验证发版流程仍然通**

```bash
cd ~/MarkdownTree && cz bump --yes --increment patch
```

用**裸 `cz`**而不是 `uv run cz`：前者的解析路径确定（PATH 上的工具），
后者依赖 uv 的回退行为，踩到问题时不好排查。确认 CHANGELOG 正确追加、
版本号改对后再 `git reset --hard HEAD~1` 撤销这次试跑。

- [ ] **Step 14: 提交**

```bash
git add -A
git commit -F - <<'EOF'
refactor(cz_plugin): 把 commitizen 插件移出本项目，改为独立分发包

commitizen 的 discover_plugins() 在 import commitizen 执行期就遍历环境里
所有 commitizen.plugin 入口点并 ep.load()，所以只要本库被安装，任何用户的
cz 就多出一个跟他项目无关的 chore 选项。插件还直接改写 commitizen 内部
结构 prefix["choices"]，对方环境的 commitizen 版本与我们不同就可能在他敲 cz
时抛异常——这些代价不该由库的用户承担。

更根本的是它属于开发期工具：commitizen 只是 dev 依赖，库的用户根本装不上，
而模块级 __getattr__ 惰性构造这类绕行只为对付"本模块在 commitizen 的
import 中期被加载"，整套复杂度都进了发布 wheel。

注意 commitizen 只认入口点，没有按模块路径加载的回退——移出 src/ 但不做成
独立安装的包，插件会直接失效；而保留入口点却让 wheel 不打包该模块，用户
的 ep.load() 会抛 ModuleNotFoundError，反而弄坏他们的 commitizen。两条死路
都不走，只能做成分发包。

插件、测试、惰性构造的绕行与 logging 恢复 workaround 一并搬到独立包
cz-dl909。README 记录装法。

本仓库的 [tool.commitizen] 配置原样保留——那只是注册表查表的 key。
commitizen 从 dev 依赖组移出，否则 .venv/bin/cz 会继续遮住工具包里的那个，
uv run cz bump 会挑中没有插件的 cz。
EOF
```

---

## 五、做完之后的样子

| | 之前 | 之后 |
|---|---|---|
| 库 wheel 内容 | 含 cz_plugin.py | 干净 |
| 用户装库后自己的 cz | 多一个无关的 chore | 不受影响 |
| 库 repo 的 pyproject | 带一个 entry point | 无 |
| 库 repo 测试数 | 469 | 约 455 |
| 本地发版 | `uv run cz bump` | `cz bump`（工具包提供） |
| 维护 cz 插件 | 跟着库的 release 走 | 独立 repo，独立版本 |

## 六、回滚

四个 Task 互相独立，可以只做一部分：
- 想撤回全部：`git revert <Task 4 的提交>`，再 `uv sync` 恢复。
- 插件代码本身零改动，只是换了个仓库，所以任何时候都能原样搬回来。
