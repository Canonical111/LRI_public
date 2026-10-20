#!/usr/bin/env python3
"""Profile one raw task with lib_opt (cProfile, cumulative top entries).  usage: prof_task.py Lmax cache file"""
import cProfile, pstats, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regress_opt as ro
import engine as eg
Lmax, cache, fname = int(sys.argv[1]), sys.argv[2], sys.argv[3]
tasks, N = ro.task_list(Lmax)
t = [x for x in tasks if x["file"] == fname][0]
modes = eg.Modes(N, 3)
ro.run_task(t, N, modes) if False else None
pr = cProfile.Profile(); t0 = time.time(); pr.enable(); ro.run_task(t, N, modes); pr.disable()
print(f"task {fname} K={t['K']} nl={t['nl']} nk={t['nk']}: {time.time()-t0:.1f}s")
pstats.Stats(pr).sort_stats("tottime").print_stats(14)
