#!/usr/bin/env python3
"""Campaign status: every planned cutoff as done, running, queued, unknown, killed, interrupted, failed, not-reached,
exhausted or unsubmitted.

Usage (Expanse login node, after `source cluster/expanse/env.sh`): python cluster/expanse/status.py [--json]
Reads $LRIHT_HOME/campaign/{plan.json,SUBMITTED.jsonl,EXHAUSTED.jsonl,events/*.jsonl}, squeue and sacct. An item is
done only if its output exists, carries the current source fingerprint and passes lri_hpc.validate.check_result.

A job absent from squeue counts as finished only if sacct succeeds and reports a terminal state (review LRI-012);
otherwise its unfinished items are "unknown", and submit_cutoffs.py will not resubmit them. For a started item:
  - an end event with the child SIGKILLed (rc -9/137) while the lane supervisor survived -> killed (the cgroup OOM
    killer; scancel and the wall limit signal the supervisor first, which then logs "terminated" and exits);
  - no end event: TIMEOUT -> interrupted, OUT_OF_MEMORY -> killed, any other terminal state (CANCELLED, NODE_FAIL,
    FAILED, ...) -> failed;
  - any other nonzero end -> failed.
Only killed and interrupted are retried automatically. Exhaustion decisions are persisted in EXHAUSTED.jsonl
(review LRI-014).
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent)); sys.path.insert(0, str(HERE))
import campaign as C
from lri_hpc.validate import check_result

MAX_ATTEMPTS = 2   # the first attempt plus one retry (PLAN §3.4, review LRI-006)


def load_submitted():
    f = C.CAMPAIGN / 'SUBMITTED.jsonl'
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []


def squeue_jobs():
    out = subprocess.run(['squeue', '--me', '-h', '-o', '%i|%j|%T|%P'], capture_output=True, text=True, check=True).stdout
    jobs = {}
    for line in out.splitlines():
        i, n, t, p = line.split('|')
        jobs[i] = dict(name=n, state=t, partition=p)
    return jobs


TERMINAL = {'COMPLETED', 'FAILED', 'TIMEOUT', 'OUT_OF_MEMORY', 'CANCELLED', 'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL',
            'DEADLINE'}


def sacct_states(ids):
    """{jobid: state} from sacct; raises if sacct fails. Missing or nonterminal jobs are handled by the caller."""
    if not ids:
        return {}
    p = subprocess.run(['sacct', '-X', '-n', '-P', '-o', 'JobID,State', '-j', ','.join(ids)], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f'sacct failed ({p.returncode}): {p.stderr.strip()}')
    return {l.split('|')[0]: l.split('|')[1].split()[0] for l in p.stdout.splitlines() if '|' in l}


def load_exhausted():
    f = C.CAMPAIGN / 'EXHAUSTED.jsonl'
    return {json.loads(l)['key']: json.loads(l) for l in f.read_text().splitlines() if l.strip()} if f.exists() else {}


def events(job):
    f = C.CAMPAIGN / 'events' / f'{job}.jsonl'
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []


def output_ok(it, fp):
    out = C.output_path(it)
    if not out.exists():
        return False, 'no output'
    try:
        r = json.loads(out.read_text())
        if (r.get('task'), r.get('degree'), r.get('cutoff')) != (it['task'], it['degree'], it['cutoff']):
            return False, f"output identity {(r.get('task'), r.get('degree'), r.get('cutoff'))} != requested item"
        if r.get('source_sha256') != fp:
            return False, 'output from other source'
        check_result(r)
        return True, f"{r['seconds']:.0f} s, {r['ranks'][0]['maxrss_kib'] / 2**20:.1f} GiB"
    except Exception as e:  # noqa: BLE001
        return False, f'rejected: {e}'


def collect(items, subs, queue, fp, exhausted=None):
    """Per-item state. attempts = lanes in which the item started (not-reached lanes do not count)."""
    exhausted = load_exhausted() if exhausted is None else exhausted
    active_jobs = {s['job'] for s in subs if s['job'] in queue}
    ended = [s['job'] for s in subs if s['job'] not in queue]
    acct = sacct_states(ended)
    unknown_jobs = {j for j in ended if acct.get(j) not in TERMINAL}
    ev = {s['job']: events(s['job']) for s in subs}
    res = {}
    for it in items:
        key = C.item_key(it)
        ok, detail = output_ok(it, fp)
        mine = [s for s in subs if key in s['items']]
        st = dict(key=key, attempts=0, lanes=[s['job'] for s in mine], detail=detail)
        if ok:
            st['state'] = 'done'; res[key] = st; continue
        act = [s for s in mine if s['job'] in active_jobs]
        if act:
            s = act[-1]; q = queue[s['job']]['state']
            started = any(e.get('key') == key and e['event'] == 'start' for e in ev[s['job']])
            st['state'] = 'running' if (q == 'RUNNING' and started) else 'queued'
            st['detail'] = f"job {s['job']} {q}"
            res[key] = st; continue
        unk = [s['job'] for s in mine if s['job'] in unknown_jobs]
        if unk:
            st['state'] = 'unknown'
            st['detail'] = 'no terminal accounting for job(s) ' + ','.join(f"{j}:{acct.get(j, 'missing')}" for j in unk)
            res[key] = st; continue
        last = None
        for s in mine:
            evs = [e for e in ev[s['job']] if e.get('key') == key]
            if any(e['event'] == 'start' for e in evs):
                st['attempts'] += 1
                t0 = [e['t'] for e in evs if e['event'] == 'start' and 't' in e]
                t1 = [e['t'] for e in evs if e['event'] in ('end', 'terminated') and 't' in e]
                elapsed = (t1[-1] - t0[-1]) if t0 and t1 else None
                end = [e for e in evs if e['event'] == 'end']
                js = acct[s['job']]
                if end:
                    e = end[-1]
                    kind = 'killed' if e['rc'] in (-9, 137) else 'failed'
                    reason = e.get('reason')
                else:
                    kind = {'TIMEOUT': 'interrupted', 'OUT_OF_MEMORY': 'killed'}.get(js, 'failed')
                    reason = f'job {js}, no end event'
                last = dict(kind=kind, reason=reason, job=s['job'], job_state=js, mem_gib=s['mem_gib'], wall_s=s['wall_s'],
                            elapsed_s=elapsed)
        if key in exhausted:
            st['state'] = 'exhausted'; st['last'] = last
            st['detail'] = f"exhausted: {exhausted[key]['reason']}"
        elif not mine:
            st['state'] = 'unsubmitted'
        elif last is None:
            st['state'] = 'not-reached'
            st['detail'] = 'lane(s) ' + ','.join(f"{j}:{acct.get(j, '?')}" for j in st['lanes']) + ' ended before this item'
        else:
            st['state'] = last['kind'] if last['kind'] == 'failed' or st['attempts'] < MAX_ATTEMPTS else 'exhausted'
            st['last'] = last
            st['detail'] = f"{last['kind']} in job {last['job']} ({last['reason']})"
        res[key] = st
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--json', action='store_true'); a = ap.parse_args()
    from lri_hpc.solver import source_fingerprint
    plan = json.loads((C.CAMPAIGN / 'plan.json').read_text())
    subs = load_submitted()
    res = collect(plan['items'], subs, squeue_jobs(), source_fingerprint())
    for r in plan['rejected']:   # memory-rejected candidates are part of the inventory (review IR-002)
        key = f"{r['task']}_d{r['degree']}_L{r['cutoff']}"
        res[key] = dict(key=key, state='exhausted', attempts=0, lanes=[], detail=r['reason'])
    if a.json:
        print(json.dumps(res, indent=1)); return
    count = {}
    for it in plan['items']:
        s = res[C.item_key(it)]
        count[s['state']] = count.get(s['state'], 0) + 1
        print(f"{s['key']:22s} {it['partition']:12s} {it['request_gib']:5d}G {s['state']:12s} {s['detail']}")
    for r in plan['rejected']:
        key = f"{r['task']}_d{r['degree']}_L{r['cutoff']}"
        count['exhausted'] = count.get('exhausted', 0) + 1
        print(f"{key:22s} {'-':12s} {'-':>5s}  {'exhausted':12s} {r['reason']}")
    print('summary:', json.dumps(count))


if __name__ == '__main__':
    main()
