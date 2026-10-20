#!/usr/bin/env python3
"""Compare reproduced outputs (WORK/reproduced/...) with the reference results shipped in results/ and data/.

Usage: compare_outputs.py WORK                 run every comparison whose reproduced output exists; write WORK/reproduced/VERIFY.md
       compare_outputs.py WORK --require-all   fail if a comparison's reproduced output is missing

JSON comparison: every key of the reference must exist in the reproduction (extra keys are listed, not failures); strings, booleans,
integers and None must be equal; floats must agree to rtol (default 1e-9, plus 1e-12 absolute). Keys that necessarily differ between
runs (time stamps, host, interpreter versions, run directories) are skipped per comparison and listed in the report.
Floating-point results reproduce to ~1e-11 relative across machines (BLAS rounding); bit-for-bit identity is not expected off the
original hosts.

Public-release copy (2026-10-13): at Delta_sigma = 0.1625 and 0.1727335 the 1D label (and with it sigma_sys and the quotable set) depends on
the platform (note, section "Reproducibility of the fitting stage across platforms"). A refit that differs from production there ONLY in
those fields is reported as KNOWN-PLATFORM-SENSITIVE and does not fail; a difference in the quoted configuration, Delta_epsilon or
sigma_stat, or any label difference at another point, is a FAIL. A comparison whose reference file is missing is reported as
REFERENCE MISSING and fails (a renamed or deleted results folder must not disappear from the report).

Re-pinned records: RE-PINNED.json lists the records whose host labels and file names were scrubbed after the results, with their original
and published SHA-256 (and, for registries, the portable-view hash). Records outside that list keep their original pins. Before every JSON
comparison, published hashes are mapped back to the original ones in both the reference and the reproduction, so a pin of a scrubbed file
compares equal whichever version it names.
"""
import argparse, json, math, re, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]

# The reported maximum relative difference ignores reference values below REL_FLOOR (machine-precision residuals such as
# max_reproduction_error ~ 1e-16, whose relative change is meaningless); those are compared with the absolute tolerance only.
REL_FLOOR = 1e-9

def walk(ref, new, path, skip, rtol, out, atol=1e-12):
    if path and path[-1] in skip: return
    if isinstance(ref, dict):
        if not isinstance(new, dict): out['diff'].append((path, 'type')); return
        for k in ref:
            if k in skip: continue
            if k not in new: out['diff'].append((path + (k,), 'missing in reproduction')); continue
            walk(ref[k], new[k], path + (k,), skip, rtol, out, atol)
        out['extra'] += [path + (k,) for k in new if k not in ref and k not in skip]
    elif isinstance(ref, list):
        if not isinstance(new, list) or len(ref) != len(new): out['diff'].append((path, f'list length {len(ref)} vs {len(new) if isinstance(new, list) else type(new).__name__}')); return
        for i, (a, b) in enumerate(zip(ref, new)): walk(a, b, path + (i,), skip, rtol, out, atol)
    elif isinstance(ref, float) and isinstance(new, (int, float)) and not isinstance(new, bool):
        if math.isnan(ref) and math.isnan(new): return
        d = abs(new - ref); out['nfloat'] += 1
        if abs(ref) > REL_FLOOR and d / abs(ref) > out['maxrel']: out['maxrel'] = d / abs(ref); out['maxfield'] = '/'.join(map(str, path))
        if not d <= atol + rtol * abs(ref): out['diff'].append((path, f'{new!r} vs {ref!r}'))
    elif type(ref) != type(new) or ref != new:
        out['diff'].append((path, f'{new!r} vs {ref!r}'))

def load_repins():
    """published -> original SHA-256 (files, and registry portable-view hashes) from RE-PINNED.json, if shipped."""
    f = PKG / 'RE-PINNED.json'
    if not f.exists(): return {}
    m = {}
    for e in json.loads(f.read_text())['files']:
        m[e['published_sha256']] = e['original_sha256']
        if 'published_portable_sha256' in e: m[e['published_portable_sha256']] = e['original_portable_sha256']
    return {k: v for k, v in m.items() if k != v}
REPINS = load_repins()

def unpin(x):
    if isinstance(x, dict): return {unpin(k): unpin(v) for k, v in x.items()}
    if isinstance(x, list): return [unpin(v) for v in x]
    if isinstance(x, str) and REPINS:
        for a, b in REPINS.items():
            if a in x: x = x.replace(a, b)
    return x

def cmp_json(ref, new, skip=(), rtol=1e-9, select=None, transform=None, atol=1e-12, informational=False, platform_point=None):
    R = unpin(json.loads(Path(ref).read_text())); N = unpin(json.loads(Path(new).read_text()))
    if select: R, N = select(R), select(N)
    if transform: R, N = transform(R), transform(N)
    out = dict(diff=[], extra=[], nfloat=0, maxrel=0.0, maxfield=''); walk(R, N, (), set(skip), rtol, out, atol)
    return out

# Absolute paths recorded in the outputs name the machine they ran on; compare them from the project-layout component on.
PATH_RX = [(re.compile(r'^.*/(?:scan_data|lri_mc/scan)/'), 'SCAN/'),
           (re.compile(r'^.*/(LRI_2d_MC|LRI_3d_MC|LRI_2d3d_reanalysis|lri_cluster)/'), r'\1/'),
           (re.compile(r'^.*/(?:prod2d|lri2d/prod2d)/'), 'LRI_2d_MC/prod/'), (re.compile(r'^.*/(?:prod3d|lri3d/prod3d)/'), 'LRI_3d_MC/prod/')]
def norm_paths(x):
    if isinstance(x, dict): return {k: norm_paths(v) for k, v in x.items()}
    if isinstance(x, list): return [norm_paths(v) for v in x]
    if isinstance(x, str) and '/' in x:
        for rx, sub in PATH_RX:
            y = rx.sub(sub, x)
            if y != x: return y
    return x

PLATFORM_SENSITIVE = {'0.1625', '0.1727335'}
LABEL_FIELDS = {'decision', 'sigma_sys', 'n_quotable', 'quotable'}

def decision_summary(points):
    """1D refit, decision level: what the 1D table reports for each point."""
    out = {}
    for k, P in points.items():
        q = P.get('quoted') or {}; Q = [x.get('key', str(x)) if isinstance(x, dict) else str(x) for x in (P.get('quotable') or [])]
        out[k] = dict(decision=P.get('decision'), quoted_config=q.get('key'), Delta_epsilon=q.get('Delta_epsilon'), sigma_stat=q.get('sigma_stat'),
                      sigma_sys={k: (P.get('sigma_sys') or {}).get(k) for k in ('value', 'coverage_ok', 'n_quotable', 'range')},
                      n_quotable=len(Q), quotable=sorted(Q))
    return out

def strip_nonprod(x):
    """1D refit: a run outside the original filesystem is stamped NON-PRODUCTION; compare the decision it 'would be'."""
    if isinstance(x, dict): return {k: strip_nonprod(v) for k, v in x.items()}
    if isinstance(x, list): return [strip_nonprod(v) for v in x]
    if isinstance(x, str) and x.startswith('NON-PRODUCTION') and '; would be: ' in x: return x.split('; would be: ', 1)[1]
    return x

def comparisons(W):
    rp = W / 'reproduced'; C = []
    TIME = ('time', 'created', 'host', 'python', 'numpy', 'elapsed_s')
    for dim, base, p1 in ((2, 'data/2d/prod/evaluation_20260922_083649/evaluation_2d.json', 'results/2d/evaluation_P1_20260930_215057/evaluation_2d.json'),
                          (3, 'data/3d/prod/evaluation_54387089_20260923_194523/evaluation_3d.json', 'results/3d/evaluation_P1_54387089_20260930_215057/evaluation_3d.json')):
        C.append((f'{dim}D frozen rule vs pinned production evaluation (all per-point fields)', PKG / base, rp / f'eval_fixed_{dim}d/evaluation_{dim}d.json',
                  dict(skip=('results', 'index_path_read'), select=lambda r: r['points'], transform=norm_paths)))
        C.append((f'{dim}D amendment-P1 evaluation vs shipped P1 evaluation', PKG / p1, rp / f'eval_p1_{dim}d/evaluation_{dim}d.json', dict(skip=TIME, transform=norm_paths)))
    C.append(('P1 calibration: strata, A3, information (header provenance skipped)', PKG / 'results/2d3d_reanalysis/calibration/run_20260930_213748/CALIBRATION.json',
              rp / 'calibration/CALIBRATION.json', dict(select=lambda r: {k: r[k] for k in ('strata', 'A3', 'A3_information', 'information')})))
    C.append(('1D profiled-cross-check study (Δσ = 0.15, 0.175)', PKG / 'results/1d/oned_xcheck/run_20260930_202320/oned_xcheck.json', rp / 'oned_xcheck/oned_xcheck.json', dict(skip=TIME)))
    C.append(('1D 20-point scan table (scan_v3_report.py)', PKG / 'data/1d/scan_data/FIT_V3_SCAN.json', rp / '1d_scan/FIT_V3_SCAN.json', {}))
    for tree in sorted(x.name for x in rp.glob('1d_refit*') if x.is_dir()):   # 1d_refit (make refit1d) and any variant trees, e.g. other software stacks
        for ds_dir in sorted(x for x in (rp / tree).glob('ds*') if x.is_dir()):
            ds = ds_dir.name[2:]; sel = json.loads((PKG / f'data/1d/scan_data/ds{ds}/fits_v3_SELECTED.json').read_text())['selected_run']
            ref = PKG / f'data/1d/scan_data/ds{ds}/{sel}/fit_v3.json'; new = ds_dir / 'fit_v3.json'
            # decision level: label, quoted configuration, quoted value and errors (absolute 1e-6), set of quotable fits. This is what
            # the 1D table reports and must agree.
            C.append((f'1D refit ({tree}) of Δσ = {ds}: decision, quoted fit, σ_stat, σ_sys, quotable set', ref, new,
                      dict(select=lambda r: decision_summary(r['points']), transform=strip_nonprod, rtol=0.0, atol=1e-6, platform_point=ds)))
            # every field (paths normalised), informational: nonlinear least-squares optima (and hence bootstrap percentiles, residual
            # statistics) agree only to ~1e-7 absolute across software stacks, so off the production host this normally shows DIFF.
            C.append((f'1D refit ({tree}) of Δσ = {ds}: all fields vs production run {sel} (informational)', ref, new,
                      dict(select=lambda r: r['points'], transform=lambda r: norm_paths(strip_nonprod(r)), informational=True,
                           skip=('provenance', 'elapsed_s', 'time', 'production', 'non_production_reasons'), rtol=1e-6)))
    return C

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('work'); p.add_argument('--require-all', action='store_true'); a = p.parse_args()
    W = Path(a.work).resolve(); lines = ['# Verification of reproduced outputs', '', '| comparison | status | floats compared | max rel. diff | notes |', '|---|---|---|---|---|']
    bad = 0
    for name, ref, new, kw in comparisons(W):
        if not Path(ref).exists():
            lines.append(f'| {name} | REFERENCE MISSING | | | {Path(ref).relative_to(PKG)} missing |'); bad += 1; continue
        if not new.exists():
            lines.append(f'| {name} | NOT RUN | | | {new.relative_to(W)} missing |'); bad += a.require_all; continue
        try: out = cmp_json(ref, new, **kw)
        except Exception as e: lines.append(f'| {name} | ERROR | | | {type(e).__name__}: {e} |'); bad += 1; continue
        ok = not out['diff']; info = kw.get('informational', False)
        known = (not ok and kw.get('platform_point') in PLATFORM_SENSITIVE and all(len(d[0]) > 1 and d[0][1] in LABEL_FIELDS for d in out['diff']))
        bad += (not ok) and not info and not known
        note = '; '.join(f"{'/'.join(map(str, d[0]))}: {d[1]}" for d in out['diff'][:3]) + (f" … ({len(out['diff'])} differences)" if len(out['diff']) > 3 else '')
        if out['extra']: note += (' ' if note else '') + f"{len(out['extra'])} extra keys in reproduction (e.g. {'/'.join(map(str, out['extra'][0]))})"
        status = ('SAME' if ok else 'DIFF') if info else ('PASS' if ok else ('KNOWN-PLATFORM-SENSITIVE' if known else 'FAIL'))
        mf = f" (at {out['maxfield']})" if out['maxfield'] and out['maxrel'] > 0 else ''
        lines.append(f"| {name} | {status} | {out['nfloat']} | {out['maxrel']:.1e}{mf} | {note} |")
    # 1D report tables: text identity
    for f in ('final_table_rows.tex', 'largest_pairs_rows.tex', 'pre_rows.tex'):
        new = W / 'LRI_1d_MC_report/tables' / f; ref = PKG / 'results/1d/tables' / f
        if not ref.exists(): lines.append(f'| 1D report table {f} | REFERENCE MISSING | | | |'); bad += 1; continue
        if not new.exists(): lines.append(f'| 1D report table {f} | NOT RUN | | | |'); bad += a.require_all; continue
        same = new.read_text() == ref.read_text(); bad += not same
        lines.append(f"| 1D report table {f} (text) | {'PASS' if same else 'FAIL'} | | | |")
    text = '\n'.join(lines) + '\n'; (W / 'reproduced').mkdir(parents=True, exist_ok=True); (W / 'reproduced/VERIFY.md').write_text(text); print(text)
    sys.exit(1 if bad else 0)

if __name__ == '__main__': main()
