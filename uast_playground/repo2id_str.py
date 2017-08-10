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
    Print and mark with color all specific role from repository in the same order and with the same
    positions.
    """
    MODEL_CLASS = Repo2IdStrModel

    def __init__(self, *args, role=SIMPLE_IDENTIFIER, color=GREEN, **kwargs):
        super(Repo2IdStr, self).__init__(*args, **kwargs)
        self.role = role
        self.color = color
        self.background = WHITE

    def find_max_pos(self, root, max_pos=None):
        if max_pos is None:
            max_pos = [0, 0]
        max_pos[0] = max(root.end_position.line, max_pos[0])
        max_pos[1] = max(root.end_position.col, max_pos[1])
        for ch in root.children:
            max_pos = self.find_max_pos(ch, max_pos)

        return max_pos

    def uast2str(self, root, text):
        for ch in root.children:
            if self.role in ch.roles:
                skip_id = False
                start_col = ch.start_position.col - 1
                end_col = ch.end_position.col
                start_line = ch.start_position.line - 1
                end_line = ch.end_position.line - 1

                # check correctness of length
                if end_col - start_col != len(ch.token):
                    # something wrong with length of token
                    print(
                        "Wrong length of token '%s' (expected %d - %d = %d)" %
                        (ch.token, end_col, start_col, end_col - start_col)
                    )
                    skip_id = True

                # check that token has the same start & end line
                if start_line != end_line:
                    print("Something wrong with token '%s' start & end line: %d, %d" % (ch.token,
                                                                                        start_line,
                                                                                        end_line))
                    skip_id = True

                if not skip_id:
                    text[start_line] = (text[start_line][:start_col] + self.color + ch.token +
                                        self.background + text[start_line][end_col:])

            self.uast2str(ch, text)

    def convert_uasts(self, file_uast_generator):
        for file_uast in file_uast_generator:
            print("-" * 20 + " " + str(file_uast.filepath))

            text = []
            with open(file_uast.filepath) as f:
                for line in f.readlines():
                    

                    text.append(line.rstrip())

            self.uast2str(file_uast.response.uast, text)
            print("\n".join(text))
