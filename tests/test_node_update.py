"""Node.update 的删除逻辑测试（覆盖历史上「连续 deprecated 漏删」的 bug）。"""

from dl909agentframework.tree_doc.node import Node


def _tree(n: int) -> tuple[Node, list[Node]]:
    root = Node()
    kids = []
    for _ in range(n):
        k = Node()
        root.addchild(k)
        kids.append(k)
    return root, kids


def test_removes_two_consecutive_deprecated_children():
    root, (a, b, c) = _tree(3)
    b.deprecated = True
    c.deprecated = True  # 连续两个：旧实现会漏删 c
    root.update()
    assert root.children == [a]


def test_removes_all_deprecated():
    root, kids = _tree(4)
    for k in kids:
        k.deprecated = True
    root.update()
    assert root.children == []


def test_keeps_non_deprecated():
    root, (a, b, c) = _tree(3)
    b.deprecated = True
    root.update()
    assert root.children == [a, c]


def test_update_recurses_into_grandchildren():
    root, (a,) = _tree(1)
    g1 = Node()
    g2 = Node()
    a.addchild(g1)
    a.addchild(g2)
    g1.deprecated = True
    g2.deprecated = True
    root.update()
    assert a.children == []
    assert root.children == [a]
