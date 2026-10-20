import subprocess, sys
for N, ns in ((16, 200), (32, 100), (48, 60), (64, 30), (80, 16)):
    subprocess.run([sys.executable, "time_t5.py", str(N), str(ns)])
