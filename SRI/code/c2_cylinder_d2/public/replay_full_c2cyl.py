#!/usr/bin/env python3
"""Full replay of c_2 in d = 2 from the raw records (new tool, 2026-10-15). Run from code/c2_cylinder_d2/.

Reruns the continuum analysis exactly as it produced the shipped generation (the command of
code/continuum/continuum_driver.py, with the inputs listed in C2_estimate.json meta.inputs_sha256), into a work copy:

  python scripts/run.py continuum -- run \\
      --records outputs/merged_production_plan_20261013.json \\
      --diagnostic-records outputs/merged_analysis_checks_plan_20261013.json \\
                           outputs/merged_analysis_checks_plan_rev6_20261014.json \\
      --aux-dir outputs/symmetry/c2aux_574247 \\
      --legacy-receipt results/continuum_2026-10/evidence/legacy_macos/legacy_reproduction.json \\
      --deviations results/continuum_2026-10/evidence/DEVIATIONS_ANALYSIS.md \\
      --output <work>/continuum_2026-10

The driver itself verifies every input (archived records against MANIFEST.sha256, cluster records against the merged
indexes and their task SHA256SUMS, the auxiliary job against its SHA256SUMS, the science-source digest of every
receipt). The only difference from the original command is the path of the deviation record: the original read it
from the plan folder (not shipped); the copy in results/continuum_2026-10/evidence/ has the same sha256.

Then compares, leaf by leaf, the rerun generation with the shipped one (continuum_points.json, regulator_fits.json,
C2_estimate.json; REPORT.md number by number). Run-description meta fields (generated_utc, python, platform, numpy,
generation) are skipped; the input set (files and sha256) must be identical (the deviation record matched by name).
  * Discrete leaves (keys, list lengths, strings, booleans, integers, None: every selection, admissibility and
    validation flag, count, status and branch): equal (a placeholder of the public export in a shipped string, such as
    <NODE> for a host name, matches any text).
  * Tier A, the chain to the quoted number (h and every error component of the 25 PRIMARY points; h0 of every regulator
    fit and joint variant; per-order and joint h0, E, components, C2, dC2; the outcome table; the error budget; final):
    |difference| <= 1e-7 absolute (they are in units of h ~ 3.4 or of C2 ~ 4; the quoted digit is 1e-4). Measured
    on other platforms (2026-10-15): at most 1.1e-8 (Linux x86-64, OpenBLAS; a joint-variant h0) and 8.4e-9 (macOS,
    OpenBLAS); the tolerance was set after those measurements, with a margin of about 10.
  * Tier B, diagnostics of individual fits (spectral and regulator fit coefficients, residuals, influence rows,
    unselected spectral limits, extraction profiles, prefix and cross-N tables, ...): |difference| <= 1e-6 + 1e-3 |x|;
    condition numbers 1e-2 relative. Spectral fits keep condition numbers up to ~1e15 (truncated SVD at rcond 1e-13),
    so their last digits follow the platform's linear algebra; differences of large nearly equal numbers (for example
    the prefix shift of the mixed limits, |prefix - full| ~ 1e-6 of limits ~ 1e4) carry absolute noise ~ 1e-8.
The shipped generation was computed on macOS arm64 (CPython 3.13.5, numpy 2.3.5). With that interpreter the rerun is
bit-identical (every float); the replay reports the number of bit-identical floats as an INFO row.
Usage: python3 public/replay_full_c2cyl.py [--work DIR] [--python PY] [--out FILE]
"""
import argparse, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

from c2cyl_common import L, PKG, RESULTS, current_generation, load_json, matches_paren, quoted_entries, same_leaf

FILES = ('continuum_points.json', 'regulator_fits.json', 'C2_estimate.json')
VOLATILE_META = ('generated_utc', 'python', 'platform', 'numpy', 'generation', 'inputs_sha256')
TIER_A_ATOL = 1e-7
TIER_B = (1e-3, 1e-6)
COND_RTOL = 1e-2
TIER_A = {
    'continuum_points.json': [r'^/primary_points\[\d+\]/(h|eps_spec|eps/[^/]+|eps_spec_components/[^/]+)$'],
    'regulator_fits.json': [r'^/orders/\d+/(fits\[\d+\]|selected)/h0$', r'^/joint/(preferred|variants\[\d+\])/h0$',
                            r'^/joint/(E|eps_model_joint|components/[^/]+)$'],
    'C2_estimate.json': [r'^/per_order/\d+/(h0|E|components/[^/]+|C2/(C2|dC2)|S/h0)$',
                         r'^/joint/(h0|E|eps_model_joint|components/[^/]+|C2/(C2|dC2))$',
                         r'^/outcome/(h0|E|pairs\[\d+\]/(difference|limit)|envelope/[^/]+)$',
                         r'^/final/(h0|E_h0|C2|dC2)$', r'^/error_budget/.*/(h0|C2|E|E_C2|E_h0)$',
                         r'^/error_budget/order_consistency/.*', r'^/superseded_rev4/.*',
                         r'^/comparison_after_computation/.*'],
}
NUM = re.compile(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?')


def norm_inputs(d):
    """inputs_sha256 with the deviation record keyed by its file name (its original key was an absolute path)."""
    return {('DEVIATIONS_ANALYSIS.md' if k.endswith('DEVIATIONS_ANALYSIS.md') else k): v for k, v in d.items()}


def compare(a, b, fname):
    tier_a = [re.compile(p) for p in TIER_A[fname]]
    st = dict(floats=0, bitid=0, A=0, B=0, maxA=0.0, maxA_at='', maxB=0.0, maxB_at='', bad=[], discrete=0)

    def walk(x, y, p):
        if p.startswith('/meta/') and p.split('/')[2] in VOLATILE_META:
            return
        if isinstance(x, dict) and isinstance(y, dict):
            if set(x) != set(y):
                st['bad'].append(f'{p}: keys differ')
            for k in sorted(set(x) & set(y)):
                walk(x[k], y[k], f'{p}/{k}')
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                st['bad'].append(f'{p}: length {len(x)} vs {len(y)}')
                return
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, f'{p}[{i}]')
        elif type(x) is float or type(y) is float:
            if not all(type(z) in (int, float) for z in (x, y)):
                st['bad'].append(f'{p}: {x!r} vs {y!r}')
                return
            st['floats'] += 1
            d = abs(x - y)
            if d == 0:
                st['bitid'] += 1
                return
            if any(r.match(p) for r in tier_a):
                st['A'] += 1
                if d > st['maxA']:
                    st['maxA'], st['maxA_at'] = d, p
                if d > TIER_A_ATOL:
                    st['bad'].append(f'{p}: {x!r} vs {y!r} (tier A)')
            else:
                st['B'] += 1
                r = d / max(abs(x), abs(y))
                if r > st['maxB']:
                    st['maxB'], st['maxB_at'] = r, p
                ok = r <= COND_RTOL if p.endswith('/condition') else d <= TIER_B[1] + TIER_B[0] * abs(x)
                if not ok:
                    st['bad'].append(f'{p}: {x!r} vs {y!r} (tier B)')
        else:
            st['discrete'] += 1
            if not same_leaf(x, y):
                st['bad'].append(f'{p}: {x!r} vs {y!r}')
    walk(a, b, '')
    return st


def report_tokens(text, gen_name):
    text = text.replace(gen_name, '<GEN>')
    text = re.sub(r'\d{4}-\d\d-\d\dT[\d:.]+\+00:00', '<UTC>', text)
    text = re.sub(r'\(python [^)]*\)', '(python <...>)', text)
    return text


def compare_report(a, b, gen_a, gen_b):
    """Same text; every number within one unit of its last printed digit, 1e-6 absolute or 1e-2 relative (REPORT.md
    renders the JSON leaves compared above, including condition numbers)."""
    la = report_tokens(a, gen_a).splitlines()
    lb = report_tokens(b, gen_b).splitlines()
    if len(la) != len(lb):
        return False, f'{len(la)} vs {len(lb)} lines'
    bad, nnum, ndiff = [], 0, 0
    for i, (x, y) in enumerate(zip(la, lb)):
        nx, ny = NUM.findall(x), NUM.findall(y)
        nnum += len(nx)
        if x == y:
            continue
        if NUM.split(x) != NUM.split(y) or len(nx) != len(ny):
            bad.append(i + 1)
            continue
        for u, v in zip(nx, ny):
            if u == v:
                continue
            ndiff += 1
            fu, fv = float(u), float(v)
            mant = re.split('[eE]', u)[0]
            last = 10.0 ** (-len(mant.split('.')[1]) if '.' in mant else 0)
            if re.search('[eE]', u):
                last *= 10.0 ** int(re.split('[eE]', u)[1])
            if abs(fu - fv) > max(1.0000001 * last, 1e-6, 1e-2 * abs(fu)):
                bad.append(i + 1)
                break
    return not bad, (f'{len(la)} lines, {nnum} numbers, {ndiff} differ in print; {len(bad)} lines outside'
                     + (f' (first: line {bad[0]})' if bad else ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default=str(PKG / '.work' / 'replay_full'))
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--out', default=str(PKG / '.work' / 'replay_full_c2cyl.txt'))
    a = ap.parse_args()
    T = L.Table('c2_cylinder_d2 replay-full (continuum analysis rerun from the raw records)')
    work = Path(a.work).resolve()
    out = work / 'continuum_2026-10'
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    ship_gen = current_generation()
    ship = {f: load_json(ship_gen / f) for f in FILES}
    dev = RESULTS / 'evidence' / 'DEVIATIONS_ANALYSIS.md'
    cmd = [a.python, 'scripts/run.py', 'continuum', '--', 'run',
           '--records', 'outputs/merged_production_plan_20261013.json',
           '--diagnostic-records', 'outputs/merged_analysis_checks_plan_20261013.json',
           'outputs/merged_analysis_checks_plan_rev6_20261014.json',
           '--aux-dir', 'outputs/symmetry/c2aux_574247',
           '--legacy-receipt', 'results/continuum_2026-10/evidence/legacy_macos/legacy_reproduction.json',
           '--deviations', str(dev.relative_to(PKG)),
           '--output', str(out)]
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    t0 = time.time()
    r = subprocess.run(cmd, cwd=PKG, env=env, capture_output=True, text=True)
    (work / 'driver.log').write_text(r.stdout + r.stderr)
    T.check('continuum driver run', r.returncode == 0, f'exit {r.returncode}, {time.time() - t0:.0f} s',
            'exit 0', 'scripts/run.py continuum -- run ... (the driver verifies every input hash); log in <work>/driver.log')
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit(T.report(a.out))
    new_gen = current_generation(out)
    new = {f: load_json(new_gen / f) for f in FILES}
    vers = subprocess.run([a.python, '-c', 'import sys, platform, numpy; print(sys.version.split()[0], numpy.__version__, '
                           'platform.machine())'], capture_output=True, text=True).stdout.strip()

    si, ni = norm_inputs(ship['C2_estimate.json']['meta']['inputs_sha256']), norm_inputs(new['C2_estimate.json']['meta']['inputs_sha256'])
    same = set(si) == set(ni) and all(si[k] == ni[k] for k in si)
    T.check('inputs (files and sha256)', same, f'{len(ni)} inputs' + ('' if same else f'; differ: {sorted(set(si) ^ set(ni))[:3]}'
            + str([k for k in set(si) & set(ni) if si[k] != ni[k]][:3])),
            f'{len(si)} inputs of the shipped meta.inputs_sha256', 'deviation record matched by name')
    nfl = nbit = 0
    for f in FILES:
        c = compare(ship[f], new[f], f)
        nfl += c['floats']; nbit += c['bitid']
        T.check(f, not c['bad'], f"{c['discrete']} discrete leaves equal; {c['floats']} floats: {c['bitid']} bit-identical, "
                f"tier A {c['A']} differ (max {c['maxA']:.1e}{' at ' + c['maxA_at'] if c['maxA_at'] else ''}), tier B "
                f"{c['B']} differ (max rel {c['maxB']:.1e}); {len(c['bad'])} outside"
                + (f" (first: {c['bad'][0][:140]})" if c['bad'] else ''),
                'discrete equal; tier A 1e-7 abs; tier B 1e-6 + 1e-3|x| (conditions 1e-2 rel)', 'shipped vs rerun generation')
    T.add('bit-identical floats', 'INFO', f'{nbit} of {nfl}', 'all on the production platform (macOS arm64, CPython '
          '3.13.5, numpy 2.3.5)', f'this run: python {vers}')
    ok, how = compare_report((ship_gen / 'REPORT.md').read_text(), (new_gen / 'REPORT.md').read_text(),
                             ship_gen.name, new_gen.name)
    T.check('REPORT.md', ok, how, 'same text; numbers within 1 unit of the last printed digit, 1e-6 abs or 1e-2 rel',
            'run-description line (python/platform) and generation name masked')
    fin = new['C2_estimate.json']['final']
    Q, _ = quoted_entries()
    e = Q['\\SRtwoCtwoHT']
    ok, how = matches_paren(fin['C2'], fin['dC2'], e['text'])
    T.add('\\SRtwoCtwoHT (rerun)', 'PASS' if ok else 'FAIL', f"{fin['C2']:.10f} +- {fin['dC2']:.10f} [{how}]", e['text'],
          'rerun C2 and dC2 rounded half-up to the printed digits')
    nmax = max(q['N'] for q in new['continuum_points.json']['primary_points'])
    T.quoted(Q['\\SRtwoCtwoHTNmax'], [nmax], 'largest N of the rerun PRIMARY points')
    T.check('outcome', fin['label'] == 'extraction coverage complete' and new['C2_estimate.json']['outcome']['branch'] == 4,
            f"branch {new['C2_estimate.json']['outcome']['branch']}, {fin['label']}", 'branch 4, coverage complete',
            'pre-declared outcome table')
    r = subprocess.run([a.python, 'code/continuum/continuum_driver.py', 'check', '--output', str(out)], cwd=PKG, env=env,
                       capture_output=True, text=True)
    T.check('driver check (work output)', r.returncode == 0 and 'CONSISTENT' in r.stdout,
            r.stdout.strip().replace(str(work), '<work>').replace('\n', '; '), 'CONSISTENT',
            'top-level copies equal the CURRENT generation')
    sys.exit(T.report(a.out))


if __name__ == '__main__':
    main()
