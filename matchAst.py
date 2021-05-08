from buildAst import AstNode
from buildAst import Ast
from pycparser import parse_file
from buildAst import Macro

threshold = 0.8
attr_types = ['Constant', 'EmptyStatement', 'IdentifierType', 'ID', 'ArrayRef', 'StructRef']
'''
需要排除掉不参与匹配的节点类型,因为它们更像是属性,或者基本代码句的子类型
IdentifierType 只能推出基本数据类型
ID，Constant只是单值
'''
block_types = ['Case', 'Compound', 'DeclList', 'EnumeratorList', 'ExprList', 'file', 'InitList',
               'NamedInitializer', 'ParamList', 'Struct', 'Union']
'''
对于FuncDef、for、while等节点，它的body/stmt部分孩子中的语句块允许不是一一对应关系（可能有插入和删除），拟采用LCS算法寻找实际匹配的代码段
'''
version = 2  # 块节点相似度算法版本


def find_perfectMatch_1(oldNode: AstNode, newNode: AstNode) -> bool:
    """
    尝试匹配两棵子树，如果成功返回true
    :param oldNode: 旧语法树根
    :param newNode: 新语法树根
    """
    '''
    缺点:只能顺序地进行匹配,并且也只能识别深度相同的完全匹配
    '''
    res = True
    if oldNode.type != newNode.type or oldNode.attrs != newNode.attrs:
        res = False
    if len(oldNode.children) != len(newNode.children):
        res = False
    for i in range(min(len(oldNode.children), len(newNode.children))):
        res = res & find_perfectMatch_1(oldNode.children[i][1], newNode.children[i][1])
    if res:
        oldNode.state = Macro.PREFECT_MATCH
        oldNode.match = (newNode, 1.0)
        newNode.state = Macro.PREFECT_MATCH
        newNode.match = (oldNode, 1.0)
    return res


def setPerfectState_and_Match(old: AstNode, new: AstNode):
    # set state for a sub-tree
    old.state = Macro.PREFECT_MATCH
    new.state = Macro.PREFECT_MATCH
    old.match = (new, 1)
    new.match = (old, 1)
    for i in range(len(old.children)):
        setPerfectState_and_Match(old.children[i][1], new.children[i][1])


def find_perfectMatch_2(oldast: Ast, newast: Ast):
    '''
    对高度和类型都相同的两棵子树,尝试去判断它们是否完美匹配
    :param oldast: 旧代码整棵语法树
    :param newast: 新代码整棵语法树
    '''
    '''
    如果将语法树视为完全-p叉树，树高h，本算法复杂度大概为O（p^(2h-3)），语法节点数量级大概在O（p^h）左右
    所以对于n个节点的语法树，复杂度大概在O（n^2）
    '''
    for typ, old in oldast.head_ofType.items():
        if typ in attr_types:
            continue
        if typ not in newast.head_ofType:
            continue
        while old:
            if old.state is None:
                new = newast.head_ofType[typ]
                while new:
                    if new.state is None and new.height == old.height and old == new:
                        # 如果新语法树节点已经匹配过，那就看下一个
                        setPerfectState_and_Match(old, new)
                        break
                    new = new.next_ofType
            old = old.next_ofType


def count_attrs(node: AstNode):
    # 计算某节点共有多少个属性值
    res = len(node.attrs)
    for child in node.children:
        res += count_attrs(child[1])
    return res


def cal_Similarity(old: AstNode, new: AstNode) -> float:
    '''
    计算old和new两棵子树的相似度(0~1)
    匹配节点的相似度算法：0.6*sum(孩子相似度)/非空孩子并集的大小+0.4*(相同属性/属性个数)
    '''
    diff_info = []
    if old.type != new.type:
        return 0, [(Macro.TYPE_DIFF, (old.type, old.range), (new.type, new.range))]
    attr_sim = 0.0
    for attr in old.attrs.keys():
        # 相同类型的节点拥有同种属性
        if old.attrs[attr] == new.attrs[attr]:
            attr_sim += 1
        else:
            diff_info.append((Macro.CHANGE_ATTR + old.type + '_' + attr, old.attrs[attr], new.attrs[attr]))
    attr_sim = attr_sim / len(old.attrs) if old.attrs else -1

    children_sim = 0.0
    if old.type in block_types:
        n, m = len(old.children), len(new.children)

        # oldchildren,newchildren={},{}
        # for child in old.children:
        #     typ=child[1].type
        #     if typ not in oldchildren:
        #         oldchildren[typ]=[child[1]]
        #     else:
        #         oldchildren[typ].append(child[1])
        # for child in new.children:
        #     typ=child[1].type
        #     if typ not in newchildren:
        #         newchildren[typ]=[child[1]]
        #     else:
        #         newchildren[typ].append(child[1])

        # 目前只能做匹配成功的LCS，比较简陋
        '''
        version 1
        孩子相似度=匹配成功的孩子所占孩子比例
        有不妥之处，较庞大的child应该占有更大的权重
        '''
        if version == 1:
            last = 0  # 上一个匹配成功的new节点
            match_cnt = 0
            for i in range(n):
                oldchild = old.children[i][1]
                if oldchild.state:
                    continue
                for j in range(last, m):
                    newchild = new.children[j][1]
                    if newchild.type != oldchild.type or newchild.state:
                        continue
                    sim, diff = cal_Similarity(oldchild, newchild)
                    if sim > threshold:
                        # 这里可以顺便做一下匹配
                        oldchild.state = Macro.NORMAL_MATCH
                        oldchild.match = (newchild, sim)
                        oldchild.diff = diff

                        newchild.state = Macro.NORMAL_MATCH
                        newchild.match = (oldchild, sim)
                        newchild.diff = diff

                        last = j
                        match_cnt += 1
            children_sim = match_cnt / max(n, m)

            for child in old.children:
                if child[1].match[0] is None:
                    diff_info.append((Macro.DEL_NODE + child[1].type, child[1].range, child[1].attrs))
            for child in new.children:
                if child[1].match[0] is None:
                    diff_info.append((Macro.ADD_NODE + child[1].type, child[1].range, child[1].attrs))
        elif version > 1:
            last = 0  # 上一个匹配成功的new节点
            old_size = 0
            old_sizes = [0] * n
            for i in range(n):
                old_sizes[i] = count_attrs(old.children[i][1])
                old_size += old_sizes[i]
            new_size = 0
            new_sizes = [0] * m
            for i in range(m):
                new_sizes[i] = count_attrs(new.children[i][1])
                new_size += new_sizes[i]

            for i in range(n):
                oldchild = old.children[i][1]
                for j in range(last, m):
                    newchild = new.children[j][1]
                    if oldchild.match[0] is newchild:
                        # 如果他们已经匹配了
                        children_sim += max(old_sizes[i], new_sizes[j])
                        if version == 3:
                            last = j
                    else:
                        # elif oldchild.state is None and newchild.state is None:
                        sim, diff = cal_Similarity(oldchild, newchild)
                        if sim > threshold:
                            # 这里可以顺便做一下匹配
                            oldchild.state = Macro.NORMAL_MATCH
                            oldchild.match = (newchild, sim)
                            oldchild.diff = diff

                            newchild.state = Macro.NORMAL_MATCH
                            newchild.match = (oldchild, sim)
                            newchild.diff = diff
                            if version == 3:
                                last = j
                            children_sim += max(old_sizes[i], new_sizes[j])

            children_sim /= max(old_size, new_size)

            for child in old.children:
                if child[1].match[0] is None:
                    diff_info.append((Macro.DEL_NODE + child[1].type, child[1].range, child[1].attrs))
            for child in new.children:
                if child[1].match[0] is None:
                    diff_info.append((Macro.ADD_NODE + child[1].type, child[1].range, child[1].attrs))
    else:
        oldchildren = dict(old.children)
        oldnames = oldchildren.keys()
        newchildren = dict(new.children)
        newnames = newchildren.keys()
        intersect_children = set(oldchildren.keys()).intersection(set(newchildren.keys()))  # 共有的孩子名
        union_children = set(oldchildren.keys()).union(set(newchildren.keys()))  # 孩子名的并集

        for name in union_children:
            if name in intersect_children:
                if oldchildren[name].match[0] is newchildren[name]:
                    sim, diff = oldchildren[name].match[1], []
                else:
                    sim, diff = cal_Similarity(oldchildren[name], newchildren[name])
                children_sim += sim
                diff_info += diff
            elif name in oldnames:
                diff_info.append(
                    (Macro.DEL_NODE + oldchildren[name].type, oldchildren[name].range, oldchildren[name].attrs))
            else:
                diff_info.append(
                    (Macro.ADD_NODE + newchildren[name].type, newchildren[name].range, newchildren[name].attrs))
        children_sim = children_sim / len(union_children) if union_children else -1

    if attr_sim == -1 and children_sim != -1:
        sim = children_sim
    elif attr_sim != -1 and children_sim == -1:
        sim = attr_sim
    else:
        sim = 0.6 * children_sim + 0.4 * attr_sim
    return sim, diff_info


def find_normalMatch(oldast: Ast, newast: Ast, version=1):
    '''
    和完美匹配寻找到相同子树后不需要看孩子不同，普通匹配中记录不同层级的匹配信息是有意义的
    寻找两棵语法树的不完美匹配，要求必须节点类型是一样的
    匹配节点的相似度算法：0.6*sum(孩子相似度)+0.4*非空属性中相同的所占比例
    '''

    oldTypes = set(oldast.head_ofType.keys())
    newTypes = set(newast.head_ofType.keys())
    types = oldTypes.intersection(newTypes)
    for attr in attr_types:
        types.discard(attr)
    for typ in types:
        old = oldast.head_ofType[typ]
        while old:
            if old.state is None:
                # 给旧语法树上所有typ类型未匹配节点进行匹配
                new = newast.head_ofType[typ]
                while new:
                    if new.state is None:
                        # 遍历新语法树上所有未匹配typ类型节点
                        similarity, diff_info = cal_Similarity(old, new)
                        if similarity > threshold:
                            old.match = (new, similarity)
                            new.match = (old, similarity)
                            old.diff = diff_info
                            new.diff = diff_info
                            old.state = Macro.NORMAL_MATCH
                            new.state = Macro.NORMAL_MATCH
                            break
                    new = new.next_ofType
            old = old.next_ofType


def print_perfectMatch(node: AstNode):
    for child in node.children:
        if child[1].state == Macro.PREFECT_MATCH:
            print(child[1].type + ' ' + str(child[1].range) + str(child[1].match[0].range) + ' ' + str(child[1].attrs))
        else:
            print_perfectMatch(child[1])


def print_normalMatch(node: AstNode):
    for child in node.children:
        if child[1].state == Macro.NORMAL_MATCH and child[1].type not in attr_types:
            print(child[1].type + ' ' + str(child[1].match[1]) + ' ' + str(child[1].range) + str(
                child[1].match[0].range) + ' ' + str(child[1].attrs))
            print(str(child[1].diff) + ' \n')
        print_normalMatch(child[1])


def print_Convex(ast: Ast):
    for i in range(len(ast.convex)):
        if ast.convex[i]:
            print(str(i) + ': ' + ast.convex[i].type + ' ' + str(ast.convex[i].match[0]))


def check_NoneState(node: AstNode):
    if node.state is None:
        print(str(node.type) + str(node.range))
    for child in node.children:
        check_NoneState(child[1])


if __name__ == '__main__':
    oldfilename = 'old.cpp'
    newfilename = 'main.cpp'
    with open(oldfilename, 'r') as f:
        oldcodes = f.readlines()
    oldast = parse_file(oldfilename, use_cpp=False)
    oldast = Ast(oldast, oldcodes)
    with open(newfilename, 'r') as f:
        newcodes = f.readlines()
    newast = parse_file(newfilename, use_cpp=False)
    newast = Ast(newast, newcodes)
    # find_perfectMatch_1(oldast.root, newast.root)
    find_perfectMatch_2(oldast, newast)
    find_normalMatch(oldast, newast)
    oldast.build_Convex()
    newast.build_Convex()
    print_normalMatch(oldast.root)
    print_perfectMatch(oldast.root)
    print_Convex(oldast)
    # print(oldast==newast)
    # check_NoneState(oldast.root)
