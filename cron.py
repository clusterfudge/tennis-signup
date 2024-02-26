import sys
from client import main as bookit


def main(args):
    bookit(args[0])


if __name__ == "__main__":
    main(sys.argv[1:])