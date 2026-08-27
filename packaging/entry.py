"""PyInstaller entry point.

``python -m drpc`` cannot be frozen directly: PyInstaller runs the script as
``__main__`` with no parent package, so the relative import inside
``src/drpc/__main__.py`` has nothing to resolve against. This module does the
same job with an absolute import.
"""

import sys

from drpc.cli import main

if __name__ == "__main__":
    sys.exit(main())
