"""Small helper to run pytest from inside the CLEAN_APP directory.

Keep helper scripts inside CLEAN_APP so the project is self-contained.
"""

import os
import sys
from pathlib import Path

if __name__ == "__main__":
    here = Path(__file__).parent
    os.chdir(str(here))
    sys.exit(os.system("pytest -q"))
