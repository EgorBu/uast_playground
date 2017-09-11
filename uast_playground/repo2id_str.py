from collections import defaultdict
from heapq import heappop, heappush

from ast2vec.bblfsh_roles import SIMPLE_IDENTIFIER
from ast2vec.repo2.base import Repo2Base

WHITE = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
ORANGE = "\033[33m"
BLUE = "\033[34m"
PURPLE = "\033[35m"


class Repo2IdStrModel:
    NAME = "Repo2IdStrModel"


class Repo2IdStr(Repo2Base):
    """
    Helper to debug UAST.
    Print and mark with color specific role from repository in the same order and with the same
    positions.
    Print errors:
    * when specific role has position (0, 0)
    * when token at specific position doesn't match code
    * when several tokens have the same position
    """
    MODEL_CLASS = Repo2IdStrModel

    def __init__(self, *args, role=SIMPLE_IDENTIFIER, color=GREEN, err_color=RED,
                 background=WHITE, **kwargs):
        """
        Initialization
        :param args: some arguments to pass to super
        :param role: role to use (default: SIMPLE_IDENTIFIER)
        :param color: color to use for role
        :param err_color: error color
        :param background: default color for text
        :param kwargs: some arguments to pass to super
        """
        super(Repo2IdStr, self).__init__(*args, **kwargs)
        self.role = role
        self.color = color
        self.background = background
        self.err_color = err_color

    def colorize_str(self, text, color):
        """
        Add colot to text
        :param text: text that should be colorized
        :param color: color to use
        :return: colorized text
        """
        return color + text + self.background

    def uast2heap(self, root, heapsters=None, pos_token=None):
        """
        Create heap with positions of tokens for each line of repository.
        Then this heap will be used to colorize the text of repo.
        :param root: root of tree/sub-tree
        :param heapsters: dict: (row: heap with (start position, node))
        :param pos_token: dict: ((line, row): token)
        :return: heapsters
        """
        if heapsters is None:
            heapsters = defaultdict(list)
        if pos_token is None:
            pos_token = dict()

        for ch in root.children:
            if self.role in ch.roles:
                if ch.start_position.line == 0 or ch.start_position.col == 0:
                    err = "# Something wrong with token '%s' - it has position (%d, %d)"
                    err = err % (ch.token, ch.start_position.line, ch.start_position.col)
                    print(self.colorize_str(err, self.err_color))

                    if ch.token == "":
                        print(ch)

                elif (ch.start_position.line, ch.start_position.col) in pos_token:
                    err = "# New token '%s' at position (%d, %d) has the same position as token " \
                          "'%s' at the same position. Skip new token."
                    err = err % (ch.token, ch.start_position.line, ch.start_position.col,
                                 pos_token[(ch.start_position.line, ch.start_position.col)])
                    print(self.colorize_str(err, self.err_color))
                else:
                    pos_token[(ch.start_position.line, ch.start_position.col)] = ch.token
                    heappush(heapsters[ch.start_position.line - 1],
                             (ch.start_position.col, ch))
            self.uast2heap(ch, heapsters, pos_token)

        return heapsters

    def uast2str(self, root, text, res=None, heapsters=None, errors=None):
        """
        Convert given UAST/text to list of colorized lines and error reports
        :param root: start node
        :param text: text representation of code (list of str)
        :param res: variable for result
        :param heapsters: dict of heaps {row: heap of (col, node)}
        :param errors: errors. {row: error messages}
        :return: res, errors
        """
        if res is None:
            res = []
        if errors is None:
            errors = defaultdict(list)
        if heapsters is None:
            heapsters = self.uast2heap(root)

        for i, row in enumerate(text):
            if i not in heapsters:
                # this line doesn't contain any tokens
                res.append(row)
            else:
                row_ = []
                prev_node = None
                while heapsters[i]:
                    skip_token = False

                    start_col, node = heappop(heapsters[i])
                    start_col = node.start_position.col - 1
                    token = node.token

                    if token != text[i][start_col:start_col + len(token)]:
                        err = "# Something wrong with token '%s' at pos (%d, %d) - it's not " \
                              "equal to '%s' at this position in code"
                        err = err % (token, node.start_position.line, node.start_position.col,
                                     text[i][start_col:start_col + len(token)])
                        err = self.colorize_str(err, self.err_color)

                        errors[i].append(err)
                        skip_token = True

                    if not skip_token:
                        if prev_node is None:
                            row_.append(text[i][:start_col])
                            row_.append(self.colorize_str(token, self.color))
                        else:
                            row_.append(text[i][prev_node.start_position.col +
                                                len(prev_node.token) - 1:start_col])
                            row_.append(self.colorize_str(token, self.color))
                        prev_node = node
                if prev_node is not None:
                    row_.append(text[i][prev_node.start_position.col - 1 + len(prev_node.token):])
                else:
                    row_.append(text[i])
                res.append("".join(row_))

        assert len(res) == len(text)
        return res, errors

    def convert_uasts(self, file_uast_generator):
        for file_uast in file_uast_generator:
            print("-" * 20 + " " + str(file_uast.filepath))

            text = []
            with open(file_uast.filepath) as f:
                for line in f.readlines():
                    text.append(line.rstrip())

            res, errors = self.uast2str(file_uast.response.uast, text)
            to_print = []
            for i, row in enumerate(res):
                to_print.append(row)
                if i in errors:
                    to_print.append("\n".join(errors[i]))
            print("\n".join(to_print))
