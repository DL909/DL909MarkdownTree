# tree_doc - Markdown Document Tree Module

**Location**: `novelWriter/tree_doc/`

**Purpose**: A Python library for symbolizing and manipulating multiple Markdown files in a tree-like structure. Provides a node-based architecture for parsing, generating, and transforming markdown documents with support for hierarchical titles, numbered outlines, foldable content, and YAML frontmatter.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Class Hierarchy](#class-hierarchy)
- [Core Components](#core-components)
  - [Base Classes](#base-classes)
  - [Markdown Nodes](#markdown-nodes)
  - [Numbered Markdown Nodes](#numbered-markdown-nodes)
  - [Foldable Markdown Nodes](#foldable-markdown-nodes)
  - [Attributed Markdown Nodes](#attributed-markdown-nodes)
  - [Markdown Folder Nodes](#markdown-folder-nodes)
  - [Foldable Markdown Folder Nodes](#foldable-markdown-folder-nodes)
  - [Attributed Markdown Folder Nodes](#attributed-markdown-folder-nodes)
- [Key Features](#key-features)
- [Usage Examples](#usage-examples)
- [Parser Design Pattern](#parser-design-pattern)
- [File Structure](#file-structure)

---

## Architecture Overview

The `tree_doc` module uses a **Node-based tree structure** built on Pydantic models. All nodes inherit from the base `Node` class which provides:

- Parent-child relationships
- Tree manipulation methods (`addchild()`, `dispatch()`, `update()`)
- Deprecation support for node removal

The module follows a **layered architecture**:

```
Base Layer (Node, TextNode, FileNode)
       ↓
Core Layer (markdown_nodes.py - basic markdown support)
       ↓
Extended Layers:
  - numbered_markdown_nodes.py (numbered outlines)
  - foldable_markdown_nodes.py (collapsible content)
  - attributed_markdown_nodes.py (YAML frontmatter)
       ↓
File Layer (markdown_folder_nodes.py - multi-file directory nodes)
  - foldable_markdown_folder_nodes.py (foldable folder)
  - attributed_markdown_folder_nodes.py (attributed folder)
```

---

## Class Hierarchy

```
Node (BaseModel, ABC)
├── TextNode (ABC)
│   ├── PlainTextNode
│   ├── MarkdownTitleNode
│   │   └── NumberedMarkdownTitleNode
│   │       └── FoldableMarkdownTitleNode
│   ├── MarkdownTextNode
│   │   └── NumberedMarkdownTextNode
│   │       └── FoldableMarkdownTextNode
│   └── AttributedMarkdownTextFileNode (Generic[T])
└── FileNode (ABC)
    ├── TextFileNode
    ├── MarkdownTextFileNode
    │   └── NumberedMarkdownTextFileNode
    │       └── FoldableMarkdownTextFileNode
    └── AttributedMarkdownTextFileNode (also inherits from TextNode)
    ├── MarkdownFolderNode (FileNode + TextNode)
    │   └── FoldableMarkdownFolderNode
    │       └── AttributedMarkdownFolderNode (Generic[T])
```

---

## Core Components

### Base Classes

#### `Node` (`Node.py`)

- **Purpose**: Root of all tree nodes
- **Key Properties**:
  - `parent: Node | None` - Parent node reference
  - `children: list[Node]` - Child nodes list
  - `deprecated: bool` - Deprecation flag for removal
- **Key Methods**:
  - `update()` - Recursively update children, remove deprecated
  - `addchild(child)` - Add orphan node as child
  - `dispatch()` - Remove from parent, become orphan

#### `TextNode` (`text_node.py`)

- **Purpose**: Abstract base for text-bearing nodes
- **Abstract Methods**:
  - `get_text() -> str` - Get text content
  - `set_text(text) -> None` - Set text content

#### `FileNode` (`file_node.py`)

- **Purpose**: Abstract base for file-backed nodes
- **Properties**:
  - `file_path: pathlib.Path` - File location
- **Abstract Methods**:
  - `save()` - Save to file
  - `reload()` - Reload from file

#### `PlainTextNode` (`plain_text_file_node.py`)

- **Purpose**: Simple text container
- **Properties**:
  - `text: str` - Raw text content

---

### Markdown Nodes

#### `MarkdownTitleNode` (`markdown_nodes.py`)

Represents a markdown title with optional children (subtitles or text).

**Properties**:

- `level: int` - Title level (1-6)
- `title: str` - Title text
- `children: list[PlainTextNode | MarkdownTitleNode]`

**Key Methods**:

- `get_title(show_level_sign=True)` - Get title with optional `#` prefix
- `set_text(text)` - Parse and set child content
- `recursive_find_title_node_by_name(title_name)` - Find title by name
- `all_children_are_titles()` - Check if all children are titles

**Example**:

```python
title = MarkdownTitleNode(title="Chapter 1", level=1)
title.set_text("This is the content...")
# Renders as:
# # Chapter 1
# This is the content...
```

#### `MarkdownTextNode`

Represents a markdown text block that can contain titles and plain text.

**Key Methods**:

- `parse_markdown(text)` - Parse markdown string into tree structure
- `recursive_find_title_node_by_name(title_name)` - Search for title

#### `MarkdownTextFileNode`

File-backed node for markdown files.

**Properties**:

- `markdown_text_node: MarkdownTextNode` - Root text node

**Methods**:

- `save_to_file(file_path)` - Save to specified path
- `save()` - Save to own file_path
- `reload()` - Reload from file

---

### Numbered Markdown Nodes

Located in `numbered_markdown_nodes.py`

#### `NumberedMarkdownTitleNode`

Extends `MarkdownTitleNode` with automatic numbering support.

**Properties**:

- `number: list[int]` - Hierarchical number (e.g., `[1, 2, 3]`)
- `auto_correct: bool` - Auto-correct incorrect numbers

**Features**:

- Parses numbered titles: `# 1.2.3 Title`
- Validates number sequence automatically
- Auto-corrects when `auto_correct=True`

**Example**:

```python
title = NumberedMarkdownTitleNode(
    level=1,
    number=[1],
    title="Introduction",
    auto_correct=True
)
# Renders as: "# 1. Introduction"
```

#### `NumberedMarkdownTextNode`

Extends `MarkdownTextNode` with numbered title parsing.

**Features**:

- Parses outlines with hierarchical numbering
- Validates and auto-corrects number sequences
- Detects structure errors (e.g., `1.2.3` after `1.1`)

#### `NumberedMarkdownTextFileNode`

File-backed node for numbered markdown documents.

---

### Foldable Markdown Nodes

Located in `foldable_markdown_nodes.py`

#### `FoldMode` (Enum)

- `SHOW_TITLE` - Show only title with fold indicators
- `SHOW_CHILD` - Show child titles

#### `FoldableMarkdownTitleNode`

Extends `NumberedMarkdownTitleNode` with collapsible content.

**Properties**:

- `fold_mode: FoldMode` - Current display mode

**Key Methods**:

- `get_text(with_fold_info=True, full_text=False)` - Get text with folding
- `unfold()` - Expand this node
- `recursive_unfold()` - Expand this node and all children
- `set_load_depth(depth)` - Set loading depth for lazy loading

**Example**:

```python
title = FoldableMarkdownTitleNode(
    level=1,
    number=[1],
    title="Chapter 1"
)
title.fold_mode = FoldMode.SHOW_TITLE
# Renders as: "# 1. Chapter 1 [text folded] [5 child title folded]"
```

#### `FoldableMarkdownTextNode`

Extends `NumberedMarkdownTextNode` with foldable titles.

#### `FoldableMarkdownTextFileNode`

File-backed node for foldable markdown documents.

**Note**: Always saves full text regardless of fold mode.

---

### Attributed Markdown Nodes

Located in `attributed_markdown_nodes.py`

#### `AttributedMarkdownTextFileNode`

Extends `FoldableMarkdownTextFileNode` with YAML frontmatter support.

**Generic Type**:

- `T: BaseModel` - Attribute type

**Properties**:

- `attribute: T` - Typed YAML frontmatter

**File Format**:

```markdown
---
status: draft
chapter: 1
word_count: 5000
---
# 1. Chapter 1
Content here...
```

**Key Methods**:

- `save()` - Save with YAML frontmatter
- `reload()` - Parse frontmatter and content

**Example**:

```python
from pydantic import BaseModel

class ChapterAttribute(BaseModel):
    status: str
    chapter: int
    word_count: int

node = AttributedMarkdownTextFileNode(
    file_path=Path("chapter1.md"),
    attribute_type=ChapterAttribute
)
# Access: node.attribute.status
```

---

### Markdown Folder Nodes

Located in `markdown_folder_nodes.py`

#### `MarkdownFolderNode`

Manages a group of numbered markdown files stored in a `.mdf` directory. Each `.mdp` file in the directory represents a first-level markdown section.

**File Format**:

```
.mdf/                       # Directory (extension .mdf)
├── 0.mdp                   # Optional preamble (no level-1 title)
├── 1_Introduction.mdp      # N_[Title].mdp pattern
├── 2_Background.mdp
└── 3_Details.mdp
```

**File Naming Convention**:

- Files must match `N_[Title].mdp` pattern where `N` is an integer number
- `N` maps to the section number: a file named `1_Intro.mdp` contributes `# 1. Intro` as a level-1 heading
- `0.mdp` is reserved for preamble content (text before any level-1 heading)
- Non-matching `.mdp` files raise an exception; non-`.mdp` files are ignored

**.mdp Content Rules**:

- Each `.mdp` file may contain only level-2+ headings (`##` or deeper), never `#` (level 1)
- The level-1 heading is synthesized from the filename number + title
- Preamble file `0.mdp` may contain arbitrary text including level-2+ headings

**Class Structure**:

```python
MarkdownFolderNode(FileNode, TextNode)
    markdown_text_node: NumberedMarkdownTextNode
    file_path: Path         # Points to .mdf directory
```

**Inherits from**: `FileNode`, `TextNode` (same as `MarkdownTextFileNode`)

**Internal Architecture**:

- Contains a `NumberedMarkdownTextNode` as the internal text representation
- On `reload()`: scans `.mdf` dir, constructs synthetic text by prepending `# N. Title\n` before each `.mdp` file's content, feeds the combined text to the parser core
- On `save()`: iterates over level-1 children of the internal tree, maps by number `N` to filenames, then writes/renames/deletes `.mdp` files accordingly
- The first child before any level-1 heading is stored as `0.mdp` (preamble); if no preamble exists, `0.mdp` is deleted

**Key Methods**:

- `reload()` - Scan `.mdf` directory, parse files into tree structure
- `save()` - Write internal tree back to individual `.mdp` files
- `get_text()` - Get combined markdown text from internal tree
- `set_text(text)` - Parse markdown text into internal tree

**File Lifecycle**:

`save()` handles file mapping by number:
| Internal Tree | Disk State | Action |
|---------------|-----------|--------|
| `[1]` → Title: "New" | `1_Old.mdp` exists | Rename to `1_New.mdp` + rewrite |
| `[4]` exists | No `4_*.mdp` exists | Create `4_[Title].mdp` |
| `[3]` removed | `3_Old.mdp` exists | Delete `3_Old.mdp` |
| No preamble | `0.mdp` exists | Delete `0.mdp` |

**Numbering Example**:

```python
# .mdf/1_Introduction.mdp content:
## 1.1 Opening
Text about opening
## 1.2 Thesis
Main argument

# .mdf/2_Background.mdp content:
## 2.1 History
Historical context
## 2.2 Prior Work
Related research

# After reload(), internal tree is equivalent to:
# 1. Introduction
## 1.1 Opening
Text about opening
## 1.2 Thesis
Main argument
# 2. Background
## 2.1 History
Historical context
## 2.2 Prior Work
Related research
```

---

### Foldable Markdown Folder Nodes

Located in `foldable_markdown_folder_nodes.py`

#### `FoldableMarkdownFolderNode`

Extends `MarkdownFolderNode` with foldable content support across all files in the folder.

**Class Structure**:

```python
FoldableMarkdownFolderNode(MarkdownFolderNode)
    markdown_text_node: FoldableMarkdownTextNode
```

**Key Methods**:

- Inherits all methods from `MarkdownFolderNode`
- `get_text(with_fold_info=True, full_text=False)` - Get text with folding applied
- Fold/unfold operations propagate through the entire composite tree

**Save Behavior**:

Always saves full text (regardless of fold mode) back to `.mdp` files, matching the convention established by `FoldableMarkdownTextFileNode`.

---

### Attributed Markdown Folder Nodes

Located in `attributed_markdown_folder_nodes.py`

#### `AttributedMarkdownFolderNode`

Extends `FoldableMarkdownFolderNode` with typed YAML frontmatter stored as a separate `FrontMatter.yaml` file inside the `.mdf` directory.

**Generic Type**: `T: BaseModel` - Pydantic model for folder-level metadata

**Class Structure**:

```python
AttributedMarkdownFolderNode(FoldableMarkdownFolderNode, Generic[T])
    markdown_text_node: FoldableMarkdownTextNode
    attribute: T
    file_path: Path         # Points to .mdf directory
```

**File Format**:

```
.mdf/
├── FrontMatter.yaml        # YAML metadata (typed via Pydantic)
├── 0.mdp                   # Optional preamble
├── 1_Introduction.mdp
└── 2_Background.mdp
```

**FrontMatter.yaml**:

Same content format as inline YAML frontmatter in `AttributedMarkdownTextFileNode`, but stored as a standalone file. Contains folder-level metadata such as author, status, tags, etc.

```yaml
author: test_author
version: 2.0.0
tags:
  - draft
  - fiction
```

**Key Methods**:

- `save()` - Saves `FrontMatter.yaml` and all `.mdp` files
- `reload()` - Loads `FrontMatter.yaml` and all `.mdp` files

---

## Key Features

### 1. Hierarchical Tree Structure

- Parent-child relationships for all nodes
- Easy tree traversal and manipulation
- Deprecation-based node removal

### 2. Markdown Parsing

- Automatic parsing of titles and text
- Code block preservation (``` blocks)
- Configurable root level detection

### 3. Numbered Outlines

- Automatic hierarchical numbering (1, 1.1, 1.1.1)
- Validation and auto-correction
- Support for both numbered and plain titles

### 4. Foldable Content

- Two display modes: title-only or child titles
- Fold indicators: `[text folded]`, `[N child title folded]`
- Lazy loading with depth control

### 5. YAML Frontmatter

- Typed attributes via Pydantic models
- Automatic serialization/deserialization
- Separated from content with `---` delimiters

### 6. File I/O

- Automatic save/reload
- UTF-8 encoding
- Custom file paths

---

## Usage Examples

### Basic Markdown Document

```python
from pathlib import Path
from tree_doc.markdown_nodes import MarkdownTextFileNode

# Load existing file
doc = MarkdownTextFileNode(file_path=Path("chapter.md"))

# Find and modify title
chapter = doc.recursive_find_title_node_by_name("# Chapter 1")
if chapter:
    chapter.add_text("New content here...")

# Save changes
doc.save()
```

### Numbered Outline

```python
from tree_doc.numbered_markdown_nodes import NumberedMarkdownTextNode

outline = NumberedMarkdownTextNode(
    text="""
# 1. Introduction
This is the intro.

# 1.1. Background
Background content.

# 1.2. Motivation
Motivation content.

# 2. Main Content
More content...
""",
    auto_correct=True
)

# Auto-corrects any numbering mistakes
outline.save()
```

### Foldable Document

```python
from tree_doc.foldable_markdown_nodes import (
    FoldableMarkdownTextFileNode,
    FoldMode
)

doc = FoldableMarkdownTextFileNode(file_path=Path("outline.md"))

# Collapse to show only top-level titles
root_titles = doc.markdown_text_node.children
for child in root_titles:
    if isinstance(child, FoldableMarkdownTitleNode):
        child.fold_mode = FoldMode.SHOW_TITLE

# Save (full text is always saved)
doc.save_to_file(Path("collapsed_outline.md"))
```

### Markdown Folder Document

```python
from pathlib import Path
from tree_doc.markdown_folder_nodes import MarkdownFolderNode

# Load a .mdf directory
node = MarkdownFolderNode(file_path=Path("chapter1.mdf"))

# Access combined text
text = node.get_text()

# Find a specific section
section = node.recursive_find_title_node_by_name("## 2.1. History")
if section:
    section.add_text("More historical context...")

# Save changes back to .mdp files
node.save()
```

### Foldable Markdown Folder Document

```python
from pathlib import Path
from tree_doc.foldable_markdown_folder_nodes import (
    FoldableMarkdownFolderNode,
    FoldMode,
)

doc = FoldableMarkdownFolderNode(file_path=Path("outline.mdf"))

# Collapse all top-level sections
root_titles = doc.markdown_text_node.children
for child in root_titles:
    child.fold_mode = FoldMode.SHOW_TITLE

# Save (full text is always saved)
doc.save()
```

### Attributed Folder Document

```python
from pathlib import Path
from pydantic import BaseModel
from tree_doc.attributed_markdown_folder_nodes import AttributedMarkdownFolderNode

class ChapterMeta(BaseModel):
    status: str = "draft"
    word_count: int = 0
    revised: bool = False

# Load .mdf directory with FrontMatter.yaml
node = AttributedMarkdownFolderNode(
    file_path=Path("chapter1.mdf"),
    attribute_type=ChapterMeta
)

# Access/modify metadata
node.attribute.status = "completed"
node.attribute.word_count = 5000
node.attribute.revised = True

# Save FrontMatter.yaml + all .mdp files
node.save()
```

### Attributed Document

```python
from pathlib import Path
from pydantic import BaseModel
from tree_doc.attributed_markdown_nodes import AttributedMarkdownTextFileNode

class ChapterMeta(BaseModel):
    status: str = "draft"
    word_count: int = 0
    revised: bool = False

# Create new attributed file
doc = AttributedMarkdownTextFileNode(
    file_path=Path("chapter1.md"),
    attribute_type=ChapterMeta
)

# Modify attributes
doc.attribute.status = "completed"
doc.attribute.word_count = 5000

# Save with frontmatter
doc.save()
```

---

## Parser Design Pattern

The module uses a **Mixin-based Template Method Pattern** for markdown parsing.

### `_MarkdownParserCore` (`markdown_parser_core.py`)

**Purpose**: Provides fine-grained hooks for markdown parsing.

**Parsing Flow**:

1. `_get_root_level()` - Get root title level
2. `_process_first_line_if_needed()` - Handle first line if needed
3. For each line:
   - `_is_code_block_boundary()` - Detect code blocks
   - `_handle_code_block_line()` - Process code content
   - `_is_title_line()` - Detect title lines
   - `_parse_title_line()` - Parse title (override in subclass)
   - `_validate_title_level()` - Validate level
   - `_create_title_node()` - Create node (override in subclass)
   - `_handle_text_line()` - Process plain text
4. `_flush_cached_text()` - Commit cached text

**Extensibility**:
Subclasses override hooks to customize behavior without duplicating main loop logic.

---

## File Structure

```text
tree_doc/
├── __init__.py                 # Package initialization (empty)
├── Node.py                     # Base Node class
├── text_node.py                # TextNode abstract base
├── file_node.py                # FileNode abstract base
├── plain_text_file_node.py     # PlainTextNode, TextFileNode
├── markdown_parser_core.py     # _MarkdownParserCore Mixin
├── markdown_nodes.py           # Basic markdown nodes
├── numbered_markdown_nodes.py  # Numbered outline support
├── foldable_markdown_nodes.py  # Foldable content support
├── attributed_markdown_nodes.py # YAML frontmatter support
├── markdown_folder_nodes.py     # Folder node base (proposed)
├── foldable_markdown_folder_nodes.py  # Foldable folder nodes (proposed)
├── attributed_markdown_folder_nodes.py # Attributed folder nodes (proposed)
└── README.md                   # This documentation
```

### Dependencies

**Internal**:

- All modules depend on `Node.py`, `text_node.py`, `file_node.py`
- Layer hierarchy: `markdown_nodes` → `numbered_*` → `foldable_*` → `attributed_*`

**External**:

- `pydantic` - Model validation and serialization
- `pydantic_yaml` - YAML frontmatter handling

---

## Best Practices

1. **Type Annotations**: All methods have full type hints (Python 3.13+ syntax)

2. **Node Lifecycle**:
   - Use `addchild()` for adding nodes
   - Use `deprecated=True` + `parent.update()` for removal
   - Use `dispatch()` to orphan nodes

3. **File I/O**:
   - Always use UTF-8 encoding
   - Call `save()` after modifications
   - Use `reload()` to refresh from disk

4. **Folding**:
   - Set `fold_mode` before rendering
   - Use `recursive_unfold()` for full expansion
   - `set_load_depth()` for lazy loading

5. **Numbering**:
   - Enable `auto_correct=True` for forgiving parsing
   - Validate numbering before final output

---

## Testing

Tests located in `test/` directory:

- `test_markdown_nodes.py` - Basic markdown node tests
- `test_foldable_markdown_nodes.py` - Folding behavior tests
- `test_numbered_markdown_nodes.py` - Numbering validation tests
- `test_markdown_folder_nodes.py` - Folder node tests (proposed)
- `test_foldable_markdown_folder_nodes.py` - Foldable folder node tests (proposed)
- `test_attributed_markdown_folder_nodes.py` - Attributed folder node tests (proposed)

Run tests:

```bash
uv run pytest test/test_markdown_nodes.py
uv run pytest test/test_foldable_markdown_nodes.py
```

---

## License

Part of the novelWriter project.
