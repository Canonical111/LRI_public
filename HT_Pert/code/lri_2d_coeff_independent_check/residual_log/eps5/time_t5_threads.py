import subprocess, sys, os
for thr in ("1", "64"):
    env = dict(os.environ, NUMBA_NUM_THREADS=thr, OMP_NUM_THREADS=thr, OPENBLAS_NUM_THREADS=thr, MKL_NUM_THREADS=thr)
    for N, ns in ((48, 40), (64, 20)):
        print(f"threads={thr}", flush=True)
        subprocess.run([sys.executable, "time_t5.py", str(N), str(ns)], env=env)
