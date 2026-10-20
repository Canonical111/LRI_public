#!/usr/bin/env python3
r"""Driver of the arbitrary-N continuum analysis (PLAN_ANALYSIS.md rev 7; built at rev 4).

  python code/continuum/continuum_driver.py run \
      --records outputs/merged_production_plan_20261013.json \
      --diagnostic-records outputs/merged_analysis_checks_plan_20261013.json \
                           outputs/merged_analysis_checks_plan_rev6_20261014.json \
      --aux-dir outputs/symmetry/c2aux_574247 \
      --legacy-receipt results/continuum_2026-10/evidence/legacy_macos/legacy_reproduction.json \
      --output results/continuum_2026-10
  python code/continuum/continuum_driver.py check --output results/continuum_2026-10
  python code/continuum/continuum_driver.py sync --output results/continuum_2026-10
  python code/continuum/continuum_driver.py legacy --output <dir>

(also reachable as `python scripts/run.py continuum -- <arguments>`).

`run` publishes one immutable generation, <output>/generations/<name>/ with continuum_points.json,
regulator_fits.json, C2_estimate.json and REPORT.md, and switches <output>/CURRENT to it by one atomic rename
under an exclusive writer lock; the top-level files of <output> are copies of the CURRENT generation (`check`
verifies them, `sync` restores them). All selection rules are the constants of continuum_analysis.RULES, fixed
before anything is computed and written into every output. `legacy` runs the unmodified historical scripts under
the recorded-legacy policy (A1); see continuum_legacy.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import continuum_analysis as ca                       # noqa: E402
import continuum_records as cr                        # noqa: E402

PKG = ca.PKG


def rel(p: Path) -> str:
    p = Path(p).resolve()
    return str(p.relative_to(PKG)) if p.is_relative_to(PKG) else str(p)


def select_primary(records: list) -> tuple[dict, list]:
    """M5: largest-N PRIMARY record per (order, lambda); deterministic tie-break."""
    groups: dict[tuple, list] = {}
    for r in records:
        if r.pool == 'primary':
            groups.setdefault((r.order, r.lam), []).append(r)
    chosen, log = {}, []

    def rank(r):
        fam = (r.oversample, r.radius_cost) == cr.PRODUCTION_GRID_FAMILY
        return (r.N, fam, r.mixed_cutoff, r.tail_cutoff, r.collapsed_cutoff)
    for key, rs in sorted(groups.items()):
        rs = sorted(rs, key=rank, reverse=True)
        if len(rs) > 1 and rank(rs[0]) == rank(rs[1]):
            raise ValueError(f'M5 tie that the rule does not resolve at {key}')
        chosen[key] = rs[0]
        for r in rs[1:]:
            log.append(dict(order=key[0], lam=key[1], replaced=r.ident, replaced_N=r.N, by=rs[0].ident, by_N=rs[0].N,
                            reason='superseded by a larger-N primary record; kept as an M4b cross-N check'))
    return chosen, log


def extraction_status(ident: str, measured: dict, rev4: dict, rev4_source: str) -> dict:
    """epsilon_grid of one primary point (rev 6/7). A5-1 value from its full-coverage comparisons; without any
    (a failed completion row) the FROZEN rev-4 per-point value and provenance (R6-002), flagged. No L1 is ever
    computed from an absent or partial profile; there is no transport, inheritance or continuation."""
    m = measured.get(ident)
    if m and m['comparisons']:
        return dict(eps_grid=m['eps_grid'], status='measured', n_full_coverage=m['n_full_coverage'],
                    from_check=m['from_check'], smooth=m['smooth'], rough=m['rough'], rev4_l1=m['rev4_l1'],
                    signed_shift=m['signed_shift'], max_abs_rho=m['max_abs_rho'], flags=[])
    old = rev4.get(ident)
    if old is None:
        raise ValueError(f'{ident}: no full-coverage comparison and no frozen rev-4 epsilon_grid')
    ox = old['extraction']
    frozen = dict(eps_grid=old['eps']['eps_grid'], status=ox.get('status'), kind=ox.get('kind'),
                  donor=ox.get('donor'), donor_eps_grid=ox.get('donor_eps_grid'),
                  sum_abs_v_ratio=ox.get('sum_abs_v_ratio'), flags=ox.get('flags'), source=rev4_source)
    return dict(eps_grid=old['eps']['eps_grid'], status='rev-4 exception', frozen_rev4=frozen, n_full_coverage=0,
                smooth=None, rough=None, rev4_l1=old['eps']['eps_grid'], signed_shift=None, max_abs_rho=None,
                flags=['extraction comparison missing: rev-4 exception'])


def lambda_n_ok(order: int, lam: float, N: int) -> bool:
    return lam * N >= ca.LAMBDA_N_MINIMUM[order] - 1e-9


def run(a: argparse.Namespace) -> None:
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    inputs: dict[str, str] = {}
    records = cr.load_archived(inputs)
    records += cr.load_merged(a.records, 'primary', 'production', inputs, cr.PRODUCTION_SOURCES_SHA256)
    for idx in a.diagnostic_records:
        records += cr.load_merged(idx, 'diagnostic', 'm4d', inputs, cr.PRODUCTION_SOURCES_SHA256)
    cr.check_pools(records)                      # R001: no record in both pools
    aux_raw = cr.load_aux_dir(a.aux_dir, inputs)
    primary, replaced = select_primary(records)

    # ---- aligned auxiliary inputs, one set per (order, lambda) (M1, M2, M2b)
    aux = {key: cr.aligned_aux(key[0], key[1], rec, aux_raw, ca.mixed_extrapolate) for key, rec in primary.items()}

    # ---- every record of a primary (order, lambda): M3 with the aligned inputs
    analyses: dict[str, ca.PointAnalysis] = {}
    groups: dict[tuple, list] = {}
    for r in records:
        key = (r.order, r.lam)
        if key not in primary:
            raise ValueError(f'record {r.ident} has no primary point')
        groups.setdefault(key, []).append(r)
        analyses[r.ident] = ca.PointAnalysis(r, aux[key], full=(r is primary[key]))

    # ---- M4d extraction (rev 6/7): SIGNED full-coverage profiles, A5-1 split; no transport or inheritance
    measured: dict[str, dict] = {}

    def sample(delta: np.ndarray, N: int) -> dict:
        return {str(n): float(delta[n - 1]) for n in sorted({1, N // 4, N // 2, 5 * N // 8, 3 * N // 4, 7 * N // 8, N})}

    def add_full(rec, check, kind: str, delta: np.ndarray, other_chain, extra: dict | None = None) -> None:
        cr.check_comparison(rec, check)          # R001: two different Cauchy grids, never a record with itself
        an = analyses[rec.ident]
        g = an.grid_split(delta)
        c = dict(check_record=check.ident, kind=kind,
                 check_grid=dict(N=check.N, oversample=check.oversample, radius_cost=check.radius_cost),
                 coverage=f'n <= {rec.N} (complete)', max_delta=float(np.max(np.abs(delta))),
                 last_delta=float(delta[-1]), eps_grid=g['eps_grid'], smooth=g['smooth'], rough=g['rough'],
                 rev4_l1=g['rev4_l1'], signed_shift=g['signed_shift'], max_abs_rho=g['max_abs_rho'],
                 per_fit=g['per_fit'], illustrative_not_in_budget=an.illustrative_grid(delta, other_chain),
                 delta_profile_sample=sample(delta, rec.N))
        c.update(extra or {})
        measured.setdefault(rec.ident, dict(comparisons=[], partial=[]))['comparisons'].append(c)

    for key, rs in groups.items():
        p = primary[key]
        xp = np.asarray(p.data['raw']['Xchain'])
        for d in [r for r in rs if r.pool == 'diagnostic']:
            if d.N < p.N:
                raise ValueError(f'diagnostic record {d.ident} does not cover the primary record {p.ident}')
            xd = np.asarray(d.data['raw']['Xchain'])
            add_full(p, d, 'M4d extraction-check record', xp - xd[:p.N], xd)
    # archived overlaps: fine N=256 (o5, r4.0) vs extended N=384 (o4, r4.5) at the same (order, lambda).
    # Full coverage for the N=256 record (reported; those records are not primary); partial for N=384: reported only.
    for key, rs in groups.items():
        fine = [r for r in rs if r.origin == 'archived-fine']
        ext = [r for r in rs if r.origin == 'archived-extended']
        if not (fine and ext):
            continue
        f, e = fine[0], ext[0]
        xf = np.asarray(f.data['raw']['Xchain'])
        xe = np.asarray(e.data['raw']['Xchain'])
        recorded = (e.extra.get('cauchy_grid_comparison') or {}).get('maximum_overlap_difference')
        add_full(f, e, 'archived overlap (N=256 grid vs N=384 grid)', xf - xe[:f.N], xe,
                 dict(recorded_maximum_overlap_difference=recorded))
        measured.setdefault(e.ident, dict(comparisons=[], partial=[]))['partial'].append(dict(
            check_record=f.ident, kind='archived overlap (N=384 grid vs N=256 grid)',
            coverage=f'n <= {f.N} of {e.N}: PARTIAL, reported only, never used for epsilon_grid',
            max_delta=float(np.max(np.abs(xe[:f.N] - xf))), recorded_maximum_overlap_difference=recorded))
    for m in measured.values():
        cs = m['comparisons']
        if cs:
            best = max(cs, key=lambda c: c['eps_grid'])
            m.update(eps_grid=best['eps_grid'], smooth=best['smooth'], rough=best['rough'],
                     from_check=best['check_record'], rev4_l1=max(c['rev4_l1'] for c in cs),
                     signed_shift=max(c['signed_shift'] for c in cs), max_abs_rho=max(c['max_abs_rho'] for c in cs),
                     n_full_coverage=len(cs))

    rev4_path = Path(a.rev4_points).resolve()
    inputs[rel(rev4_path)] = cr.sha256(rev4_path)
    rev4 = {q['id']: q for q in json.loads(rev4_path.read_text())['primary_points']}
    rev4_est_path = rev4_path.parent / 'C2_estimate.json'
    inputs[rel(rev4_est_path)] = cr.sha256(rev4_est_path)
    rev4_est = json.loads(rev4_est_path.read_text())

    def eps_grid_for(rec) -> dict:
        return extraction_status(rec.ident, measured, rev4, rel(rev4_path))

    # ---- per primary point: M1-M4
    points_out, points = [], {}
    for key in sorted(primary):
        p = primary[key]
        an = analyses[p.ident]
        if an.main['h'] is None:
            raise ValueError(f'{p.ident}: no accepted selected spectral fit')
        prefix = an.prefix_test()
        mix = an.eps_mix()
        coll = an.eps_coll()
        tail = an.eps_tailcut()
        rnd = an.roundoff()
        grid = eps_grid_for(p)
        cross_rows, cross_eps = [], None
        for r in sorted(groups[key], key=lambda r: (-r.N, r.pool, r.site)):
            if r is p:
                continue
            h = analyses[r.ident].main['h']
            ok = lambda_n_ok(r.order, r.lam, r.N)
            diff = None if h is None else abs(an.main['h'] - h)
            differing = [k for k in ('N', 'oversample', 'radius_cost', 'mixed_cutoff', 'tail_cutoff',
                                     'collapsed_cutoff', 'sources', 'site') if getattr(r, k) != getattr(p, k)]
            row = dict(record=r.ident, pool=r.pool, origin=r.origin, N=r.N, lambda_N=r.lam * r.N,
                       meets_lambda_N_minimum=ok, h=h, abs_difference_to_primary=diff,
                       configuration_differences_from_primary=differing,
                       note='record configuration listed; auxiliary inputs aligned to the primary point')
            if r.pool == 'primary' and r.N < p.N and ok and diff is not None:
                row['enters_eps_cross'] = True
                cross_eps = diff if cross_eps is None else max(cross_eps, diff)
            else:
                row['enters_eps_cross'] = False
            cross_rows.append(row)
        eps_spec = max(an.main['half_spread'], prefix['d34'] or 0.0, cross_eps or 0.0)
        flags = []
        if not lambda_n_ok(p.order, p.lam, p.N):
            flags.append(f'lambda*N = {p.lam * p.N:g} below the order-{p.order} minimum {ca.LAMBDA_N_MINIMUM[p.order]}')
        flags += grid['flags']
        if an.main['rejected_selected']:
            flags.append(f"{len(an.main['rejected_selected'])} selected spectral fit(s) rejected by the rank/dof guard")
        pid = p.ident
        points[pid] = dict(id=pid, order=p.order, lam=p.lam, h=an.main['h'], eps_spec=eps_spec,
                           eps_mix=mix['eps_mix'], eps_coll=coll['eps_coll'], eps_grid=grid['eps_grid'],
                           eps_round=rnd['eps_round'], eps_tailcut=tail['eps_tailcut'],
                           half_spread=an.main['half_spread'], prefix_d34=prefix['d34'], eps_cross=cross_eps,
                           grid_smooth=grid['smooth'], grid_rough=grid['rough'], grid_rev4_l1=grid['rev4_l1'],
                           grid_signed=grid['signed_shift'])
        legacy = None
        if p.origin.startswith('archived'):
            legacy = legacy_comparison(p, an)
        aux_k = aux[key]
        points_out.append(dict(
            id=pid, record=p.describe(), order=p.order, lam=p.lam, N=p.N, lambda_N=p.lam * p.N, flags=flags,
            h=an.main['h'], eps_spec=eps_spec,
            eps_spec_components=dict(half_spread=an.main['half_spread'], prefix_d34=prefix['d34'],
                                     eps_cross=cross_eps),
            eps=dict(eps_mix=mix['eps_mix'], eps_coll=coll['eps_coll'], eps_grid=grid['eps_grid'],
                     eps_round=rnd['eps_round'], eps_tailcut=tail['eps_tailcut']),
            auxiliary=dict(source=aux_k.source, checks=aux_k.checks, mixed=mix, collapsed=coll, tail=tail,
                           mixed_selected_fits=an.mixed['selected'], mixed_prefix_selected=an.mixed_prefix['selected']),
            assembly=an.asm,
            spectral=dict(an.main, rule='M3 selected ensemble'),
            prefix_test=prefix, cross_N=cross_rows, extraction=dict(grid, measured=measured.get(pid)),
            roundoff=rnd, legacy_inputs_comparison=legacy))
    # diagnostic and lower-N records (reported alongside)
    others = []
    for r in records:
        if r is primary[(r.order, r.lam)]:
            continue
        an = analyses[r.ident]
        others.append(dict(record=r.describe(), lambda_N=r.lam * r.N, meets_lambda_N_minimum=lambda_n_ok(r.order, r.lam, r.N),
                           h=an.main['h'], half_spread=an.main['half_spread'],
                           n_selected_accepted=an.main['n_selected_accepted'],
                           selected_values=an.main.get('values'), extraction_measured=measured.get(r.ident),
                           role='DIAGNOSTIC (M4d; never an estimate)' if r.pool == 'diagnostic'
                           else 'lower-N PRIMARY record (M4b check only)'))

    deviations_path = Path(a.deviations).resolve() if a.deviations else None
    legacy_path = Path(a.legacy_receipt).resolve() if a.legacy_receipt else None
    aux_sources = {f'{k[0]}:{k[1]!r}': v.source for k, v in aux.items()}
    estimate_and_write(points, points_out, others, replaced, measured, aux_sources, inputs, started, Path(a.output),
                       rev4_est, deviations_path, legacy_path)


LEGACY_FILES = ('FINAL_NUMERICAL_RESULTS.json', 'extended_analysis.json', 'tail_transseries_fits.json')
LEGACY_TOLERANCES = dict(value_and_residual_abs=1e-4, representative_C2_abs=1e-8, condition_rel_gate=0.1,
                         unclassified='fails')


def legacy_receipt_problems(rep) -> list[str]:
    """IR2-004: everything an A1 receipt must contain before PASSED or FAILED can be stated."""
    if not isinstance(rep, dict):
        return ['the receipt is not a JSON object']
    problems = []
    s = rep.get('summary') if isinstance(rep.get('summary'), dict) else {}
    for key in ('same_platform_pristine_bytes_identical', 'cross_platform_passed'):
        m = s.get(key)
        if not isinstance(m, dict) or set(m) != set(LEGACY_FILES):
            problems.append(f'summary.{key} must list exactly {sorted(LEGACY_FILES)}')
        elif not all(isinstance(v, bool) for v in m.values()):
            problems.append(f'summary.{key} must hold an explicit boolean for each file')
    if (rep.get('same_platform_pristine') or {}).get('commit') != '474487c':
        problems.append('same_platform_pristine.commit must be 474487c')
    pol = rep.get('policy') if isinstance(rep.get('policy'), dict) else {}
    cases = pol.get('tail_transseries_cases')
    if not (isinstance(cases, list) and len(cases) == 11 and [3, 0.35] not in [list(c) for c in cases]):
        problems.append('policy.tail_transseries_cases must be the 11 historical cases without (3, 0.35)')
    if pol.get('historically_missing') != ['fine_k3_a0.35.json'] or pol.get('guards_applied') is not False:
        problems.append('policy must record historically_missing = [fine_k3_a0.35.json] and guards_applied = false')
    if rep.get('tolerances') != LEGACY_TOLERANCES:
        problems.append(f'tolerances must be {LEGACY_TOLERANCES}')
    comps = rep.get('comparisons')
    if not (isinstance(comps, list) and sorted(c.get('file') for c in comps if isinstance(c, dict)) == sorted(LEGACY_FILES)):
        problems.append('comparisons must hold one entry for each legacy file')
    plat = rep.get('platform') if isinstance(rep.get('platform'), dict) else {}
    if not all(plat.get(k) for k in ('python', 'platform', 'numpy')):
        problems.append('platform must record python, platform and numpy')
    return problems


def legacy_validation(path: Path | None) -> dict:
    """R005/IR2-004: the report's legacy statements come from an inspected, schema-checked legacy receipt.
    status: PASSED (complete, every check true), FAILED (complete, some check false) or INCOMPLETE."""
    if path is None:
        return dict(performed=False, status='NOT PERFORMED',
                    note='legacy validation was not performed for this run (no --legacy-receipt)')
    try:
        rep = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        rep, problems = None, [f'unreadable receipt: {exc}']
    else:
        problems = legacy_receipt_problems(rep)
    out = dict(performed=True, file=rel(path), sha256=cr.sha256(path) if path.is_file() else None,
               problems=problems)
    if problems:
        out.update(status='INCOMPLETE', passed=False)
        return out
    s = rep['summary']
    pristine, cross = s['same_platform_pristine_bytes_identical'], s['cross_platform_passed']
    passed = all(pristine.values()) and all(cross.values())
    out.update(status='PASSED' if passed else 'FAILED', passed=passed, platform=rep['platform'],
               tolerances=rep['tolerances'], pristine_commit=rep['same_platform_pristine']['commit'],
               same_platform_pristine_bytes_identical=pristine, cross_platform_passed=cross,
               bytes_identical_to_reference=s.get('bytes_identical_to_reference'),
               max_abs_value_difference=s.get('max_abs_value_difference'),
               max_rel_condition_difference=s.get('max_rel_condition_difference'),
               max_abs_representative_C2_difference=s.get('max_abs_representative_C2_difference'))
    return out


def order_result(k: int, reg: dict, points: dict) -> tuple[dict, dict | None]:
    pref = reg['preferred']
    res = dict(order=k, selection_status=reg['selection_status'], validated=reg['validated'],
               validation_status=reg['validation_status'], exclusion_reason=reg.get('exclusion_reason'),
               n_admissible_distinct=reg['n_admissible_distinct'], n_fits=reg['n_fits'],
               admissible_descriptive=reg.get('admissible_descriptive'),
               preferred=dict(terms=pref.get('terms'), weighted=pref.get('weighted'), windows=pref.get('windows'),
                              available=pref.get('available', True), admissible=pref.get('admissible'),
                              rejection_reasons=pref.get('rejection_reasons')))
    if reg['S'] is None:
        return res, None
    S = reg['S']
    b = ca.order_budget(reg, points)
    res.update(S=dict(point_ids=S['point_ids'], lambdas=S['lambdas'], terms=S['terms'], weighted=S['weighted'],
                      windows=S['windows'], coefficients=S['coefficients'], influence=S['influence'],
                      condition=S['condition'], max_residual=S['max_residual'], dof=S['dof'],
                      preferred=bool(S.get('preferred'))),
               h0=b['h0'], E=b['E'], components=b['components'], sum_abs_influence=b['sum_abs_influence'],
               C2=ca.c2_from_h0(b['h0'], b['E']))
    return res, (dict(h0=b['h0'], E=b['E']) if reg['validated'] else None)


GENERATIONS = 'generations'
POINTER = 'CURRENT'
WRITER_LOCK = '.writer.lock'
TOP_FILES = ('continuum_points.json', 'regulator_fits.json', 'C2_estimate.json', 'REPORT.md')


def acquire_writer_lock(out: Path) -> Path:
    """IR2-002: exclusive writer lock (O_CREAT | O_EXCL). A second writer is refused; a lock left by a killed
    writer must be removed by hand after checking that no writer is running."""
    lock = out / WRITER_LOCK
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        raise RuntimeError(f'{lock} exists: another writer is publishing into {out}; remove it only after '
                           f'verifying that no writer is running') from None
    with os.fdopen(fd, 'w') as f:
        f.write(json.dumps(dict(pid=os.getpid(), host=platform.node(),
                                started_utc=dt.datetime.now(dt.timezone.utc).isoformat())) + '\n')
    return lock


def release_writer_lock(lock: Path) -> None:
    try:
        lock.unlink()
    except FileNotFoundError:
        pass


def atomic_copy(src: Path, dst: Path) -> None:
    tmp = dst.with_name(f'.{dst.name}.tmp.{os.getpid()}')
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def switch_current(out: Path, name: str) -> None:
    """Point CURRENT at generations/<name> with a single atomic rename (the source of truth for readers)."""
    tmp = out / f'.{POINTER}.tmp.{os.getpid()}'
    with open(tmp, 'w') as f:
        f.write(f'{GENERATIONS}/{name}\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, out / POINTER)


def current_generation(out: Path) -> Path | None:
    """The generation directory named by CURRENT (readers resolve every result file from it)."""
    ptr = Path(out) / POINTER
    if not ptr.is_file():
        return None
    rel_dir = ptr.read_text().strip()
    gen = (Path(out) / rel_dir).resolve()
    if not (rel_dir.startswith(GENERATIONS + '/') and gen.is_dir() and gen.parent == (Path(out) / GENERATIONS).resolve()
            and not gen.name.startswith('.')):
        raise ValueError(f'{ptr}: does not name a complete generation ({rel_dir!r})')
    return gen


def sync_top_level(out: Path) -> None:
    """Refresh the top-level copies (for people and the paper) from the CURRENT generation. Each copy is replaced
    atomically; if a run is interrupted between files, running `continuum_driver.py sync` (or any later run)
    restores them, and `continuum_driver.py check` reports any mismatch. CURRENT, not the copies, is authoritative;
    every copy names its generation (meta.generation in the JSON files, the first lines of REPORT.md)."""
    gen = current_generation(out)
    if gen is None:
        raise ValueError(f'{out}: no CURRENT generation')
    for f in TOP_FILES:
        atomic_copy(gen / f, Path(out) / f)
        (Path(out) / f).chmod(0o644)


def check_top_level(out: Path) -> list[str]:
    """Top-level copies that differ from the CURRENT generation (empty list: consistent)."""
    gen = current_generation(out)
    if gen is None:
        return ['no CURRENT generation']
    return [f for f in TOP_FILES if not (Path(out) / f).is_file() or (Path(out) / f).read_bytes() != (gen / f).read_bytes()]


def estimate_and_write(points: dict, points_out: list, others: list, replaced: list, measured: dict,
                       aux_sources: dict, inputs: dict, started: str, out: Path, rev4_est: dict | None,
                       deviations_path: Path | None = None, legacy_path: Path | None = None) -> dict:
    """M6, M7, M8 and the outputs, published as one immutable generation (IR2-002): the complete set is written to
    generations/.<name>.partial, renamed to generations/<name>, and CURRENT is switched to it by one atomic rename,
    under an exclusive writer lock. A failed or interrupted run leaves the previous generation current."""
    for extra in (deviations_path, legacy_path):
        if extra is not None:
            inputs[rel(extra)] = cr.sha256(extra)
    by_order: dict[int, list] = {}
    for pt in points.values():
        by_order.setdefault(pt['order'], []).append(pt)
    regs = {k: ca.regulator_order(v, k) for k, v in sorted(by_order.items())}
    per_order, order_results = {}, {}
    for k, reg in regs.items():
        order_results[k], kept = order_result(k, reg, points)
        if kept is not None:
            per_order[k] = kept
    retained = sorted(per_order)
    joint = ca.joint_analysis(regs, retained, points, by_order) if len(retained) >= 2 else None
    out_table = ca.outcome(per_order, joint)
    final = None
    if out_table['h0'] is not None:
        final = dict(h0=out_table['h0'], E_h0=out_table['E'], **ca.c2_from_h0(out_table['h0'], out_table['E']))
    budget = error_budget(out_table, order_results, joint)

    meta = dict(generated_utc=started, python=sys.version, platform=platform.platform(),
                numpy=np.__version__, inputs_sha256=dict(sorted(inputs.items())), rules=ca.RULES,
                proposed_closed_form_used=False,
                status='numerical diagnostics, not rigorous bounds')
    exceptions = [dict(id=q['id'], order=q['order'], lam=q['lam'], N=q['N'], frozen_rev4=q['extraction']['frozen_rev4'])
                  for q in points_out if q['extraction']['status'] == 'rev-4 exception']
    coverage = dict(complete=not exceptions, exceptions=exceptions,
                    label='extraction coverage complete' if not exceptions else 'extraction coverage incomplete',
                    n_points=len(points_out), n_measured=len(points_out) - len(exceptions))
    if final is not None:
        final['label'] = coverage['label']
    superseded = None
    if rev4_est is not None:
        superseded = dict(note='rev-4 result (L1 extraction rule with inheritance), archived in evidence/rev4; '
                               'superseded', outcome_branch=rev4_est['outcome']['branch'], h0=rev4_est['final']['h0'],
                          E_h0=rev4_est['final']['E_h0'], C2=rev4_est['final']['C2'], dC2=rev4_est['final']['dC2'],
                          per_order={k: dict(h0=v['h0'], E=v['E']) for k, v in rev4_est['per_order'].items()})
    deviations = []
    if deviations_path is not None:
        deviations = [dict(title=l[3:].strip(), file=f'evidence/{deviations_path.name}', sha256=cr.sha256(deviations_path))
                      for l in deviations_path.read_text().splitlines() if l.startswith('## ')]
    estimate = dict(meta=meta, extraction_coverage=coverage, superseded_rev4=superseded, deviations=deviations,
                    legacy_validation=legacy_validation(legacy_path),
                    per_order=order_results, retained_orders=retained, joint=None if joint is None else dict(
        h0=joint['preferred']['h0'], accepted=joint['preferred']['accepted'], blocks=joint['preferred']['blocks'],
        condition=joint['preferred']['condition'], n_variants=joint['n_variants'],
        n_admissible_distinct=joint['n_admissible_distinct'], eps_model_joint=joint['eps_model_joint'],
        components=joint['components'], E=joint['E'], validated=joint['validated'],
        C2=ca.c2_from_h0(joint['preferred']['h0'], joint['E'])),
        outcome=out_table, final=final, error_budget=budget)
    # Comparison with earlier numbers: computed only after every estimate above is fixed.
    estimate['comparison_after_computation'] = historical_comparison(final, order_results)

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lock = acquire_writer_lock(out)              # IR2-002: one writer at a time, or refuse
    gen = None
    try:
        name = (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                + f'_{os.getpid()}_{os.urandom(3).hex()}')
        meta['generation'] = name
        estimate['meta'] = meta
        gens = out / GENERATIONS
        gens.mkdir(exist_ok=True)
        gen = gens / f'.{name}.partial'           # invisible to readers until it is complete
        gen.mkdir()
        write(gen / 'continuum_points.json', dict(
            meta=meta, primary_points=points_out, other_records=others, replaced_by_M5=replaced,
            extraction_measurements=measured, aligned_auxiliary_sources=aux_sources))
        write(gen / 'regulator_fits.json', dict(meta=meta, orders={str(k): dict(
            order=k, fits=v['fits'], skipped_underdetermined=v['skipped_underdetermined'],
            selected=order_results[k].get('S'), preferred=order_results[k]['preferred'],
            preferred_terms=list(ca.PREFERRED['terms']), selection_status=v['selection_status'],
            validation_status=v['validation_status'], exclusion_reason=v.get('exclusion_reason'))
            for k, v in regs.items()}, joint=joint))
        write(gen / 'C2_estimate.json', estimate)
        from continuum_report import write_report
        write_report(gen, points_out, others, order_results, regs, joint, out_table, final, budget, estimate,
                     replaced, measured, meta)
        for f in TOP_FILES:
            (gen / f).chmod(0o444)                # an immutable generation
        final_dir = gens / name
        os.rename(gen, final_dir)                 # complete generation, atomically visible
        gen = None
        if deviations_path is not None:           # input copy kept with the evidence (identical bytes each run)
            (out / 'evidence').mkdir(exist_ok=True)
            atomic_copy(deviations_path, out / 'evidence' / deviations_path.name)
        switch_current(out, name)                 # THE publication step: one atomic rename of CURRENT
        sync_top_level(out)                       # human/paper copies of the current generation
    finally:
        if gen is not None:                       # an interrupted generation never becomes current
            shutil.rmtree(gen, ignore_errors=True)
        release_writer_lock(lock)
    print('WROTE', current_generation(out), '(CURRENT) and the top-level copies in', out)
    return estimate


def legacy_comparison(p, an) -> dict:
    """h with the record's original auxiliary inputs (legacy) against the aligned inputs: M1, M2, M2b shifts."""
    d = p.data
    legacy_mixed = ca.mixed_select(d['mixed']['fits'], d['mixed']['Nmax'])
    seq_old, asm_old = ca.assemble(d, d['two_point'], legacy_mixed['selected'])
    a_old = p.legacy_a_face['asymptotic_tail_coefficient']
    h_old = ca.m3(seq_old, p.N, p.lam, p.order, a_old, full=False)['h']
    h_mix = an.variant_h(two_point=d['two_point'], a_face=a_old)          # aligned mixed only
    h_mix_coll = an.variant_h(a_face=a_old)                               # aligned mixed + collapsed
    return dict(
        legacy_inputs=dict(mixed_cutoff=d['mixed']['Nmax'], mixed_limit=legacy_mixed['median'],
                           collapsed_cutoff=d['two_point']['N'], tail_cutoff=p.legacy_a_face['N'], A_face=a_old,
                           h=h_old),
        aligned_inputs=dict(mixed_cutoff=an.aux.mixed_cutoff, mixed_limit=an.mixed['median'], collapsed_cutoff=800000,
                            tail_cutoff=8192, A_face=an.aux.a8192_800, h=an.main['h']),
        M1_mixed_shift_t_times_delta=float(asm_old['t'] * (an.mixed['median'] - legacy_mixed['median'])),
        M1_mixed_shift_h=float(h_mix - h_old),
        M2b_collapsed_shift_h=float(h_mix_coll - h_mix),
        M2_tail_shift_h=float(an.main['h'] - h_mix_coll),
        total_shift_h=float(an.main['h'] - h_old))


def error_budget(out_table: dict, order_results: dict, joint: dict | None) -> dict:
    """M8: each component separately in h0 and in C2."""
    conv = ca.c2_from_h0(0.0)['dC2_per_dh0']
    names = [('eps_prop', 'spectral, propagated (sum |w| eps_spec)'),
             ('half_spread', '  of which: spectral-model half-spread (breakdown, not additive)'),
             ('prefix_d34', '  of which: prefix drift |h(N)-h(3N/4)| (breakdown, not additive)'),
             ('eps_cross', '  of which: cross-N (breakdown, not additive)'),
             ('eps_mix', 'mixed cutoff and mixed-model spread'),
             ('eps_tailcut', 'tail cutoff (2048 vs 8192)'),
             ('eps_coll', 'collapsed cutoff (400000 vs 800000)'),
             ('eps_grid', 'grid/coefficient extraction (M4d, rev 6/7: |v.s| + sum|v||rho|)'),
             ('grid_smooth', '  of which: smooth part |v.s| (breakdown)'),
             ('grid_rough', '  of which: rough part sum|v||rho| (breakdown)'),
             ('grid_rev4_l1', 'rev-4 L1 sum|v||delta| (superseded, not in E)'),
             ('grid_signed', 'signed shift |sum v delta| (reported, not in E)'),
             ('eps_round', 'roundoff (M4e)'),
             ('eps_model', 'regulator model')]

    def table(comp: dict) -> list:
        return [dict(component=k, description=d, h0=comp.get(k), C2=None if comp.get(k) is None else comp[k] * conv)
                for k, d in names]
    out = dict(conversion_dC2_per_dh0=conv, per_order={str(k): dict(table=table(v['components']), E=v['E'],
                                                                      E_C2=v['E'] * conv)
                                                      for k, v in order_results.items() if 'components' in v})
    if joint is not None:
        out['joint'] = dict(table=table(joint['components']), E=joint['E'], E_C2=joint['E'] * conv)
    pairs = out_table.get('pairs') or []
    out['order_consistency'] = dict(pairs=pairs, max_pair_difference=max([p['difference'] for p in pairs] or [0.0]),
                                    envelope=out_table.get('envelope'))
    out['quoted'] = dict(branch=out_table['branch'], label=out_table['label'], E_h0=out_table['E'],
                         E_C2=None if out_table['E'] is None else out_table['E'] * conv)
    out['status'] = 'linear sums of systematic diagnostics, not rigorous bounds or standard deviations'
    return out


def historical_comparison(final: dict | None, order_results: dict) -> dict:
    ref = json.loads((cr.REFERENCE / 'FINAL_NUMERICAL_RESULTS.json').read_text())
    hist = {p['order']: dict(h0=p['h0'], C2=p['C2']) for p in ref['representative_regulator_fits']}
    rows = []
    for k, v in sorted(order_results.items()):
        if 'C2' in v:
            rows.append(dict(order=k, new_C2=v['C2']['C2'], new_dC2=v['C2']['dC2'], historical_C2=hist[k]['C2'],
                             difference=v['C2']['C2'] - hist[k]['C2'],
                             in_units_of_new_error=(v['C2']['C2'] - hist[k]['C2']) / v['C2']['dC2']))
    out = dict(note='Computed after every estimate was fixed; the historical numbers are not inputs.',
               historical_representative=hist, per_order=rows,
               earlier_reviewers=dict(C2=-4.067, uncertainty=0.004))
    if final is not None:
        out['final_minus_reviewers'] = final['C2'] - (-4.067)
        out['final_dC2'] = final['dC2']
    return out


def write(path: Path, obj) -> None:
    path.write_text(json.dumps(ca.clean(obj), indent=1, allow_nan=False) + '\n')


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--records', type=Path, required=True, help='merged index of the PRIMARY production records')
    r.add_argument('--diagnostic-records', type=Path, nargs='*', default=[],
                   help='merged indexes of the M4d extraction-check records (DIAGNOSTIC pool)')
    r.add_argument('--deviations', type=Path,
                   help='record of user-approved deviations from the plan; copied to <output>/evidence/ and listed in '
                        'REPORT.md')
    r.add_argument('--legacy-receipt', type=Path,
                   help='legacy_reproduction.json of a `continuum_driver.py legacy` run; its result is reported '
                        '(without it, the report states that legacy validation was not performed)')
    r.add_argument('--rev4-points', type=Path,
                   default=ca.PKG / 'results/continuum_2026-10/evidence/rev4/continuum_points.json',
                   help='archived rev-4 continuum_points.json (frozen epsilon_grid for R6-002 exceptions)')
    r.add_argument('--aux-dir', type=Path, required=True, help='published c2aux job directory (SHA256SUMS)')
    r.add_argument('--output', type=Path, required=True)
    sy = sub.add_parser('sync', help='refresh the top-level copies from the CURRENT generation')
    sy.add_argument('--output', type=Path, required=True)
    ck = sub.add_parser('check', help='verify that the top-level copies equal the CURRENT generation')
    ck.add_argument('--output', type=Path, required=True)
    lg = sub.add_parser('legacy')
    lg.add_argument('--output', type=Path, required=True)
    lg.add_argument('--python', default=sys.executable)
    a = p.parse_args(argv)
    if a.cmd == 'run':
        run(a)
    elif a.cmd == 'sync':
        lock = acquire_writer_lock(a.output)
        try:
            sync_top_level(a.output)
        finally:
            release_writer_lock(lock)
        print('SYNCED', current_generation(a.output))
    elif a.cmd == 'check':
        bad = check_top_level(a.output)
        print('CURRENT', current_generation(a.output))
        if bad:
            print('MISMATCH', *bad)
            sys.exit(1)
        print('CONSISTENT')
    else:
        from continuum_legacy import run_legacy
        rep = run_legacy(a.output, a.python)
        print(json.dumps(rep['summary'], indent=1))


if __name__ == '__main__':
    main()
