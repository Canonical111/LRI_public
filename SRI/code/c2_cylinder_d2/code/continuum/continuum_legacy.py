"""Recorded-legacy mode (PLAN_ANALYSIS.md A1; rev 6 A6-2 and rev 7 R6-001).

Runs the UNMODIFIED historical scripts of code/hamiltonian on the archived
records, in a temporary staged directory, under the recorded-legacy policy:
  * tail_transseries_fit.py sees only the 11 historically available N=256 cases
    (order 3, lambda 0.35 absent), so final_analysis.py takes its documented
    raw-power-fit fallback for that point;
  * analyze_extended.py regenerates the N=384 analysis (truncated-SVD lstsq,
    rcond=1e-13, ill-conditioned fits kept);
  * final_analysis.py assembles FINAL_NUMERICAL_RESULTS.json (saturated
    order-2/3 regulator fits kept).
None of the new rank, dof or acceptance guards is applied here.

Two checks (A1):
  * same platform (A6-2): the identical policy is run on the scripts and data of
    the pristine commit 474487c (git archive), on the same machine and
    interpreter; all three JSONs must be byte-identical to the legacy outputs;
  * cross platform (R6-001), against data/hamiltonian/reference: every leaf is
    classified -- exact (discrete metadata, case availability, counts, term
    sets, lambda grids and powers), fitted value or residual (1e-4 absolute),
    representative C2 (1e-8), condition number (reported; gated at 10%
    relative) -- and a leaf that fits no category fails. Byte identity with
    the reference is asserted only with C2_LEGACY_EXPECT_BITWISE=1.
"""
from __future__ import annotations

import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
REFERENCE = PKG / 'data' / 'hamiltonian' / 'reference'
FILES = ('tail_transseries_fits.json', 'extended_analysis.json', 'FINAL_NUMERICAL_RESULTS.json')
HISTORICALLY_MISSING_TAIL_CASES = ('fine_k3_a0.35.json',)
PRISTINE_COMMIT = '474487c'

TOL_VALUE = 1e-4                  # fitted values and residuals, absolute
TOL_REPRESENTATIVE_C2 = 1e-8      # representative C2, absolute
TOL_CONDITION_REL = 0.10          # condition numbers, relative (reported; gate only)
# Floats that are discrete metadata (inputs copied through, compared exactly).
EXACT_FLOAT_SUFFIXES = ('/lam', '/powers[]', '/lambdas[]')
# Fitted values and copied numerical inputs, compared within TOL_VALUE.
VALUE_SUFFIXES = (
    '/limit', '/last', '/mixed_spread', '/h_estimate', '/spectral_model_half_spread', '/spectral_model_values[]',
    '/h0', '/C2', '/coefficients[]', '/spectral_half_spread_linear_L1',
    '/selected/half_spread', '/selected/maximum', '/selected/median', '/selected/minimum', '/selected/values[]',
    '/tail/asymptotic_tail_coefficient', '/tail/face_sum', '/tail/middle_adjacent', '/tail/middle_nested',
    '/tail/outer', '/cauchy_grid_comparison/maximum_overlap_difference',
    '/cauchy_grid_comparison/overlap_last_difference')


HISTORICAL_TAIL_CUTOFF = '2048'   # the literal of the pristine 474487c scripts (exact_leading_tail.py, etc.)


def _env(work: Path) -> dict:
    """Environment of the unchanged historical commands (scripts/run.py analyze / analyze-recorded):
    inherits the caller's settings, as those commands always have."""
    return dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
                PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg', MPLCONFIGDIR=str(work / '.mpl'))


def _legacy_env(work: Path) -> dict:
    """Environment of the recorded-legacy policy runs (IR2-003): the historical tail cutoff 2048 is forced, so an
    inherited LRI_TAIL_CUTOFF (the scripts at HEAD read it; the pristine 474487c scripts use the literal 2048)
    cannot change the policy."""
    return dict(_env(work), LRI_TAIL_CUTOFF=HISTORICAL_TAIL_CUTOFF)


def _stage(work: Path, root: Path = PKG, exclude: tuple[str, ...] = ()) -> None:
    """Copy root's code/hamiltonian/*.py and data/hamiltonian/{raw,auxiliary}/*.json into a flat work dir."""
    work.mkdir(parents=True)
    for p in (root / 'code' / 'hamiltonian').glob('*.py'):
        shutil.copy2(p, work / p.name)
    for group in ('raw', 'auxiliary'):
        for p in (root / 'data' / 'hamiltonian' / group).glob('*.json'):
            if p.name not in exclude:
                shutil.copy2(p, work / p.name)


def _run(python: str, work: Path, script: str) -> None:
    subprocess.run([python, script], cwd=work, env=_legacy_env(work), check=True, stdout=subprocess.DEVNULL)


def run_policy(root: Path, output: Path, python: str) -> None:
    """The recorded-legacy policy on the scripts and data under root; writes the three JSONs to output."""
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='c2legacy_') as d:
        base = Path(d)
        tail = base / 'tail'
        _stage(tail, root, exclude=HISTORICALLY_MISSING_TAIL_CASES)
        _run(python, tail, 'tail_transseries_fit.py')
        final = base / 'final'
        _stage(final, root)
        _run(python, final, 'analyze_extended.py')
        shutil.copy2(tail / 'tail_transseries_fits.json', final / 'tail_transseries_fits.json')
        _run(python, final, 'final_analysis.py')
        for name in FILES:
            shutil.copy2(final / name, output / name)


def extract_pristine(dest: Path, commit: str = PRISTINE_COMMIT) -> Path:
    """git archive of the pristine commit's code/hamiltonian and data/hamiltonian into dest; returns its root."""
    dest.mkdir(parents=True, exist_ok=True)
    arch = subprocess.run(['git', '-C', str(PKG), 'archive', '--format=tar', commit, 'code/hamiltonian',
                           'data/hamiltonian'], check=True, capture_output=True).stdout
    subprocess.run(['tar', '-x', '-C', str(dest)], input=arch, check=True)
    return dest


def leaves(x, path=''):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f'{path}/{k}')
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f'{path}[{i}]')
    else:
        yield path, x


def categorize(path: str, value) -> str:
    gpath = re.sub(r'\[\d+\]', '[]', path)
    if not isinstance(value, float):
        return 'exact'                                   # str, int, bool, None: discrete metadata
    if gpath.endswith('/representative_regulator_fits[]/C2'):
        return 'representative_C2'
    if gpath.endswith('/condition'):
        return 'condition'
    if gpath.endswith('/max_residual'):
        return 'residual'
    if gpath.endswith(EXACT_FLOAT_SUFFIXES):
        return 'exact'
    if gpath.endswith(VALUE_SUFFIXES):
        return 'value'
    return 'unclassified'


def compare(ref_path: Path, new_path: Path) -> dict:
    """R6-001: category-wise comparison against the shipped reference."""
    a_bytes, b_bytes = ref_path.read_bytes(), new_path.read_bytes()
    a, b = dict(leaves(json.loads(a_bytes))), dict(leaves(json.loads(b_bytes)))
    out = dict(file=ref_path.name, bytes_identical=a_bytes == b_bytes, structure_identical=list(a) == list(b),
               leaves=len(a))
    if list(a) != list(b):
        out.update(missing=sorted(set(a) - set(b))[:20], extra=sorted(set(b) - set(a))[:20], passed=False)
        return out
    cats: dict[str, dict] = {}
    failures = []
    for k in a:
        x, y = a[k], b[k]
        c = categorize(k, x)
        st = cats.setdefault(c, dict(leaves=0, differing=0, max_abs=0.0, max_rel=0.0, worst=None))
        st['leaves'] += 1
        if type(x) is not type(y):
            failures.append(f'{k}: type {type(x).__name__} -> {type(y).__name__}')
            continue
        if isinstance(x, float) and not (math.isfinite(x) and math.isfinite(y)):
            # R004: a NaN or infinity makes every tolerance comparison false; it is an explicit failure instead.
            st['non_finite'] = st.get('non_finite', 0) + 1
            failures.append(f'{k}: non-finite numerical leaf (reference {x!r}, legacy {y!r})')
            continue
        if c == 'unclassified':
            failures.append(f'{k}: unclassified leaf')
            continue
        if x == y:
            continue
        st['differing'] += 1
        if c == 'exact':
            failures.append(f'{k}: exact leaf differs ({x!r} -> {y!r})')
            continue
        d = abs(x - y)
        r = d / abs(x) if x else math.inf
        if d > st['max_abs']:
            st['max_abs'], st['worst'] = d, k
        st['max_rel'] = max(st['max_rel'], r)
        if c in ('value', 'residual') and d > TOL_VALUE:
            failures.append(f'{k}: {c} differs by {d:.3e} > {TOL_VALUE}')
        elif c == 'representative_C2' and d > TOL_REPRESENTATIVE_C2:
            failures.append(f'{k}: representative C2 differs by {d:.3e} > {TOL_REPRESENTATIVE_C2}')
        elif c == 'condition' and r > TOL_CONDITION_REL:
            failures.append(f'{k}: condition number differs by {100 * r:.2f}% > {100 * TOL_CONDITION_REL:.0f}%')
    out.update(categories=cats, failures=failures[:50], n_failures=len(failures), passed=not failures)
    return out


def _versions(python: str) -> dict:
    """numpy/scipy versions of the interpreter that ran the legacy scripts."""
    code = 'import json,numpy,scipy;print(json.dumps(dict(numpy=numpy.__version__,scipy=scipy.__version__)))'
    out = subprocess.run([python, '-c', code], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def run_legacy(output: Path, python: str = sys.executable, pristine: bool = True) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    run_policy(PKG, output, python)
    cases = [(r['order'], r['lam']) for r in json.loads((output / FILES[0]).read_text())]
    final_obj = json.loads((output / FILES[2]).read_text())
    rep = dict(
        policy={'tail_transseries_cases': cases, 'historically_missing': list(HISTORICALLY_MISSING_TAIL_CASES),
                'guards_applied': False, 'tail_cutoff_forced': HISTORICAL_TAIL_CUTOFF,
                'order 3, lambda 0.35 source': 'final_analysis.py raw-power-fit fallback (no transseries entry)'
                if [3, 0.35] not in [list(c) for c in cases] else 'transseries'},
        platform=dict(python=sys.version, platform=platform.platform(), machine=platform.machine(),
                      **_versions(python)),
        tolerances=dict(value_and_residual_abs=TOL_VALUE, representative_C2_abs=TOL_REPRESENTATIVE_C2,
                        condition_rel_gate=TOL_CONDITION_REL, unclassified='fails'),
        comparisons=[compare(REFERENCE / n, output / n) for n in FILES],
        representative=[dict(order=p['order'], h0=p['h0'], C2=p['C2'], points=p['number_of_points'],
                             parameters=p['number_of_parameters'])
                        for p in final_obj['representative_regulator_fits']])
    ref = json.loads((REFERENCE / FILES[2]).read_text())
    rep['representative_minus_reference'] = [
        dict(order=x['order'], h0=x['h0'] - y['h0'], C2=x['C2'] - y['C2'])
        for x, y in zip(final_obj['representative_regulator_fits'], ref['representative_regulator_fits'])]
    if pristine:
        with tempfile.TemporaryDirectory(prefix='c2pristine_') as d:
            root = extract_pristine(Path(d) / 'tree')
            prist_out = Path(d) / 'out'
            run_policy(root, prist_out, python)
            rep['same_platform_pristine'] = dict(
                commit=PRISTINE_COMMIT, policy='identical 11-case recorded policy',
                bytes_identical={n: (prist_out / n).read_bytes() == (output / n).read_bytes() for n in FILES})
    rep['summary'] = dict(
        same_platform_pristine_bytes_identical=rep.get('same_platform_pristine', {}).get('bytes_identical'),
        cross_platform_passed={c['file']: c.get('passed') for c in rep['comparisons']},
        bytes_identical_to_reference={c['file']: c['bytes_identical'] for c in rep['comparisons']},
        structure_identical={c['file']: c['structure_identical'] for c in rep['comparisons']},
        max_abs_value_difference={c['file']: c.get('categories', {}).get('value', {}).get('max_abs', 0.0)
                                  for c in rep['comparisons']},
        max_rel_condition_difference={c['file']: c.get('categories', {}).get('condition', {}).get('max_rel', 0.0)
                                      for c in rep['comparisons']},
        max_abs_representative_C2_difference=max(abs(x['C2']) for x in rep['representative_minus_reference']))
    (output / 'legacy_reproduction.json').write_text(json.dumps(rep, indent=1) + '\n')
    return rep


def historical_commands(python: str, work: Path) -> dict[str, Path]:
    """Run the unchanged `scripts/run.py analyze` and `analyze-recorded` (same interpreter)."""
    outs = {}
    for cmd in ('analyze', 'analyze-recorded'):
        out = work / cmd
        subprocess.run([python, str(PKG / 'scripts' / 'run.py'), cmd, '--output', str(out)], cwd=PKG,
                       env=_env(work), check=True, stdout=subprocess.DEVNULL)
        outs[cmd] = out
    return outs
