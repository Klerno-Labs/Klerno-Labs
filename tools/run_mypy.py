import subprocess
import sys

cmd = [sys.executable, "-m", "mypy", "app", "--show-error-codes"]
print("Running:", " ".join(cmd))
proc = subprocess.run(cmd, capture_output=True, text=True)
print(proc.stdout)
print(proc.stderr)
sys.exit(proc.returncode)
