#!/usr/bin/env python3
"""Verify every chain of every ACTIVE campaign against its manifest and the registry's expected counts (plan §6 step 5).

Checks per task: manifest measurements == registry 'measurements'; DONE.json exists; its N, beta, seed equal the
task's; measurements_done == measurements_target == expected; samples.bin size == 32 * expected; 'replicas' complete
replicas per (s, N, beta); stderr logs contain nothing but the known harmless anaconda libuuid notice.
Exit 0 only if everything passes.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, re, time
from collections import Counter
from pathlib import Path
from registry import load, validate, grid_of

# Known harmless stderr: the anaconda libuuid notice, and Slurm's cancellation banner. The banner appears for chains that
# were deliberately moved between jobs (scancel -> checkpoint -> resume elsewhere); a chain that was cancelled and never
# completed is still caught by the DONE.json / replica checks, so whitelisting the banner loses no signal.
HARMLESS = re.compile(r'libuuid\.so\.1: no version information available|slurmstepd: error: \*\*\* (JOB|STEP) \S+ ON \S+ CANCELLED AT ')

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''): h.update(chunk)
    return h.hexdigest()

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('registry', type=Path); p.add_argument('--max-N', type=int)
    p.add_argument('--campaigns', nargs='+', help='check only these active campaigns (per-host snapshot of a split point)')
    p.add_argument('--evidence', type=Path, help='write a JSON completion record (per task: DONE.json and samples.bin SHA-256 and size; manifest hash)')
    a = p.parse_args(); r = load(a.registry); root = Path(r['root']); pairs = validate(r, root, 'stageA' if a.max_N else 'all')
    M0 = r['measurements']; R0 = r['replicas']   # legacy defaults; every campaign is checked against its own grid (REV-003)
    names = sorted({c['name'] for lst in pairs.values() for c, _ in lst}); ok = missing = mismatched = 0; groups = Counter(); problems = []
    if a.campaigns:
        unknown = sorted(set(a.campaigns) - set(names))
        if unknown: raise SystemExit(f'--campaigns not active in the registry: {unknown}')
        names = [n for n in names if n in a.campaigns]
    expected_groups = 0; evidence = dict(registry=str(a.registry.resolve()), registry_sha256=sha(a.registry), host=platform.node(),
                                         time=time.strftime('%F_%T'), campaigns={}, tasks=[])
    for name in names:
        c = next(c for c in r['campaigns'] if c['name'] == name); cdir = root / c['dir']
        active_pairs = {k for k, lst in pairs.items() if any(cc['name'] == name for cc, _ in lst)}
        evidence['campaigns'][name] = dict(dir=str(cdir), manifest_sha256=sha(cdir / 'manifest.json'), host_declared=c.get('host'), pairs=sorted(active_pairs))
        MAN = json.loads((cdir / 'manifest.json').read_text()); g = grid_of(r, c, MAN); M = g['measurements']; R = g['replicas']; bp = g['beta_points']
        for t in MAN['tasks']:
            k = f"{float(t['s'])}:{int(t['N'])}"
            if k not in active_pairs or (a.max_N and t['N'] > a.max_N): continue
            if t['measurements'] != M: mismatched += 1; problems.append(dict(campaign=name, task=t['id'], manifest_measurements=t['measurements'], expected=M)); continue
            d = cdir / t['directory']; done = d / 'DONE.json'
            if not done.exists(): missing += 1; continue
            st = json.loads(done.read_text()); raw = d / 'samples.bin'
            engine = t.get('engine', 'v1')
            good = (st['N'] == t['N'] and abs(st['beta'] - t['beta']) < 1e-15 and st['seed'] == t['seed']
                    and st['measurements_done'] == M and st['measurements_target'] == M
                    and st.get('warmup_done') == t['warmup']                    # IR21-003: the warm-up the manifest prescribes (§5.1)
                    and raw.exists() and raw.stat().st_size == 32 * M
                    and st.get('record_columns', 4) == 4                       # 4-column record (32 bytes/row) for both engines
                    and (st.get('engine', 'v1') == engine)                     # the record was produced by the task's engine
                    and st.get('nn_extra', 0) == 0                              # IR18-001: the production Hamiltonian has no auxiliary nearest-neighbour coupling
                    and (engine == 'v1' or (st.get('sampler') == 'backbone' and abs(st.get('s', -1) - float(t['s'])) < 1e-12
                                            # IR18-001: the sampler parameters exactly as run_task.py issues them for this task
                                            and st.get('core_radius') == t.get('core_radius', 256) and st.get('near_radius') == t.get('near_radius', 1)
                                            and st.get('batch') == t.get('batch', 0))))
            if good: ok += 1; groups[(name, t['s'], t['N'], t['beta'])] += 1
            else: mismatched += 1; problems.append(dict(campaign=name, task=t['id'], status=st, raw_size=raw.stat().st_size if raw.exists() else None))
            if a.evidence and good:
                evidence['tasks'].append(dict(campaign=name, task=t['id'], s=t['s'], N=t['N'], beta=t['beta'], seed=t['seed'], directory=t['directory'], engine=t.get('engine', 'v1'),
                                              done_sha256=sha(done), samples_size=raw.stat().st_size, samples_sha256=sha(raw)))
        errs = [l for f in (cdir / 'logs').glob('*.err') for l in f.read_text().splitlines() if l.strip() and not HARMLESS.search(l)]
        if errs: problems.append(dict(campaign=name, stderr_lines=errs[:20], count=len(errs)))
    grids = {c['name']: grid_of(r, c, json.loads((root / c['dir'] / 'manifest.json').read_text())) for c in r['campaigns'] if c['name'] in names}
    for k, lst in pairs.items():
        for c, tasks in lst:
            if c['name'] in names and (not a.max_N or int(k.split(':')[1]) <= a.max_N): expected_groups += grids[c['name']]['beta_points']
    short = {g: n for g, n in groups.items() if n != grids[g[0]]['replicas']}
    print(f'{ok} ok, {missing} missing, {mismatched} mismatched; {len(groups)}/{expected_groups} groups present, {len(short)} groups without their full replica count')
    for pr in problems[:10]: print(json.dumps(pr)[:300])
    if short: print('incomplete groups:', list(short.items())[:10])
    good = not (missing or mismatched or short or problems) and len(groups) == expected_groups
    print('completion check:', 'PASS' if good else 'FAIL', f'(campaigns {names})')
    if a.evidence:
        evidence.update(result='PASS' if good else 'FAIL', ok=ok, missing=missing, mismatched=mismatched, groups=len(groups),
                        expected_groups=expected_groups, problems=problems[:20])
        a.evidence.write_text(json.dumps(evidence, indent=1) + '\n'); print(f'evidence written: {a.evidence}')
    raise SystemExit(0 if good else 1)
if __name__ == '__main__': main()
