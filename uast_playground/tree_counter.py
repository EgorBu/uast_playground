from collections import defaultdict
import os

from ast2vec.repo2.base import Repo2Base
from ast2vec.bblfsh_roles import _get_role_id as get_role_id

os.environ["PYTHONHASHSEED"] = "0"  # to have the same hash function in all sub-processes


class TreeCounterModel:
    NAME = "TreeCounterModel"


class TreeAdvCounter(Repo2Base):
    """
    1) Count unique subtrees
        * pos & token are not used
        * only information about structure is used - order of children is not used
        *
    2) Store most frequent subtrees
    """
    MODEL_CLASS = TreeCounterModel

    tree_counter = defaultdict(int)
    tree_file_node = defaultdict(list)
    threshold = None

    def hash_node(self, node, filepath):
        """
        Extract hash from subtree that starts at this node
        :param node: UAST node
        :param filepath: UAST was extracted from this filepath
        :return: hash of node
        """
        ch_hash = self.hash_children(node, filepath)
        res = hash(self.hash_roles(node) + ch_hash)

        if self.threshold is None:
            # create tree cnter in first iteration
            self.tree_counter[res] += 1
        elif self.tree_counter[res] >= self.threshold:
            # keep filepaths, nodes
            self.tree_file_node[res].append((filepath, node))
        return hash(str(res))

    def hash_roles(self, node):
        """
        Logic to extract hash from node's roles
        :param node: UAST node
        :return: hash of roles
        """
        res = hash(self.MODEL_CLASS)
        for role in node.roles:
            res += hash(str(role))
        return hash(str(res))

    def hash_children(self, node, filepath):
        """
        Logic to extract hash from node's children
        :param node: UAST node
        :param filepath: UAST was extracted from this filepath
        :return: hash of node's children
        """
        if len(node.children) == 0:
            return 0
        res = hash(self.MODEL_CLASS)
        for ch in node.children:
            res += self.hash_node(ch, filepath)
        return hash(str(res))

    def convert_uasts(self, file_uast_generator):
        for file_uast in file_uast_generator:
            self.hash_node(file_uast.response.uast, file_uast.filepath)
            if self.threshold is None:
                print("Process " + str(file_uast.filepath) + ": total number of hashes is " +
                      str(len(self.tree_counter)))
            else:
                print("Process " + str(file_uast.filepath) + ": total number of stored nodes is "
                      + str(len(self.tree_file_node)))
        if self.threshold is not None:
            for tree_hash in list(self.tree_counter.keys()):
                if self.tree_counter[tree_hash] < self.threshold:
                    del self.tree_counter[tree_hash]


def find_min_max_pos(node, st_line=10**20, st_col=10**20, end_line=0, end_col=0):
    """
    Find position of code related to subtree that starts at this node
    :param node: UAST node
    :param st_line: start line of related piece of code
    :param st_col: start column of related piece of code
    :param end_line: end line of related piece of code
    :param end_col: end column of related piece of code
    :return:
    """
    st_line = min(st_line, node.start_position.line)
    st_col = min(st_col, node.start_position.col)
    end_line = max(end_line, node.end_position.line)
    end_col = max(end_col, node.end_position.col)

    for ch in node.children:
        pos = find_min_max_pos(ch, st_line, st_col, end_line, end_col)
        st_line = min(st_line, pos[0])
        st_col = min(st_col, pos[1])
        end_line = max(end_line, pos[2])
        end_col = max(end_col, pos[3])

    return st_line, st_col, end_line, end_col


def count_roles(node):
    cnter = defaultdict(int)
    stack = [node]
    while stack:
        n = stack.pop()
        stack.extend(n.children)
        for r in n.roles:
            cnter[r] += 1
    return cnter


def debug_print(file_nodes, max_print=10, filter_func=None):
    prev_file = ""
    res = []
    for f, n in file_nodes:
        pos = find_min_max_pos(n)
        # 0 not in pos - it means that subtree doesn't have correct position information
        if 0 not in pos and f != prev_file and filter_func(n):
            with open(f) as fopen:
                lines = fopen.readlines()
                st_pos = max(0, pos[0] - 2)
                end_pos = min(len(lines), pos[2] + 1)
                res.append(("+" * 4 + f, "\n".join([l.rstrip() for l in lines[st_pos:end_pos]])))
                prev_file = f
                max_print -= 1
        if max_print <= 0:
            break
    return res

if __name__ == "__main__":
    SIMPLE_IDENTIFIER = get_role_id("SIMPLE_IDENTIFIER")
    FUNCTION_DECLARATION = get_role_id("FUNCTION_DECLARATION")
    IF = get_role_id("IF")
    IF_CONDITION = get_role_id("IF_CONDITION")
    IF_ELSE = get_role_id("IF_ELSE")
    FOR = get_role_id("FOR")

    repo = "/usr/lib/python3/dist-packages/"
    tc = TreeAdvCounter(linguist="/home/egor/workspace/ast2vec/enry",
                        bblfsh_endpoint="0.0.0.0:9432")
    # Count subtrees
    tc.convert_repository(repo)
    # setup threshold
    tc.threshold = 5
    # Extract most frequent subtrees
    tc.convert_repository(repo)

    max_print = 4

    un_files = set()

    filter_func = lambda n: (count_roles(n)[IF] or count_roles(n)[IF_CONDITION]
                             or count_roles(n)[IF_ELSE] and count_roles(n)[SIMPLE_IDENTIFIER] > 1)

    for tree_hash in tc.tree_counter:
        res = debug_print(tc.tree_file_node[tree_hash], max_print=max_print,
                          filter_func=filter_func)
        if len(res):
            print(tree_hash, tc.tree_counter[tree_hash], len(tc.tree_file_node[tree_hash]))
            for r in res:
                print(r[0])
                print(r[1])
