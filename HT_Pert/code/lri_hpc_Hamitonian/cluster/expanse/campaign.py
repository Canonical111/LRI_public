"""Cutoff-push campaign on Expanse (PLAN G5): planned cutoffs, calibrated memory/time models, routing, lanes.

Pure planning code (no Slurm calls); submit_cutoffs.py and status.py use it. Units: GiB (2**30 bytes).

Memory model (per task/degree, from the two largest calibration cutoffs of a passing validation job V):
    RSS = a + dim * (n + e(L)),   e(L) = int32 edge bytes per state (incl. the two int64 row pointers),
extrapolated linearly in L (the measured growth is concave, so this is conservative). Above 2**31-1 states the
edge indices are int64 (lri_hpc.basis.make_edges): each edge grows from 7 to 11 bytes. Request = 1.3*RSS + 4 GiB
(PLAN §3.3). A cutoff whose request exceeds the node limit is admitted as a best-effort "stretch" item if
1.15*RSS + 4 GiB still fits; stretch items run last in their lane.

Time model: t = 60 s + c*dim, with c the seconds/state (fixed costs included) of the 64-thread calibration run at
the largest calibration cutoff. Threads are capped at 64 (the largest measured configuration; review LRI-010). A lane's
wall limit is 3x its summed model time + 10 min, at least 1 h, at most 20 h and at most the time left before the
assumed allocation expiry minus 1 h.
"""
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

LRIHT_HOME = Path(os.environ.get('LRIHT_HOME', '<SCRATCH>/temp_project/lri_ht'))
# Overrides exist for tests only (tests/test_lane_claims.py); production uses the defaults.
CAMPAIGN = Path(os.environ.get('LRIHT_CAMPAIGN', LRIHT_HOME / 'campaign'))
RESULTS = Path(os.environ.get('LRIHT_RESULTS', LRIHT_HOME / 'results'))
# The allocation page says "Expiration September 30, 2026" without a time; assume the end of that day (Pacific).
EXPIRY = datetime(2026, 9, 30, 23, 59, tzinfo=timezone(timedelta(hours=-7)))

CAPS = {('thermal', 7): (15, 12), ('phi6', 5): (14, 8), ('phi6', 3): (10, 4)}
MARGIN, MARGIN_STRETCH, PAD_GIB = 1.3, 1.15, 4.0
SHARED_MAX_GIB = 240          # shared MaxMemPerNode = 249325 MB = 243.5 GiB
LARGE_MAX_GIB = 1950          # large-shared MaxMemPerNode = 2055652 MB = 2007.5 GiB
SHARED_GIB_PER_CORE = 1.9
MIN_SHARED_CORES, MAX_THREADS = 16, 64
WALL_FACTOR, WALL_MIN_S, WALL_MAX_S, LANE_PAD_S, ITEM_OVERHEAD_S = 3.0, 3600, 20 * 3600, 600, 60
SHARED_LANE_TARGET_S = 2400   # target model time per shared lane
MAX_SHARED_LANES = 18         # user rule: <= 22 running normal-QOS node jobs in total (2 others already running)
MAX_LARGE_SUBMITTED = 4       # QOS large-shared-normal: MaxSubmitPU=4, MaxJobsPU=2
INT32_MAX = 2**31 - 1


def dimension(task, degree, cutoff):
    from lri_hpc.basis import count_tables
    pmax, qmax = CAPS[(task, degree)]
    G, Z = count_tables(cutoff, pmax, qmax)
    return int(Z[pmax, qmax, 4 * cutoff])


def planned_cutoffs(task, degree):
    """Candidate cutoffs, largest admissible determined later by the memory model."""
    if (task, degree) == ('thermal', 7):
        return list(range(52, 131, 2))
    if (task, degree) == ('phi6', 5):   # 54 and 58 exist already (phi6_extension.json)
        return [52, 56] + list(range(60, 124, 2)) + list(range(124, 181, 4))
    if (task, degree) == ('phi6', 3):   # 64..128 exist already (phi6_thin3*.json)
        return list(range(136, 257, 8)) + list(range(288, 1025, 32))
    raise KeyError((task, degree))


def load_calibration(val_dir: Path):
    """Calibration rows from V's per-run outputs (the summary lists them); returns {(task,degree): rows}."""
    s = json.loads((val_dir / 'summary.json').read_text())
    out = {}
    for row in s['runs']:
        r = json.loads((val_dir / row['file']).read_text())
        k = r['ranks'][0]
        out.setdefault((r['task'], r['degree']), []).append(dict(
            cutoff=r['cutoff'], dim=r['basis_dimension'], threads=row.get('threads') or r.get('threads'),
            rss=k['maxrss_kib'] * 1024, edges=k['edges_bytes'], seconds=r['seconds'], source=r['source_sha256']))
    return s, out


class Model:
    def __init__(self, task, degree, rows):
        self.task, self.degree = task, degree
        by_cut = {}
        for r in rows:  # RSS does not depend on threads; keep the largest RSS per cutoff
            if r['cutoff'] not in by_cut or r['rss'] > by_cut[r['cutoff']]['rss']:
                by_cut[r['cutoff']] = r
        cuts = sorted(by_cut)
        if len(cuts) < 2:
            raise ValueError(f'{task} d{degree}: need two calibration cutoffs, have {cuts}')
        r1, r2 = by_cut[cuts[-2]], by_cut[cuts[-1]]
        rest1, rest2 = r1['rss'] - r1['edges'], r2['rss'] - r2['edges']
        self.n = (rest2 - rest1) / (r2['dim'] - r1['dim'])
        self.a = max(0.0, rest2 - self.n * r2['dim'])
        e1, e2 = r1['edges'] / r1['dim'], r2['edges'] / r2['dim']
        self.e_ref, self.L_ref = e2, r2['cutoff']
        self.e_slope = max(0.0, (e2 - e1) / (r2['cutoff'] - r1['cutoff']))
        fast = [r for r in rows if r['cutoff'] == cuts[-1] and r['threads'] == MAX_THREADS]
        if not fast:
            raise ValueError(f'{task} d{degree}: no {MAX_THREADS}-thread calibration row at the largest cutoff')
        # seconds/state of the largest calibration run, fixed costs included (smaller runs are overhead-dominated)
        self.c = max(r['seconds'] / r['dim'] for r in fast)
        self.calibration = [(r['cutoff'], r['dim']) for r in (r1, r2)]

    def edge_bytes_per_state(self, L, dim):
        e = self.e_ref + self.e_slope * (L - self.L_ref)
        return e if dim <= INT32_MAX else 16 + (e - 16) * 11 / 7

    def rss_gib(self, L, dim):
        return (self.a + dim * (self.n + self.edge_bytes_per_state(L, dim))) / 2**30

    def seconds(self, dim):
        return ITEM_OVERHEAD_S + self.c * dim

    def describe(self):
        return dict(a_gib=self.a / 2**30, bytes_per_state_nonedge=self.n, edge_bytes_per_state_ref=self.e_ref,
                    edge_slope_per_cutoff=self.e_slope, ref_cutoff=self.L_ref, seconds_per_state=self.c,
                    calibration=self.calibration)


def route(model, L, dim):
    """Return an item dict with request and partition, or None if no admissible single-node request exists."""
    rss = model.rss_gib(L, dim)
    req = math.ceil(MARGIN * rss + PAD_GIB)
    stretch = False
    if req > LARGE_MAX_GIB:
        if MARGIN_STRETCH * rss + PAD_GIB > LARGE_MAX_GIB:
            return None
        req, stretch = LARGE_MAX_GIB, True
    part = 'shared' if req <= SHARED_MAX_GIB else 'large-shared'
    return dict(task=model.task, degree=model.degree, cutoff=L, dim=dim, int64=dim > INT32_MAX,
                model_rss_gib=round(rss, 2), request_gib=req, partition=part, stretch=stretch,
                model_seconds=round(model.seconds(dim), 1))


def item_key(it):
    return f"{it['task']}_d{it['degree']}_L{it['cutoff']}"


def output_path(it):
    return RESULTS / f"{it['task']}_d{it['degree']}" / f"{item_key(it)}.json"


def plan_items(models, dim_fn=dimension):
    items, rejected = [], []
    for (task, degree), model in models.items():
        for L in planned_cutoffs(task, degree):
            dim = dim_fn(task, degree, L)
            it = route(model, L, dim)
            if it is None:
                rss = round(model.rss_gib(L, dim), 1)
                rejected.append(dict(task=task, degree=degree, cutoff=L, dim=dim, model_rss_gib=rss,
                                     reason=f'memory: model {rss} GiB, no admissible single-node request'))
                # memory grows with the cutoff: every larger candidate of this task is rejected too (review IR-002)
                rejected += [dict(task=task, degree=degree, cutoff=M, dim=None, model_rss_gib=None,
                                  reason=f'memory: larger than the rejected cutoff {L}')
                             for M in planned_cutoffs(task, degree) if M > L]
                break
            items.append(it)
    return items, rejected


def resources(partition, mem_gib):
    """(cores, threads). shared: cores follow memory, so both are charged alike. large-shared: exactly MAX_THREADS
    cores, the threads actually used, so a lane fits beside other jobs on a partly used 128-core node (only three
    large-shared nodes were usable on 2026-09-29)."""
    if partition == 'shared':
        cores = min(128, max(MIN_SHARED_CORES, math.ceil(mem_gib / SHARED_GIB_PER_CORE)))
    else:
        cores = MAX_THREADS
    return cores, min(cores, MAX_THREADS)


def wall_seconds(model_seconds, now=None):
    now = now or datetime.now(timezone.utc)
    left = (EXPIRY - now).total_seconds() - 3600
    want = max(WALL_MIN_S, WALL_FACTOR * model_seconds + LANE_PAD_S)
    return int(min(want, WALL_MAX_S, left)), int(want)


def make_lanes(items):
    """Group remaining items into lanes (one Slurm job each; items run sequentially, largest first).

    large-shared: thermal alternates between two lanes (submitted first), phi6 d5 between two more; stretch items go
    last in the first lane of their task. shared: per task/degree, greedy descending lanes of about
    SHARED_LANE_TARGET_S model time.
    """
    big = [it for it in items if it['partition'] == 'large-shared']
    small = [it for it in items if it['partition'] == 'shared']
    lanes = []
    for task_key in [('thermal', 7), ('phi6', 5), ('phi6', 3)]:
        sel = sorted([it for it in big if (it['task'], it['degree']) == task_key and not it['stretch']],
                     key=lambda it: -it['dim'])
        stretch = sorted([it for it in big if (it['task'], it['degree']) == task_key and it['stretch']],
                         key=lambda it: it['dim'])
        if not sel and not stretch:
            continue
        pair = [[], []]
        for i, it in enumerate(sel):
            pair[i % 2].append(it)
        pair[0].extend(stretch)
        lanes += [p for p in pair if p]
    for task_key in [('thermal', 7), ('phi6', 5), ('phi6', 3)]:
        sel = sorted([it for it in small if (it['task'], it['degree']) == task_key], key=lambda it: -it['dim'])
        cur, t = [], 0.0
        for it in sel:
            if cur and t + it['model_seconds'] > SHARED_LANE_TARGET_S:
                lanes.append(cur); cur, t = [], 0.0
            cur.append(it); t += it['model_seconds']
        if cur:
            lanes.append(cur)
    out = []
    for items_ in lanes:
        part = items_[0]['partition']
        mem = max(it['request_gib'] for it in items_)
        cores, threads = resources(part, mem)
        msec = sum(it['model_seconds'] for it in items_)
        first = items_[0]
        name = f"lriht-{first['task']}{first['degree']}-L{first['cutoff']}x{len(items_)}"
        out.append(dict(name=name, partition=part, qos='large-shared-normal' if part == 'large-shared' else None,
                        mem_gib=mem, cores=cores, threads=threads, model_seconds=round(msec, 1),
                        items=[dict(it, threads=threads) for it in items_]))
    return out
