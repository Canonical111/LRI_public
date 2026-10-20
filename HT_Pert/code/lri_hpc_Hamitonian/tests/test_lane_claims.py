"""Runtime claims (review LRI-013): two lane supervisors given the same items never run one item concurrently.

Needs a frozen checkout (GIT_SHA); skipped otherwise. Runs run_lane.py twice in parallel on small thermal cutoffs
with a temporary campaign/results directory, then checks the event journals: per item, the start-end intervals of
the two jobs do not overlap, every item is done exactly once or skipped/resumed, and both outputs pass the gates.
"""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / 'GIT_SHA').exists():
    print('SKIP test_lane_claims (no GIT_SHA: not a frozen checkout)'); sys.exit(0)
rev = (ROOT / 'GIT_SHA').read_text().strip()
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, LRIHT_CAMPAIGN=f'{tmp}/campaign', LRIHT_RESULTS=f'{tmp}/results')
    items = [dict(task='thermal', degree=7, cutoff=L, threads=2, model_rss_gib=0.1) for L in (20, 24, 28)]
    lane = dict(name='claims-test', revision=rev, mem_gib=1, items=items)
    lf = Path(tmp) / 'lane.json'; lf.write_text(json.dumps(lane))
    procs = [subprocess.Popen([sys.executable, str(ROOT / 'cluster/expanse/run_lane.py'), str(lf)],
                              env=dict(env, SLURM_JOB_ID=j), cwd=ROOT) for j in ('A', 'B')]
    rcs = [p.wait(timeout=1800) for p in procs]
    assert rcs == [0, 0], rcs
    ev = {j: [json.loads(l) for l in (Path(tmp) / 'campaign/events' / f'{j}.jsonl').read_text().splitlines()]
          for j in ('A', 'B')}
    to_t = lambda e: e['t']
    for it in items:
        key = f"thermal_d7_L{it['cutoff']}"
        iv = {}
        for j, es in ev.items():
            s = [to_t(e) for e in es if e['key'] == key and e['event'] == 'start']
            e_ = [to_t(e) for e in es if e['key'] == key and e['event'] == 'end']
            assert len(s) == len(e_) <= 1, (j, key, es)
            if s:
                iv[j] = (s[0], e_[0])
        assert iv, f'{key} never ran'
        if len(iv) == 2:   # both ran it: strictly one after the other (the second is a --resume skip)
            (a0, a1), (b0, b1) = iv['A'], iv['B']
            assert a1 <= b0 or b1 <= a0, (key, iv)
        out = Path(tmp) / 'results/thermal_d7' / f'{key}.json'
        sys.path.insert(0, str(ROOT))
        from lri_hpc.validate import check_result
        check_result(json.loads(out.read_text()))
    skipped = sum(e['event'] == 'skipped' for es in ev.values() for e in es)
    print(f'claims: {skipped} skipped starts across the two lanes')

    # Supervisor death while its solver lives on: the solver still holds the claim (inherited descriptor).
    import signal
    it = dict(task='thermal', degree=7, cutoff=50, threads=1, model_rss_gib=1.3)
    lf2 = Path(tmp) / 'lane2.json'; lf2.write_text(json.dumps(dict(lane, name='claims-test-2', items=[it])))
    evC = Path(tmp) / 'campaign/events/C.jsonl'
    pc = subprocess.Popen([sys.executable, str(ROOT / 'cluster/expanse/run_lane.py'), str(lf2)],
                          env=dict(env, SLURM_JOB_ID='C'), cwd=ROOT)
    t0 = time.time()
    while not (evC.exists() and '"start"' in evC.read_text()):
        assert time.time() - t0 < 300 and pc.poll() is None, 'lane C did not start'
        time.sleep(0.2)
    time.sleep(1.0)
    os.kill(pc.pid, signal.SIGKILL); pc.wait()          # supervisor gone, solver (its child) still running
    out = Path(tmp) / 'results/thermal_d7/thermal_d7_L50.json'
    assert not out.exists(), 'solver finished too early for this test; use a larger cutoff'
    rd = subprocess.run([sys.executable, str(ROOT / 'cluster/expanse/run_lane.py'), str(lf2)],
                        env=dict(env, SLURM_JOB_ID='D'), cwd=ROOT)
    evD = [json.loads(l) for l in (Path(tmp) / 'campaign/events/D.jsonl').read_text().splitlines()]
    assert [e['event'] for e in evD] == ['skipped'], evD
    t0 = time.time()
    while not out.exists():                              # the orphaned solver completes and publishes
        assert time.time() - t0 < 1800, 'orphaned solver did not finish'
        time.sleep(1)
    check_result(json.loads(out.read_text()))
    print('claims: orphaned solver kept the claim; the second lane skipped the item')
print('PASS test_lane_claims')
