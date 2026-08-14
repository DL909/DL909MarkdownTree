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
