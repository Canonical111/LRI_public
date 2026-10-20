#!/usr/bin/env python3
"""Campaign registry: one or more active 5-point grids per expected (s, N) (FIT_MODEL_V3.md §4.7 union schema); job-id records;
consumed-usage accounting.

campaigns.json = {"root": ABS, "measurements": 2000000, "replicas": 8, "beta_points": 5,
                  "expected_pairs": ["0.8:1024", ...],            # the production grid, fixed independently of 'active'
                  "stageA_max_N": 65536,
                  "campaigns": [{"name","dir","stage","seed_base","s","sizes","status","job_ids"}...],
                  "active": {"<s>:<N>": ["<campaign name>", ...], ...}}   # legacy string values are read as one-element lists
validate() requires active.keys() == expected_pairs exactly, and for every listed campaign of every pair a manifest grid with
beta_points temperatures, replicas replicas each, and the expected measurement count. It returns {pair: [(campaign, tasks), ...]}.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from collections import defaultdict
from pathlib import Path

STORAGE_CAP_BYTES = 60_000_000_000


class RegistryLock:
    """IR18-002 / IR23-001/002: one mutex per registry file for every read-modify-write, implemented with a kernel-arbitrated advisory
    lock (fcntl.flock LOCK_EX on <registry>.lock). The kernel releases the lock when the holder exits or dies, so there is no stale-lock
    state, no takeover and no holder bookkeeping; waiting longer than `wait` seconds is an error. Lustre (Expanse), BeeGFS, ext4/APFS all
    support flock (the simulator's chain.lock uses the same call on the same file systems)."""
    def __init__(self, path: Path, wait: float = 120.0, stale: float = 0.0):
        self.path = Path(str(path) + '.lock'); self.wait = wait; self.fd = None
    def __enter__(self):
        import fcntl, time
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o664); t0 = time.time()
        while True:
            try: fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB); return self
            except (BlockingIOError, OSError) as ex:
                if getattr(ex, 'errno', None) not in (11, 35, None) and not isinstance(ex, BlockingIOError):   # EAGAIN/EWOULDBLOCK = held; anything else = failure
                    os.close(self.fd); self.fd = None; raise SystemExit(f'registry lock {self.path}: flock failed ({ex})')
                if time.time() - t0 > self.wait: os.close(self.fd); self.fd = None; raise SystemExit(f'registry lock {self.path} held for more than {self.wait:.0f} s: giving up')
                time.sleep(0.2)
    def owned(self) -> bool:
        return self.fd is not None
    def __exit__(self, *exc):
        import fcntl
        if self.fd is not None:
            try: fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally: os.close(self.fd); self.fd = None

def locked_update(path: Path, fn, validate: bool = True):
    """IR18-002: reload the registry under its lock, apply fn(r) and write it back atomically; returns fn's result."""
    with RegistryLock(path) as lock:
        r = load(path) if validate else json.loads(path.read_text())
        out = fn(r)
        if not lock.owned(): raise SystemExit(f'registry lock {lock.dir} was lost during the update (taken over as stale?): nothing written')   # IR22-001
        atomic_write(path, r); return out

def atomic_write(path: Path, obj) -> None:
    """R17-003: registries are rewritten atomically (temp + rename) so a concurrent reader never sees a partial file."""
    import os
    tmp = path.with_name(path.name + f'.tmp.{os.getpid()}'); tmp.write_text(json.dumps(obj, indent=1) + '\n'); os.replace(tmp, path)

def key(s: float, n: int) -> str: return f"{float(s)}:{int(n)}"

def load(path: Path) -> dict:
    r = json.loads(path.read_text()); names = [c['name'] for c in r['campaigns']]
    if len(set(names)) != len(names): raise SystemExit('duplicate campaign names')
    for f in ('root', 'measurements', 'replicas', 'beta_points', 'expected_pairs', 'stageA_max_N', 'campaigns', 'active'):
        if f not in r: raise SystemExit(f'registry lacks field {f}')
    for pair, v in list(r['active'].items()):          # §4.7: active values are lists of campaign names; legacy strings become one-element lists
        lst = [v] if isinstance(v, str) else list(v)
        if not lst or len(set(lst)) != len(lst) or not all(isinstance(x, str) for x in lst): raise SystemExit(f'active[{pair}] must be a non-empty list of distinct campaign names: {v!r}')
        r['active'][pair] = lst
    return r

def active_names(r: dict) -> list[str]:
    """Distinct campaign names appearing in any active list, in registry order."""
    names = {n for lst in r['active'].values() for n in lst}
    return [c['name'] for c in r['campaigns'] if c['name'] in names]

def portable_view(r: dict) -> dict:
    """Host-independent content of a registry (IR6-002): everything except `root`, job ids, statuses and host declarations."""
    return dict(measurements=r['measurements'], replicas=r['replicas'], beta_points=r['beta_points'], expected_pairs=sorted(r['expected_pairs']),
                stageA_max_N=r['stageA_max_N'], active={k: list(v) for k, v in sorted(r['active'].items())},
                campaigns=[{k: c[k] for k in sorted(c) if k not in ('job_ids', 'status', 'host', 'activation')} for c in r['campaigns']])

def campaign_index(r: dict, name: str) -> int:
    """Position of a campaign in the registry's campaigns list (recorded in merged entries, §4.7)."""
    return next(i for i, c in enumerate(r['campaigns']) if c['name'] == name)

def expected(r: dict, coverage: str) -> set[str]:
    if coverage == 'all': return set(r['expected_pairs'])
    if coverage == 'stageA': return {k for k in r['expected_pairs'] if int(k.split(':')[1]) <= r['stageA_max_N']}
    raise SystemExit(f'unknown coverage {coverage}')

def validate(r: dict, root: Path, require: str = 'all') -> dict:
    """Return {pair: [(campaign, manifest tasks), ...]} for the ACTIVE pairs (one entry per active campaign of the pair).
    require='all'   : active == expected_pairs (final acceptance, full merges);
    require='stageA': active ⊇ expected pairs with N <= stageA_max_N, active ⊆ expected (stage-A operations while
                      stage B is not yet prepared);
    require='active': active ⊆ expected (validate whatever is registered, e.g. window filtering of a partial summary).
    Every active campaign of a pair must have a manifest grid with beta_points temperatures, replicas replicas, expected measurements."""
    exp = set(r['expected_pairs']); act = set(r['active'])
    if act - exp: raise SystemExit(f'active pairs outside expected_pairs: {sorted(act - exp)}')
    if require == 'all' and act != exp: raise SystemExit(f'active pairs != expected pairs; missing {sorted(exp - act)}')
    if require == 'stageA':
        need = expected(r, 'stageA')
        if not need <= act: raise SystemExit(f'stage-A pairs not active: {sorted(need - act)}')
    if require not in ('all', 'stageA', 'active'): raise SystemExit(f'unknown require={require}')
    by = {c['name']: c for c in r['campaigns']}; out = {}
    for pair, names in r['active'].items():
        out[pair] = []
        for name in names:
            if name not in by: raise SystemExit(f'active campaign {name} for {pair} not registered')
            c = by[name]; s, n = pair.split(':'); s = float(s); n = int(n)
            if s not in [float(x) for x in c['s']] or n not in c['sizes']: raise SystemExit(f'pair {pair} not covered by campaign {name}')
            man = root / c['dir'] / 'manifest.json'
            if not man.exists(): raise SystemExit(f'missing manifest {man}')
            M = json.loads(man.read_text()); g = grid_of(r, c, M)   # REV-003: each campaign is validated against ITS OWN grid
            tasks = [t for t in M['tasks'] if abs(t['s'] - s) < 1e-12 and t['N'] == n]
            betas = sorted({t['beta'] for t in tasks}); idx = sorted({t['beta_index'] for t in tasks})
            if len(betas) != g['beta_points'] or idx != list(range(g['beta_points'])):
                raise SystemExit(f'{pair} in {name}: not a {g["beta_points"]}-point grid ({len(betas)} betas, indices {idx})')
            per = defaultdict(int)
            for t in tasks: per[t['beta']] += 1
            if any(v != g['replicas'] for v in per.values()): raise SystemExit(f'{pair} in {name}: replicas per temperature {dict(per)} != {g["replicas"]}')
            bad = [t['id'] for t in tasks if t['measurements'] != g['measurements']]
            if bad: raise SystemExit(f'{pair} in {name}: tasks {bad[:5]} have measurements != {g["measurements"]}')
            out[pair].append((c, tasks))
    return out

def grid_of(r: dict, c: dict, manifest: dict | None = None) -> dict:
    """The grid a campaign must satisfy (REV-003 / IR9-001): the registry-wide budget (beta_points, replicas, measurements) unless the
    campaign's REGISTRY entry declares an explicit `grid` override (independently registered, e.g. {"beta_points": 3} for a supplemental
    temperature grid). The manifest under validation never defines its own requirement. Minimum 3 temperatures (§4.7), >= 1 replica."""
    over = c.get('grid') or {}
    unknown = set(over) - {'beta_points', 'replicas', 'measurements'}
    if unknown: raise SystemExit(f"{c['name']}: unknown grid override keys {sorted(unknown)}")
    g = dict(beta_points=int(over.get('beta_points', r['beta_points'])), replicas=int(over.get('replicas', r['replicas'])), measurements=int(over.get('measurements', r['measurements'])))
    if g['beta_points'] < 3 or g['replicas'] < 1 or g['measurements'] < 1: raise SystemExit(f"{c['name']}: invalid grid {g} (need >= 3 temperatures)")
    return g

def activate(r: dict, root: Path, name: str) -> list[str]:
    """§4.7: append campaign `name` to the active list of every expected pair it covers (never replacing anything); the campaign
    must be registered and its manifest must pass the grid checks. Returns the pairs touched."""
    by = {c['name']: c for c in r['campaigns']}
    if name not in by: raise SystemExit(f'unknown campaign {name}')
    c = by[name]; touched = []
    for s in c['s']:
        for n in c['sizes']:
            pair = key(s, n)
            if pair not in r['expected_pairs']: raise SystemExit(f'{name}: pair {pair} not in expected_pairs')
            lst = r['active'].setdefault(pair, [])
            if name not in lst: lst.append(name); touched.append(pair)
    validate(r, root, 'active')
    return touched

def executed_without_jobs(r: dict, root: Path) -> list[str]:
    """Campaigns that have any DONE.json (i.e. were executed) but no recorded job ids."""
    bad = []
    for c in r['campaigns']:
        d = root / c['dir']
        if not c.get('job_ids') and (c.get('status') in ('submitted', 'complete') or any((d / 'chains').glob('*/DONE.json'))):
            bad.append(c['name'])
    return bad

def active_dirs(r: dict, max_n: int | None) -> list[str]:
    dirs = []
    for pair, names in r['active'].items():
        if max_n is None or int(pair.split(':')[1]) <= max_n:
            for name in names:
                d = next(c['dir'] for c in r['campaigns'] if c['name'] == name)
                if d not in dirs: dirs.append(d)
    return dirs

def storage_bytes(root: Path, r: dict | None = None) -> int:
    """Allocated bytes of THIS registry's campaign directories (raw samples, checkpoints, logs), not of everything that
    happens to live under root (other campaigns may share the root, e.g. the Δσ scan under $CAMP/scan)."""
    dirs = [root / c['dir'] for c in r['campaigns']] if r else [root]
    total = 0
    for d in dirs:
        if not d.exists(): continue
        p = subprocess.run(['du', '-s', '--block-size=1', str(d)], capture_output=True, text=True)   # allocated bytes
        if p.returncode != 0 or not p.stdout.split(): raise SystemExit(f'du failed for {d}: {p.stderr.strip()}')
        total += int(p.stdout.split()[0])
    return total

def usage(r: dict, root: Path, su_cap: float) -> bool:
    """Consumed SUs from sacct over every recorded job id (all allocation records once). Returns True only if the
    evidence is complete and both caps hold; any missing/unreadable accounting is a failure, not a smaller total."""
    ids = [(c['name'], j) for c in r['campaigns'] for j in c.get('job_ids', [])]
    total = 0.0; per = defaultdict(float); seen = set(); failed = []; empty = []
    fmt = 'JobID,DBIndex,Submit,AllocCPUS,ElapsedRaw,State'
    for name, jid in ids:
        p = subprocess.run(['sacct', '-j', str(jid), '-X', '--duplicates', '-n', '-P', '--format', fmt], capture_output=True, text=True)
        if p.returncode != 0: failed.append((jid, p.stderr.strip()[:200])); continue
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        if not lines: empty.append(jid); continue
        for line in lines:
            job, dbi, sub, cpus, el, state = line.split('|')[:6]
            rec = (job, dbi, sub)
            if rec in seen: continue
            seen.add(rec)
            try: su = int(cpus) * int(el) / 3600.0
            except ValueError: failed.append((jid, f'non-numeric record {line[:80]}')); continue
            per[name] += su; total += su
    sb = storage_bytes(root, r)
    for name in per: print(f'{name}: {per[name]:.1f} SU consumed')
    print(f'TOTAL consumed: {total:.1f} SU over {len(seen)} allocation records from {len(ids)} recorded job ids')
    print(f'storage (campaign dirs {[c["dir"] for c in r["campaigns"]]}): {sb:,} bytes = {sb/1e9:.2f} GB (decimal) = {sb/2**30:.2f} GiB; cap {STORAGE_CAP_BYTES/1e9:.0f} GB')
    ok = True
    if failed: print(f'ACCOUNTING INCOMPLETE: sacct failed for {failed}'); ok = False
    if empty: print(f'ACCOUNTING INCOMPLETE: no records for job ids {empty}'); ok = False
    if not ids: print('ACCOUNTING INCOMPLETE: no job ids recorded'); ok = False
    nojobs = executed_without_jobs(r, root)
    if nojobs: print(f'ACCOUNTING INCOMPLETE: executed campaigns without recorded job ids: {nojobs}'); ok = False
    if total > su_cap: print(f'SU CAP EXCEEDED: {total:.1f} > {su_cap}'); ok = False
    if sb > STORAGE_CAP_BYTES: print('STORAGE CAP EXCEEDED'); ok = False
    print('usage check:', 'PASS' if ok else 'FAIL')
    return ok

def estimate(r: dict, root: Path) -> None:
    rate = {16384: 1.63e7, 65536: 1.54e7, 262144: 1.48e7, 1048576: 1.18e7}   # measured on Expanse (tests/expanse_benchmark.json)
    def v(n):
        ks = sorted(rate)
        if n <= ks[0]: return rate[ks[0]]
        if n >= ks[-1]: return rate[ks[-1]]
        lo = max(k for k in ks if k <= n); hi = min(k for k in ks if k >= n)
        return rate[lo] if lo == hi else rate[lo] + (rate[hi] - rate[lo]) * (n - lo) / (hi - lo)
    tot = 0.0
    for c in r['campaigns']:
        man = root / c['dir'] / 'manifest.json'
        if not man.exists(): continue
        su = sum(t['N'] * (t['measurements'] + t['warmup']) / v(t['N']) for t in json.loads(man.read_text())['tasks']) / 3600
        print(f"{c['name']}: {su:.0f} SU (benchmark ESTIMATE; planning aid only, not consumption)"); tot += su
    print(f'TOTAL estimate: {tot:.0f} SU')

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('registry', type=Path)
    p.add_argument('--active-dirs', action='store_true'); p.add_argument('--max-N', type=int)
    p.add_argument('--record-job', nargs=2, metavar=('CAMPAIGN', 'JOBID'))
    p.add_argument('--usage', action='store_true'); p.add_argument('--su-cap', type=float, default=5000.0)
    p.add_argument('--estimate', action='store_true'); p.add_argument('--no-validate', action='store_true')
    p.add_argument('--require', choices=['all', 'stageA', 'active'], default='active', help='validation strictness for this call')
    p.add_argument('--activate', metavar='CAMPAIGN', help='append this registered campaign to the active lists of its pairs (§4.7) and save')
    a = p.parse_args(); r = load(a.registry); root = Path(r['root'])
    if a.activate:
        touched = locked_update(a.registry, lambda rr: activate(rr, root, a.activate)); print(f'activated {a.activate} for {touched}'); return   # R17-003 / IR18-002: atomic under the registry lock
    if a.record_job:
        name, jid = a.record_job
        if not any(c['name'] == name for c in r['campaigns']): raise SystemExit(f'unknown campaign {name}')
        def rec(rr):
            c = next(c for c in rr['campaigns'] if c['name'] == name)
            if int(jid) not in c.setdefault('job_ids', []): c['job_ids'].append(int(jid))
            c['status'] = 'submitted'
        locked_update(a.registry, rec, validate=False); print(f'recorded job {jid} for {name}'); return   # R17-003 / IR18-002
    if not a.no_validate:
        pairs = validate(r, root, a.require); print(f'registry OK ({a.require}): {len(pairs)} active pairs, {len(r["campaigns"])} campaigns', file=sys.stderr)
    if a.active_dirs: print('\n'.join(active_dirs(r, a.max_N)))
    if a.estimate: estimate(r, root)
    if a.usage and not usage(r, root, a.su_cap): raise SystemExit(2)
if __name__ == '__main__': main()
