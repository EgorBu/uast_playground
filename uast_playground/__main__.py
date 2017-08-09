import argparse
import logging

from uast_playground.repo2id_str import Repo2IdStr
from uast_playground.repo2id_str import SIMPLE_IDENTIFIER


def main():
    """
    Creates all the argparse-rs and call function.

    :return: The result of the function.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", default="INFO",
                        choices=logging._nameToLevel,
                        help="Logging verbosity.")
    subparsers = parser.add_subparsers(help="Commands", dest="command")

    repo2id_str_parser = subparsers.add_parser(
        "repo2id_str", help="Print code of repo and mark specific role with color.")
    repo2id_str_parser.set_defaults(handler=repo2id_str)
    repo2id_str_parser.add_argument(
        "-r", "--repository", required=True, nargs="+", help="URLs or files with URLs.")
    repo2id_str_parser.add_argument(
        "--linguist", help="Path to src-d/enry executable. If specified will save only files "
        "classified by enry.")
    repo2id_str_parser.add_argument(
        "--role", default=SIMPLE_IDENTIFIER, type=int, help="UAST role to colorize.")
    repo2id_str_parser.add_argument(
        "--bblfsh", help="Babelfish server's endpoint, e.g. 0.0.0.0:9432.",
        dest="bblfsh_endpoint")

    args = parser.parse_args()
    args.log_level = logging._nameToLevel[args.log_level]
    try:
        handler = args.handler
    except AttributeError:
        def print_usage(_):
            parser.print_usage()

        handler = print_usage
    return handler(args)


def repo2id_str(args):
    """
    Invokes Repo2IdStr(\*\*args).convert_repository(repo)() on the specified input.

    :param args: :class:`argparse.Namespace` with "input", "output" and "ignore". "input" is a \
                 list of files and/or Git urls. "output" is the path to directory for storing \
                 all repositories. "ignore" is a flag for specifying to ignore Git clone problems.
    :return: None
    """
    repo = args.repository[0]
    args = _sanitize_kwargs(args)
    del args["repository"]
    Repo2IdStr(**args).convert_repository(repo)


def _sanitize_kwargs(args):
    clone_args = getattr(args, "__dict__", args).copy()
    blacklist = ("command", "ignore", "input", "handler", "output")
    for arg in blacklist:
        clone_args.pop(arg, None)
    return clone_args


if __name__ == "__main__":
    main()
