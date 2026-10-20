"""Convergence study of the two-bubble engine at delta=0 against the exact Bethe-ansatz J2, run in parallel."""
import sys, time, json, multiprocessing as mpc
import mpmath as mp
def task(args):
    level, Kc, rad, npc, dps = args
    mp.mp.dps = dps
    from two_bubble import J2, J2_BA
    K = mp.mpc(Kc); t0 = time.time()
    J = J2(K, level=level, cauchy=(mp.mpf(rad), npc))
    ba = J2_BA(K)
    return dict(level=level, K=str(Kc), rad=rad, npc=npc, dps=dps, time=time.time() - t0,
                J0=str(J[0]), BA=str(ba), reldiff=float(abs(J[0] / ba - 1)), J=[str(x) for x in J])
if __name__ == '__main__':
    jobs = []
    for Kc in [complex(0.92, 0.05), complex(0.9, -0.08), complex(1.05, 0.06)]:
        for level in (3, 4, 5):
            jobs.append((level, Kc, '0.25', 64, 35))
        jobs.append((4, Kc, '0.2', 80, 35))
    with mpc.Pool(min(len(jobs), 60)) as pool, open(sys.argv[1], 'a') as fh:
        for r in pool.imap_unordered(task, jobs):
            fh.write(json.dumps(r) + '\n'); fh.flush()
            print(f"K={r['K']:>22} level {r['level']} rad {r['rad']} npc {r['npc']}  reldiff {r['reldiff']:.2e}  t {r['time']:.0f}s", flush=True)
