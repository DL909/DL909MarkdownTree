## v3.0.0 (2026-09-29)

### BREAKING CHANGE

- get_markdown_text_node() 自 v2.0.3 起就是公开 API，
本次移除。改用公开属性 markdown_text_node，或 get_root_title()。
同一批未发布的破坏性变更还有：文件节点 get_text() 改零参数、
AttributedMarkdownTextFileBase 不再保证可折叠。

### Fix

- **tools**: correct replace_lines targeting and protect every rollback
- **Node,FolderNode**: reparent from_self copies, keep reload's base signature
- **MarkdownTitle**: use one heading regex so a stray "# " cannot brick a file
- **AttributedMarkdown**: accept unterminated frontmatter and wrap errors
- **FolderNode**: keep mdp trailing newlines and warn on lossy filenames
- **TitlePathPermissionChecker**: rebind entries when a title is renamed
- **FolderNode**: initialize children on folder nodes
- **MarkdownTitle**: stop add_text indexing empty strings
- **tools**: require write for unfold, reject forged titles, read full text

### Refactor

- **cz**: 用 cz_customize 配置取代自写插件
- **interface**: 删掉与基类重复的抽象声明，移除 get_markdown_text_node
- **Attributed**: 把属性抽成 mixin，补上非编号非折叠的带属性文件
- **interface**: 把折叠视图从文件节点下沉到标题节点
- **FolderNode**: settle each section by delete-then-write when saving
- **NumberedMarkdown,interface**: copy number lists, complete annotations

### Perf

- **permissions**: index node grants and forbid Permission.NONE as a grant

### Ci

- pin pyright pythonVersion and enforce ruff format

### Docs

- **plan**: 用 cz_customize 配置取代自写插件
- **plan**: cz 插件独立化的计划
- **plan**: 回填实施偏差
- **plan**: 属性 mixin 化的实施计划
- **spec**: 记录属性 mixin 化重构的设计规格
- **TODO**: mark all 23 review findings as fixed with their commits
- **USAGE**: correct the parser notes and state the intended limitations
- **TODO**: record code review findings and priorities

### Test

- cover cz_plugin and the remaining branches, fix its import cycle

## v2.0.3 (2026-09-27)

### Fix

- **FoldableMarkdownTitleNode**: fix incompatible method override
- numbered markdown title can't auto correct title without number field

## v2.0.2 (2026-09-13)

### Fix

- **MarkdownTitle**: return empty title for level 0 nodes
- **Node**: copy children list and reset parent in from_self
- **FoldableMarkdownTitle**: preserve descendant fold states across set_text
- **FoldableMarkdownTitle**: propagate recursive_up_unfold from already unfolded node
- **interface**: declare get_markdown_text_node and implement for attributed node
- **AttributedMarkdownFolderNode**: honor explicitly passed attribute
- **AttributedMarkdownFolderNode**: handle empty FrontMatter.yaml
- **tools**: snapshot full text for rollback to keep folded content
- **MarkdownTitle**: set parent when appending plain text child
- **AttributedMarkdownTextFileNode**: remove extra blank line before frontmatter end
- **PlainTextFileNode**: create missing file instead of raising FileNotFoundError
- **tools**: return failure message instead of AttributeError for unfold on non-foldable nodes
- **MarkdownTitle**: recognize tilde fences and closing fence at end of text
- **FolderNode**: accept str file_path by converting to Path
- **tools**: match replace_lines against full text including folded content
- **FoldableMarkdownTitle**: use full text in add_text to keep folded content

### Chore

- **deps**: remove unused lxml dependency

### Docs

- **USAGE**: align examples and notes with actual behavior
- **TODO**: add newly found issues
- **USAGE.md-&-TODO.md**: add usage and some todo

### Test

- **tools**: ensure replace_lines never matches folded view markers

## v2.0.1 (2026-08-15)

### Fix

- **FoldableFolderNode**: tolerate corrupt fold_state.json
- **FolderNode**: clean duplicate mdp files and avoid silent rename overwrite
- **tools**: roll back in-memory changes on save failure
- **tools**: persist fold state after unfold
- **MarkdownTitle**: reject title levels above six in from_line
- **Node**: clear parent of removed deprecated children
- **MarkdownTitle**: allow longer closing code fence
- **MarkdownTitle**: merge consecutive plain text children
- **AttributedMarkdown**: support empty frontmatter

### Refactor

- **interface**: move FoldMode to interface and expose fold_mode
- **PlainTextFileNode**: drop useless pydantic Field

### Chore

- ignore coverage artifacts

### Ci

- **cz**: patch cz

### Docs

- **tools**: clarify target title matching for numbered nodes

## v2.0.0 (2026-08-14)

### Feat

- **permission**: abstract permission checker and provide another approach by node tree path along side original node object

### Perf

- replace deepcopy with a better solution

## v1.1.1 (2026-08-14)

### Fix

- **FoldableMarkdown**: fix save question

## v1.1.0 (2026-08-13)

### Feat

- replace business asserts with InvalidNodeOperationError
- make DENY permission absolute
- auto-save after write tools

### Fix

- clean up misc issues in error messages and internals
- support code fences longer than three backticks
- sanitize mdp section filenames
- make PlainTextFileNode.save always write content
- include License file in wheel
- enforce permission check on full-document reads
- honor explicit auto_correct=False in folder reload

### Refactor

- extract shared tool logic for mcp and langchain

## v1.0.0 (2026-08-13)

### Feat

- **Exception**: add custom exception family
- enhance refactored parser logic

### Refactor

- rewrite parser

### Perf

- change import style
- fix some type check and add ignore for pyright
- remove nested if
- **src/dl909markdowntree/node.py**: add return type hint to Node::addchild and Node::dispatch
- fix ruff question

## v0.2.1 (2026-08-10)

### Fix

- **AttributedMarkdownFolderNode**: not poped attribute when folder exist cause exception
- **AttributedMarkdownTextFileNode**: unify inconsistent frontmatter split logic

### Perf

- remove redundant **kwargs

## v0.2.0 (2026-08-09)

### Feat

- add get_markdown_text_node to protocol

### Perf

- more format and type hint fix
- format, rename and some type hint fix
