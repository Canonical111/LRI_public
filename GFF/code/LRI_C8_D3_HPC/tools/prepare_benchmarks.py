#!/usr/bin/env python3
"""Create portable, deterministic profiling/benchmark input fixtures.

--order 7 (C7(3)'s fixtures, kept): the earlier timing summaries survive, but their original net/task files were not
separately delivered. These fixtures (benchmarks/fixtures/, committed in C7(3)) choose 16 highest-cost graphs per
sector/loop, with a documented seed; they allow matched old/new comparisons and are the f_E basis of A-PERF-1 (the same
files ran on symmetry in benchmarks/symmetry_2026-10/validation_567197/bench/). In C8(3) inputs/ holds the order-8
inputs, so `--order 7` only verifies the committed files (verify_fixtures7); it never rebuilds them.

--order 8 (C8(3) Stage 4a, PLAN "Performance plan", P1-P4; the design of C62d's tools/prepare_benchmarks.py --order 8,
LRI_C8_D2_HPC@2083d84, ported to d=3): frozen workloads in benchmarks/fixtures8/, chosen from the J-SWEEP-1 cost model
(seconds per point per graph, campaign a, measured on the Stage-3 baseline bin/c8d3_gmp 24adff54..., --mp-check on;
FIX8['cost_model']) and the sweep's per-graph promotion counts (FIX8['promotions']: graph_promotions.csv of every
group in sweep_groups.tgz, 2 x 512 points per graph and campaign). Both are J-SWEEP-1's committed evidence files
(benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/sweep1/); the model there is the byte copy (sha256 fc78fc8f...)
that Stages 3b-4a also had as cost_models/gmp_expanse_epyc7742_c8.json. The fixtures never read cost_models/: that
is the live site model, which Stage 5's Expanse calibration refresh (J-SWEEP-2, data-only commit) replaces. The blocks:
  strat_{free,power}_L7   P1: the plan's L7 blocks: 120 graphs drawn at random within 8 equal-count bins of T (the
                          number of terms; 15 per bin) plus the 8 heaviest by cost model, 2 replicates x 4 chunks
                          (1,024 tasks; a graph whose task would exceed max_task_seconds gets more chunks); ~45 s at 64
                          threads. Every graph carries its stratum and weight (bin size / 15; 1 for the heaviest), so the
                          per-graph tier timers of bin/c8d3_gmp_prof re-weight the block to the population
  strat_{free,power}_L8   P1: the same at L8, 2 replicates x 1 chunk (256 tasks nominal); ~90 s at 64 threads
  heavy_{free,power}_L8   P1 (per-call law at the heavy end; MP self-check overhead): the 128 heaviest graphs, 2 x 1
  nopromo_free_L7/L8      P2: promotion-free graphs (quad = mp = 0 in both campaigns' sweep rows), heaviest first: 64
                          graphs x 2 x 8 chunks at L7, 128 x 2 x 1 at L8; ~30-40 s at 64 threads. The power sector has
                          no promotion-free graph at d=3 (J-SWEEP-1)
  random_{free,power}_L7/L8  P3: 256 graphs drawn uniformly, 2 x 1; ~30 s at 128 threads
  p4_{free,power}_L8      P4: the fixed L8 lane-shape workload, graphs drawn uniformly per sector in proportion to the
                          sector sizes (16,064 : 4,336), 2 replicates x 32,768 points, cut into tasks by production's
                          rule (chunk = the largest power of two <= 60 s / c_g, clamped to [256, 32,768]), sized to ~330 s
                          of ideal node time at 128 cores; a prefix of each sector's draw is again a uniform draw, so
                          --fraction 0.5 halves it
Before any selection the inputs are verified against their manifest (prepare_inputs.verify through
benchkit.verified_inputs: every pinned file, the Stage-2b chain, the vendored pins; S4-005), and the fixture manifest's
inputs_manifest_sha256, inventory_sha256 and gamma_sha256 are those verified hashes; a failure refuses (65) and leaves
no fixture folder.
Points per graph and replicate are the power of two that puts the cost model's predicted wall closest (in log2) to the
target; a graph whose task would exceed max_task_seconds (a quarter of the target wall) is cut into more chunks.
Every block uses campaign a's native settings (rate .8, layout 0, compensated sums, 52-bit nets, --mp-check on) and
its own native and net seeds: SHA-256 of 'c8-d3-bench|<seed>|<block>|native' or '|net' (benchkit.bench_seed) with the
documented master seed FIX8['seed']; uniform draws sort graph ids by SHA-256 of 'c8-d3-bench|<seed>|<draw>|<id>'
(benchkit.rank_key). No result of these fixtures is physical; their seeds are not campaign seeds (a fixture never plans,
merges or assembles anything; tools/seeds.py never sees it).
The task and net files and manifest.json are committed (< 2 MB); graph members are staged at run time from the pinned
packs (the L8 packs are not in git: `make link-l8 STORE=$C8_STORE` on Expanse) and verified against their inventory
sha256. The task files and the selections are pure functions of the cost model, the promotion counts, the inventory and
the seed; the Sobol nets come from scipy (production.make_net) and are pinned by sha256 (their bytes can differ between
scipy versions, which --check reports).
  prepare_benchmarks.py --order 8            build benchmarks/fixtures8 if absent, else verify it (sha256 and pins)
  prepare_benchmarks.py --order 8 --check    rebuild into a temporary folder and compare with the committed fixtures
  prepare_benchmarks.py --order 8 --stage-check DIR   also stage every fixture graph from the packs into DIR (cluster)
  prepare_benchmarks.py --order 7            verify the committed C7(3) fixtures (benchmarks/fixtures)
"""
from __future__ import annotations
import argparse,csv,io,json,math,shutil,sys,tarfile,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT, load, checked, digest
from production import make_net, TASK_SECONDS, MIN_CHUNK


def prepare_benchmarks() -> dict:
    """C7(3)'s order-7 fixtures: verified, never rebuilt (verify_fixtures7). C7(3)'s builder called
    prepare_inputs.prepare(), which in C8(3) refuses (inputs/ holds the order-8 inputs), so a missing manifest is an
    error here."""
    return verify_fixtures7()


def verify_fixtures7(folder: Path | None = None) -> dict:
    """The committed C7(3) fixtures (benchmarks/fixtures): every listed file against the manifest's sha256. The
    inventory pin of that manifest is C7(3)'s prepared inputs/inventory.json at a6ce987, which this package keeps as
    tests/fixtures/c7_inputs/inventory.json (checked)."""
    folder = Path(folder) if folder else ROOT / 'benchmarks' / 'fixtures'
    manifest = folder / 'manifest.json'
    if not manifest.exists():
        raise FileNotFoundError(f'{manifest} is missing: the C7(3) fixtures are committed files; they are not rebuilt in C8(3)')
    result = load(manifest)
    checked(ROOT / 'tests/fixtures/c7_inputs/inventory.json', result['inventory_sha256'])
    for name, sha in result['sha256'].items():
        checked(folder / name, sha)
    return result

# ---------------------------------------------------------------- order 8 (C8(3) Stage 4a)
# cost_model: the Stage-3 Expanse model (J-SWEEP-1, sha256 fc78fc8f..., executable 24adff54...) as J-SWEEP-1's evidence
# copy, never cost_models/gmp_expanse_epyc7742_c8.json (the live site model; Stage 5's refresh replaces it). Until
# 2026-10-06 the manifest named the cost_models/ path (the Stage-4a manifest, sha256 becacd70..., that the Stage-4a
# profiling records cite); the bytes read are the same.
FIX8 = dict(seed=2026100531, inputs='inputs', campaign='a', rate='.8', layout=0, sum_mode='compensated', bits=52, mp_check='on',
            cost_model='benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/sweep1/gmp_expanse_epyc7742_c8.json',
            promotions='benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/sweep1/sweep_groups.tgz')
BLOCKS8 = (
    dict(name='strat_free_L7', purpose='P1', sector='free', L=7, select='tbins', graphs=128, bins=8, heaviest=8, replicates=2, chunks=4, target_seconds=45, target_threads=64),
    dict(name='strat_power_L7', purpose='P1', sector='power', L=7, select='tbins', graphs=128, bins=8, heaviest=8, replicates=2, chunks=4, target_seconds=45, target_threads=64),
    dict(name='strat_free_L8', purpose='P1', sector='free', L=8, select='tbins', graphs=128, bins=8, heaviest=8, replicates=2, chunks=1, target_seconds=90, target_threads=64),
    dict(name='strat_power_L8', purpose='P1', sector='power', L=8, select='tbins', graphs=128, bins=8, heaviest=8, replicates=2, chunks=1, target_seconds=90, target_threads=64),
    dict(name='heavy_free_L8', purpose='P1', sector='free', L=8, select='heaviest', graphs=128, replicates=2, chunks=1, target_seconds=90, target_threads=64),
    dict(name='heavy_power_L8', purpose='P1', sector='power', L=8, select='heaviest', graphs=128, replicates=2, chunks=1, target_seconds=90, target_threads=64),
    dict(name='nopromo_free_L7', purpose='P2', sector='free', L=7, select='nopromo', graphs=64, replicates=2, chunks=8, target_seconds=30, target_threads=64),
    dict(name='nopromo_free_L8', purpose='P2', sector='free', L=8, select='nopromo', graphs=128, replicates=2, chunks=1, target_seconds=40, target_threads=64),
    dict(name='random_free_L7', purpose='P3', sector='free', L=7, select='random', graphs=256, replicates=2, chunks=1, target_seconds=30, target_threads=128),
    dict(name='random_power_L7', purpose='P3', sector='power', L=7, select='random', graphs=256, replicates=2, chunks=1, target_seconds=30, target_threads=128),
    dict(name='random_free_L8', purpose='P3', sector='free', L=8, select='random', graphs=256, replicates=2, chunks=1, target_seconds=30, target_threads=128),
    dict(name='random_power_L8', purpose='P3', sector='power', L=8, select='random', graphs=256, replicates=2, chunks=1, target_seconds=30, target_threads=128),
)
WORKLOADS8 = (dict(name='p4_L8', purpose='P4', L=8, sectors=('free', 'power'), replicates=2, points=32768, target_seconds=330, target_threads=128),)
SELECTION = {
    'tbins': 'the plan\'s P1 block: graphs drawn at random (benchkit.rank_key order) within equal-count bins of T (terms, ties by id) of '
             'the sector\'s graphs other than the heaviest, plus the heaviest graphs by cost model (campaign a)',
    'heaviest': 'the graphs with the largest cost-model seconds per point (campaign a), ties by id',
    'nopromo': 'promotion-free graphs (no binary128 and no MP evaluation in either campaign\'s J-SWEEP-1 rows), heaviest first',
    'random': 'a uniform draw: graph ids sorted by benchkit.rank_key(seed, block, id), the first N',
    'proportional': 'a uniform draw per sector (benchkit.rank_key order), sector counts in proportion to the sector sizes, grown until the predicted ideal wall reaches the target',
}


def _spp(cm: dict, campaign: str, sector: str, L: int, gid: int) -> float:
    k = f'{campaign}:{sector}:{L}:{gid}'
    if k not in cm['seconds_per_point']:
        raise KeyError(f'the cost model has no key {k}')
    return float(cm['seconds_per_point'][k])


def read_promotions(path: Path) -> dict:
    """{(campaign, sector, L, graph): [points, quad, mp]} from the sweep's graph_costs.csv and graph_promotions.csv (L7
    and L8 groups of sweep_groups.tgz; every replicate summed)."""
    out = {}
    with tarfile.open(path, 'r:gz') as tf:
        for c in ('a', 'b'):
            for s in ('free', 'power'):
                for L in (7, 8):
                    g = f'groups/{c}_{s}_L{L}/'
                    pts = {int(r['graph']): int(r['points']) for r in csv.DictReader(io.TextIOWrapper(tf.extractfile(g + 'graph_costs.csv'), 'utf-8'))}
                    for r in csv.DictReader(io.TextIOWrapper(tf.extractfile(g + 'graph_promotions.csv'), 'utf-8')):
                        k = (c, s, L, int(r['graph']))
                        v = out.setdefault(k, [pts[int(r['graph'])], 0, 0])
                        v[1] += int(r['quad']); v[2] += int(r['mp'])
    return out


def _pow2_points(cost_per_point_sum: float, target_seconds: float, threads: int) -> int:
    """The power of two P that puts P x cost_per_point_sum / threads closest to target_seconds in log2."""
    x = target_seconds * threads / cost_per_point_sum
    return 1 << max(6, min(22, round(math.log2(x))))


def _pow2_ceil(x: float) -> int:
    return 1 if x <= 1 else 1 << math.ceil(math.log2(x))


def _select(spec: dict, cm: dict, inv: dict, prom: dict, seed: int) -> tuple[list[int], dict]:
    """The block's graphs and, per graph, its stratum and weight (graphs it stands for in the sector population)."""
    from benchkit import rank_key
    s, L, c = spec['sector'], spec['L'], FIX8['campaign']
    rows = {r['id']: r for r in inv[s][str(L)]}
    ids = sorted(rows)
    heavy = sorted(ids, key=lambda g: (-_spp(cm, c, s, L, g), g))
    strata = {}
    if spec['select'] == 'heaviest':
        pick = heavy[:spec['graphs']]
        strata = {g: {'stratum': 'heaviest', 'weight': 1.0} for g in pick}
    elif spec['select'] == 'nopromo':
        free = [g for g in ids if all(prom[(x, s, L, g)][1] == 0 and prom[(x, s, L, g)][2] == 0 for x in ('a', 'b'))]
        pick = sorted(free, key=lambda g: (-_spp(cm, c, s, L, g), g))[:spec['graphs']]
        strata = {g: {'stratum': 'nopromo', 'weight': None} for g in pick}
    elif spec['select'] == 'random':
        pick = sorted(ids, key=lambda g: rank_key(seed, spec['name'], g))[:spec['graphs']]
        strata = {g: {'stratum': 'uniform', 'weight': len(ids) / spec['graphs']} for g in pick}
    elif spec['select'] == 'tbins':
        top = heavy[:spec['heaviest']]
        rest = sorted((g for g in ids if g not in set(top)), key=lambda g: (int(rows[g]['terms']), g))
        nb = spec['bins']; per = (spec['graphs'] - len(top)) // nb
        if per * nb + len(top) != spec['graphs']:
            raise ValueError(f'{spec["name"]}: {spec["graphs"]} graphs is not {nb} bins x a whole number plus {len(top)} heaviest')
        pick = list(top)
        for g in top:
            strata[g] = {'stratum': 'heaviest', 'weight': 1.0}
        for b in range(nb):
            lo, hi = len(rest) * b // nb, len(rest) * (b + 1) // nb
            members = rest[lo:hi]
            draw = sorted(members, key=lambda g: rank_key(seed, f'{spec["name"]}_bin{b}', g))[:per]
            for g in draw:
                strata[g] = {'stratum': f'T{b}', 'weight': len(members) / len(draw),
                             'terms_range': [int(rows[members[0]]['terms']), int(rows[members[-1]]['terms'])]}
            pick += draw
    else:
        raise ValueError(f'unknown selection {spec["select"]}')
    if not pick:
        raise ValueError(f'{spec["name"]}: no graph meets the selection {spec["select"]}')
    return sorted(pick), strata


def _write_block(folder: Path, name: str, sector: str, L: int, ids: list, reps: int, chunks: dict, total: int, seed: int,
                 cm: dict, prom: dict, inv: dict, purpose: str, selection: str, target: dict | None, strata: dict | None) -> tuple[dict, dict]:
    """chunks: {graph: number of equal chunks of its `total` points per replicate} (each a power of two)."""
    from benchkit import bench_seed, write_tasks
    rows, u = [], 0
    for rep in range(reps):
        for g in sorted(ids):
            k = chunks[g]; step = total // k
            for i in range(k):
                rows.append((u, rep, g, i * step, (i + 1) * step, total)); u += 1
    tasks, net = folder / f'{name}.tasks', folder / f'{name}.net'
    write_tasks(tasks, 8, L, rows)
    meta = make_net(net, reps, 4 * L - 1, FIX8['bits'], bench_seed(seed, name, 'net'), total)
    c = FIX8['campaign']
    spp = {str(g): _spp(cm, c, sector, L, g) for g in sorted(ids)}
    cms = math.fsum(spp[str(r[2])] * (r[4] - r[3]) for r in rows)
    frac = lambda g, i: prom[(c, sector, L, g)][i] / prom[(c, sector, L, g)][0]
    pts = sum(r[4] - r[3] for r in rows)
    quad = math.fsum(frac(r[2], 1) * (r[4] - r[3]) for r in rows); mp = math.fsum(frac(r[2], 2) * (r[4] - r[3]) for r in rows)
    prim = {r['id'] for r in inv[sector][str(L)] if r.get('primitive')}
    rec = dict(name=name, purpose=purpose, sector=sector, L=L, selection=selection, graphs=sorted(ids), primitive_graphs=len(prim & set(ids)),
               replicates=reps, total=total, chunks={str(g): chunks[g] for g in sorted(ids)}, tasks=len(rows), points=pts,
               native_seed=bench_seed(seed, name, 'native'), net=meta, files={'tasks': tasks.name, 'net': net.name},
               seconds_per_point=spp,
               predicted=dict(cost_model_seconds=cms, quad_calls=quad, mp_calls=mp, quad_fraction=quad / pts, mp_fraction=mp / pts,
                              max_task_seconds=max(spp[str(r[2])] * (r[4] - r[3]) for r in rows),
                              **({'threads': target['threads'], 'wall_seconds': cms / target['threads'], 'target_seconds': target['seconds']} if target else {})))
    if strata is not None:
        rec['strata'] = {str(g): strata[g] for g in sorted(ids)}
    return rec, {tasks.name: digest(tasks), net.name: digest(net)}


def build_fixtures8(folder: Path, inputs_rel: str = FIX8['inputs'], cost_model: Path | None = None, promotions: Path | None = None,
                    seed: int = FIX8['seed'], blocks=BLOCKS8, workloads=WORKLOADS8) -> dict:
    """Write the order-8 fixtures into the new folder (refused when it exists) and return the manifest."""
    import scipy, numpy
    from benchkit import FIXTURE_SCHEMA, rank_key, verified_inputs
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    try:   # S4-005: the inputs verified against their manifest (prepare_inputs.verify) before any selection; the fixture
        _, inv, vin = verified_inputs(inputs_rel)   # pins below are the verified hashes, never digests of unchecked bytes
    except BaseException:
        folder.rmdir()
        raise
    cmp = Path(cost_model) if cost_model else ROOT / FIX8['cost_model']
    prp = Path(promotions) if promotions else ROOT / FIX8['promotions']
    cm = load(cmp)
    prom = read_promotions(prp)
    c = FIX8['campaign']
    recs, hashes = {}, {}
    for spec in blocks:
        ids, strata = _select(spec, cm, inv, prom, seed)
        unit = math.fsum(_spp(cm, c, spec['sector'], spec['L'], g) for g in ids) * spec['replicates']
        total = _pow2_points(unit, spec['target_seconds'], spec['target_threads'])
        cap = spec['target_seconds'] / 4   # max task seconds (one thread runs a task): a quarter of the target wall
        chunks = {g: max(spec['chunks'], min(total // 64, _pow2_ceil(_spp(cm, c, spec['sector'], spec['L'], g) * total / cap))) for g in ids}
        rule = SELECTION[spec['select']] + f' (N = {spec["graphs"]}' + (f'; {spec["bins"]} bins + {spec["heaviest"]} heaviest' if spec['select'] == 'tbins' else '') + ')'
        rec, h = _write_block(folder, spec['name'], spec['sector'], spec['L'], ids, spec['replicates'], chunks, total, seed, cm, prom, inv,
                              spec['purpose'], rule, {'threads': spec['target_threads'], 'seconds': spec['target_seconds']}, strata)
        rec['max_task_seconds_rule'] = 'a graph is cut into the smallest power-of-two number of chunks (at least the block\'s) whose predicted task time is <= a quarter of the target wall'
        recs[spec['name']] = rec
        hashes.update(h)
    wls = {}
    for wl in workloads:
        L, P, R = wl['L'], wl['points'], wl['replicates']
        order = {s: sorted((r['id'] for r in inv[s][str(L)]), key=lambda g: rank_key(seed, f'{wl["name"]}_{s}', g)) for s in wl['sectors']}
        sizes = {s: len(order[s]) for s in wl['sectors']}
        lead = wl['sectors'][0]
        cost = {s: [_spp(cm, c, s, L, g) * P * R for g in order[s]] for s in wl['sectors']}
        need = wl['target_seconds'] * wl['target_threads']
        k = {s: 0 for s in wl['sectors']}
        for kl in range(1, sizes[lead] + 1):
            k = {s: (kl if s == lead else min(sizes[s], max(1, round(kl * sizes[s] / sizes[lead])))) for s in wl['sectors']}
            if math.fsum(math.fsum(cost[s][:k[s]]) for s in wl['sectors']) >= need:
                break
        names = []
        for s in wl['sectors']:
            name = f'{wl["name"].split("_")[0]}_{s}_L{L}'
            ids = order[s][:k[s]]
            # production's chunking (D.5): chunk_g = the largest power of two <= TASK_SECONDS / c_g, clamped to [MIN_CHUNK, P]
            chunks = {}
            for g in ids:
                ch = 1 << max(0, math.floor(math.log2(TASK_SECONDS / _spp(cm, c, s, L, g))))
                ch = min(P, max(MIN_CHUNK, ch))   # a stratum smaller than MIN_CHUNK points is one task
                chunks[g] = P // ch
            rule = SELECTION['proportional'] + f' ({k[s]} of {sizes[s]} {s} L{L} graphs, in draw order {wl["name"]}_{s})'
            rec, h = _write_block(folder, name, s, L, ids, R, chunks, P, seed, cm, prom, inv, wl['purpose'], rule, None,
                                  {g: {'stratum': 'uniform', 'weight': sizes[s] / len(ids)} for g in ids})
            rec['draw_order'] = list(ids)
            rec['chunk_rule'] = f'production D.5: chunk = the largest power of two <= {TASK_SECONDS:g} s / c_g, clamped to [{MIN_CHUNK}, {P}]'
            recs[name] = rec
            hashes.update(h)
            names.append(name)
        cms = math.fsum(recs[n]['predicted']['cost_model_seconds'] for n in names)
        wls[wl['name']] = dict(purpose=wl['purpose'], blocks=names, L=L, replicates=R, points_per_graph_replicate=P, target_seconds=wl['target_seconds'],
                               target_threads=wl['target_threads'], cost_model_seconds=cms, predicted_ideal_wall_seconds=cms / wl['target_threads'],
                               fraction_rule='--fraction F keeps the first ceil(F x k) graphs of each sector in draw order (both replicates)')
    rel = lambda p: (p.resolve().relative_to(ROOT.resolve()).as_posix() if str(p.resolve()).startswith(str(ROOT.resolve())) else str(p))
    m = dict(schema=FIXTURE_SCHEMA, dimension=3, order=8, seed=seed,
             seed_rule="native/net seed of a block: SHA-256('c8-d3-bench|<seed>|<block>|native'/'net'), first 8 bytes LE mod 2^63; uniform draws: ids sorted by SHA-256('c8-d3-bench|<seed>|<draw>|<id>')",
             inputs=inputs_rel, inputs_manifest_sha256=vin['manifest_sha256'], inventory_sha256=vin['inventory_sha256'],
             gamma_sha256=vin['gamma_sha256'],
             cost_model=dict(path=rel(cmp), sha256=digest(cmp), campaign=c, executable_sha256=cm.get('executable_sha256'),
                             cpu_model=cm.get('cpu_model'), lane_shape=cm.get('lane_shape'), mp_check=cm.get('mp_check'), job_ids=cm.get('job_ids'),
                             units='seconds of native task time per point on one thread (J-SWEEP-1, 16-thread NUMA lanes, --mp-check on)'),
             promotions=dict(path=rel(prp), sha256=digest(prp), source='graph_costs.csv + graph_promotions.csv of the L7/L8 groups (J-SWEEP-1, both campaigns, 2 x 512 points)'),
             native=dict(layout=FIX8['layout'], rate=FIX8['rate'], sum_mode=FIX8['sum_mode'], bits=FIX8['bits'], grid='-', order=8, mp_check=FIX8['mp_check']),
             blocks=recs, workloads=wls, sha256=hashes, scipy=scipy.__version__, numpy=numpy.__version__,
             provenance='C8(3) Stage 4a profiling fixtures (tools/prepare_benchmarks.py --order 8); never a physical result; their seeds are not campaign seeds.')
    (folder / 'manifest.json').write_text(json.dumps(m, indent=1, sort_keys=True) + '\n')
    return m


def check_fixtures8(folder: Path, **kw) -> dict:
    """Rebuild into a temporary folder and compare with the committed fixtures: the task files and every manifest field
    byte-identical; the net files too when the scipy version equals the manifest's (else reported, not compared)."""
    from benchkit import load_fixtures
    m = load_fixtures(folder)
    with tempfile.TemporaryDirectory(prefix='c8d3_fixtures8_') as td:
        new = build_fixtures8(Path(td) / 'f', **kw)
        same_scipy = new['scipy'] == m['scipy']
        diffs = []
        for name in sorted(set(m['sha256']) | set(new['sha256'])):
            if name.endswith('.net') and not same_scipy:
                continue
            if m['sha256'].get(name) != new['sha256'].get(name):
                diffs.append(name)
        strip = lambda d: {k: v for k, v in d.items() if not k.startswith('_') and k not in ('sha256', 'scipy', 'numpy')}
        def blocks_wo_net(d):
            return {n: {k: v for k, v in b.items() if k != 'net' or same_scipy} for n, b in d['blocks'].items()}
        a, b = strip(m), strip(new)
        if not same_scipy:
            a['blocks'], b['blocks'] = blocks_wo_net(m), blocks_wo_net(new)
        if a != b:
            diffs.append('manifest.json fields: ' + ', '.join(sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))))
        if same_scipy and (Path(folder) / 'manifest.json').read_bytes() != (Path(td) / 'f' / 'manifest.json').read_bytes():
            diffs.append('manifest.json bytes')
    return {'folder': str(folder), 'identical': not diffs, 'differences': diffs, 'scipy_committed': m['scipy'], 'scipy_here': new['scipy'],
            'nets_compared': same_scipy}


def stage_check(m: dict, dest: Path) -> dict:
    """Stage every fixture graph from the packs (each member verified against its inventory sha256)."""
    from benchkit import stage_graphs
    I = m['_inputs']
    inv = load(I.where('inventory.json'))
    out = {}
    for name, b in sorted(m['blocks'].items()):
        out[name] = stage_graphs(I, inv, b['sector'], b['L'], b['graphs'], Path(dest) / name)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--order', type=int, choices=(7, 8), default=7)
    p.add_argument('--folder', type=Path, help='order 8: the fixture folder (default benchmarks/fixtures8)')
    p.add_argument('--check', action='store_true', help='order 8: rebuild in a temporary folder and compare')
    p.add_argument('--stage-check', type=Path, metavar='DIR', help='order 8: stage every fixture graph from the packs into the new DIR')
    a = p.parse_args(argv)
    if a.order == 7:
        if a.folder or a.check or a.stage_check:
            p.error('--folder, --check and --stage-check are order-8 options')
        print(json.dumps(prepare_benchmarks(), indent=2))
        return 0
    from benchkit import FIXTURES8, BenchError, load_fixtures
    folder = a.folder or FIXTURES8
    try:
        if a.check:
            r = check_fixtures8(folder)
            print(json.dumps(r, indent=1))
            return 0 if r['identical'] else 1
        if not (folder / 'manifest.json').exists():
            if folder.exists() and any(folder.iterdir()):
                raise BenchError(65, f'{folder} exists without manifest.json (an interrupted build?): remove it and rerun')
            if folder.exists():
                folder.rmdir()
            m = build_fixtures8(folder)
            print(json.dumps({'built': str(folder), 'blocks': {n: {k: b[k] for k in ('tasks', 'points', 'total')} | {'wall': b['predicted'].get('wall_seconds')}
                                                               for n, b in m['blocks'].items()},
                              'workloads': m['workloads']}, indent=1))
        m = load_fixtures(folder)
        out = {'verified': str(folder), 'manifest_sha256': m['_manifest_sha256'], 'files': len(m['sha256'])}
        if a.stage_check:
            if a.stage_check.exists():
                raise BenchError(64, f'{a.stage_check} exists; give a new directory')
            out['staged'] = stage_check(m, a.stage_check)
            shutil.rmtree(a.stage_check)
        print(json.dumps(out, indent=1))
        return 0
    except BenchError as e:
        print(f'prepare_benchmarks: {e}', file=sys.stderr)
        return e.code


if __name__ == '__main__':
    sys.exit(main())
