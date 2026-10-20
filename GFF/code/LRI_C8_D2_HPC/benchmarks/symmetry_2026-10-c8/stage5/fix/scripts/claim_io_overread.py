#!/usr/bin/env python3
"""Post-hoc analysis of the A-ORC-13 real-Slurm run (fxio): why tools/claim_io.py fails, and the comparison once the
cause is accounted for. Run in the export (it imports tools/production.py) on the login node (reads JSON only):
  claim_io_overread.py RUN EVIDENCE_DIR OUT.json
Hypothesis: production.stage_graphs opens the pack with Python's default buffering, whose buffer is the file system's
st_blksize (BeeGFS: 524,288 bytes). After each seek outside the buffer, read(length) reads whole buffer blocks and then
refills one 512 KiB buffer, so the claim process reads pack bytes beyond its members; those bytes are the claim's own
pack data but are not counted in its own bytes. This script replays CPython's BufferedReader seek/read rules over every
block's sorted members (inventory offsets and lengths) and gives, per run, the predicted pack bytes read, the over-read
(predicted - staged), and the non-own bytes minus the over-read; then the plan's comparison (smallest against largest
group by tasks.sqlite, max(10%, 2 MB)) on the corrected values. Nothing in the campaign is changed."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'tools'))
import production as P  # noqa: E402
import claim_io as C  # noqa: E402

run, ev, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
m = json.loads((run / 'manifest.json').read_text())
I = P.Inputs('inputs', json.loads(Path('inputs/manifest.json').read_text())); inv_all = P.load_inventory(I)


def buffered_bytes(members, B):
    tot = 0; bs = be = None
    for off, ln in members:
        if bs is not None and bs <= off <= be: pos = off
        else: bs = be = None; pos = off
        avail = (be - pos) if bs is not None else 0
        if ln <= avail: continue
        rem = ln - avail; pos += avail; direct = rem - rem % B; tot += direct; pos += direct; rem -= direct
        if rem > 0: tot += B; bs = pos; be = pos + B
        else: bs = be = None
    return tot


rep = C.evaluate(run, sorted((ev / 'logs').glob('idx*.log')))
runs = []
for f in sorted((ev / 'logs').glob('idx*.log')):
    r = C.last_record(f)
    if not r or r.get('status') != 'ok': continue
    j = m['jobs'][r['index']]; p, cfg = P.group_of(run, m, j['group']); rows = P.job_rows(run, j)
    B = os.stat(I.pack(cfg['sector'], cfg['L'])).st_blksize
    inv = {x['id']: x for x in inv_all[cfg['sector']][str(cfg['L'])]}
    staged = pred = 0
    for block in P.blocks_of_rows(rows, m['checkpoint_tasks']):
        mem = [(inv[g]['offset'], inv[g]['length']) for g in sorted({t[2] for t in block})]
        staged += sum(l for _, l in mem); pred += buffered_bytes(mem, B)
    own_staged = r['own']['staged_members']['bytes']
    over = pred - staged
    runs.append(dict(index=r['index'], group=j['group'], tasks_sqlite_bytes=(run / 'groups' / j['group'] / 'tasks.sqlite').stat().st_size,
                     st_blksize=B, staged=staged, own_staged_counted=own_staged, predicted_pack_reads=pred, overread=over,
                     non_own_minus_fingerprint_rchar=r['non_own_minus_fingerprint_rchar'], non_own_minus_fingerprint_bytes=r['non_own_minus_fingerprint_bytes'],
                     non_own_bytes=r['non_own_bytes'],
                     corrected=dict(non_own_bytes=r['non_own_bytes'] - over, non_own_minus_fingerprint_bytes=r['non_own_minus_fingerprint_bytes'] - over,
                                    non_own_minus_fingerprint_rchar=r['non_own_minus_fingerprint_rchar'] - over)))
sizes = {x['group']: x['tasks_sqlite_bytes'] for x in runs}
small = min(sizes, key=lambda g: (sizes[g], g)); large = max(sizes, key=lambda g: (sizes[g], g))
comp = {}
for v in C.VARIANTS:
    a = [x['corrected'][v] for x in runs if x['group'] == small]; b = [x['corrected'][v] for x in runs if x['group'] == large]
    worst = max(((abs(p - q), max(C.REL * min(p, q), C.ABS)) for p in a for q in b), key=lambda t: t[0] / t[1])
    comp[v] = dict(small=[min(a), max(a)], large=[min(b), max(b)], largest_difference=worst[0], tolerance=worst[1], passed=worst[0] <= worst[1])
allc = [x['corrected']['non_own_minus_fingerprint_rchar'] for x in runs]
doc = dict(schema='c8-d2-claim-io-overread-1', run=str(run), claim_io_verdict=rep.get('verdict'), claim_io_comparison=rep.get('comparison'),
           hypothesis=__doc__.split('\n\n')[0], smallest=small, largest=large, tasks_sqlite_ratio=round(sizes[large] / sizes[small], 2),
           corrected_comparison=comp, corrected_passed=all(c['passed'] for c in comp.values()),
           corrected_non_own_minus_fingerprint_rchar_range_all_runs=[min(allc), max(allc)], runs=sorted(runs, key=lambda x: x['index']))
out.write_text(json.dumps(doc, indent=1) + '\n')
print(json.dumps({k: doc[k] for k in ('claim_io_verdict', 'smallest', 'largest', 'tasks_sqlite_ratio', 'corrected_passed', 'corrected_non_own_minus_fingerprint_rchar_range_all_runs')}))
for x in doc['runs']: print(x['index'], x['group'], 'overread', x['overread'], 'non_own-fp_rchar', x['non_own_minus_fingerprint_rchar'], 'corrected', x['corrected']['non_own_minus_fingerprint_rchar'])
