#!/usr/bin/env python3
"""Run one lane (a list of cutoffs) inside a Slurm allocation; called by lane.slurm.

Each item runs in its own `python -m lri_hpc ... --resume` process, so a killed item (e.g. an OOM kill) does not
end the lane; the remaining items still run. Every start and end is appended to
$LRIHT_HOME/campaign/events/<jobid>.jsonl. An item counts as done only if its output passes
lri_hpc.validate.check_result and carries the current source fingerprint. Exit status is nonzero if any item
failed.

Before an item starts, the lane takes an exclusive flock on $LRIHT_HOME/campaign/claims/<item>.lock (Lustre
flock is cluster-coherent and released when the last holder dies). The solver process inherits the locked
descriptor, so the claim lasts for the solver's lifetime even if the supervisor dies first. On SIGTERM the
supervisor terminates and reaps the solver before exiting. If another job holds the claim, the item is skipped and
a "skipped" event is logged (review LRI-013). A done output is detected by the CLI's --resume and not recomputed.
"""
import fcntl, json, os, signal, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent.parent
sys.path.insert(0, str(CODE)); sys.path.insert(0, str(HERE))
import campaign as C
from lri_hpc.validate import check_result
from lri_hpc.solver import source_fingerprint

job = os.environ.get('SLURM_JOB_ID', 'local')
lane = json.loads(Path(sys.argv[1]).read_text())
rev = (CODE / 'GIT_SHA').read_text().strip()
if lane['revision'] != rev:
    sys.exit(f"lane revision {lane['revision']} != code revision {rev}")
fp = source_fingerprint()
events = C.CAMPAIGN / 'events' / f'{job}.jsonl'
events.parent.mkdir(parents=True, exist_ok=True)
current = {'item': None, 'proc': None}


def log(**kw):
    kw.update(time=time.strftime('%Y-%m-%dT%H:%M:%S%z'), t=time.time(), job=job, lane=lane['name'], revision=rev)
    with events.open('a') as f:
        f.write(json.dumps(kw) + '\n'); f.flush(); os.fsync(f.fileno())


def on_term(signum, frame):  # Slurm sends SIGTERM at the wall limit or on scancel
    if current['item'] is not None:
        log(event='terminated', key=current['item'], signal=signum)
    proc = current['proc']
    if proc is not None:  # reap the solver before exiting (and before the claim can be released)
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()
    sys.exit(143)


signal.signal(signal.SIGTERM, on_term)
failed = 0
for it in lane['items']:
    key = C.item_key(it)
    out = C.output_path(it)
    cmd = [sys.executable, '-m', 'lri_hpc', '--task', it['task'], '--degree', str(it['degree']),
           '--cutoffs', str(it['cutoff']), '--threads', str(it['threads']),
           '--output-dir', str(out.parent), '--checkpoint-dir', str(out.parent / 'checkpoints'), '--resume']
    claims = C.CAMPAIGN / 'claims'; claims.mkdir(exist_ok=True)
    claim = open(claims / f'{key}.lock', 'a+')
    try:
        fcntl.flock(claim, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        claim.seek(0); owner = claim.read().strip().splitlines()[-1:] or ['?']
        log(event='skipped', key=key, reason=f'claimed by {owner[0]}'); claim.close(); continue
    claim.write(f'{job}\n'); claim.flush()
    current['item'] = key
    log(event='start', key=key, cmd=cmd, model_rss_gib=it['model_rss_gib'], request_gib=lane['mem_gib'])
    t0 = time.time()
    # The solver inherits the claim descriptor, so the flock is held while either process lives: if the supervisor
    # dies, a surviving solver still owns the cutoff (review LRI-013).
    current['proc'] = subprocess.Popen(cmd, cwd=CODE, pass_fds=(claim.fileno(),))
    rc = current['proc'].wait()
    current['proc'] = None
    ok, why, rss = False, None, None
    if rc == 0:
        try:
            r = json.loads(out.read_text())
            if (r.get('task'), r.get('degree'), r.get('cutoff')) != (it['task'], it['degree'], it['cutoff']):
                raise ValueError('output identity differs from the requested item')
            if r.get('source_sha256') != fp:
                raise ValueError('source fingerprint mismatch')
            check_result(r)
            ok, rss = True, r['ranks'][0]['maxrss_kib'] / 2**20
        except Exception as e:  # noqa: BLE001 - record any acceptance failure
            why = f'{type(e).__name__}: {e}'
    else:
        why = 'killed by signal %d' % -rc if rc < 0 else f'exit {rc}'
    log(event='end', key=key, rc=rc, ok=ok, reason=why, seconds=round(time.time() - t0, 1), maxrss_gib=rss)
    current['item'] = None
    claim.close()   # releases the flock
    failed += not ok
sys.exit(1 if failed else 0)
