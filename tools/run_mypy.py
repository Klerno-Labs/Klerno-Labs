import subprocess
import sys

cmd = [sys.executable, "-m", "mypy", "app", "--show-error-codes"]
proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
sys.exit(proc.returncode)
