from pycparser import parse_file


class Macro():
    # 节点状态
    NORMAL_MATCH = 'normalMatch'
    PREFECT_MATCH = 'perfectMatch'
    ADD_STATE = 'add'
    DEL_STATE = 'del'
    # 差别信息类型
    TYPE_DIFF = 'TypeDifferent'
    ADD_NODE = 'add_'
    DEL_NODE = 'del_'
    CHANGE_ATTR = 'change_'


class AstNode():
    def __init__(self, name, start, col):
        self.id = AstNode.count
        AstNode.count += 1
        self.type = name
        self.range = (start, -1)  # 用一个tuple描述节点管辖的代码行范围
        self.col = col  # 起始行的起始列
        self.literal = ''
        self.children = []  # [(child_name, child)]
        self.attrs = {}  # {'attr_name': attr}

        self.height = 1  # 节点高度
        self.match = (None, 0.0)  # (node, sim) sim（相似度）=0和1分别表示无匹配和完美匹配
        self.state = None  # 匹配状态：'match', 'delete', 'add'
        self.diff = None  # 如果匹配的话，在这里记录区别信息
        self.next_ofType = None  # type链的下一个节点
        self.next_ofHeight = None  # height链的下一个节点

    count = 0

    def add_child(self, name, child):
        self.children.append((name, child))

    def add_attr(self, attr):
        self.attrs[attr[0]] = attr[1]

    def __eq__(self, other):
        '''
        最大复杂度O(子树节点个数),剪枝后平均复杂度减半
        这里可以考虑第二种实现方式:直接比较对应代码段(但是需要去空白符什么的)
        '''
        res = self.type == other.type and self.height == self.height and len(self.children) == len(
            other.children) and len(self.attrs) == len(other.attrs)
        if not res:
            return res
        for attr in self.attrs.keys():
            res = res & bool(self.attrs[attr] == other.attrs[attr])
            if not res:
                return res
        for i in range(len(self.children)):
            res = res & bool(self.children[i][1] == other.children[i][1])
            if not res:
                return res
        return res


class Ast():
    def __init__(self, old_root, codes):
        '''
        根据pycparser生成语法树(old_root)构建本语法树
        :param old_root: 旧语法树根
        :param codes: 该语法树对应的代码 [code]
        '''
        self.codes = codes
        self.convex = [None] * (len(codes) + 1)  # 存放每行所能代表的最高节点
        self.root = AstNode('file', 0, 0)
        self.nodes = [self.root]  # 存储所有节点的数组

        self.buildAst(old_root, self.root)  # 建树
        self.set_range(self.root, len(self.codes))  # 计算每个节点的管辖范围

        self.curPoint = {}
        self.head_ofType = {}  # 根据类型索引节点的索引头
        self.build_TypeChain(self.root)  # 建立根据语法类型的节点索引

        self.head_ofHeight = {}  # 根据子树高度索引节点的索引头
        self.build_HeightChain(self.root)

    def buildAst(self, old, new):
        if old.attr_names:
            for attr in old.attr_names:
                new.add_attr((attr, getattr(old, attr)))
        for child in old.children():  # child类型为(name, child_node)
            newChild = AstNode(child[1].__class__.__name__, child[1].coord.line, child[1].coord.column)
            self.nodes.append(newChild)
            new.add_child(child[0], newChild)
            self.buildAst(child[1], newChild)
            new.height = max(new.height, newChild.height + 1)  # 构建height

    def set_range(self, node: AstNode, limit):
        if node.type == 'file':
            node.range = (0, limit)

        for i, child in enumerate(node.children):
            r = limit if child[1] is node.children[-1][1] else node.children[i + 1][1].range[0] - 1
            l = child[1].range[0]
            r = max(r, l)
            child[1].range = (l, r)
            self.set_range(child[1], r)

    def build_TypeChain(self, node: AstNode):
        # 为语法树的节点建立通过不同语法类型访问的索引链
        type = node.type
        if type not in self.head_ofType:
            self.head_ofType[type] = node
            self.curPoint[type] = node
        else:
            last = self.curPoint[type]
            last.next_ofType = node
            self.curPoint[type] = node
        for child in node.children:
            self.build_TypeChain(child[1])

    def build_HeightChain(self, node: AstNode):
        # 为语法树的节点建立通过不同子树高度访问的索引链
        height = node.height
        if height not in self.curPoint:
            self.head_ofHeight[height] = node
            self.curPoint[height] = node
        else:
            last = self.curPoint[height]
            last.next_ofHeight = node
            self.curPoint[height] = node
        for child in node.children:
            self.build_HeightChain(child[1])

    def build_Convex(self, node=None):
        if node is None:
            node = self.root
        # 构建每行的节点索引
        start = node.range[0]
        if self.convex[start] is None or (self.convex[start].match[0] is None and node.match[0]):
            self.convex[start] = node
        for child in node.children:
            self.build_Convex(child[1])


def print_tree(node, indent):
    info = indent + node.type + ': ' + str(node.range) + ' height: ' + str(node.height) + ' ' + str(node.attrs)
    print(info)
    for child in node.children:
        print_tree(child[1], indent + ' ' * 2)


def print_typeChain(head_ofType):
    for typeItem in head_ofType.items():
        type, node = typeItem[0], typeItem[1]
        s = type + ': '
        while node:
            s += str(node.id) + str(node.range) + ' '
            node = node.next_ofType
        print(s)


def print_HeightChain(head_ofHeight):
    for heightItem in head_ofHeight.items():
        height, node = heightItem[0], heightItem[1]
        s = str(height) + ': '
        while node:
            s += str(node.id) + str(node.range) + ' '
            node = node.next_ofHeight
        print(s)


if __name__ == '__main__':
    filename = 'main.cpp'
    with open(filename, 'r') as f:
        codes = f.readlines()
    ast = parse_file(filename, use_cpp=False)
    ast = Ast(ast, codes)
    print_tree(ast.root, '')
    print_typeChain(ast.head_ofType)
    print_HeightChain(ast.head_ofHeight)
    # print(AstNode.count)
    # print(len(ast.codes))
