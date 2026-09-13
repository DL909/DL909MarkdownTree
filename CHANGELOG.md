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
