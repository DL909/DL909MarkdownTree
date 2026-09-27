class MarkdownTreeError(Exception):
    """dl909markdowntree 项目所有自定义异常的基类"""


class InvalidMarkdownLineError(MarkdownTreeError):
    """无法从一行中解析出合法的 Markdown 标题"""


class InvalidNumberedTitleLineError(InvalidMarkdownLineError):
    """无法从一行中解析出合法的编号标题"""


class InvalidTitleLevelError(MarkdownTreeError):
    """标题层级过高，无法作为当前标题的子标题"""


class UnclosedCodeBlockError(MarkdownTreeError):
    """Markdown 代码块未闭合"""


class IncorrectNumberError(MarkdownTreeError):
    """标题编号错误"""


class InvalidMdpFilenameError(MarkdownTreeError):
    """.mdp 文件名不符合 N_Title.mdp 命名格式"""


class MarkdownFileError(MarkdownTreeError):
    """读取或写入 Markdown 文件失败（IO 错误、非 UTF-8 编码等）"""


class InvalidFrontMatterError(MarkdownTreeError):
    """FrontMatter 结构缺失、无法切分，或无法解析为属性对象"""


class InvalidNodeOperationError(MarkdownTreeError):
    """节点操作不合法，如向树中添加已有父节点的节点"""
