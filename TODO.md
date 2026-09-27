# TODO

代码走查结果。基线：`375 passed`（pytest）、`ruff check` 通过、`pyright` 报 27 个错误。
下文每条都附最小复现（`sys.path` 已含 `src`），均已实际跑过。

> **全部 23 项已处理完毕。** 每条下方标注了修复它的提交。
> 当前状态：`461 passed`、`ruff check` 与 `ruff format --check` 通过、
> `pyright src` 仅剩 8 个 `reportMissingImports`（本地 venv 未装可选依赖
> `pydantic_yaml` / `commitizen` / `langchain_core` / `fastmcp`，CI 装齐后为 0）、
> 覆盖率 99%（剩余 4 行为抽象方法 `pass` 体，不可达）。
>
> 其中 **第 12 项是公开行为变更**：`set_text()` / `from_text()` 不再因空标题行
> 抛错，该行按正文保留并告警；`from_line()` 仍严格拒绝。详见 `USAGE.md` 4.2。

---

## P0 — 正确性 / 安全

### 1. `unfold_tool` 用 `READ` 权限执行了写盘操作（权限绕过）

> **已修复** — `91c55cc`：unfold_tool 改用 READ_WRITE。


`src/dl909markdowntree/extra/tools.py:101` 校验 `Permission.READ`，随后 `node.unfold()`
改内存态并调用 `markdown_node.save()`。对文件夹节点这会真的往磁盘写文件。

```python
node = FoldableMarkdownFolderNode(d)                      # d/1_Alpha.mdp
target = node.get_root_title().recursive_find_title_node_by_name("# 1. Alpha")
checker = NodePermissionChecker([(target, Permission.READ)])
before = sorted(p.name for p in d.iterdir())
unfold_tool(node, checker, "# 1. Alpha")
# dir before: ['1_Alpha.mdp'] -> after: ['1_Alpha.mdp', 'fold_state.json']
```

只读主体可以创建/覆盖磁盘文件。**改用 `Permission.READ_WRITE`**。

### 2. `rename_title_tool` 不校验 `new_title_name`，可注入伪造标题

> **已修复** — `91c55cc`：拒绝空标题与含换行的标题。


`extra/tools.py:187` 直接 `node.title = new_title_name`，未拒绝换行 / `#`。

```python
rename_title_tool(f, None, "# 1. A", "Injected\n\n# 9. Sneaky\nowned")
# 返回 "rename_title succeeded"，落盘文件变成：
#   # 1. Injected
#   # 9. Sneaky
#   owned
#   body A
# 再次 parse 时 "# 9. Sneaky" 就是货真价实的一级标题
```

`title` 字段里还真的存进了带换行的字符串。**校验：无换行、无 `#` 开头前缀、strip 后非空**；
`replace_tool` / `append_tool` 的 `*_text` 参数也应有同类检查（目前只靠解析期抛错兜底）。

### 3. `add_text()` 在空文本上抛 `IndexError`

> **已修复** — `8bd843e`：空文本提前返回。


`markdown_nodes.py:188` 与 `foldable_markdown_nodes.py:66` 都是
`current_text[-1] != "\n" and text[0] != "\n"`，两个下标在空串上都会炸。

```python
node = NumberedMarkdownTitleNode(level=0)     # get_text() == ""
node.add_text("body")                        # IndexError: string index out of range
node.add_text("\nbody")                      # 同上
node.add_text("", ensure_new_line=False)     # 同上（text[0] 越界）
node.add_text("body", ensure_new_line=False) # 同样（text[0] 越界）
```

新建的空节点 / 空文档走 MCP `append` 即可触发。
**改用 `current_text.endswith("\n")` 和 `text.startswith("\n")`。**

### 4. 文件夹节点没有 `children` 属性，`Node.update()` 直接崩

> **已修复** — `9d78a32`：构造时初始化 children。


`markdown_folder_nodes.py:31-56` 的 `__init__` 自己赋值 `self.file_path`，
**从未调用 `super().__init__()`**，因此 `Node.__init__` 里 `self.children = []` 没执行。
`children` 只是类注解，没有类级默认值兜底。

```python
node = NumberedMarkdownFolderNode(d)
node.children     # AttributeError: 'NumberedMarkdownFolderNode' object has no attribute 'children'
node.update()     # 同样 AttributeError（update() 是 Node 基类的公开 API）
```

`FoldableMarkdownFolderNode` / `AttributedMarkdownFolderNode` 一并继承此问题。
**在 `__init__` 开头补 `super().__init__(file_path=file_path)`**（注意 MRO 会走到
`FileNode.__init__`，需确认不会与现有赋值冲突），或给 `Node.children` 加类级默认值 `= []`…—
不过类级可变默认值有共享风险，优先补 `super().__init__()`。

### 5. `TitlePathPermissionChecker` 的条目在重命名后静默失效，DENY 被绕过

> **已修复** — `d2d5fa7`：改名时重解析整棵子树的条目。


`permissions.py:193-222` 以「标题文本元组」为键。`rename_title` 改了标题，
旧路径再也匹配不上，节点回落到祖先/默认——**原本 DENY 的节点变成可读**。

```python
checker = TitlePathPermissionChecker([(a, Permission.DENY), (root, Permission.READ_WRITE)])
checker.check_permission(a, Permission.READ)      # (False, "...权限...DENY")
rename_title_tool(f, None, "# 1. A", "A2")
checker.check_permission(a2, Permission.READ)     # (True, '')   ← DENY 条目静默失效
```

docstring 只声明了「`reload()` 后仍有效」，没提重命名/移动同样会失效。
两个方向都要做：**要么**在工具里对目标节点的写操作连带校验并迁移/拒绝，
**要么**把 `NONE`/缺失时的回落从「默认 DENY」改成显式报错，避免静默放行。

### 6. `read_tool` 返回折叠占位符而非正文

> **已修复** — `91c55cc`：读取折叠节点时取 full_text。


`extra/tools.py:47` 调 `node.get_text()`，对 `FoldableMarkdownTitleNode` 走的是
`with_fold_info=True, full_text=False` 的折叠视图；而工具签名写的是
「读取全文或指定标题段落」。

```python
a = f.get_root_title().recursive_find_title_node_by_name("# 1. A")
a.fold_mode = FoldMode.SHOW_TITLE
read_tool(f, None, "# 1. A")
# '# 1. A [text folded] [1 child title folded]'     ← 实际内容 "SECRET BODY A" 和子标题都没了
```

同一文件里 `replace_lines_tool` 已经特意用 `_get_full_text()` 了（见 tools.py:126），
`read_tool` 没跟上。**改用 `_get_full_text(node)`**，或给 `read` 加显式的
`full_text: bool` 参数。

---

## P1 — 健壮性 / 数据保真

### 7. 单文件 `FoldableMarkdownTextFileNode` 的折叠状态完全不持久

> **已修复** — `1fe76da`：按用户决定不持久化，改为在 USAGE.md 6.5 声明该限制。


文件夹节点靠 `fold_state.json`（`foldable_markdown_folder_nodes.py:96-105`），
单文件节点没有任何等价机制，`save()` 写出的就是全展开文本。

```python
f = FoldableMarkdownTextFileNode(p)
a3 = f.get_root_title().recursive_find_title_node_by_name("# 1. A")
a3.unfold_by_depth(99)      # 全部展开
f.save(); f.reload()
f.get_root_title().recursive_find_title_node_by_name("# 1. A").fold_mode
# SHOW_TITLE  ← 展开状态丢失
```

MCP `unfold` 工具对单文件实际上是不可持久的。
**方案**：在 `FoldableMarkdownTextFileNode` 里同样落一份旁路状态文件（需确认不会污染用户的 .md），
或在文件头加 HTML 注释形式的折叠标记。

### 8. 文件夹每次 save 都吞掉所有 `.mdp` / `0.mdp` 的结尾换行

> **已修复** — `6c431dc`：统一归一化，保留结尾换行。


`markdown_folder_nodes.py:94` 的 `.rstrip("\n")` 对每个 section 生效。
结果是**每次保存都产生一次与用户无关的 diff**。

```python
(d / "1_A.mdp").write_text("body\n")
(d / "0.mdp").write_text("intro\n")
n = NumberedMarkdownFolderNode(d); n.save()
# 0.mdp:  'intro\n' -> 'intro'
# 1_A.mdp:'body\n'  -> 'body'
```

section 内部的尾部空行同样被吃掉：`"# 1. A\nline1\n\n\n## 2. B\nsub\n"` 往返后变成
`"# 1. A\nline1\n\n\n## 1.1. B\nsub"`（末尾换行没了）。
**明确约定**（保 trailing newline / 统一 strip），并补往返一致性测试。

### 9. `.mdp` 文件名消毒有损，且静默改写用户标题

> **已修复** — `6c431dc`：消毒有损时输出 warning。


`markdown_folder_nodes.py:22-23` 把 `/ : * ? " < > |` 和控制字符替换成 `_`，
**不可逆且无任何提示**。

```python
n.set_text("# 1. a/b:c\nbody\n"); n.save()
# 目录里: 1_a_b_c.mdp
n.reload(); n.get_root_title().children[0].get_title()   # '# 1. a_b_c'  ← 原文永久丢失
```

**至少**：在标题被改写时 `logger.warning`（模块里已有 logger 先例）；更好的做法是
在正文里保留原标题、只让文件名退化。

### 10. `AttributedMarkdownTextFileNode` 缺 `markdown_text_node_type`

> **已修复** — `418a859`：补上 markdown_text_node_type 声明。


该类（`attributed_markdown_nodes.py:18-22`）直接继承 `AttributedMarkdownTextFileBase`，
没有经过 `MarkdownTextFileNode`，因此拿不到基类里定义的
`markdown_text_node_type = MarkdownTitleNode`（`markdown_nodes.py:195`）。
它自己重写了 `reload()` 所以目前没炸，但 `hasattr(node, "markdown_text_node_type")` 为 `False`，
任何走基类 `reload()` 的代码路径都会 `AttributeError`。

```python
AttributedMarkdownTextFileNode(p, attribute_type=Meta)
# hasattr(node, "markdown_text_node_type") -> False
```

**显式声明 `markdown_text_node_type = FoldableMarkdownTitleNode`**，或调整继承链。

### 11. `_split_frontmatter` 拒绝「结尾无换行」的合法 frontmatter

> **已修复** — `418a859`：接受结尾无换行的 frontmatter。


`attributed_markdown_nodes.py:69` 只找 `"\n---\n"`，文件以 `---` 结尾且无换行时误报。

```python
p.write_text("---\nowner: me\n---")     # 合法 YAML frontmatter，只是没尾换行
AttributedMarkdownTextFileNode(p, attribute_type=Meta)
# MarkdownTreeError: 文件缺少 FrontMatter 结束标记 '---'   ← 实际存在，且报错信息误导
```

**补一条 `content.rstrip()` 后的匹配分支**，并把错误信息改成带上文件路径。

### 12. 裸 `# ` 行会让整篇文档解析失败（检测/解析两条正则不一致）

> **已修复** — `503ee1b`：检测与解析统一走 _TITLE_LINE_PATTERN；**公开行为变更**。


`markdown_nodes.py:115` 用 `^#{1,6} ` 判断「这是标题」，
`markdown_nodes.py:29` 用 `^(#{1,6}) (.+)$` 解析。`# `（空标题）能过前者、过不了后者。

```python
MarkdownTitleNode.from_text("# 1. Title\nbody\n\n# \n\n## 2. Sub\nmore\n")
# InvalidMarkdownLineError: invalid Markdown title line: #
```

一行空标题把**整篇文档**的解析打断了。**让检测和解析共用同一条正则**，
或对 `(.+)` 用 `(.*)` 并在解析后拒绝空标题为「普通文本」。

### 13. `NumberedMarkdownFolderNode(markdown_text_node=...)` 传参被静默丢弃

> **已修复** — `83e9a36`：传入的节点即最终状态，落盘后不再 reload。


`markdown_folder_nodes.py:52-56` 先 `save()`，紧接着无条件 `self.reload(auto_correct)`，
而 `reload()` 会用磁盘内容**整个替换** `self.markdown_text_node`（`markdown_folder_nodes.py:100-105`）。

```python
new_root = NumberedMarkdownTitleNode.from_text("# 5. Injected\ninjected body\n")
n = NumberedMarkdownFolderNode(d, markdown_text_node=new_root)
n.get_root_title() is new_root   # False —— 调用方拿回的是另一个对象
n.get_root_title().get_text()    # '# 1. Injected\ninjected body'（编号还被 auto_correct 改了）
```

**要么**传入时跳过 reload，**要么**在签名里去掉这个形参。当前行为是「写进去了但没告诉你」。

### 14. 异常类型外泄，调用方无法用单一类型兜底

> **已修复** — `418a859`：新增 MarkdownFileError / InvalidFrontMatterError。


`MarkdownTreeError` 家族定义得很好，但多条路径会漏出原始异常：

- `attributed_markdown_folder_nodes.py:79` / `attributed_markdown_nodes.py:84`：
  `FrontMatter.yaml` 损坏时直接抛 `pydantic_yaml.ParserError`（不是 `MarkdownTreeError`）。
- `MarkdownTextFileNode.save_to_file`（`markdown_nodes.py:210`）/ `reload`（`:230`）：
  裸 `open()` → `OSError` / `UnicodeDecodeError`。
- `markdown_folder_nodes.py:110`：`file_path.mkdir(parents=True)` 缺 `exist_ok=True`，
  竞态下抛 `FileExistsError`。

**在公开入口统一 `except Exception → raise MarkdownTreeError(...) from e`**
（读文件路径尤其需要，参见 `tools.py:12` 已有的 `_TOOL_OPERATION_ERRORS` 约定）。

### 15. `Node.from_self` 产出的副本，其子节点 `parent` 仍指向原对象

> **已修复** — `83e9a36`：副本接管共享子节点并重挂 parent。


`node.py:21-28` 用 `copy.copy` + `list(origin.children)`：列表是新的，**元素对象是共享的**，
且 `child.parent` 没有跟着改。副本因此是一棵「反向」的树。

```python
a = NumberedMarkdownTitleNode.from_text("# 1. A\nbody\n")
b = NumberedMarkdownTitleNode.from_self(a)
kid = a.children[0]
kid.parent is a      # True
kid.parent is b      # False  ← 副本的子节点指着原节点
kid.dispatch()       # 从副本摘除一个孩子
a.children           # []    ← 原树被清空了
b.children           # [kid] ← 孩子还在副本里
```

当前 `_parse_markdown` 总是用 `from_self(self, children=[])` 覆盖 children，所以没暴露；
但 `from_self` 是公开 API，`NumberedMarkdownTitleNode.from_self` 还覆写了它。
**要么在 `from_self` 里重挂 `child.parent = result`，要么改名/文档化为私有**。

### 16. `replace_lines_tool` 的空串分支是死代码，模糊匹配可能替换错位置

> **已修复** — `845c758`：空串先判；模糊替换改按行号切片。


- `tools.py:137-138` 的 `if old_count == 0: return "...old_lines is empty"` 不可达——
  非空文本里 `"...".count("")` 恒 ≥ 2，会在 `tools.py:160` 的 `match_count > 1` 提前返回，
  用户看到的是莫名其妙的 "15 matches found"。
  ```python
  replace_lines_tool(f, None, "# 1. A", "", "INSERTED")
  # 'replace_lines failed: 15 matches found, provide more context'
  ```
- `tools.py:152` 模糊分支用 `current_text.replace(matched, new_lines, 1)`，
  替换的是**第一次出现**的位置，而 `best_start` 是逐行扫描出来的最优位置，两者不一定一致。
  ```python
  # 正文: "# 1. A\nrepeat me\nrepeat me\nrepeat me\n"，old_lines="repat me"
  replace_lines_tool(...)   # -> 改掉了第 1 行，而匹配打分选中的是第 2 行
  ```
  **改成按行号切片替换**（`"".join(current_lines[:best_start] + [new_lines] + current_lines[best_end:])`）。

### 17. 工具的失败回滚自身不受保护，可能二次抛错

> **已修复** — `845c758`：统一 _commit()，回滚失败记日志并返回原始错误。


`tools.py:68-70 / 88-90 / 155-157 / 170-172 / 190-192` 一律是
`except ...: node.set_text(old_text); return "xxx failed"`。
`set_text(old_text)` 是在 `except` 块里裸调的，一旦它再抛，异常会穿透工具函数，
且此时节点已处于半改状态。**把回滚包在 `try/except` 里并记日志**。

---

## P2 — 工程质量 / 性能

### 18. 缺 `[tool.pyright]` 配置，CI 的 `pyright src/` 步骤必挂

> **已修复** — `fb2b514`：补 [tool.pyright] 并把 ruff format 纳入 CI。


`pyproject.toml` 没有 `[tool.pyright]`，pyright 拿不到 `pythonVersion`，
于是对 3.12 才有的语法（`class Foo[T: BaseModel]` PEP 695）和 `typing.Self` / `typing.override`
（3.12 才加入 `typing`）全部报错。本地实测：**27 errors**；
加 `--pythonversion 3.12` 后只剩 8 个 `reportMissingImports`（本地 venv 缺可选依赖，
CI 里 `uv sync --all-extras` 会装上）。

```toml
[tool.pyright]
pythonVersion = "3.12"
include = ["src"]
```

顺带：CI 只跑 `ruff check src/`，**不跑 `ruff format --check`**，
而 `ruff format --check src` 现在就有 5 个文件不合规
（`markdown_folder_nodes.py`、`extra/tools.py` 等）。要么补 `ruff format` 到 CI，要么显式声明不格式化。

### 19. `NodePermissionChecker._find_effective_permission` 是 O(深度 × 条目数) 线性扫描

> **已修复** — `237484c`：改为 id(node) -> Permission 索引，实测快约 400 倍。


`permissions.py:136-151` 每一层向上都把整个 `_permissions` 列表扫一遍，且用 `is` 比较。

```python
# 4721 个节点全部登记为 READ，探测其中 400 个
# 400 checks took 0.070s (0.17 ms/check)
```

大文档上 MCP 工具逐节点校验会明显变慢。
**改用 `id(node) -> Permission` 字典**，查找降为 O(深度)。
（注意 `id()` 需防对象回收后复用——持有节点引用即可。）

### 20. `Permission.NONE` 可以被登记为授权值，且凌驾一切

> **已修复** — `237484c`：set_permissions 拒绝 NONE 作为授权值。


`permissions.py:32` 里 `NONE = 3`，docstring 说「仅用于工具声明」，
但它是公开枚举、可以进 `set_permissions`，而 `check_permission` 用 `>=` 比较
（`permissions.py:71`）——一旦某节点被授予 `NONE`，任何 `required` 都通过。

```python
c = NodePermissionChecker([(a, Permission.NONE), (root, Permission.READ)])
c.check_permission(a, Permission.READ_WRITE)   # (True, '')  ← 等于完全放行
```

**要么**把 `NONE` 从授权取值里排除（`set_permissions` 里校验），
**要么**拆成独立的 `Bypass` 标记、不参与数值比较。

### 21. `NumberedMarkdownFolderNode.reload` 签名违反 LSP

> **已修复** — `83e9a36`：reload() 回到无参签名，另加 reload_with(auto_correct)。


`markdown_folder_nodes.py:100` 是 `reload(self, auto_correct: bool | None = None)`，
基类 `FileNode.reload(self)`（`file_node.py:19`）无参。
带 `@override` 却扩了签名，静态检查只能靠 `pyright: ignore` 压掉。
**改成 `reload(self)` + 单独一个 `reload_with(auto_correct)`**，
或把 `auto_correct` 提到构造期字段（`self.auto_correct` 本来就存了，却没被 `reload` 读取）。

### 22. 其它小问题

> **已修复** — `766e05b / 3bc5aa0`：number 改拷贝、get_title 用 join、补全类型标注、save_to_file 化简。


- `attributed_markdown_folder_nodes.py:48-49` 与 `:64-65`：`self.attribute` 在 `__init__`
  里被赋值两次（`super().__init__()` 前后各一次），后者是死代码。
- `numbered_markdown_nodes.py:131`：`self.number = origin.number` 共享同一个 list 对象。
  `origin` 通常是临时对象所以没暴露，但 `from_self` 里对 `number` 做了 `list()` 拷贝，
  这里没跟上，行为不一致。
- `markdown_folder_nodes.py:38`：`self.auto_correct` 赋值后从未被读取。
- `markdown_folder_nodes.py:60-86` / `:145-192`：`save_to_file` 里的重命名逻辑
  （`for ... if old_path == target_path: break` + 后续删除循环）绕且难验证，
  建议改成「目标名 → 源名」的显式映射，一次性算清楚再落盘。
- `numbered_markdown_nodes.py:118-126`：`get_title` 用循环拼字符串，改为 `"".join` / f-string。
- `markdown_nodes.py:106`：`rf"^{fence_char}{{{fence_run},}}\s*$"` 在**每行**循环里重新
  拼字符串（实测 2 万行解析仅 11ms，暂时不痛，建议顺手提为模块级常量）。
- `interface.py:93-95`：`get_text(self, with_fold_info: bool = True, full_text=False)`
  —— `full_text` 没写类型注解（其余地方都写了 `bool`）。
- `interface.py:126` `AttributedMarkdownTextFileBase[T: BaseModel]` 与
  `attributed_markdown_nodes.py:18` 的泛型写法重复；`attributed_markdown_nodes.py:15`
  的模块级 `T = TypeVar(...)` 和它并存，容易混用。
- `text_node.py:17 / file_node.py:15-20`：`set_text(self, text)` 缺类型注解；
  `get_text`/`set_text` 的 `-> str` 在 `text_node.py` 有、`plain_text_nodes.py:39` 又漏了。

### 23. 测试与文档缺口

> **已修复** — `1fe76da / 18017ca`：补 cz_plugin 与各分支测试，覆盖率 97% -> 99%。


- `cz_plugin.py` 覆盖率 **0%**（15 行全未执行），CI 里 `cz_dl909` 入口点无人验证。
- 覆盖率未接进 CI（`.github/workflows/release.yml` 只跑 `pytest -q`，
  `pyproject.toml` 也没配 `--cov`），建议加 `--cov=src --cov-fail-under`。
- 未覆盖的关键分支：`extra/tools.py:123,138,155-157`（找不到标题 / 空 `old_lines` / 模糊匹配回滚）、
  `markdown_folder_nodes.py:53,110,113,133,212`、`foldable_markdown_folder_nodes.py:73-74,105`、
  `permissions.py:93,204`。
- `README.md` 只有 3 行；`USAGE.md`（25 KB）没有覆盖
  「文件夹往返会改写文件名 / 吞尾换行」「单文件不持久化折叠态」
  「`TitlePathPermissionChecker` 在重命名后失效」这三条**反直觉行为**。
- 解析器的简化假设（只认 1–6 级 ATX 标题、不支持 setext、不支持 0–3 空格缩进、
  `##` 结尾的闭合井号会被并进标题文本）应在 USAGE.md 显式声明为「有意为之」。

---

## 已核查、判定无需改动

- `Node.update()` 反向遍历删除 deprecated 子节点、`dispatch()` 的父链摘除：逻辑正确。
- `NodePermissionChecker` / `TitlePathPermissionChecker` 的 DENY 绝对生效与默认拒绝回落：符合 docstring。
- `cz_plugin.py` 的 commit 解析正则：与 `ConventionalCommitsCz` 语义一致。
- `mcp/server.py` / `langchain/toolkit.py`：仅做薄封装，无重复逻辑；toolkit 的
  `PermissionError` → 字符串降级处理得当。
