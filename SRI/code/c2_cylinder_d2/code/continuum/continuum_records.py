"""Record pools and auxiliary inputs for the arbitrary-N continuum analysis (PLAN_ANALYSIS.md A3, M5).

Every record is keyed by (order, lambda, N, oversample, radius_cost, mixed cutoff,
tail cutoff, collapsed cutoff, science-source hash, site). Only verified records
are loaded:
  * archived records (data/hamiltonian/raw): sha256 checked against MANIFEST.sha256;
  * production and extraction-check records: sha256 checked against the merged
    index written by cluster/sitekit/merge_records.py, and the fixed-lambda
    sidecar against the task directory's SHA256SUMS;
  * auxiliary inputs (code/continuum/aux_inputs.py, Slurm job c2aux-*): every
    file checked against the job's SHA256SUMS.
Two pools are kept apart (rev 4, R3-001): PRIMARY (archived + production plan)
and DIAGNOSTIC (the M4d extraction-check plan). Nothing here fits anything.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
RAW = PKG / 'data' / 'hamiltonian' / 'raw'
AUXILIARY = PKG / 'data' / 'hamiltonian' / 'auxiliary'
REFERENCE = PKG / 'data' / 'hamiltonian' / 'reference'
RUN_PLAN = PKG / 'data' / 'hamiltonian' / 'run_plan.json'
PRODUCTION_SOURCES_SHA256 = 'eebafa82d84143734b4e3dde29fe81e89accf2d763cac3bed7ca7c6733d02398'
PRODUCTION_GRID_FAMILY = (4, 4.5)          # (oversample, radius_cost) of the production plan
# Approved plan identities per pool (R001, fix round 1). A merged index is accepted for a pool only if its plan
# name is listed there, and every record (and its task receipt) carries one of these plan sha256 values and names.
APPROVED_PLANS = {
    'primary': {
        'c8a9023db5df34916f71708b298e38255029574436e0a432aae3a9eea47059ba': dict(
            file='cluster/production_plan.json', index_plan='production_plan',
            name='C2 Hamiltonian production plan: PILOT, P1 (N=768), P2 (N=1024); fixed-regulator records only'),
        'b52f11e2513da32ce916c51779900287a4f6e6fff9d2b8bd7d913ecb0864d67c': dict(
            file='cluster/expanse/expanse_plan.json at cef281f (its PILOT row; renamed cluster/production_plan.json '
                 'in 417b75d)', index_plan='production_plan',
            name='Expanse production plan: PILOT, P1 (N=768), P2 (N=1024); fixed-regulator records only'),
    },
    'diagnostic': {
        'b2435b4e8dadd838498a5b652df4a188d258c9e49693f45295ac4be29d72b7a8': dict(
            file='cluster/analysis_checks_plan.json', index_plan='analysis_checks_plan',
            name='M4d extraction checks for the arbitrary-N continuum analysis: DIAGNOSTIC records only, '
                 'never estimates'),
        '77f9c5d6862571b0b2f843b5f381d3bc5a7d727533c1defea8f19056dcb1bd2b': dict(
            file='cluster/analysis_checks_plan_rev6.json', index_plan='analysis_checks_plan_rev6',
            name='M4d completion rows (PLAN_ANALYSIS rev 6/7, A6-1): DIAGNOSTIC records only, never estimates'),
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def sources_digest(source_hashes) -> str | None:
    """sha256 of a {file: sha256} map as JSON with sorted keys (= cluster/sitekit/jobtools.py sources_digest)."""
    if not isinstance(source_hashes, dict) or not source_hashes:
        return None
    return hashlib.sha256(json.dumps(source_hashes, sort_keys=True).encode()).hexdigest()


def read_sums(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text().splitlines():
        if line.strip():
            digest, _, name = line.partition('  ')
            out[name.strip()] = digest.strip()
    return out


@dataclass
class Record:
    order: int
    lam: float
    N: int
    oversample: int
    radius_cost: float
    mixed_cutoff: int
    tail_cutoff: int
    collapsed_cutoff: int
    sources: str
    site: str
    pool: str                      # 'primary' | 'diagnostic'
    origin: str                    # archived-fine | archived-extended | archived-large-lambda | production | m4d
    path: str
    sha256: str
    data: dict = field(repr=False)
    sidecar: dict | None = field(default=None, repr=False)
    legacy_a_face: dict | None = field(default=None, repr=False)   # archived A_face record actually used historically
    replicas: list = field(default_factory=list)                   # other sites of the same configuration
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> tuple:
        return (self.order, self.lam, self.N, self.oversample, self.radius_cost, self.mixed_cutoff,
                self.tail_cutoff, self.collapsed_cutoff, self.sources, self.site)

    @property
    def ident(self) -> str:
        r = format(self.radius_cost, 'g')
        return (f'k{self.order}_a{self.lam!r}_N{self.N}_o{self.oversample}_r{r}_m{self.mixed_cutoff}'
                f'_t{self.tail_cutoff}_c{self.collapsed_cutoff}_{self.sources[:12]}_{self.site}')

    def describe(self) -> dict:
        return dict(ident=self.ident, order=self.order, lam=self.lam, N=self.N, oversample=self.oversample,
                    radius_cost=self.radius_cost, mixed_cutoff=self.mixed_cutoff, tail_cutoff=self.tail_cutoff,
                    collapsed_cutoff=self.collapsed_cutoff, sources=self.sources, site=self.site,
                    pool=self.pool, origin=self.origin, path=self.path, sha256=self.sha256,
                    replicas=[dict(site=r['site'], path=r['path'], sha256=r['sha256'],
                                   max_abs_raw_chain_difference=r.get('max_abs_raw_chain_difference'),
                                   finite_cutoff_h_difference=r.get('finite_cutoff_h_difference'))
                              for r in self.replicas],
                    **self.extra)


def manifest() -> dict[str, str]:
    return {name: digest for name, digest in
            ((l.split('  ', 1)[1], l.split('  ', 1)[0]) for l in (PKG / 'MANIFEST.sha256').read_text().splitlines()
             if l and not l.startswith('#'))}


def load_archived(inputs: dict) -> list[Record]:
    """Archived records with their configuration from data/hamiltonian/run_plan.json."""
    man = manifest()
    plan = json.loads(RUN_PLAN.read_text())
    conf = {}
    for job in plan['jobs']:
        for lam in job['lambda']:
            conf[(job['cutoff'], job['order'], lam)] = job
    tails = json.loads((AUXILIARY / 'exact_leading_tail.json').read_text())
    out = []
    for prefix, origin in [('fine', 'archived-fine'), ('extended', 'archived-extended'),
                           ('large_lambda', 'archived-large-lambda')]:
        for path in sorted(RAW.glob(f'{prefix}_k*_a*.json')):
            rel = path.relative_to(PKG).as_posix()
            digest = sha256(path)
            if man.get(rel) != digest:
                raise ValueError(f'archived record {rel} does not match MANIFEST.sha256')
            inputs[rel] = digest
            obj = json.loads(path.read_text())
            d = obj.get('data', obj)
            k, lam, N = d['order'], d['lam'], d['N']
            job = conf[(N, k, lam)]
            if d['two_point']['N'] != job['collapsed_cutoff']:
                raise ValueError(f'{rel}: collapsed cutoff differs from run_plan.json')
            mixed_cutoff = d['mixed']['Nmax']
            if origin == 'archived-extended':
                tpath = AUXILIARY / f'leading_N384_k{k}_a{lam}.json'
                t = json.loads(tpath.read_text())
                inputs[tpath.relative_to(PKG).as_posix()] = sha256(tpath)
            elif origin == 'archived-fine':
                t = [z for z in tails if z['order'] == k and z['lam'] == lam and z['N'] == 2048][0]
            else:                                   # bundle_helpers.refresh_large: the largest tail cutoff
                t = max([z for z in tails if z['order'] == k and z['lam'] == lam], key=lambda z: z['N'])
            out.append(Record(order=k, lam=lam, N=N, oversample=job['oversample'], radius_cost=float(job['radius_cost']),
                              mixed_cutoff=mixed_cutoff, tail_cutoff=t['N'], collapsed_cutoff=d['two_point']['N'],
                              sources='archived', site='archived', pool='primary', origin=origin, path=rel,
                              sha256=digest, data=d, legacy_a_face=t,
                              extra=dict(cauchy_grid_comparison=d.get('cauchy_grid_comparison'))))
    tpath = AUXILIARY / 'exact_leading_tail.json'
    inputs[tpath.relative_to(PKG).as_posix()] = sha256(tpath)
    inputs[RUN_PLAN.relative_to(PKG).as_posix()] = sha256(RUN_PLAN)
    return out


def load_merged(index_path: Path, pool: str, origin: str, inputs: dict, expect_sources: str | None) -> list[Record]:
    """Records listed by a merged index (merge_records.py), verified by sha256; replicas of the
    same configuration on several sites become one record (Expanse first) with the others attached."""
    index_path = index_path.resolve()
    idx = json.loads(index_path.read_text())
    inputs[str(index_path.relative_to(PKG)) if index_path.is_relative_to(PKG) else str(index_path)] = sha256(index_path)
    if not idx.get('all_verified_and_compatible'):
        raise ValueError(f'{index_path}: merged index is not verified and compatible')
    approved = APPROVED_PLANS[pool]
    if idx.get('plan') not in {v['index_plan'] for v in approved.values()}:
        raise ValueError(f'{index_path}: plan {idx.get("plan")!r} is not an approved {pool} plan')
    recs = []
    for e in idx['records']:
        plan = approved.get(e.get('plan_sha256'))
        if plan is None or e.get('plan_name') != plan['name'] or plan['index_plan'] != idx['plan']:
            raise ValueError(f'{e["path"]}: plan {e.get("plan_name")!r} ({e.get("plan_sha256")}) is not an approved '
                             f'{pool} plan of index {idx["plan"]!r}')
        path = (PKG / e['path']) if not Path(e['path']).is_absolute() else Path(e['path'])
        digest = sha256(path)
        if digest != e['sha256']:
            raise ValueError(f'{path}: sha256 differs from the merged index')
        if expect_sources and e['sources_sha256'] != expect_sources:
            raise ValueError(f'{path}: science sources {e["sources_sha256"]} differ from {expect_sources}')
        sums = read_sums(path.parent / 'SHA256SUMS')
        if sums.get(path.name) != digest:
            raise ValueError(f'{path}: not listed in its SHA256SUMS')
        # IR2-001: the sidecar must be THIS record's sidecar (name derived from the record file name).
        if e['analysis_sidecar'] != path.stem + '_analysis.json' or Path(e['analysis_sidecar']).name != e['analysis_sidecar']:
            raise ValueError(f'{path}: index names sidecar {e["analysis_sidecar"]!r}, not {path.stem}_analysis.json')
        side = path.parent / e['analysis_sidecar']
        side_digest = sha256(side)
        if sums.get(side.name) != side_digest:
            raise ValueError(f'{side}: sidecar does not match SHA256SUMS')
        receipt = path.parent / 'task_receipt.json'
        receipt_digest = sha256(receipt)
        if sums.get(receipt.name) != receipt_digest:
            raise ValueError(f'{receipt}: task receipt does not match SHA256SUMS')
        tr = json.loads(receipt.read_text())
        c = e['config']
        job = tr.get('job', {})
        if (tr.get('plan_sha256') != e['plan_sha256'] or tr.get('plan_name') != plan['name']
                or job.get('cutoff') != c['cutoff'] or job.get('order') != e['order'] or e['lam'] not in job.get('lambda', [])
                or job.get('oversample') != c['oversample'] or float(job.get('radius_cost')) != float(c['radius_cost'])
                or job.get('mixed_cutoff') != c['mixed_cutoff'] or job.get('collapsed_cutoff') != c['collapsed_cutoff']
                or job.get('tail_cutoff') != c['tail_cutoff']):
            raise ValueError(f'{receipt}: task receipt (plan, configuration) disagrees with the merged index')
        # IR2-001: the science-source digest is recomputed from the verified receipt (as cluster/sitekit/jobtools.py
        # sources_digest computes it) and must agree with the index and with the expected source set.
        receipt_sources = sources_digest(tr.get('source_hashes'))
        if receipt_sources != e['sources_sha256'] or (expect_sources and receipt_sources != expect_sources):
            raise ValueError(f'{receipt}: science sources {receipt_sources} (from the receipt) disagree with the index '
                             f'({e["sources_sha256"]}) or the expected set ({expect_sources})')
        inputs[e['path']] = digest
        inputs[str(side.relative_to(PKG)) if side.is_relative_to(PKG) else str(side)] = side_digest
        inputs[str(receipt.relative_to(PKG)) if receipt.is_relative_to(PKG) else str(receipt)] = receipt_digest
        d = json.loads(path.read_text())
        if (d['order'], d['lam'], d['N']) != (e['order'], e['lam'], e['N']) or d['N'] != c['cutoff']:
            raise ValueError(f'{path}: record and index disagree')
        if d['two_point']['N'] != c['collapsed_cutoff'] or d['mixed']['Nmax'] != c['mixed_cutoff']:
            raise ValueError(f'{path}: embedded cutoffs differ from the index')
        sc = json.loads(side.read_text())
        lt = sc.get('leading_tail') or {}
        if ((sc.get('order'), sc.get('lam'), sc.get('N')) != (d['order'], d['lam'], d['N'])
                or (lt.get('order'), lt.get('lam')) != (d['order'], d['lam'])):
            raise ValueError(f'{side}: sidecar (order, lambda, N) or its leading-tail (order, lambda) do not match '
                             f'the record {path.name}')
        if lt.get('N') != c['tail_cutoff']:
            raise ValueError(f'{side}: tail cutoff differs from the index')
        recs.append(Record(order=d['order'], lam=d['lam'], N=d['N'], oversample=c['oversample'],
                           radius_cost=float(c['radius_cost']), mixed_cutoff=c['mixed_cutoff'],
                           tail_cutoff=c['tail_cutoff'], collapsed_cutoff=c['collapsed_cutoff'],
                           sources=e['sources_sha256'], site=e['site'], pool=pool, origin=origin,
                           path=e['path'], sha256=digest, data=d, sidecar=sc,
                           extra=dict(task_dir=e['task_dir'], plan_sha256=e['plan_sha256'], plan_file=plan['file'],
                                      host=e.get('host'), cpu_model=e.get('cpu_model'), sidecar=e['analysis_sidecar'])))
    # Replicas: identical configuration and sources on several sites -> one record (Expanse first).
    merged: dict[tuple, Record] = {}
    for r in sorted(recs, key=lambda r: (r.site != 'expanse', r.site)):
        k = r.key[:-1]
        if k in merged:
            rep = merged[k]
            import numpy as np
            diff = float(np.max(np.abs(np.asarray(rep.data['raw']['Xchain']) - np.asarray(r.data['raw']['Xchain']))))
            rep.replicas.append(dict(site=r.site, path=r.path, sha256=r.sha256, max_abs_raw_chain_difference=diff,
                                     finite_cutoff_h_difference=float(rep.sidecar['last'] - r.sidecar['last'])))
        else:
            merged[k] = r
    return list(merged.values())


def check_pools(records: list) -> None:
    """R001: no record may sit in both pools (same file, same content, or same configuration and site)."""
    seen: dict[str, dict] = {'path': {}, 'sha256': {}, 'key': {}}
    for r in records:
        for kind, value in (('path', r.path), ('sha256', r.sha256), ('key', r.key)):
            other = seen[kind].get(value)
            if other is not None and other.pool != r.pool:
                raise ValueError(f'record {r.ident} is in both pools ({other.pool} {other.path} / {r.pool} {r.path})')
            seen[kind].setdefault(value, r)


def grid_identity(r) -> tuple:
    return (r.N, r.oversample, float(r.radius_cost))


def check_comparison(primary, check) -> None:
    """R001: an extraction comparison counts only between two different Cauchy grids, i.e. a different
    (N, oversample, radius_cost); the same record or the same grid is refused."""
    if check.sha256 == primary.sha256 or check.path == primary.path:
        raise ValueError(f'{check.ident}: an extraction comparison of a record with itself')
    if grid_identity(check) == grid_identity(primary):
        raise ValueError(f'{check.ident} and {primary.ident} use the same extraction grid '
                         f'{grid_identity(primary)}; not an extraction comparison')


@dataclass
class Aux:
    """Aligned auxiliary inputs for one (order, lambda) (M1, M2, M2b)."""
    order: int
    lam: float
    source: str                    # 'production record' or 'c2aux job'
    mixed_cutoff: int
    mixed_fits: list
    mixed_prefix_fits: list
    tp800: dict
    tp400: dict
    a8192_800: float
    a8192_400: float
    a2048_800: float
    checks: dict = field(default_factory=dict)


def load_aux_dir(aux_dir: Path, inputs: dict) -> dict[tuple, dict]:
    aux_dir = aux_dir.resolve()
    sums = read_sums(aux_dir / 'SHA256SUMS')
    out = {}
    for name, digest in sums.items():
        p = aux_dir / name
        if sha256(p) != digest:
            raise ValueError(f'{p}: does not match SHA256SUMS')
        rel = str(p.relative_to(PKG)) if p.is_relative_to(PKG) else str(p)
        inputs[rel] = digest
        if name.startswith('aux_k') and name.endswith('.json'):
            d = json.loads(p.read_text())
            out[(d['order'], d['lam'])] = d
    rec = json.loads((aux_dir / 'aux_receipt.json').read_text())
    if rec['science_sources_sha256'] != PRODUCTION_SOURCES_SHA256:
        raise ValueError(f'{aux_dir}: auxiliary job used science sources {rec["science_sources_sha256"]}')
    return out


def aligned_aux(order: int, lam: float, primary: Record, aux: dict[tuple, dict], mixed_extrapolate) -> Aux:
    """Aligned (collapsed 800000, tail 8192, mixed 16384) inputs for one (order, lambda).
    Taken from the primary production record where it has them (its own two_point, mixed sums
    and sidecar tail coefficient), otherwise from the c2aux job; the 400000 and tail-2048
    variants always come from the c2aux job."""
    a = aux.get((order, lam))
    if a is None:
        raise ValueError(f'no auxiliary inputs for order {order}, lambda {lam}')
    faces = a['a_face']
    checks = {}
    if primary.origin in ('production', 'm4d'):
        d, sc = primary.data, primary.sidecar
        mixed_fits = d['mixed']['fits']
        prefix = mixed_extrapolate(d['mixed']['Xmixed'][:d['mixed']['Nmax'] // 2])
        tp800 = d['two_point']
        a800 = sc['leading_tail']['asymptotic_tail_coefficient']
        src = 'production record (two_point 800000, mixed 16384, sidecar A_face 8192); c2aux job for the 400000 and tail-2048 variants'
        checks = dict(aux_two_point_800000_Xdisc_minus_record=a['two_point']['800000']['Xdisc'] - tp800['Xdisc'],
                      aux_A8192_minus_sidecar=faces['tail8192_collapsed800000']['asymptotic_tail_coefficient'] - a800,
                      sidecar_mixed_limit_rule_Nmin_ge_2048=sc['mixed_limit'])
        nmix = d['mixed']['Nmax']
    else:
        m = a['mixed']
        mixed_fits, prefix, nmix = m['fits'], m['prefix_fits'], m['Nmax']
        tp800 = a['two_point']['800000']
        a800 = faces['tail8192_collapsed800000']['asymptotic_tail_coefficient']
        src = 'c2aux job (mixed 16384, two_point 400000/800000, A_face 8192/2048)'
    if 'mixed' in a and primary.origin in ('production', 'm4d'):
        # the c2aux job also recomputed mixed 16384 for (r, lambda) that are archived AND new
        checks['aux_mixed_last_minus_record'] = a['mixed']['Xmixed'][-1] - primary.data['mixed']['Xmixed'][-1]
    return Aux(order=order, lam=lam, source=src, mixed_cutoff=nmix, mixed_fits=mixed_fits, mixed_prefix_fits=prefix,
               tp800=tp800, tp400=a['two_point']['400000'], a8192_800=a800,
               a8192_400=faces['tail8192_collapsed400000']['asymptotic_tail_coefficient'],
               a2048_800=faces['tail2048_collapsed800000']['asymptotic_tail_coefficient'], checks=checks)
