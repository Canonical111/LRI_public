"""Exact standard-library verification of complete Task B."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(root/'engine/finalize_B_aggregate.py')],check=True)
