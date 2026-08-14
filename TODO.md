# TODO

## 已记录问题（暂不修复）

### 性能：set_text/add_text 全树深拷贝（#13）

`MarkdownTitleNode._parse_markdown` 对非根节点调用时执行 `copy.deepcopy(self)`，
每次 `set_text`/`add_text` 都会深拷贝整个子树。对大型文档多次增量修改呈二次复杂度。

可能的改进方向：复用现有标题节点、仅重建受影响的子树。

### reload() 后基于身份（identity）的权限条目失效

`PermissionChecker` 的权限条目以节点对象身份（`is` 比较）为键。
调用 `reload()` 会重建节点树，旧节点对象被替换，已有权限条目随之失效。
需重新登记权限条目。