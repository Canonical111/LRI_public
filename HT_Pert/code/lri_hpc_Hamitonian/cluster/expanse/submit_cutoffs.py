#!/usr/bin/env python3
"""Submit the cutoff-push campaign (PLAN G5) from a frozen checkout, after a passing validation job V.

Usage (Expanse login node):
  source <checkout>/cluster/expanse/env.sh
  python <checkout>/cluster/expanse/submit_cutoffs.py --validation <V jobid> [--dry-run]    # initial / top-up
  python <checkout>/cluster/expanse/submit_cutoffs.py --validation <V jobid> --retry [--dry-run]

Refuses unless V's summary passed for this checkout's revision and V's outputs carry this source fingerprint.
Writes $LRIHT_HOME/campaign/plan.json, lanes/<name>_<stamp>.json and appends SUBMITTED.jsonl. Items already done
(output passes check_result) or in a queued/running lane are never resubmitted. Slot limits: large-shared at most
4 submitted jobs (QOS MaxSubmitPU); normal QOS at most 22 of the user's jobs in total (user rule). Lanes that do
not fit are deferred to a later invocation (run it again when slots free up).

--retry resubmits items that failed or were interrupted, once (review LRI-006): killed (OOM) items get 1.5x the
failed memory request, moved to large-shared if needed, capped at the node limit; interrupted (timeout) items get
1.5x the failed wall limit, capped at 20 h and at the expiry minus 1 h. Items that failed for another reason (for
example an acceptance-gate failure) are not retried. Items with no admissible request are reported as exhausted.
Items whose lane ended before they started (not-reached) are resubmitted by the normal (non-retry) mode.
Exhaustion decisions are appended to EXHAUSTED.jsonl and status.py reports them (review LRI-014). Items in "unknown"
state (no terminal accounting for a job that left the queue) are never resubmitted.

Concurrency (review LRI-013): the whole invocation, from reading the queue and journals through the last
SUBMITTED.jsonl append, holds an exclusive flock on $LRIHT_HOME/campaign/submit.lock (Lustre is mounted with
cluster-coherent flock). A second invocation exits instead of waiting. Lane files are created exclusively
(O_EXCL). At run time each item additionally takes a per-item flock (run_lane.py), so a duplicate lane can never
run the same cutoff concurrently. If sbatch succeeds but the journal append does not, the job shows up as a
campaign-named job missing from SUBMITTED.jsonl and blocks further submission until reconciled by hand.
--dry-run validates every sbatch command with `sbatch --test-only` without submitting.
"""
import argparse, fcntl, json, math, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent.parent
sys.path.insert(0, str(CODE)); sys.path.insert(0, str(HERE))
import campaign as C
import status as S
from lri_hpc.solver import source_fingerprint

NORMAL_QOS_JOB_CAP = 22


def hms(s):
    s = int(s); return f'{s // 3600}:{s % 3600 // 60:02d}:00'


def sbatch_command(ln, wall, lane_file, test_only=False):
    """The exact sbatch argument list for a lane (review LRI-011: every option is one complete argument)."""
    cmd = ['sbatch', '--parsable', f"--job-name={ln['name']}", f"--partition={ln['partition']}"]
    if ln['qos']:
        cmd.append(f"--qos={ln['qos']}")
    cmd += [f"--cpus-per-task={ln['cores']}", f"--mem={ln['mem_gib']}G", f'--time={hms(wall)}',
            f'--export=ALL,CODE={CODE},LANE={lane_file}']
    if test_only:
        cmd.insert(1, '--test-only')
    return cmd + [str(HERE / 'lane.slurm')]


def deadline_filter(items, now):
    """Per-item deadline admissibility (review LRI-015): an item is runnable if 1.2x its own model time fits before
    expiry minus 1 h. Returns (runnable items, [(key, reason)] for the others)."""
    left = (C.EXPIRY - now).total_seconds() - 3600
    keep, gone = [], []
    for it in items:
        need = 1.2 * it['model_seconds']
        if left > 0 and left >= need:
            keep.append(it)
        else:
            gone.append((C.item_key(it), f'needs {hms(need)}, {hms(max(left, 0))} left before expiry - 1 h'))
    return keep, gone


def record_exhausted(key, reason, rev):
    if key in S.load_exhausted():
        return
    with (C.CAMPAIGN / 'EXHAUSTED.jsonl').open('a') as f:
        f.write(json.dumps(dict(key=key, reason=reason, revision=rev, time=time.strftime('%Y-%m-%dT%H:%M:%S%z'))) + '\n')


def retry_request(state, it, now):
    """(lane, None) for an admissible single-item retry, or (None, reason) (reviews LRI-006, IR-001).

    killed: 1.5x the failed lane memory, capped at the node limit. interrupted: the item's own need decides, not the
    previous lane's wall: need = 1.2 x max(time the item already ran, its model time); wall = min(max(1.5 x elapsed,
    the usual lane wall for this item), 20 h, expiry - 1 h - now)."""
    last = state['last']
    mem = last['mem_gib']
    left = (C.EXPIRY - now).total_seconds() - 3600
    cap = min(C.WALL_MAX_S, left)
    wall_override = None
    if state['state'] == 'killed':
        if mem >= C.LARGE_MAX_GIB:
            return None, 'killed at the node memory limit'
        mem = min(C.LARGE_MAX_GIB, math.ceil(1.5 * mem))
        if cap < 1.2 * it['model_seconds']:
            return None, f"needs {hms(1.2 * it['model_seconds'])}, {hms(max(cap, 0))} left before expiry - 1 h"
    else:
        ran = last.get('elapsed_s') or 0.0
        need = 1.2 * max(ran, it['model_seconds'])
        if cap < need:
            return None, f'interrupted after {hms(ran)}; needs {hms(need)}, {hms(max(cap, 0))} left'
        wall_override = int(min(cap, max(1.5 * ran, C.wall_seconds(it['model_seconds'], now)[1])))
    part = 'shared' if mem <= C.SHARED_MAX_GIB else 'large-shared'
    cores, threads = C.resources(part, mem)
    return dict(name=f"lriht-{it['task']}{it['degree']}-L{it['cutoff']}x1r", partition=part,
                qos='large-shared-normal' if part == 'large-shared' else None, mem_gib=mem, cores=cores,
                threads=threads, model_seconds=it['model_seconds'], wall_override=wall_override,
                items=[dict(it, threads=threads)], attempt='retry'), None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--validation', required=True, help='job id of the passing validation job V')
    ap.add_argument('--retry', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    rev = (CODE / 'GIT_SHA').read_text().strip()
    fp = source_fingerprint()
    vdir = C.LRIHT_HOME / 'validation' / a.validation
    summary, cal = C.load_calibration(vdir)
    if summary.get('pass') is not True or summary.get('revision') != rev:
        sys.exit(f"validation {a.validation}: pass={summary.get('pass')} revision={summary.get('revision')}; need pass for {rev}")
    bad = {r['source'] for rows in cal.values() for r in rows} - {fp}
    if bad:
        sys.exit(f'validation outputs carry other source fingerprints {bad}; rerun V for this checkout')
    models = {k: C.Model(*k, v) for k, v in cal.items() if k in C.CAPS}
    if set(models) != set(C.CAPS):
        sys.exit(f'calibration missing for {set(C.CAPS) - set(models)}')
    items, rejected = C.plan_items(models)
    plan = dict(revision=rev, validation=a.validation, source=fp, created=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                models={f'{t}_d{d}': m.describe() for (t, d), m in models.items()}, items=items, rejected=rejected)
    C.CAMPAIGN.mkdir(parents=True, exist_ok=True)
    lock = open(C.CAMPAIGN / 'submit.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit('another submit_cutoffs.py invocation holds the campaign lock')
    if not a.dry_run:
        (C.CAMPAIGN / 'plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    queue = S.squeue_jobs()
    subs = S.load_submitted()
    known = {s['job'] for s in subs}
    stray = [j for j, q in queue.items() if q['name'].startswith('lriht-') and q['name'] != 'lriht-validate' and j not in known]
    if stray:
        sys.exit(f'campaign-named jobs not in SUBMITTED.jsonl: {stray}; resolve before submitting')
    st = S.collect(items, subs, queue, fp)
    now = datetime.now(timezone.utc)
    lanes, exhausted = [], []
    if not a.retry:
        todo = [it for it in items if st[C.item_key(it)]['state'] in ('unsubmitted', 'not-reached')]
        todo, gone = deadline_filter(todo, now)
        exhausted += gone
        lanes = [dict(ln, attempt='initial') for ln in C.make_lanes(todo)]
    else:
        by_key = {C.item_key(it): it for it in items}
        for key, s in st.items():
            if s['state'] not in ('killed', 'interrupted'):
                if s['state'] in ('failed', 'unknown'):
                    print('NOT RETRIED', key, s['state'], s['detail'])
                continue
            ln, why = retry_request(s, dict(by_key[key]), now)
            if ln is None:
                exhausted.append((key, why))
            else:
                lanes.append(ln)
    large_used = sum(1 for q in queue.values() if q['partition'] == 'large-shared')
    normal_used = sum(1 for q in queue.values() if q['partition'] != 'large-shared')
    free = {'large-shared': C.MAX_LARGE_SUBMITTED - large_used, 'shared': NORMAL_QOS_JOB_CAP - normal_used}
    shared_lanes = 0
    stamp = time.strftime('%Y%m%dT%H%M%S')
    (C.CAMPAIGN / 'lanes').mkdir(exist_ok=True)
    unknown = [k for k, v in st.items() if v['state'] == 'unknown']
    if unknown:
        print('UNKNOWN (not resubmitted until accounting is reconciled):', unknown)
    for ln in lanes:
        wall, want = C.wall_seconds(ln['model_seconds'], now)
        if ln.get('wall_override'):
            wall = want = ln['wall_override']
        keys = [C.item_key(it) for it in ln['items']]
        # Every item passed deadline_filter; a lane whose capped wall cannot hold all its items is still submitted,
        # and its unreached items return as not-reached for a later top-up.
        if ln['partition'] == 'shared' and shared_lanes >= C.MAX_SHARED_LANES:
            print('DEFER (shared lane cap)', ln['name'], keys); continue
        if free[ln['partition']] <= 0:
            print('DEFER (no slot)', ln['name'], ln['partition'], keys); continue
        note = '' if wall >= want else f' (wall capped from {hms(want)})'
        print(f"{'DRY ' if a.dry_run else ''}SUBMIT {ln['name']} {ln['partition']} mem={ln['mem_gib']}G cores={ln['cores']} "
              f"threads={ln['threads']} wall={hms(wall)}{note} model={ln['model_seconds'] / 3600:.2f}h items={[it['cutoff'] for it in ln['items']]}")
        if a.dry_run:
            t = subprocess.run(sbatch_command(ln, wall, C.CAMPAIGN / 'lanes' / 'DRYRUN.json', test_only=True),
                               capture_output=True, text=True)
            print('  sbatch --test-only:', t.returncode, (t.stderr or t.stdout).strip().splitlines()[-1:])
            if t.returncode != 0:
                sys.exit('sbatch --test-only refused the command')
            free[ln['partition']] -= 1; shared_lanes += ln['partition'] == 'shared'; continue
        lane = dict(ln, revision=rev, validation=a.validation, wall_s=wall)
        lf = C.CAMPAIGN / 'lanes' / f"{ln['name']}_{stamp}_{os.getpid()}.json"
        with open(os.open(lf, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644), 'w') as f:
            f.write(json.dumps(lane, indent=1) + '\n')
        job = subprocess.run(sbatch_command(ln, wall, lf), capture_output=True, text=True,
                             check=True).stdout.strip().split(';')[0]
        rec = dict(time=time.strftime('%Y-%m-%dT%H:%M:%S%z'), job=job, name=ln['name'], lane_file=str(lf),
                   partition=ln['partition'], qos=ln['qos'], mem_gib=ln['mem_gib'], cores=ln['cores'],
                   threads=ln['threads'], wall_s=wall, wanted_wall_s=want, model_seconds=ln['model_seconds'],
                   items=keys, attempt=ln['attempt'], revision=rev, validation=a.validation)
        with (C.CAMPAIGN / 'SUBMITTED.jsonl').open('a') as f:
            f.write(json.dumps(rec) + '\n')
        print('  job', job)
        free[ln['partition']] -= 1; shared_lanes += ln['partition'] == 'shared'
    for k, why in exhausted:
        print('EXHAUSTED', k, why)
        if not a.dry_run:
            record_exhausted(k, why, rev)
    print('rejected at planning (memory):', [f"{r['task']}_d{r['degree']}_L{r['cutoff']}" for r in rejected])
    if not a.dry_run:   # persisted like every other exhaustion decision (review IR-002)
        for r in rejected:
            record_exhausted(f"{r['task']}_d{r['degree']}_L{r['cutoff']}", r['reason'], rev)


if __name__ == '__main__':
    main()
