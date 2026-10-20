#!/usr/bin/env python3
"""SEALED COMPARISON STEP: independence-hygiene check of the definitions-only spec.

1. Runtime audit.  Copies spec/scripts, spec/review/*.json and nothing else into a scratch
   directory (so spec/comparison does not exist there), reruns the whole archive-free
   pipeline with a Python audit hook that records every file opened, and FAILS if any
   opened path lies inside the compendium or inside a 'comparison' directory.  The fresh
   outputs must be byte-identical to spec/out/*.json, spec_definitions.json, spec.json, spec.md.
2. Static scan.  The production scripts (spec/scripts/*.py) may not contain a numeric literal
   whose first 12 significant digits match an archive number.
3. Fingerprint scan.  Every number with >= 12 significant digits in spec_definitions.json,
   spec.json, spec.md and spec/out/*.json that matches an archive number (first 12 significant
   digits) must be one of OUR archive-free values: a closed form re-evaluated here from its
   'exact' string, or an entry tagged independent-numeric.  Anything else is a leak.
Output: ../sealing_report.json
"""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import sympy as s
import mpmath as mp

HERE = Path(__file__).resolve().parent
CMP = HERE.parent
SPEC = CMP.parent
COMP = '<PROJECT>/LRI_SRI_research_compendium'
PIPELINE = ['derive_requirements.py', 'two_kink_exact.py', 'derive_invariants.py', 'check_closed_forms.py',
            'sanity_finite_cutoff.py', 'validation_targets.py',
            # C8 extension (2026-10-03): its archive-free scripts feed build_spec.py (block C8_EXTENSION)
            'derive_requirements_C8.py', 'two_kink_exact_C8.py', 'derive_invariants_C8.py', 'rg_logs_C8.py', 'poles_C8.py',
            'budget_C8.py', 'validation_targets_C8.py',
            'build_spec.py', 'make_spec_md.py']
WRAP = r'''
import sys, os, json, atexit, runpy
opened = []
def hook(ev, args):
    if ev in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], (str, bytes, os.PathLike)):
        try:
            opened.append(os.path.realpath(os.fsdecode(args[0])))   # realpath: /var vs /private/var (gate fix)
        except Exception:
            pass
sys.addaudithook(hook)
log = sys.argv[2]
atexit.register(lambda: json.dump(sorted(set(opened)), open(log, 'w')))
script = sys.argv[1]
sys.argv = [script]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name='__main__')
'''
report = {}

# ------------------------------------------------------------------ 1. runtime audit in a scratch copy
tmp = Path(tempfile.mkdtemp(prefix='spec_sealing_', dir=os.environ.get('TMPDIR'))).resolve()   # gate fix: compare resolved paths
try:
    shutil.copytree(SPEC / 'scripts', tmp / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    (tmp / 'out').mkdir()
    (tmp / 'out' / 'C8').mkdir()
    (tmp / 'review').mkdir()
    for f in (SPEC / 'review').glob('*.json'):
        shutil.copy(f, tmp / 'review' / f.name)
    (tmp / 'wrap.py').write_text(WRAP)
    violations, per_script = [], {}
    for sc in PIPELINE:
        log = tmp / f'{sc}.opened.json'
        r = subprocess.run([sys.executable, str(tmp / 'wrap.py'), str(tmp / 'scripts' / sc), str(log)],
                           cwd=tmp / 'scripts', capture_output=True, text=True)
        opened = json.load(open(log)) if log.exists() else []
        bad = [p for p in opened if p.startswith(COMP) or p.startswith(str(CMP)) or p.startswith(str(SPEC / 'comparison_C8'))
               or (p.startswith(str(tmp)) and '/comparison' in p)]
        local = sorted({os.path.relpath(p, tmp) for p in opened if p.startswith(str(tmp)) and not p.endswith('.opened.json')
                        and '__pycache__' not in p and not p.endswith('.py')})
        per_script[sc] = {'returncode': r.returncode, 'data_files_opened': local, 'forbidden_opened': bad}
        violations += bad
        if r.returncode != 0:
            violations.append(f'{sc} failed: {r.stderr[-400:]}')
    same = {}
    for rel in ([f'out/{p.name}' for p in sorted((SPEC / 'out').glob('*.json')) if not p.is_symlink()]
                + [f'out/C8/{p.name}' for p in sorted((SPEC / 'out' / 'C8').glob('*.json'))]
                + ['spec_definitions.json', 'spec.json', 'spec.md']):
        a, b = SPEC / rel, tmp / rel
        same[rel] = b.exists() and a.read_bytes() == b.read_bytes()
    report['runtime_audit'] = {'scripts': per_script, 'violations': violations,
                               'compat_symlinks_in_out_not_produced_by_pipeline': [p.name for p in (SPEC / 'out').glob('*') if p.is_symlink()],
                               'fresh_outputs_byte_identical': same, 'pass': not violations and all(same.values())}
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print('runtime audit pass:', report['runtime_audit']['pass'], flush=True)

# ------------------------------------------------------------------ archive fingerprints
NUM_RE = re.compile(r'-?\d+\.\d+(?:[eE][-+]?\d+)?')


def fp(txt):
    d = re.sub(r'[eE].*$', '', txt).lstrip('-').replace('.', '').lstrip('0')
    return d[:12] if len(d) >= 12 else None


ARCH = {}
for f in ('archive_comparison.json', 'archive_inputs.json', 'archive_raw_coefficients.json', 'archive_normalized_atoms.json'):
    for m in NUM_RE.finditer((CMP / f).read_text()):
        k = fp(m.group(0))
        if k and set(k) != {'0'}:
            ARCH.setdefault(k, f)
report['archive_fingerprints'] = len(ARCH)

# ------------------------------------------------------------------ 2. static literal scan of production scripts
lit = []
for f in sorted((SPEC / 'scripts').glob('*.py')):
    for m in NUM_RE.finditer(f.read_text()):
        k = fp(m.group(0))
        if k and k in ARCH:
            lit.append(f'{f.name}: {m.group(0)}')
report['production_script_literals_matching_archive'] = lit

# ------------------------------------------------------------------ 3. fingerprint scan of the archive-free outputs
mp.mp.dps = 60
z = s.symbols('z2 z3 z4 z5 z6 L2 L3 Li2h Li4h')
CONST = dict(zip(map(str, z), [mp.zeta(2), mp.zeta(3), mp.zeta(4), mp.zeta(5), mp.zeta(6), mp.log(2), mp.log(3),
                               mp.polylog(2, -mp.mpf(1) / 2), mp.polylog(4, mp.mpf(1) / 2)]))
vt = json.load(open(SPEC / 'out' / 'validation_targets.json'))
ours = []
for t in vt['targets']:
    ex = s.sympify(t['exact'], locals={k: s.Symbol(k) for k in CONST})
    syms = sorted(ex.free_symbols, key=str)
    ours.append(mp.mpf(s.lambdify(syms, ex, 'mpmath')(*[CONST[str(x)] for x in syms])) if syms else mp.mpf(s.Rational(ex).p) / s.Rational(ex).q)
inv = json.load(open(SPEC / 'out' / 'invariants.json'))
ours += [mp.mpf(v) for v in inv['claims_value_60'].values()]
INDEP = [mp.mpf(r['value']) for r in vt['independent_input_values']] + \
        [mp.mpf(f['value']) for f in vt['finite_cutoff']['independent_values']]
# C8 extension: archive-free values of out/C8/validation_targets_C8.json (closed forms evaluated here, independent numerics)
vt8p = SPEC / 'out' / 'C8' / 'validation_targets_C8.json'
if vt8p.exists():
    vt8 = json.load(open(vt8p))
    INDEP += [mp.mpf(t_['value']) for t_ in vt8['targets'] if t_.get('value') not in (None, 'None')]
    INDEP += [mp.mpf(r['value']) for r in vt8['independent_values']]


def explained(x):
    x = mp.mpf(x)
    tol = mp.mpf(10)**-11 * (1 + abs(x))
    if any(abs(x - y) < tol for y in ours):
        return 'closed-form (re-evaluated here)'
    if any(abs(x - y) < tol for y in INDEP):
        return 'independent-numeric (tagged)'
    return None


leaks, explained_hits = [], {}
files = [SPEC / 'spec_definitions.json', SPEC / 'spec.json', SPEC / 'spec.md'] + \
        [p for p in sorted((SPEC / 'out').glob('*.json')) if not p.is_symlink()] + sorted((SPEC / 'out' / 'C8').glob('*.json'))
for f in files:
    for m in NUM_RE.finditer(f.read_text()):
        k = fp(m.group(0))
        if not k or k not in ARCH:
            continue
        why = explained(m.group(0))
        rel = str(f.relative_to(SPEC))
        if why is None:
            leaks.append(f'{rel}: {m.group(0)}')
        else:
            explained_hits.setdefault(rel, {}).setdefault(why, 0)
            explained_hits[rel][why] += 1
report['fingerprint_scan'] = {'files': [str(f.relative_to(SPEC)) for f in files], 'leaks': leaks,
                              'matches_explained_by_our_own_values': explained_hits}
report['PASS'] = report['runtime_audit']['pass'] and not lit and not leaks
json.dump(report, open(CMP / 'sealing_report.json', 'w'), indent=1)
print('literals', lit, 'leaks', leaks[:10], 'explained', explained_hits)
print('PASS', report['PASS'])
