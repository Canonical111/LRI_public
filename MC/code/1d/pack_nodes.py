#!/usr/bin/env python3
"""Pack chains of one or more campaigns onto exclusive Expanse compute nodes and (optionally) submit them.

Usage:
  pack_nodes.py CAMPAIGN_DIR [CAMPAIGN_DIR ...] --nodes K --slots 128 --out JOBDIR [--min-N N] [--max-N N]
                [--array-job JOBID] [--time HH:MM:SS] [--submit] [--max-running 22] [--max-submitted 54]
Each node job runs `--slots` sequential queues in parallel; chains are assigned to queues by longest-processing-time
first using the per-size rate table below, so every queue ends near the same time. Each queue is pinned with taskset
to its own core (core k for k < 128) — with 128 slots all cores are used; with 40 slots the cores are spread one per
4-core L3 complex; with 64, two per complex.
If --array-job is given, each node job first cancels the array tasks of its chains (they checkpoint on SIGTERM) and
waits for them to leave the queue before resuming (same protocol as the stage-B takeover of 2026-09-15).
Completed chains (DONE.json present) are skipped at generation time; run_task.py skips them at run time as well.
Submission enforces the yun124 rule: my normal-QOS jobs <= --max-running running and <= --max-submitted queued+running,
counting collaborators' jobs (the whole account) against the 32/64 caps too.
"""
from __future__ import annotations
import argparse, json, os, secrets, subprocess, time, sys
from pathlib import Path

# measured spin-sweeps/s per chain on an Expanse node (exclusive, cache-resident sizes) and observed for large N
RATE = {1024: 1.6e7, 2048: 1.6e7, 4096: 1.6e7, 8192: 1.6e7, 16384: 1.63e7, 32768: 1.6e7, 65536: 1.54e7,
        131072: 1.5e7, 262144: 1.3e7, 524288: 1.47e7}
# engine '1d' (bin/lri_mc_1d): measured on Expanse exp-9-56 with 128 concurrent chains per node (job 54360665, 2026-09-19); the rate is
# flat in the concurrency (32 -> 128 chains at 2^19: 30.4 -> 28.5 ms/sweep), so 128 slots per node are used for 1d campaigns
RATE_1D = {65536: 1.52e7, 131072: 1.73e7, 262144: 1.83e7, 524288: 1.84e7}

def seconds(t: dict) -> float:
    if t.get('engine', 'v1') == '1d':
        return t['N'] * (t['measurements'] + t['warmup']) / RATE_1D.get(t['N'], 1.5e7)
    return t['N'] * (t['measurements'] + t['warmup']) / RATE.get(t['N'], 1.2e7)

def pool_names(nodes: int, offset: int, remaining: int, max_running: int, pool: str = 'lriN') -> list[str]:
    """Singleton job names for `nodes` node jobs (R12-001 / R13-001): at most min(nodes, remaining) DISTINCT names of the shared pool, starting
    at `offset` (my running+pending normal-QOS jobs) modulo max_running; further node jobs reuse the names and are serialised by singleton."""
    width = max(1, min(nodes, remaining))
    return [f'{pool}{(offset + (n % width)) % max_running}' for n in range(nodes)]

def atomic_json(path: Path, obj) -> None:
    tmp = path.with_name(path.name + f'.tmp.{os.getpid()}'); tmp.write_text(json.dumps(obj, indent=1) + '\n'); os.replace(tmp, path)

def cpu_list(slots: int) -> list[int]:
    """Slot -> core. Slots are filled by LPT in index order (longest chains first), so the lowest slots hold the heaviest
    chains: spread them one per 4-core L3 complex first (cores 0,4,...,124), then a second core per complex (2,6,...),
    then a third (1,5,...), then the rest (3,7,...)."""
    order = [4 * j for j in range(32)] + [4 * j + 2 for j in range(32)] + [4 * j + 1 for j in range(32)] + [4 * j + 3 for j in range(32)]
    return order[:slots] if slots <= 128 else list(range(slots))

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('campaigns', type=Path, nargs='+'); p.add_argument('--nodes', type=int, required=True)
    p.add_argument('--slots', type=int, default=128); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--min-N', type=int, default=0); p.add_argument('--max-N', type=int, default=1 << 30)
    p.add_argument('--sizes', type=int, nargs='*', help='keep only these N (in addition to the min/max range)')
    p.add_argument('--dependency', type=str, help='sbatch --dependency value applied to every node job (e.g. afterany:1:2:3)')
    p.add_argument('--array-job', type=str, help='array job id whose tasks are to be taken over (single campaign only)')
    p.add_argument('--array-slot-tasks', type=int, help='chains per array slot of --array-job (array.slurm: slot k runs tasks k*K .. k*K+K-1); required with --array-job (R11-003)')
    p.add_argument('--cancel-jobs', type=str, nargs='*', default=[], help='whole job ids to scancel (and wait for) when the node job starts, e.g. competing shared arrays')
    p.add_argument('--time', default='06:00:00'); p.add_argument('--mem', default='240G'); p.add_argument('--name', default='lriPack')
    p.add_argument('--account', default='yun124'); p.add_argument('--partition', default='compute')
    p.add_argument('--submit', action='store_true'); p.add_argument('--max-running', type=int, default=22); p.add_argument('--max-submitted', type=int, default=54)
    p.add_argument('--registry', type=Path, help='campaigns.json to record job ids into (campaign name = directory basename)')
    p.add_argument('--record-registries', action='store_true', help='R16-002: after each successful sbatch, append the job id to <campaign>/../campaigns.json of every campaign with chains on that node (idempotent)')
    a = p.parse_args()
    if a.array_job and len(a.campaigns) != 1: raise SystemExit('--array-job needs exactly one campaign')
    if a.array_job and not a.array_slot_tasks: raise SystemExit('--array-job requires --array-slot-tasks (chains per array slot) so that the OWNING slots are cancelled (R11-003)')
    chains = []
    for c in a.campaigns:
        man = json.loads((c / 'manifest.json').read_text())
        for t in man['tasks']:
            if not (a.min_N <= t['N'] <= a.max_N): continue
            if a.sizes and t['N'] not in a.sizes: continue
            if (c / t['directory'] / 'DONE.json').exists(): continue
            chains.append((seconds(t), str(c.resolve()), t['id'], t['N']))
    if not chains: raise SystemExit('nothing to run')
    chains.sort(reverse=True)
    # LPT over nodes*slots queues
    Q = a.nodes * a.slots; load = [0.0] * Q; queues = [[] for _ in range(Q)]
    import heapq
    heap = [(0.0, q) for q in range(Q)]; heapq.heapify(heap)
    for sec, camp, tid, N in chains:
        l, q = heapq.heappop(heap); queues[q].append((camp, tid, N)); heapq.heappush(heap, (l + sec, q)); load[q] = l + sec
    a.out.mkdir(parents=True, exist_ok=True); cpus = cpu_list(a.slots)
    POOL = 'lriN'; name_offset = 0; remaining = a.max_running
    if a.submit:   # R12-001 / R13-001: capacity = my running limit minus ALL my normal-QOS jobs running or pending (any name); refuse when none remains
        from slurm_queue import my_jobs
        me = subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip()
        mine_now = [r for r in my_jobs(account=a.account) if r['qos'] == 'normal' and r['user'] == me and r['state'] in ('RUNNING', 'PENDING', 'COMPLETING')]
        name_offset = sum(r['count'] for r in mine_now)
        remaining = a.max_running - name_offset
        if remaining <= 0: raise SystemExit(f'no running capacity left: {name_offset} of my normal-QOS jobs are running or pending (limit {a.max_running})')
    if a.array_job and a.submit and remaining < a.nodes: raise SystemExit(f'takeover needs {a.nodes} DISTINCT singleton names but only {remaining} running slots remain: refusing (R14-001)')
    names = pool_names(a.nodes, name_offset, remaining, a.max_running, POOL)
    attempt = time.strftime('%Y%m%d_%H%M%S') + '_' + secrets.token_hex(3)   # R14-004: identity of this generation, bound into replacements.json
    def rotate_receipts():
        # V3-STATIC-003 / R16-002 / R17-001: receipts of an earlier attempt never pass for this one and are kept (renamed) for the audit trail;
        # rotation happens only right before THIS attempt submits (never at bare generation), and the per-attempt confirmation files
        # replacements_<attempt>.json of earlier takeovers are never touched (pending siblings of those attempts keep reading their own file)
        old_attempt = None
        if (a.out / 'submitted_status.json').exists():
            try: old_attempt = json.loads((a.out / 'submitted_status.json').read_text()).get('attempt')
            except (json.JSONDecodeError, OSError): old_attempt = None
        for stale in ('submitted.json', 'submitted_status.json'):
            f = a.out / stale
            if f.exists(): f.rename(a.out / f'{f.stem}_{old_attempt or "unknown"}{f.suffix}')
    if a.submit: print(f'capacity: {name_offset} of my jobs running/pending -> {len(set(names))} distinct singleton names for {a.nodes} node jobs')
    est = max(load) / 3600; used = sum(1 for l in load if l > 0)
    print(f'{len(chains)} chains on {a.nodes} nodes x {a.slots} slots ({used} slots used); longest queue {est:.2f} h, mean {sum(load)/Q/3600:.2f} h')
    scripts = []
    for n in range(a.nodes):
        qs = queues[n * a.slots:(n + 1) * a.slots]
        if not any(qs): continue
        # R11-004 / R12-001: singleton names from ONE shared pool lriN0..lriN<max_running-1> (independent of --name) with an offset given by my
        # pending+running normal-QOS jobs, so the distinct names in use across packings never exceed --max-running
        lines = ['#!/bin/bash', f'#SBATCH -J {names[n]}', f'#SBATCH --comment=pack:{a.name}', f'#SBATCH -A {a.account}', f'#SBATCH -p {a.partition}',
                 f'#SBATCH --nodes=1 --ntasks-per-node=1 --cpus-per-task=128 --mem={a.mem}', f'#SBATCH -t {a.time}',
                 f'#SBATCH -o {a.out.resolve()}/{a.name}{n}_%j.out', 'set -uo pipefail',
                 'source /etc/profile.d/modules.sh; module purge; module load cpu/0.15.4 gcc/10.2.0 anaconda3 slurm/expanse/23.02.7 || exit 1',
                 'export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1', 'cd ~/lri_cluster',
                 'echo "$(date) node $(hostname) start"']
        ids = [tid for q in qs for (_, tid, _) in q]
        if a.array_job:
            K = a.array_slot_tasks; slots = sorted({tid // K for tid in ids})
            # R11-003: every unfinished chain of a cancelled slot must be in THIS packing (otherwise the takeover would strand it)
            packed_all = {tid for q in queues for (_, tid, _) in q}
            man = json.loads((a.campaigns[0] / 'manifest.json').read_text())
            for sl in slots:
                for t in man['tasks']:
                    if t['id'] // K == sl and t['id'] not in packed_all and not (a.campaigns[0] / t['directory'] / 'DONE.json').exists():
                        raise SystemExit(f'array slot {sl} of {a.array_job} owns unfinished chain {t["id"]} that is not in this packing: refusing the takeover')
            # R13-003: cancel original slots only when EVERY replacement job of this packing is present in the queue (replacements.json is
            # written by the submitter after all submissions and releases succeeded); otherwise exit without touching the original slots
            lines += [f'R={a.out.resolve()}/replacements_{attempt}.json; k=0; while [ ! -f "$R" ] && [ $k -lt 120 ]; do sleep 5; k=$((k+1)); done',   # R17-001: this attempt's own confirmation file
                      '[ -f "$R" ] || { echo "confirmation file $R missing: takeover not confirmed, leaving the original array slots untouched"; exit 3; }',
                      # R14-004: one checked parse; the file must carry THIS attempt's id
                      'IDS=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(1) if d.get(\\"attempt\\")!=sys.argv[2] else print(\\" \\".join(str(x[1]) for x in d[\\"jobs\\"]))" "$R" ' + attempt + ') || { echo "replacements.json unreadable or from another attempt: takeover not confirmed, leaving the original array slots untouched"; exit 3; }',
                      '[ -n "$IDS" ] || { echo "no replacement job recorded: takeover not confirmed, leaving the original array slots untouched"; exit 3; }',
                      # R14-001: every sibling must be queued, running or already finished (a finished sibling did its share); any other or unknown state leaves the slots untouched
                      'for j in $IDS; do st=$(squeue -h -j $j -o %T 2>/dev/null | head -1); [ -n "$st" ] || st=$(sacct -n -P -j $j -o State,ExitCode 2>/dev/null | head -1 | sed "s/|0:0$//"); case "$st" in PENDING|RUNNING|COMPLETING|COMPLETED) ;; *) echo "replacement job $j state ${st:-unknown}: takeover not confirmed, leaving the original array slots untouched"; exit 3;; esac; done',
                      # V3-STATIC-001: every scancel checked; the wait uses checked queries ("Invalid job id" = gone, any other failure = UNKNOWN and
                      # retried); a slot still present or unknown after 5 min means the handoff is unconfirmed → exit 4 WITHOUT running any chain
                      f'for i in {" ".join(map(str, slots))}; do out=$(scancel {a.array_job}_$i 2>&1) || echo "$out" | grep -qiE "invalid job id|already complet" || {{ echo "scancel {a.array_job}_$i failed: $out — takeover not confirmed, not running the chains"; exit 4; }}; done',   # R16-001: a slot already gone (cancelled by a sibling) is fine
                      f'for i in {" ".join(map(str, slots))}; do k=0; while :; do st=$(squeue -h -j {a.array_job}_$i -o %T 2>&1); q=$?; if [ $q -eq 0 ] && [ -z "$st" ]; then break; fi; if [ $q -ne 0 ] && echo "$st" | grep -qi "invalid job id"; then break; fi; [ $q -ne 0 ] && echo "squeue failed for {a.array_job}_$i: $st (UNKNOWN, retrying)"; k=$((k+1)); [ $k -ge 60 ] && {{ echo "original slot {a.array_job}_$i still present or unknown after 5 min: takeover not confirmed, not running the chains"; exit 4; }}; sleep 5; done; done',
                      'echo "$(date) array slots gone (confirmed)"']
        if a.cancel_jobs:
            J = ' '.join(a.cancel_jobs)
            # V3-STATIC-001 (stage0_race path): checked scancel and checked wait; competing jobs still present or unknown → exit 4 without running
            lines += [f'for j in {J}; do out=$(scancel $j 2>&1) || echo "$out" | grep -qiE "invalid job id|already complet" || {{ echo "scancel $j failed: $out — competing jobs not confirmed gone, not running the chains"; exit 4; }}; done',   # R16-001
                      f'for j in {J}; do k=0; while :; do st=$(squeue -h -j $j -o %T 2>&1); q=$?; if [ $q -eq 0 ] && [ -z "$st" ]; then break; fi; if [ $q -ne 0 ] && echo "$st" | grep -qi "invalid job id"; then break; fi; [ $q -ne 0 ] && echo "squeue failed for $j: $st (UNKNOWN, retrying)"; k=$((k+1)); [ $k -ge 60 ] && {{ echo "competing job $j still present or unknown after 5 min: not running the chains"; exit 4; }}; sleep 5; done; done',
                      'echo "$(date) competing jobs cancelled (confirmed)"']
        lines.append('pids=()')
        def logname(camp, tid):   # IR6-004: point, campaign, task and job attempt (%j) in the log name; unique on a node across campaigns
            pc = Path(camp); return f'{a.name}{n}_{pc.parent.name}_{pc.name}_t{tid}_$SLURM_JOB_ID.out'
        for si, q in enumerate(qs):
            if not q: continue
            # V3-STATIC-002: a queue fails if ANY of its tasks fails (not only the last one); the node's rc aggregates all queues
            cmds = 'fail=0 ; ' + ' ; '.join(f'python3 run_task.py {camp} --task {tid} > {a.out.resolve()}/{logname(camp, tid)} 2>&1 || fail=1' for camp, tid, _ in q) + ' ; exit \\$fail'
            lines.append(f'taskset -c {cpus[si]} bash -c "{cmds}" & pids+=($!); sleep 0.2')
        lines += ['rc=0; for p in "${pids[@]}"; do wait $p; r=$?; [ $r -ne 0 ] && rc=$r; done',
                  'echo "$(date) node done rc=$rc"', 'exit $rc']
        sp = a.out / f'{a.name}{n}.sbatch'; sp.write_text('\n'.join(lines) + '\n'); scripts.append(sp)
        print(f'  {sp.name}: {len(ids)} chains, sizes {sorted({N for q in qs for (_, _, N) in q})}, longest queue {max(load[n*a.slots:(n+1)*a.slots])/3600:.2f} h')
    (a.out / 'packing.json').write_text(json.dumps(dict(attempt=attempt, nodes=a.nodes, slots=a.slots, chains=len(chains), est_hours=est,
        queues=[[dict(campaign=c, task=t, N=N, log=f'{a.name}{qi // a.slots}_{Path(c).parent.name}_{Path(c).name}_t{t}_<jobid>.out') for c, t, N in q] for qi, q in enumerate(queues)]), indent=1) + '\n')
    if not a.submit: print('not submitted (add --submit)'); return
    rotate_receipts()   # R17-001: only now, when this attempt is about to submit
    from slurm_queue import my_jobs   # RV3-004: a failed or malformed scheduler query aborts; array tasks are counted
    def acct():
        rows = [r for r in my_jobs(account=a.account) if r['qos'] == 'normal']
        me = subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip()
        if not me: raise SystemExit('cannot determine the user name for the capacity check')
        return dict(acct_total=sum(r['count'] for r in rows), acct_running=sum(r['count'] for r in rows if r['state'] == 'RUNNING'),
                    my_total=sum(r['count'] for r in rows if r['user'] == me), my_running=sum(r['count'] for r in rows if r['user'] == me and r['state'] == 'RUNNING'))
    submitted = []; state = dict(aborting=False); unrecorded = []   # IR22-002: (campaign, job id) pairs whose registry recording failed
    def record(status, reason=None):
        # R14-002: submitted.json stays a LIST of (script, job id) pairs (read by stageA_go.sh, stageB_scan_go.sh, stage0_race.sh); status beside it
        (a.out / 'submitted.json').write_text(json.dumps(submitted, indent=1) + '\n')
        (a.out / 'submitted_status.json').write_text(json.dumps(dict(attempt=attempt, status=status, reason=reason, submitted=len(submitted), scripts=len(scripts)), indent=1) + '\n')
    def abort(reason):
        # R13-002 / R14-003: one cleanup path for every unsuccessful exit of a takeover submission — cancel every held replacement, verify, record, exit 2
        state['aborting'] = True; print(f'submission aborted: {reason}')
        if a.array_job and submitted:
            for _, j in submitted: subprocess.run(['scancel', '--state=PENDING', j])
            left = [j for _, j in submitted if subprocess.run(['squeue', '-h', '-j', j, '-o', '%T'], capture_output=True, text=True).stdout.strip()]
            print(f'held replacements cancelled: {[j for _, j in submitted]}; still queued: {left or "none"}; original array slots untouched')
        record('aborted', reason); raise SystemExit(2)
    try:
        for sp in scripts:
            st = acct()
            if st['my_total'] >= a.max_submitted or st['acct_total'] >= 64 - 10 or st['acct_running'] >= 32 - 10 or st['my_running'] >= a.max_running:   # each cap independently (R11-004)
                if a.array_job: abort(f'cap reached ({st}) before {sp.name}')
                print(f'cap reached ({st}); not submitting {sp.name} and the rest — resubmit later'); break
            extra = ['--dependency', (a.dependency + ',singleton') if a.dependency else 'singleton']   # R11-004: singleton on the pooled name
            hold = ['--hold'] if a.array_job else []   # R12-002: takeover replacements are held until every script is submitted and released
            r = subprocess.run(['sbatch', '--parsable', *hold, *extra, str(sp)], capture_output=True, text=True)
            if r.returncode != 0:
                if a.array_job: abort(f'sbatch failed for {sp.name}: {r.stderr.strip()[:200]}')
                print(f'sbatch failed for {sp.name}: {r.stderr.strip()}'); break
            jid = r.stdout.strip().split(';')[0]; submitted.append((sp.name, jid)); print(f'  submitted {sp.name} -> {jid}  (account normal-QOS jobs now {st["acct_total"]+1})')
            if a.record_registries:   # R16-002: recorded immediately, so a later failure (other wave, cap, exception) never leaves this job unrecorded
                n_node = scripts.index(sp); camps_here = {c for q in queues[n_node * a.slots:(n_node + 1) * a.slots] for (c, _, _) in q}
                for c in sorted(camps_here):
                    regs = sorted(Path(c).parent.glob('campaigns*.json'))   # R17-004: campaigns.json and campaigns_stage0.json alike
                    hit = False
                    from registry import locked_update   # IR18-002: read-modify-write under the registry mutex
                    for regf in regs:
                        def rec(reg, c=c, jid=jid):
                            found = [camp for camp in reg.get('campaigns', []) if camp.get('dir', '').rstrip('/').split('/')[-1] == Path(c).name]
                            for camp in found:
                                if int(jid) not in camp.setdefault('job_ids', []): camp['job_ids'].append(int(jid)); camp['status'] = 'submitted'
                            return bool(found)
                        try: found = locked_update(regf, rec, validate=False)
                        except (json.JSONDecodeError, OSError, SystemExit) as ex: print(f'  warning: {regf} not updated ({type(ex).__name__}: {ex}); job {jid} not recorded there'); unrecorded.append((c, jid)); continue
                        hit = hit or found
                    if not hit: print(f'  warning: campaign {Path(c).name} not found in any {Path(c).parent}/campaigns*.json; job {jid} not recorded there'); unrecorded.append((c, jid))
            if a.registry:   # IR19-002: under the registry lock, atomic
                from registry import locked_update
                def rec_all(reg, jid=jid):
                    for c in a.campaigns:
                        name = c.resolve().name
                        for camp in reg['campaigns']:
                            if camp['dir'].rstrip('/').split('/')[-1] == name:
                                if int(jid) not in camp.setdefault('job_ids', []): camp['job_ids'].append(int(jid))
                                camp['status'] = 'submitted'
                locked_update(a.registry, rec_all, validate=False)
        if a.array_job:
            if len(submitted) != len(scripts): abort(f'only {len(submitted)}/{len(scripts)} replacement scripts submitted')
            failed = []
            for _, j in submitted:   # R13-003: every release result is checked
                rr = subprocess.run(['scontrol', 'release', j], capture_output=True, text=True)
                if rr.returncode != 0: failed.append((j, rr.stderr.strip()[:120]))
            if failed: abort(f'release failed for {failed}')
            tmp = a.out / f'replacements_{attempt}.json.tmp'   # R14-004 / R17-001: atomic confirmation, one file per attempt
            tmp.write_text(json.dumps(dict(attempt=attempt, jobs=submitted), indent=1) + '\n'); os.replace(tmp, a.out / f'replacements_{attempt}.json')
            print('takeover replacements released and confirmed')
    except BaseException as ex:   # R14-003: any exception while replacements may be held — SystemExit from a failed scheduler query included — cleans up
        if a.array_job and not state['aborting']: abort(f'{type(ex).__name__}: {ex}')
        if not a.array_job: record('partial', f'{type(ex).__name__}: {ex}'); print(f'submission interrupted after {len(submitted)} job(s): {type(ex).__name__}: {ex}')   # V3-STATIC-003
        raise
    if unrecorded:   # IR22-002: a submitted job missing from a registry is a failed submission record, never 'complete'
        (a.out / 'unrecorded_jobs.json').write_text(json.dumps([dict(campaign=c, job_id=j) for c, j in unrecorded], indent=1) + '\n')
        record('partial', f'{len(unrecorded)} (campaign, job) registrations failed: see unrecorded_jobs.json and record them with registry.py --record-job before relying on dependencies')
        print(f'{len(submitted)}/{len(scripts)} node jobs submitted but {len(unrecorded)} registry recordings FAILED (unrecorded_jobs.json)'); raise SystemExit(2)
    record('complete' if len(submitted) == len(scripts) else 'partial')
    print(f'{len(submitted)}/{len(scripts)} node jobs submitted')
    if len(submitted) != len(scripts): raise SystemExit(2)   # incomplete submission is a failure (IR7-003)
if __name__ == '__main__': main()
