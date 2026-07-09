# Tools 模块 - 权限控制的工具调用系统

基于路径的细粒度权限控制工具系统，支持树形结构继承。

---

## 目录结构

```bash
core/tools/
├── __init__.py           # 模块导出
├── permissions.py        # 权限管理核心
├── registry.py           # 工具注册表和装饰器
├── context.py            # 工具执行上下文
├── markdown_edit_tools.py # Markdown 编辑工具集
└── README.md             # 本文档
```

---

## 快速开始

### 基础用法（无权限控制）

```python
from core.tools import ToolRegistry, ToolContext, tool

@tool
def my_tool(markdown_file_node, arguments: dict) -> str:
    """工具描述"""
    return "执行结果"

registry = ToolRegistry()
registry.register(my_tool)

context = ToolContext(markdown_file_node=node)
result, success, should_end = registry.execute("my_tool", context, {})
```

### 权限控制用法

```python
from core.tools import Permission, PermissionToolRegistry, ToolContext
from core.tools.markdown_edit_tools import create_markdown_edit_tools_registry

# 方式 1: 直接使用 PermissionToolRegistry
registry = PermissionToolRegistry(permissions=[
    (volume_node, Permission.READ_WRITE),   # 卷节点可读写
    (setting_node, Permission.READ),        # 设定节点只读
    (chapter_node, Permission.DENY),        # 章节节点禁止访问
])

# 动态添加权限
registry.add_permission(new_node, Permission.READ)
registry.remove_permission(chapter_node)

# 注册工具
registry.register(read)
registry.register(replace)

# 执行时自动检查权限
context = ToolContext(markdown_file_node=markdown_file_node)
result, success, _ = registry.execute("replace", context, {"target": "### 1.2 标题"})
# 权限不足时返回：
# ("权限不足：节点'### 1.2 标题'需要 WRITE 权限，但当前对该节点的权限为 READ", False, False)

# 方式 2: 使用工厂函数
registry = create_markdown_edit_tools_registry(
    permissions=[
        (volume_node, Permission.READ_WRITE),
        (setting_node, Permission.READ),
    ]
)
```

---

## 权限系统详解

### 权限级别（`Permission` 枚举）

| 权限级别 | 数值 | 说明 |
| ---------- | ------ | ------ |
| `DENY` | 0 | 不可读写 |
| `READ` | 1 | 可读不可写 |
| `READ_WRITE` | 2 | 可读可写 |
| `NONE` | 3 | 跳过权限检查（仅用于工具声明） |

### 权限继承规则

1. **权限列表为空** → 所有节点默认为 `READ_WRITE`（全部允许）
2. **权限列表非空** → 根节点默认为 `DENY`（拒绝）
3. **未显式设置的节点** → 继承父节点的权限
4. **权限比较** → `node_permission >= tool_required_permission` 时允许

示例：

```bash
文档（根节点）
├── 卷 1（READ_WRITE）
│   ├── 章节 1.1（继承 READ_WRITE）
│   └── 章节 1.2（READ - 只读）
│       └── 小节 1.2.1（继承 READ）
└── 卷 2（DENY - 禁止访问）
    └── 章节 2.1（继承 DENY）
```

### 权限检查流程

```text
1. 检查工具的 required_permission
   ↓
2. 如果是 NONE → 跳过检查，始终允许
   ↓
3. 从工具参数中提取 target 节点
   ↓
4. 在权限列表中查找该节点
   ↓
5. 如果未找到 → 向上遍历父节点
   ↓
6. 如果到根节点仍未找到 → 返回 DENY（列表非空时）
   ↓
7. 比较节点权限与工具所需权限
   ↓
8. 返回检查结果（成功/失败 + 错误消息）
```

---

## 核心类 API

### `PermissionChecker`

权限检查器，负责根据权限列表和继承规则检查节点权限。

```python
from core.tools.permissions import PermissionChecker, Permission

# 创建检查器
checker = PermissionChecker([
    (node1, Permission.READ),
    (node2, Permission.READ_WRITE),
])

# 设置权限
checker.set_permissions([(node1, Permission.READ_WRITE)])

# 检查权限
success, error_msg = checker.check_permission(node, Permission.WRITE)
# 返回：(True, "") 或 (False, "权限不足：节点 XXX 需要 WRITE 权限...")
```

### `Tool`

表示一个可被 LLM 调用的工具。

```python
from core.tools.registry import Tool

tool = Tool(
    name="my_tool",
    description="工具描述",
    parameters_schema={"type": "object", "properties": {}},
    func=my_function,
    must_use_time=1,       # 必须使用次数
    end_after_use=False,   # 使用后是否终止循环
)
```

### `@tool` 装饰器

将函数声明为工具。

```python
from core.tools import tool, Permission
from pydantic import BaseModel, Field

# 基础用法
@tool
def simple_tool(arguments: dict) -> str:
    """工具描述"""
    return "结果"

# 自定义名称和描述
@tool(name="custom_name", description="自定义描述")
def my_tool(arguments: dict) -> str:
    return "结果"

# 使用 Pydantic 参数模型
class MyArguments(BaseModel):
    target: str = Field(..., description="目标标题")
    content: str = Field(..., description="内容")

@tool(param_model=MyArguments)
def typed_tool(arguments: MyArguments) -> str:
    return f"处理 {arguments.target}"

# 声明权限需求（仅 PermissionToolRegistry 使用）
@tool(required_permission=Permission.READ)
def read_tool(arguments: dict) -> str:
    return "读取结果"

@tool(required_permission=Permission.WRITE)
def write_tool(arguments: dict) -> str:
    return "写入结果"
```

### `ToolRegistry`

基础工具注册表，不包含权限控制。

```python
from core.tools import ToolRegistry

registry = ToolRegistry()

# 注册工具
registry.register(my_tool)

# 获取工具
tool = registry.get("my_tool")

# 获取所有工具
all_tools = registry.get_all()

# 转换为 OpenAI API 格式
openai_tools = registry.to_openai_tools()

# 执行工具
result, success, should_end = registry.execute("my_tool", context, arguments)

# 合并注册表
combined = registry.merge(other_registry)

# 重置使用次数
registry.reset()
```

### `ToolCheck` 检查系统

`ToolCheck` 是一个函数类型别名，用于在工具调用循环退出前执行自定义检查。

```python
from core.tools import ToolCheck, ToolRegistry, ToolContext, default_must_use_check

type ToolCheck = Callable[[ToolRegistry, ToolContext], str | None]
```

**返回值语义**：
- 返回 `None` → 检查通过，循环正常退出
- 返回 `str` → 该字符串作为 system message 注入，循环继续

**默认 must_use 检查**：

`default_must_use_check` 是内置的默认检查函数，验证所有设置了 `must_use_time` 的工具是否已达到指定使用次数。

```python
from core.tools import default_must_use_check

result = default_must_use_check(registry, context)
# 返回 None（全部达标）或 str（未达标的提示信息）
```

**自定义检查示例**：

```python
def my_custom_check(registry: ToolRegistry, context: ToolContext) -> str | None:
    """自定义检查：确保特定工具至少被调用过一次"""
    tool = registry.get("my_special_tool")
    if tool and tool.use_time == 0:
        return "my_special_tool 必须至少被调用一次"
    return None

# 传入 check_list
from core.llm_client import tool_loop

messages = tool_loop(
    messages=messages,
    registry=registry,
    context=context,
    check_list=[my_custom_check],
)
```

### `PermissionToolRegistry`

扩展的注册表，支持权限控制。

```python
from core.tools import Permission, PermissionToolRegistry

# 创建时设置权限
registry = PermissionToolRegistry(permissions=[
    (node1, Permission.READ_WRITE),
    (node2, Permission.READ),
])

# 或创建后设置
registry = PermissionToolRegistry()
registry.set_permissions([(node1, Permission.READ)])

# 动态添加权限
registry.add_permission(node3, Permission.READ_WRITE)

# 移除权限（恢复继承）
registry.remove_permission(node2)

# 执行时自动检查权限
result, success, _ = registry.execute("read", context, {"target": "### 标题"})
```

### `ToolContext`

工具执行上下文，封装工具执行所需的各种资源。

```python
from core.tools import ToolContext

# 创建上下文
context = ToolContext(
    markdown_file_node=markdown_file_node,
    extra_resource1=value1,
    extra_resource2=value2,
)

# 添加资源
context.add_resource("my_resource", value)

# 获取资源
value = context.get_resource("my_resource", default=None)

# 获取所有可用资源名称
names = context.available_resources
```

---

## 内置 Markdown 编辑工具

### 工具列表

| 工具 | 权限需求 | 说明 |
| ------ | ---------- | ------ |
| `read` | `READ` | 读取文档内容 |
| `unfold` | `READ` | 展开折叠的标题 |
| `replace` | `WRITE` | 替换标题内容 |
| `replace_lines` | `WRITE` | 替换特定行 |
| `append` | `WRITE` | 追加内容 |

### 使用示例

```python
from core.tools.markdown_edit_tools import (
    read, replace, append, unfold, replace_lines,
    create_markdown_edit_tools_registry
)

# 创建包含所有工具的注册表
registry = create_markdown_edit_tools_registry(
    allow_replace=True,
    allow_append=True,
    allow_unfold=True,
    allow_read=True,
    allow_replace_lines=True,
    permissions=[
        (volume_node, Permission.READ_WRITE),
        (setting_node, Permission.READ),
    ]
)

# read 工具：读取内容
registry.execute("read", context, {})  # 读取整个文档
registry.execute("read", context, {"target": "### 1.2 标题"})  # 读取特定标题

# unfold 工具：展开折叠
registry.execute("unfold", context, {"target": "### 1.2 标题"})

# replace 工具：替换内容
registry.execute("replace", context, {
    "target": "### 1.2 标题",
    "replace_text": "新内容"
})

# append 工具：追加内容
registry.execute("append", context, {
    "target": "### 1.2 标题",
    "append_text": "追加的内容"
})

# replace_lines 工具：替换特定行
registry.execute("replace_lines", context, {
    "target": "### 1.2 标题",
    "old_lines": "原文本",
    "new_lines": "新文本"
})
```

---

## 错误处理

### 权限错误

当权限检查失败时，返回格式统一的错误消息：

```text
权限不足：节点{节点描述}需要{权限名称}权限，但当前对该节点的权限为{实际权限}
```

示例：

```python
result, success, _ = registry.execute("replace", context, {...})
if not success:
    print(result)  # "权限不足：节点'### 1.2 标题'需要 WRITE 权限，但当前对该节点的权限为 READ"
```

### 节点描述格式

- 根节点：`"根节点"`
- 有 title 属性的节点：`"'{title}'"`
- 有 name 属性的节点：`"'{name}'"`
- 其他节点：`"<{类型名}>"`

---

## 最佳实践

### 1. 选择合适的注册表

```python
# 不需要权限控制 → 使用 ToolRegistry
registry = ToolRegistry()

# 需要权限控制 → 使用 PermissionToolRegistry
registry = PermissionToolRegistry(permissions=[...])

# Markdown 编辑工具 → 使用工厂函数
registry = create_markdown_edit_tools_registry(permissions=[...])
```

### 2. 权限配置策略

```python
# 策略 1: 白名单模式（推荐）
# 只显式允许特定节点，其他全部拒绝
registry = PermissionToolRegistry(permissions=[
    (allowed_node, Permission.READ_WRITE),
])
# 未设置的节点默认为 DENY

# 策略 2: 黑名单模式
# 只显式拒绝特定节点，其他全部允许（空权限列表）
registry = PermissionToolRegistry()  # 默认为 READ_WRITE

# 策略 3: 混合模式
registry = PermissionToolRegistry(permissions=[
    (volume_node, Permission.READ_WRITE),   # 卷节点可读写
    (setting_node, Permission.READ),        # 设定节点只读
    (secret_node, Permission.DENY),         # 机密节点禁止
])
```

### 3. 工具权限声明

```python
# 只读工具
@tool(required_permission=Permission.READ)
def read_data(arguments: dict) -> str: ...

# 写入工具
@tool(required_permission=Permission.WRITE)
def write_data(arguments: dict) -> str: ...

# 不需要权限检查的工具
@tool(required_permission=Permission.NONE)
def utility_tool(arguments: dict) -> str: ...

# 普通工具（默认 NONE，跳过检查）
@tool
def normal_tool(arguments: dict) -> str: ...
```

### 4. 动态权限调整

```python
# 运行时添加权限
registry.add_permission(new_node, Permission.READ)

# 运行时移除权限（恢复继承）
registry.remove_permission(old_node)

# 运行时更新权限
registry.add_permission(node, Permission.READ_WRITE)  # 覆盖已有权限
```

---

## 完整示例

```python
from core.tools import Permission, PermissionToolRegistry, ToolContext
from core.tools.markdown_edit_tools import create_markdown_edit_tools_registry
from tree_doc.attributed_markdown_nodes import AttributedMarkdownTextFileNode

# 1. 加载 Markdown 文档
markdown_file_node = AttributedMarkdownTextFileNode(file_path="novel.md")

# 2. 获取需要设置权限的节点
volume_node = markdown_file_node.recursive_find_title_node_by_name("### 第一卷")
setting_node = markdown_file_node.recursive_find_title_node_by_name("#### 世界观设定")
chapter_node = markdown_file_node.recursive_find_title_node_by_name("##### 第 1 章")

# 3. 创建权限配置
registry = create_markdown_edit_tools_registry(
    permissions=[
        (volume_node, Permission.READ_WRITE),   # 卷节点可读写
        (setting_node, Permission.READ),        # 设定节点只读
        (chapter_node, Permission.DENY),        # 章节节点禁止访问
    ]
)

# 4. 创建上下文
context = ToolContext(markdown_file_node=markdown_file_node)

# 5. 执行工具（自动检查权限）

# 成功：读取整个文档
result, success, _ = registry.execute("read", context, {})
print(f"读取成功：{success}")  # True

# 成功：读取卷节点
result, success, _ = registry.execute("read", context, {"target": "### 第一卷"})
print(f"读取卷：{success}")  # True

# 失败：写入设定节点（只读）
result, success, _ = registry.execute("replace", context, {
    "target": "#### 世界观设定",
    "replace_text": "新内容"
})
print(f"写入设定：{success}")  # False
print(result)  # "权限不足：节点'#### 世界观设定'需要 WRITE 权限，但当前对该节点的权限为 READ"

# 失败：访问章节节点（禁止）
result, success, _ = registry.execute("read", context, {"target": "##### 第 1 章"})
print(f"读取章节：{success}")  # False
print(result)  # "权限不足：节点'##### 第 1 章'需要 READ 权限，但当前对该节点的权限为 DENY"

# 6. 动态调整权限
registry.remove_permission(chapter_node)  # 移除禁止，继承父节点权限
result, success, _ = registry.execute("read", context, {"target": "##### 第 1 章"})
print(f"移除限制后读取章节：{success}")  # 取决于父节点权限
```

---

## 注意事项

1. **权限检查时机**：在 `PermissionToolRegistry.execute()` 时检查，工具执行前
2. **节点匹配**：使用 `is` 比较（对象引用），不是 `==`（值比较）
3. **继承方向**：从子节点向上遍历到父节点
4. **空权限列表**：表示全部允许，不是全部拒绝
5. **Permission.NONE**：跳过检查，始终允许
6. **工具权限声明**：仅 `PermissionToolRegistry` 会检查，`ToolRegistry` 忽略
7. **target 参数**：工具参数中包含 `"target"` 键时，自动提取节点进行权限检查
8. **循环依赖**：`registry.py` 使用延迟导入避免与 `permissions.py` 的循环依赖
9. **Check 执行时机**：仅在 LLM 不再发起工具调用时执行检查
10. **Check 短路行为**：check_list 中第一个返回非 None 的 check 即生效，后续 check 不执行
11. **must_use 迁移**：`ToolRegistry.get_still_need_use()` 已移除，改用 `default_must_use_check()` 函数

---

## 相关文档

- [AGENTS.md](../../AGENTS.md) - 项目开发指南
- [pyproject.toml](../../pyproject.toml) - 项目配置和依赖
