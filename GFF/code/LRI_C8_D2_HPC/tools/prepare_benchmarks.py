#!/usr/bin/env python3
"""Create portable, deterministic profiling/benchmark input fixtures.

--order 7 (the default; C7(2)'s behaviour, unchanged): the earlier timing summaries survive, but their original net/task
files were not separately delivered. These NEW fixtures choose 16 highest-cost graphs per sector/loop, with a documented
seed. They allow matched old/new comparisons; they are not a reconstruction of the historical timing streams.

--order 8 (C8(2) Stage 4a, PLAN "Performance plan", P1-P4): frozen workloads in benchmarks/fixtures8/, chosen from the
J-SWEEP-1 cost model (seconds per point per graph, campaign a, measured on the Stage-3 baseline; FIX8['cost_model']):
  heavy_{free,power}_L7     P1 (and P3 context): 1,024 tasks as in C7(2)'s production blocks: the 128 graphs with the
                            largest cost per point, 2 replicates x 4 chunks; ~60 s at 64 threads
  heavy_{free,power}_L8     P1: 256 tasks on the 128 heaviest graphs, 2 replicates x 1 task; ~120 s at 64 threads
  nopromo_free_L7/L8        P2: promotion-free graphs (quad and MP fractions 0 in BOTH campaigns of the cost model; at
                            L8 every one of the 248 primitives is among them), heaviest first: 64 graphs x 2 x 8 chunks
                            (1,024 tasks) at L7, 128 x 2 (256 tasks) at L8; ~30-40 s at 64 threads. The power sector
                            has no promotion-free graph (its smallest quad fraction is 0.17 at L7 and 0.27 at L8)
  random_{free,power}_L7/L8 P3: 256 graphs drawn uniformly (the sha256 order below), 2 replicates x 1 task, ~40 s at
                            128 threads: margin histograms representative of the sector's graphs
  p4_{free,power}_L8        P4: the fixed L8 lane-shape workload, graphs drawn uniformly per sector in proportion to
                            the sector sizes (16,064 : 4,336), 2 replicates x 16,384 points each, sized to ~330 s of
                            ideal node time at 128 cores (one shape ~5.5-6.5 min on an Expanse node); a prefix of each
                            sector's draw is again a uniform draw, so --fraction 0.5 halves it (symmetry's 64 cores)
Points per task are the power of two that puts the cost model's predicted wall closest (in log2) to the target.
Every block uses campaign a's native settings (rate .8, layout 0, compensated sums, 52-bit nets) and its own native
and net seeds: SHA-256 of 'c8-d2-bench|<seed>|<block>|native' or '|net' (benchkit.bench_seed) with the documented
master seed FIX8['seed']; uniform draws sort graph ids by SHA-256 of 'c8-d2-bench|<seed>|<block>|<id>'
(benchkit.rank_key). No result of these fixtures is physical; their seeds are not campaign seeds.
The task and net files and manifest.json are committed (< 1 MB); graph members are staged at run time from the pinned
packs (the L8 packs are not in git) and verified against their inventory sha256. The task files and the selections are
pure functions of the cost model, the inventory and the seed; the Sobol nets come from scipy (production.make_net) and
are pinned by sha256 (their bytes can differ between scipy versions, which --check reports).
  prepare_benchmarks.py --order 8            build benchmarks/fixtures8 if absent, else verify it (sha256 and pins)
  prepare_benchmarks.py --order 8 --check    rebuild into a temporary folder and compare with the committed fixtures
  prepare_benchmarks.py --order 8 --stage-check DIR   also stage every fixture graph from the packs into DIR (cluster)
"""
from __future__ import annotations
import argparse,json,math,shutil,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT, load, dump, checked, digest
from production import make_net


def prepare_benchmarks() -> dict:
    # C7(2)'s order-7 builder, unchanged except that this import moved here from the module top: C8(2)'s
    # prepare_inputs has no prepare() (it has verify()), so the import failed at module load and broke every order-8 use.
    # Order 7 therefore still raises this ImportError in the C8(2) package, as before; benchmarks/fixtures/ is C7(2)'s.
    from prepare_inputs import prepare
    prepare()
    folder = ROOT / 'benchmarks' / 'fixtures'
    manifest = folder / 'manifest.json'
    if manifest.exists():
        result = load(manifest)
        checked(ROOT / 'inputs/inventory.json', result['inventory_sha256'])
        for name, sha in result['sha256'].items():
            checked(folder / name, sha)
        return result
    folder.mkdir(parents=True, exist_ok=True)
    inv = load(ROOT / 'inputs/inventory.json')
    records, hashes = {}, {}
    for si, sector in enumerate(('free', 'power')):
        for L in (6, 7):
            name = f'{sector}_L{L}'
            rows = sorted(inv[sector][str(L)], key=lambda r: (-r['cost'], r['id']))[:16]
            ids = sorted(r['id'] for r in rows)
            net = folder / (name + '.net')
            task = folder / (name + '.tasks')
            if net.exists() or task.exists():
                raise FileExistsError('Incomplete fixture creation; remove only benchmarks/fixtures and retry')
            metadata = make_net(net, 2, 4*L-1, 60, 2026093017 + 100*si + L)
            n = 512
            tasks = [(i, rep, g, 0, n, n) for i, (rep, g) in
                     enumerate((rep, g) for rep in range(2) for g in ids)]
            task.write_text(f'C7D2TASKS1 {L} {len(tasks)}\n' +
                            ''.join(' '.join(map(str, r))+'\n' for r in tasks))
            hashes[net.name], hashes[task.name] = digest(net), digest(task)
            records[name] = dict(sector=sector, L=L, ids=ids, profiling_points_per_graph_per_replicate=n, net=metadata)
    result = dict(schema='c7-d2-hpc-benchmark-fixtures-1', dimension=2, order=7,
                  inventory_sha256=digest(ROOT/'inputs/inventory.json'),
                  records=records, sha256=hashes,
                  provenance='New deterministic fixtures generated during final packaging; historical timing reports are not reasserted for these streams.')
    dump(manifest, result)
    return result

# ---------------------------------------------------------------- order 8 (C8(2) Stage 4a)
FIX8 = dict(seed=2026100408, inputs='inputs', campaign='a', rate='.8', layout=0, sum_mode='compensated', bits=52,
            cost_model='benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json')
BLOCKS8 = (
    dict(name='heavy_free_L7', purpose='P1', sector='free', L=7, select='heaviest', graphs=128, replicates=2, chunks=4, target_seconds=60, target_threads=64),
    dict(name='heavy_power_L7', purpose='P1', sector='power', L=7, select='heaviest', graphs=128, replicates=2, chunks=4, target_seconds=60, target_threads=64),
    dict(name='heavy_free_L8', purpose='P1', sector='free', L=8, select='heaviest', graphs=128, replicates=2, chunks=1, target_seconds=120, target_threads=64),
    dict(name='heavy_power_L8', purpose='P1', sector='power', L=8, select='heaviest', graphs=128, replicates=2, chunks=1, target_seconds=120, target_threads=64),
    dict(name='nopromo_free_L7', purpose='P2', sector='free', L=7, select='nopromo', graphs=64, replicates=2, chunks=8, target_seconds=30, target_threads=64),
    dict(name='nopromo_free_L8', purpose='P2', sector='free', L=8, select='nopromo', graphs=128, replicates=2, chunks=1, target_seconds=40, target_threads=64),
    dict(name='random_free_L7', purpose='P3', sector='free', L=7, select='random', graphs=256, replicates=2, chunks=1, target_seconds=40, target_threads=128),
    dict(name='random_power_L7', purpose='P3', sector='power', L=7, select='random', graphs=256, replicates=2, chunks=1, target_seconds=40, target_threads=128),
    dict(name='random_free_L8', purpose='P3', sector='free', L=8, select='random', graphs=256, replicates=2, chunks=1, target_seconds=40, target_threads=128),
    dict(name='random_power_L8', purpose='P3', sector='power', L=8, select='random', graphs=256, replicates=2, chunks=1, target_seconds=40, target_threads=128),
)
WORKLOADS8 = (dict(name='p4_L8', purpose='P4', L=8, sectors=('free', 'power'), replicates=2, points=16384, target_seconds=330, target_threads=128),)
SELECTION = {
    'heaviest': 'the graphs with the largest cost-model seconds per point (campaign a), ties by id',
    'nopromo': 'promotion-free graphs (cost-model quad and MP fractions 0 in campaigns a and b), heaviest first',
    'random': 'a uniform draw: graph ids sorted by benchkit.rank_key(seed, block, id), the first N',
    'proportional': 'a uniform draw per sector (benchkit.rank_key order), sector counts in proportion to the sector sizes, grown until the predicted ideal wall reaches the target',
}


def _spp(cm: dict, campaign: str, sector: str, L: int, gid: int) -> float:
    k = f'{campaign}:{sector}:{L}:{gid}'
    if k not in cm['seconds_per_point']:
        raise KeyError(f'the cost model has no key {k}')
    return float(cm['seconds_per_point'][k])


def _pow2_points(cost_per_point_sum: float, target_seconds: float, threads: int) -> int:
    """The power of two P that puts P x cost_per_point_sum / threads closest to target_seconds in log2."""
    x = target_seconds * threads / cost_per_point_sum
    return 1 << max(6, min(22, round(math.log2(x))))


def _select(spec: dict, cm: dict, inv: dict, seed: int) -> list[int]:
    from benchkit import rank_key
    s, L, c = spec['sector'], spec['L'], FIX8['campaign']
    ids = sorted(r['id'] for r in inv[s][str(L)])
    if spec['select'] == 'heaviest':
        pool = sorted(ids, key=lambda g: (-_spp(cm, c, s, L, g), g))
    elif spec['select'] == 'nopromo':
        free = [g for g in ids if all(float(cm[f][f'{x}:{s}:{L}:{g}']) == 0 for x in ('a', 'b') for f in ('quad_fraction', 'mp_fraction'))]
        pool = sorted(free, key=lambda g: (-_spp(cm, c, s, L, g), g))
    elif spec['select'] == 'random':
        pool = sorted(ids, key=lambda g: rank_key(seed, spec['name'], g))
    else:
        raise ValueError(f'unknown selection {spec["select"]}')
    if not pool:
        raise ValueError(f'{spec["name"]}: no graph meets the selection {spec["select"]}')
    return pool[:spec['graphs']]


def _write_block(folder: Path, name: str, sector: str, L: int, ids: list, reps: int, chunks: int, chunk_points: int, seed: int,
                 cm: dict, inv: dict, purpose: str, selection: str, target: dict | None) -> tuple[dict, dict]:
    from benchkit import bench_seed, write_tasks
    total = chunk_points * chunks
    rows = [(u, rep, g, c * chunk_points, (c + 1) * chunk_points, total)
            for u, (rep, g, c) in enumerate((rep, g, c) for rep in range(reps) for g in sorted(ids) for c in range(chunks))]
    tasks, net = folder / f'{name}.tasks', folder / f'{name}.net'
    write_tasks(tasks, 8, L, rows)
    meta = make_net(net, reps, 4 * L - 1, FIX8['bits'], bench_seed(seed, name, 'net'), total)
    spp = {str(g): _spp(cm, FIX8['campaign'], sector, L, g) for g in sorted(ids)}
    cms = math.fsum(spp[str(r[2])] * (r[4] - r[3]) for r in rows)
    w = lambda f: math.fsum(float(cm[f][f'{FIX8["campaign"]}:{sector}:{L}:{g}']) * spp[str(g)] for g in ids) / math.fsum(spp.values())
    prim = {r['id'] for r in inv[sector][str(L)] if r.get('primitive')}
    rec = dict(name=name, purpose=purpose, sector=sector, L=L, selection=selection, graphs=sorted(ids), primitive_graphs=len(prim & set(ids)),
               replicates=reps, chunks=chunks, chunk_points=chunk_points, total=total, tasks=len(rows), points=sum(r[4] - r[3] for r in rows),
               native_seed=bench_seed(seed, name, 'native'), net=meta, files={'tasks': tasks.name, 'net': net.name},
               seconds_per_point={k: v for k, v in spp.items()},
               predicted=dict(cost_model_seconds=cms, cost_weighted_quad_fraction=w('quad_fraction'), cost_weighted_mp_fraction=w('mp_fraction'),
                              **({'threads': target['threads'], 'wall_seconds': cms / target['threads'], 'target_seconds': target['seconds']} if target else {})))
    return rec, {tasks.name: digest(tasks), net.name: digest(net)}


def build_fixtures8(folder: Path, inputs_rel: str = FIX8['inputs'], cost_model: Path | None = None, seed: int = FIX8['seed'],
                    blocks=BLOCKS8, workloads=WORKLOADS8) -> dict:
    """Write the order-8 fixtures into the new folder (refused when it exists) and return the manifest."""
    import scipy, numpy
    from benchkit import FIXTURE_SCHEMA, inputs_of, rank_key
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    I = inputs_of(inputs_rel)
    cmp = Path(cost_model) if cost_model else ROOT / FIX8['cost_model']
    cm = load(cmp)
    inv = load(I.where('inventory.json'))
    recs, hashes = {}, {}
    for spec in blocks:
        ids = _select(spec, cm, inv, seed)
        unit = math.fsum(_spp(cm, FIX8['campaign'], spec['sector'], spec['L'], g) for g in ids) * spec['replicates'] * spec['chunks']
        cp = _pow2_points(unit, spec['target_seconds'], spec['target_threads'])
        rule = SELECTION[spec['select']] + f' (N = {spec["graphs"]})'
        rec, h = _write_block(folder, spec['name'], spec['sector'], spec['L'], ids, spec['replicates'], spec['chunks'], cp, seed, cm, inv,
                              spec['purpose'], rule, {'threads': spec['target_threads'], 'seconds': spec['target_seconds']})
        recs[spec['name']] = rec
        hashes.update(h)
    wls = {}
    for wl in workloads:
        L, P, R = wl['L'], wl['points'], wl['replicates']
        order = {s: sorted((r['id'] for r in inv[s][str(L)]), key=lambda g: rank_key(seed, f'{wl["name"]}_{s}', g)) for s in wl['sectors']}
        sizes = {s: len(order[s]) for s in wl['sectors']}
        lead = wl['sectors'][0]
        cost = {s: [_spp(cm, FIX8['campaign'], s, L, g) * P * R for g in order[s]] for s in wl['sectors']}
        need = wl['target_seconds'] * wl['target_threads']
        k = {s: 0 for s in wl['sectors']}
        for kl in range(1, sizes[lead] + 1):
            k = {s: (kl if s == lead else min(sizes[s], max(1, round(kl * sizes[s] / sizes[lead])))) for s in wl['sectors']}
            if math.fsum(math.fsum(cost[s][:k[s]]) for s in wl['sectors']) >= need:
                break
        names = []
        for s in wl['sectors']:
            name = f'{wl["name"].split("_")[0]}_{s}_L{L}'
            rule = SELECTION['proportional'] + f' ({k[s]} of {sizes[s]} {s} L{L} graphs, in draw order {wl["name"]}_{s})'
            rec, h = _write_block(folder, name, s, L, order[s][:k[s]], R, 1, P, seed, cm, inv, wl['purpose'], rule, None)
            rec['draw_order'] = order[s][:k[s]]
            recs[name] = rec
            hashes.update(h)
            names.append(name)
        cms = math.fsum(recs[n]['predicted']['cost_model_seconds'] for n in names)
        wls[wl['name']] = dict(purpose=wl['purpose'], blocks=names, L=L, replicates=R, points_per_task=P, target_seconds=wl['target_seconds'],
                               target_threads=wl['target_threads'], cost_model_seconds=cms, predicted_ideal_wall_seconds=cms / wl['target_threads'],
                               fraction_rule='--fraction F keeps the first ceil(F x k) graphs of each sector in draw order (both replicates)')
    try:
        cm_rel = cmp.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        cm_rel = str(cmp)
    m = dict(schema=FIXTURE_SCHEMA, dimension=2, order=8, seed=seed,
             seed_rule="native/net seed of a block: SHA-256('c8-d2-bench|<seed>|<block>|native'/'net'), first 8 bytes LE mod 2^63; uniform draws: ids sorted by SHA-256('c8-d2-bench|<seed>|<draw>|<id>')",
             inputs=inputs_rel, inputs_manifest_sha256=digest(I.dir / 'manifest.json'), inventory_sha256=digest(I.where('inventory.json')),
             gamma_sha256=digest(I.where('gamma_d2_8.txt')),
             cost_model=dict(path=cm_rel, sha256=digest(cmp), campaign=FIX8['campaign'], executable_sha256=cm.get('executable_sha256'),
                             cpu_models=cm.get('cpu_models'), lane_width=cm.get('lane_width'), job_ids=cm.get('job_ids'),
                             units='seconds of native task time per point on one thread (J-SWEEP-1, 16-thread NUMA lanes)'),
             native=dict(layout=FIX8['layout'], rate=FIX8['rate'], sum_mode=FIX8['sum_mode'], bits=FIX8['bits'], grid='-', order=8),
             blocks=recs, workloads=wls, sha256=hashes, scipy=scipy.__version__, numpy=numpy.__version__,
             provenance='C8(2) Stage 4a profiling fixtures (tools/prepare_benchmarks.py --order 8); never a physical result; their seeds are not campaign seeds.')
    (folder / 'manifest.json').write_text(json.dumps(m, indent=1, sort_keys=True) + '\n')
    return m


def check_fixtures8(folder: Path, **kw) -> dict:
    """Rebuild into a temporary folder and compare with the committed fixtures: the task files and every manifest field
    byte-identical; the net files too when the scipy version equals the manifest's (else reported, not compared)."""
    from benchkit import load_fixtures
    m = load_fixtures(folder)
    with tempfile.TemporaryDirectory(prefix='c8d2_fixtures8_') as td:
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
            print(json.dumps({'built': str(folder), 'blocks': {n: {k: b[k] for k in ('tasks', 'points', 'chunk_points')} for n, b in m['blocks'].items()},
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
