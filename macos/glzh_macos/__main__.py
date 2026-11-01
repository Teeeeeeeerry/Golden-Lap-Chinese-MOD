"""命令行入口：python -m glzh_macos <命令>"""

import sys

from glzh.cli import main
from glzh_macos import MacOS

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], MacOS()))
