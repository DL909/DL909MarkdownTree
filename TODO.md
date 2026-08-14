# TODO

## 已记录问题（暂不修复）

### reload() 后基于身份（identity）的权限条目失效

`PermissionChecker` 的权限条目以节点对象身份（`is` 比较）为键。
调用 `reload()` 会重建节点树，旧节点对象被替换，已有权限条目随之失效。
需重新登记权限条目。