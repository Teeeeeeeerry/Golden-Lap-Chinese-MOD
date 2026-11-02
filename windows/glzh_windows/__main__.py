"""命令行入口：python -m glzh_windows <命令>"""

import sys

from glzh.cli import main
from glzh_windows import Windows

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], Windows()))
