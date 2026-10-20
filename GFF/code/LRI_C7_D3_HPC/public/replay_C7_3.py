#!/usr/bin/env python3
"""Replay every published C7(3) number from the shipped records, without rerunning production.

Run from GFF/code/LRI_C7_D3_HPC (the package folder):

    python3 public/replay_C7_3.py [--results ../../results/C7_3] [--out .work/replay] [--full-run DIR]

What it does (pure Python: numpy only; no compiler, no hosted data):
  1. Identity. The run1 manifest, the 20 group configs and merged replicate records are checked against each other and
     against C7_result.json (the hashes the production tools wrote). The manifest's tool hashes must equal the shipped
     production code (git commit 4de9412), its inputs-manifest hash the shipped inputs/manifest.json.
  2. Production assembly. tools/assemble.py of the production commit (4de9412) recomputes C7_result.json from the merged
     replicate arrays (calculate(..., bootstrap=4096)); every field is compared with the record.
  3. Gates. tools/assemble.py of commit a6ce987 (reverify_a6ce987/, the re-verification tool of the results review)
     recomputes the assembly and its consistency gates; they are compared with run1_report_bb9d2ca.json.
  4. Every number the condensed note quotes for C7(3) (abstract, Section 1, Section 26.7, Section 29) is recomputed from
     these records, the shipped previous-calculation records (reference/verification, reference/README.md) and the
     cited review evidence (results/C7_3/evidence), and compared at the printed precision.

Tolerances. Recomputed floats must equal the records bit for bit on the CPU type that produced them (AMD EPYC
7532/7543, AVX2). Elsewhere the float64 assembly may differ in the last bits (NumPy/OpenBLAS SIMD paths; 4 ulp were
seen on an AVX-512 node), so the comparison accepts a relative difference of 1e-12 for C7, its SE and the
coefficient vector (as tools/report.py does) and 1e-10, scaled by the largest entry of the containing vector, for every
other float (as assemble.rounding_difference of a6ce987 does). Quoted numbers must agree with the recomputed values to
half a unit of the last printed digit. Rows marked CITED rest on a record that is not recomputable from shipped files
(the source is named); SKIP means an input from `make fetch-data` is missing.

Writes OUT/REPLAY.md and OUT/replay.json, prints the table, and exits 1 if any row FAILs.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, subprocess, sys
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REV = PKG / 'reverify_a6ce987'
RUN_NAME = 'run1-20260930-m4096'
EXISTING_REL = 1e-12   # tools/report.py (a6ce987): C7, SE and coefficients on another CPU type
ROUNDING_REL = 1e-10   # assemble.ROUNDING_REL (a6ce987): every other float, scaled by its vector


# ----------------------------------------------------------------------------------------------- helpers
def sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(',', ':'), allow_nan=False)


def object_hash(o) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def load(p: Path):
    return json.loads(Path(p).read_text())


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def maxrel(a, b, scale=0.0):
    """Largest relative float difference of two JSON trees with identical structure, identical non-float leaves and
    equal integers; None otherwise. Floats compare as |a-b| / max(|a|, |b|, scale), scale = largest magnitude in the
    innermost containing list (as assemble._rounding of a6ce987)."""
    if _num(a) and _num(b):
        if type(a) is int and type(b) is int:
            return 0.0 if a == b else None
        if a == b:
            return 0.0
        m = max(abs(a), abs(b), scale)
        return abs(a - b) / m if m > 0 else None
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return None
        w = 0.0
        for k in a:
            d = maxrel(a[k], b[k])
            if d is None:
                return None
            w = max(w, d)
        return w
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return None
        sc = max([abs(x) for x in a + b if _num(x)], default=0.0)
        w = 0.0
        for x, y in zip(a, b):
            d = maxrel(x, y, sc)
            if d is None:
                return None
            w = max(w, d)
        return w
    return 0.0 if (type(a) == type(b) and a == b) else None


def compare_result(rec: dict, r: dict, keys) -> tuple[bool, float]:
    """Recorded vs recomputed assembly fields (see the module docstring for the tolerances). The bootstrap bias is the
    difference of two quantities of the size of the coefficients, so it is judged on the coefficient scale."""
    worst, ok = 0.0, True
    for k in keys:
        a, b = rec.get(k), r[k]
        if k == 'bootstrap' and isinstance(a, dict) and isinstance(b, dict):
            scale = max(abs(x) for x in rec['coefficients'])
            d = maxrel({kk: v for kk, v in a.items() if kk != 'bias'}, {kk: v for kk, v in b.items() if kk != 'bias'})
            db = max(abs(x - y) for x, y in zip(a['bias'], b['bias'])) / scale if len(a['bias']) == len(b['bias']) else None
            d = None if d is None or db is None else max(d, db)
        elif k == 'campaigns' and isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
            # a6ce987 adds top_order/top_estimate/top_sampling_se; the delivered record has C7 and sampling_se only
            d = maxrel({t: {kk: a[t][kk] for kk in a[t]} for t in a}, {t: {kk: b[t][kk] for kk in a[t]} for t in a})
        else:
            d = maxrel(a, b)
        tol = EXISTING_REL if k in ('C7_full', 'sampling_standard_error', 'coefficients') else ROUNDING_REL
        if d is None or d > tol:
            ok = False
        worst = max(worst, d if d is not None else float('inf'))
    return ok, worst


ROWS = []


def row(rid, where, quantity, quoted, computed, status, detail=''):
    ROWS.append(dict(id=rid, where=where, quantity=quantity, quoted=str(quoted), computed=str(computed),
                     status=status, detail=detail))


def check(rid, where, quantity, ok, quoted, computed, detail=''):
    row(rid, where, quantity, quoted, computed, 'PASS' if ok else 'FAIL', detail)


def printed(rid, where, quantity, quoted: str, value: float, detail=''):
    """PASS if value rounds to the quoted string: |value - quoted| <= half a unit of its last printed digit."""
    q = Decimal(quoted)
    half = Decimal(5) * Decimal(10) ** (q.as_tuple().exponent - 1)
    v = Decimal(repr(float(value)))
    slack = abs(v) * Decimal('1e-12')          # last-bit noise of another CPU type
    ok = abs(v - q) <= half + slack
    check(rid, where, quantity, ok, quoted, f'{float(value):.12g}', detail or f'tolerance {half} (half unit of the last printed digit)')


def cited(rid, where, quantity, quoted, source):
    row(rid, where, quantity, quoted, '-', 'CITED', source)


def ceil_to(x: float, step: str) -> Decimal:
    s = Decimal(step)
    return (Decimal(repr(x)) / s).to_integral_value(rounding=ROUND_CEILING) * s


# ----------------------------------------------------------------------------------------------- assembly stages
def stage(kind: str, run: Path, out: Path) -> None:
    """Runs in its own interpreter: the production commit and a6ce987 both have tools/assemble.py and tools/common.py."""
    tools = (PKG if kind == 'production' else REV) / 'tools'
    sys.path.insert(0, str(tools))
    sys.dont_write_bytecode = True
    import numpy as np
    import assemble
    m = json.loads((run / 'manifest.json').read_bytes())
    if m['primitive_mode'] != 'recompute':
        raise SystemExit('unexpected primitive mode')
    ar = {s: {t: {} for t in 'ab'} for s in ('free', 'power')}
    for g in m['groups']:
        cfg = load(run / 'groups' / g['name'] / 'config.json')
        d = load(run / 'groups' / g['name'] / 'merged.json')
        ar[cfg['sector']][cfg['campaign']][cfg['L']] = np.asarray(d['batches'], float)
    doc = {'numpy': np.__version__, 'python': sys.version.split()[0], 'tools': str(tools.relative_to(PKG))}
    if kind == 'production':
        r = assemble.calculate(ar, None, 4096)
        doc['result'] = r
        means = {L: np.asarray(r['means']['free'][str(L)]) + np.asarray(r['means']['power'][str(L)]) for L in range(3, 8)}
        J = assemble.jacobians(means)
        doc['dC7_db70'] = float(J[7][7, 0])
        doc['dC7_dc70'] = float(J[7][7, 1])
        xa, xb = ar['power']['a'][3][:, 0], ar['power']['b'][3][:, 0]
        doc['b3p'] = float((xa.mean() + xb.mean()) / 2)
        doc['b3p_se'] = float(math.sqrt((xa.var(ddof=1) / len(xa) + xb.var(ddof=1) / len(xb)) / 4))
    else:
        vi = assemble.verified_inputs(m['inputs_manifest_sha256'])
        refs, rsha = assemble.references()
        r = assemble.calculate(ar, None, 4096, vi['B2'])
        doc.update(result=r, checks=assemble.gate_checks(r, refs), references_sha256=rsha, input_sha256=vi['sha256'])
    out.write_text(json.dumps(doc, allow_nan=False))


def run_stage(kind: str, run: Path, out: Path) -> dict:
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--stage', kind, '--run', str(run), '--stage-out', str(out)],
                   check=True, env=env)
    return load(out)


# ----------------------------------------------------------------------------------------------- main replay
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results', type=Path, default=PKG / '../../results/C7_3')
    ap.add_argument('--out', type=Path, default=PKG / '.work/replay')
    ap.add_argument('--full-run', type=Path, help='the extracted run directory of run1-20260930-m4096_full.tgz (make reverify)')
    ap.add_argument('--stage', choices=('production', 'reverify'), help=argparse.SUPPRESS)
    ap.add_argument('--run', type=Path, help=argparse.SUPPRESS)
    ap.add_argument('--stage-out', type=Path, help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.stage:
        stage(a.stage, a.run, a.stage_out)
        return 0
    if sys.version_info < (3, 10):
        sys.exit('Python >= 3.10 is required (the re-verification tool of a6ce987 needs it)')
    res = a.results.resolve()
    run = res / RUN_NAME
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    REF = PKG / 'reference'

    # ------------------------------------------------------------------ 1. identity of the shipped records
    W = 'records'
    mbytes = (run / 'manifest.json').read_bytes()
    m = json.loads(mbytes)
    mh = hashlib.sha256(mbytes).hexdigest()
    rec = load(run / 'C7_result.json')
    check('id.manifest', W, 'run1 manifest sha256 = C7_result.source_manifest_sha256',
          mh == rec['source_manifest_sha256'] == 'eefa84326816ae9307885eccb53863a2ac96c02f14c875843affa853ae885274',
          'eefa8432...', mh[:16] + '...')
    tools_ok = all(sha(PKG / 'tools' / n) == h for n, h in m['tool_sha256'].items())
    check('id.tools', W, 'manifest tool_sha256 = shipped tools/ (production commit 4de9412)', tools_ok,
          ', '.join(sorted(m['tool_sha256'])), 'equal' if tools_ok else 'DIFFERENT')
    inm = sha(PKG / 'inputs/manifest.json')
    check('id.inputs', W, 'manifest inputs_manifest_sha256 = shipped inputs/manifest.json', inm == m['inputs_manifest_sha256'],
          m['inputs_manifest_sha256'][:16] + '...', inm[:16] + '...')
    im = load(PKG / 'inputs/manifest.json')
    small = ('two_loop.json', 'gamma_d3_7.txt', 'primitive_reference.json', 'inventory.json')
    check('id.inputs_files', W, 'inputs/{two_loop,gamma_d3_7,primitive_reference,inventory} match inputs/manifest.json',
          all(sha(PKG / 'inputs' / n) == im['sha256'][n] for n in small), 'sha256 listed', 'checked')
    packs = sorted(k for k in im['sha256'] if k.startswith('packs/'))
    have = [k for k in packs if (PKG / 'inputs' / k).exists()]
    if len(have) == len(packs):
        check('id.packs', W, 'inputs/packs/*.pack match inputs/manifest.json', all(sha(PKG / 'inputs' / k) == im['sha256'][k] for k in packs),
              f'{len(packs)} packs', 'checked')
    else:
        row('id.packs', W, 'inputs/packs/*.pack match inputs/manifest.json', f'{len(packs)} packs', f'{len(have)} present', 'SKIP',
            'restored by make -f public.mk setup from public/kernels/inputs_packs.tar.gz; not needed by the replay')
    cm = REV / 'cost_models/gmp_symmetry_epyc7532.json'
    check('id.cost_model', W, 'reverify_a6ce987/cost_models/gmp_symmetry_epyc7532.json = run1 cost model (manifest cost_model_sha256)',
          cm.exists() and sha(cm) == m['cost_model_sha256'], m['cost_model_sha256'][:16] + '...', sha(cm)[:16] + '...' if cm.exists() else 'missing',
          'only places tasks on shards; used by make -f public.mk smoke')
    rv_same = all(sha(REV / 'inputs' / n) == sha(PKG / 'inputs' / n) for n in ('manifest.json', 'two_loop.json', 'primitive_reference.json'))
    check('id.reverify_inputs', W, 'reverify_a6ce987/inputs = production inputs (byte-identical)', rv_same, 'identical', 'identical' if rv_same else 'DIFFERENT')
    bad = []
    hashes = {}
    names = []
    for g in m['groups']:
        p = run / 'groups' / g['name']
        names.append(g['name'])
        cb = (p / 'config.json').read_bytes()
        cfg = json.loads(cb)
        d = load(p / 'merged.json')
        if hashlib.sha256(cb).hexdigest() != g['sha256']:
            bad.append(g['name'] + ': config hash')
        if (d.get('schema') != 'c7-d3-merged-1' or d.get('complete') is not True or d.get('manifest_sha256') != mh
                or d.get('config_hash') != object_hash(cfg) or d.get('sector') != cfg['sector'] or d.get('L') != cfg['L']
                or d.get('primitive_mode') != m['primitive_mode'] or d.get('replicates') != cfg['replicates']
                or len(d['batches']) != cfg['replicates'] or any(len(x) != 2 * (8 - cfg['L']) for x in d['batches'])):
            bad.append(g['name'] + ': merged metadata')
        if object_hash({k: v for k, v in d.items() if k != 'payload_sha256'}) != d.get('payload_sha256'):
            bad.append(g['name'] + ': merged payload hash')
        hashes[g['name']] = sha(p / 'merged.json')
    want = {f'{t}_{s}_L{L}' for t in 'ab' for s in ('free', 'power') for L in range(3, 8)}
    check('id.groups', W, '20 groups (a,b x free,power x L3..L7): configs, merged metadata and payload hashes', not bad and set(names) == want,
          '20 groups', f'{len(names)} groups' + ('; ' + '; '.join(bad) if bad else ''))
    check('id.merged', W, 'merged.json sha256 = C7_result.merged_sha256', hashes == rec['merged_sha256'], '20 hashes',
          'equal' if hashes == rec['merged_sha256'] else 'DIFFERENT')
    # graph_replicates.csv (only in the full run directory, hosted)
    fr = a.full_run.resolve() if a.full_run else None
    if fr and fr.exists():
        gbad = [n for n in names if sha(fr / 'groups' / n / 'graph_replicates.csv') != load(run / 'groups' / n / 'merged.json')['graph_replicates_sha256']]
        same = all(sha(fr / x) == sha(run / x) for x in ['manifest.json', 'C7_result.json'] + [f'groups/{n}/{f}' for n in names for f in ('config.json', 'merged.json')])
        check('id.full_run', W, 'full run directory: records byte-identical to the shipped ones; graph_replicates.csv digests', same and not gbad,
              'identical; 20 digests', ('identical' if same else 'DIFFERENT') + (f'; bad csv: {gbad}' if gbad else '; 20 digests'))
    else:
        row('id.full_run', W, 'graph_replicates.csv digests (full run directory)', '20 digests', '-', 'SKIP',
            'in run1-20260930-m4096_full.tgz (hosted); make reverify checks them')

    # ------------------------------------------------------------------ 2. production assembly (4de9412)
    P = run_stage('production', run, out / 'stage_production.json')
    r = P['result']
    keys = list(r)
    exact = [k for k in keys if canon(r[k]) == canon(rec.get(k))]
    okA, worst = compare_result(rec, r, keys)
    check('asm.production', 'C7_result.json', 'tools/assemble.py (4de9412) calculate(bootstrap=4096) reproduces every field',
          okA, f'{len(keys)} fields', f'{len(exact)}/{len(keys)} bitwise; max relative difference {worst:.1e}',
          'bitwise expected on AMD EPYC 7532/7543 (AVX2); else 1e-12 (C7, SE, coefficients) and 1e-10 (all other floats; '
          'bootstrap bias = mean - estimate, judged on the scale of the coefficient vector)')
    stale = {3: -.3535815204332, 4: 1.228063545327623, 5: -5.85035142075, 6: 33.56819679857058}
    low = [dict(order=k, estimate=r['coefficients'][k], sampling_se=r['standard_errors'][k], reference=v) for k, v in stale.items()]
    meta = (rec['primitive_mode'] == m['primitive_mode'] and rec['backend'] == m['backend'] and rec['build'] == m['build']
            and rec['test_only'] is False and maxrel(rec['lower_order_checks'], low) is not None)
    check('asm.metadata', 'C7_result.json', 'mode, backend, build, test_only and lower_order_checks (delivered tool; stale C6 ref 33.5682)',
          meta, 'recompute/gmp/gmp350', f"{rec['primitive_mode']}/{rec['backend']}/{rec['build']['mp_backend']}")

    # ------------------------------------------------------------------ 3. gates (a6ce987)
    R = run_stage('reverify', run, out / 'stage_reverify.json')
    rr, ch = R['result'], R['checks']
    rep = load(res / 'run1_report_bb9d2ca.json')
    shared = [k for k in r if k in rr and k != 'schema']
    same_phys, worst2 = compare_result(rec, rr, shared)
    same_rep = maxrel(rep['C7_full'], rr['C7_full']) <= EXISTING_REL and maxrel(rep['sampling_standard_error'], rr['sampling_standard_error']) <= EXISTING_REL
    check('asm.reverify', 'C7_result.json, run1_report_bb9d2ca.json', 'tools/assemble.py (a6ce987) gives the same result (shared fields) and report value',
          same_phys and same_rep, f"{len(shared)} fields; {rep['C7_full']!r}", f"max relative difference {worst2:.1e}; {rr['C7_full']!r}")
    gate_exact = canon(ch) == canon(rep['checks'])
    # power_differences[3] vanishes in exact arithmetic: its pull is a ratio of rounding noise and is not compared.
    def strip(c):
        c = json.loads(json.dumps(c))
        c['power_differences'] = [e for e in c['power_differences'] if e['order'] != 3]
        return c
    gd = maxrel(strip(rep['checks']), strip(ch))
    check('gates.report', 'run1_report_bb9d2ca.json', 'consistency gates equal the final re-verification report',
          gate_exact or (gd is not None and gd <= 1e-8), 'checks{}', 'bitwise' if gate_exact else f'max relative difference {gd:.1e}' if gd is not None else 'structure differs',
          'bitwise on AVX2 AMD; elsewhere 1e-8 (power differences cancel: one ulp of C4 is 1e-10 of d4; d3 excluded: rounding noise)')
    check('gates.flags', 'CAMPAIGN.md', 'no gate flagged (|pull| > 3, bootstrap ratio outside 0.8-1.2, archived > 3 archived SE)',
          ch['flags'] == [], 'none', json.dumps(ch['flags']))
    mlist = load(res / 'run1_report_bb9d2ca.json')['campaign']['merged_sha256']
    check('gates.report_identity', 'run1_report_bb9d2ca.json', 'the report re-verified the same manifest and merged files',
          rep['campaign']['manifest_sha256'] == mh and mlist == hashes and rep['existing_result']['bitwise'] is True,
          'same hashes; bitwise', f"{'same' if mlist == hashes else 'DIFFERENT'}; bitwise={rep['existing_result']['bitwise']}")

    # ------------------------------------------------------------------ 4. the note's numbers
    C7, SE = r['C7_full'], r['sampling_standard_error']
    prev = load(REF / 'verification/C7_full_result.json')
    S1, S1t, S29_1, S29_2, S29_3, S29_4, S26 = ('abstract, Sec 1', 'Sec 1 table', 'Sec 29.1', 'Sec 29.2', 'Sec 29.3', 'Sec 29.4', 'Sec 26.7')
    allow = ceil_to(4 * SE, '0.01')
    check('n.reported', S1, 'C7(3) = -220.35 +- 0.13 (4 SE rounded up to 0.01)', f'{C7:.2f}' == '-220.35' and str(allow) == '0.13',
          '-220.35 +- 0.13', f'{C7:.2f} +- {allow}')
    check('n.estimator', S1t, 'underlying estimator', abs(C7 - (-220.35448047392794)) <= EXISTING_REL * abs(C7),
          '-220.35448047392794', repr(C7), 'bitwise on the production CPU type, else 1e-12 relative')
    printed('n.se', S1t, 'sampling standard error', '0.0318188006', SE)
    printed('n.4se', S29_1, '4 sigma-hat', '0.127', 4 * SE)
    printed('n.pf', S29_1, 'power-free C7^pf(3)', '-220.3723574', r['power_free_C7'])
    printed('n.pf_se', S29_1, 'power-free SE', '0.0277073', r['power_free_se'])
    printed('n.dp', S29_1, 'power correction Delta_p C7(3)', '0.0178769', r['power_correction'])
    printed('n.dp_se', S29_1, 'power correction SE', '0.0156478', r['power_correction_se'])
    printed('n.full7', S29_1, 'complete C7(3) (table)', '-220.3544805', C7)
    printed('n.full7_se', S29_1, 'complete SE (table)', '0.0318188', SE)
    dev = [abs(h[7] - C7) for h in r['half_streams']]
    printed('n.half_dev1', S29_1, 'first half-stream deviation from C7(3)', '0.034', dev[0])
    printed('n.half_dev2', S29_1, 'second half-stream deviation from C7(3)', '0.034', dev[1])
    check('n.rule2d', S29_1, '2D rule (max of 4 sigma and half-stream deviations) gives the same allowance',
          ceil_to(max(4 * SE, *dev), '0.01') == allow, '0.13', str(ceil_to(max(4 * SE, *dev), '0.01')))
    readme = (REF / 'README.md').read_text()
    check('n.prev_report', S29_1, 'previous calculation reported -228 +- 16', '-228 +/- 16' in readme and f"{prev['C7_full']:.0f}" == '-228'
          and str(ceil_to(4 * prev['sampling_standard_error'], '1')) == '16', '-228 +- 16',
          f"{prev['C7_full']:.0f} +- {ceil_to(4 * prev['sampling_standard_error'], '1')} (reference/README.md, verification/C7_full_result.json)")
    printed('n.prev_est', S29_1, 'previous estimator', '-227.6181095', prev['C7_full'])
    printed('n.prev_se', S29_1, 'previous sampling SE', '3.8273969', prev['sampling_standard_error'])
    printed('n.prev_dist', S29_1, 'new estimator minus previous, in previous SE', '1.90', (C7 - prev['C7_full']) / prev['sampling_standard_error'])
    printed('n.prev_dist_gate', S29_1, 'same, from the gate (archived C7, in archived SE)', '1.90', ch['archived']['in_archived_se'])

    # Sec 29.2: inventory and construction checks of the previous calculation (reference/verification)
    inv = load(PKG / 'inputs/inventory.json')
    cnt = {s: [len(inv[s][str(L)]) for L in range(3, 8)] for s in ('free', 'power')}
    nprim = sum(1 for r_ in inv['free']['7'] if r_['primitive'])
    check('n.classes_free', S29_2, 'integrated power-free classes, loops 3..7', cnt['free'] == [5, 16, 76, 395, 2298], '5,16,76,395,2298', cnt['free'])
    check('n.classes_prim', S29_2, 'seven-loop classes: nonprimitive + primitive', (2298 - nprim, nprim) == (2254, 44), '2254 + 44', f'{2298 - nprim} + {nprim}')
    check('n.classes_power', S29_2, 'integrated power classes, loops 3..7', cnt['power'] == [1, 3, 20, 107, 590], '1,3,20,107,590', cnt['power'])
    check('n.kernels', S29_2, 'kernels in all', sum(cnt['free']) + sum(cnt['power']) == 3511 == sum(sum(v.values()) for v in im['counts'].values()),
          '3,511', sum(cnt['free']) + sum(cnt['power']))
    dim = load(REF / 'verification/dimension_checks.json')
    check('n.structure', S29_2, 'denominators and weights unchanged from the 2D inventory (all kernels checked)',
          dim['status'] == 'passed' and dim['graph_structure_checks'] == 3511, '3,511 checked', f"{dim['status']}, {dim['graph_structure_checks']}",
          'reference/verification/dimension_checks.json')
    tl = load(PKG / 'inputs/two_loop.json')
    printed('n.b25', S29_2, 'b_{2,5}', '26.0214190551330710', float(Decimal(tl['B2'][5])))
    check('n.b25_digits', S29_2, 'b_{2,5} digits (Decimal)', Decimal(tl['B2'][5]).quantize(Decimal('1e-16')) == Decimal('26.0214190551330710'),
          '26.0214190551330710', str(Decimal(tl['B2'][5]).quantize(Decimal('1e-16'))), 'inputs/two_loop.json')
    tlc = load(REF / 'verification/two_loop_checks.json')
    check('n.b2_contours', S29_2, 'two 65-digit evaluations, radii 0.04, 0.07, 64 and 80 Cauchy nodes',
          tlc['dps'] == 65 and [(x['radius'], x['nodes']) for x in tlc['records']] == [('0.04', 64), ('0.07', 80)], '0.04/64, 0.07/80',
          [(x['radius'], x['nodes']) for x in tlc['records']])
    printed('n.b2_agree', S29_2, 'the two evaluations agree to', '3.3e-57', float(Decimal(tlc['max_difference'])))
    printed('n.b2_c6', S29_2, 'agreement with the sixth-order input', '1.3e-54', float(Decimal(dim['two_loop_overlap_max_difference'])))
    check('n.gamma_n', S29_2, 'independent Cauchy evaluations of the Gamma factors', dim['gamma_cauchy_checks'] == 30, '30', dim['gamma_cauchy_checks'])
    printed('n.gamma', S29_2, 'Gamma-factor agreement', '8.3e-54', float(Decimal(dim['gamma_cauchy_max_difference'])))
    asm = load(REF / 'verification/assembly_checks.json')
    check('n.assembly64', S29_2, 'exact rational cases test the assembly', asm['status'] == 'passed' and asm['exact_cases'] == 64
          and len(asm['rows']) == 64 and all(x['exact_equal'] for x in asm['rows']), '64', asm['exact_cases'], 'reference/verification/assembly_checks.json')
    check('n.c7_const', S29_2, 'C7(3) contains (3 c_{7,0} - b_{7,0})/6561 (Jacobian of the production assembly)',
          abs(P['dC7_db70'] + 1 / 6561) < 1e-15 and abs(P['dC7_dc70'] - 3 / 6561) < 1e-15, '-1/6561, 3/6561',
          f"{P['dC7_db70']:.12g}, {P['dC7_dc70']:.12g}")
    b3 = -16 * math.pi / 15
    check('n.b3_exact', S29_2, 'three-loop power graph closed form -16 pi/15', dim['power_three_loop_b3_exact'] == '-16*pi/15'
          and abs(float(Decimal(dim['power_three_loop_b3_value'])) - b3) < 1e-15, '-16*pi/15', dim['power_three_loop_b3_exact'])
    printed('n.b3_value', S29_2, '-16 pi/15', '-3.3510322', b3)
    printed('n.b3_prod', S29_2, 'production b_3^p(0)', '-3.3510653', P['b3p'])
    printed('n.b3_prod_se', S29_2, 'its sampling SE', '0.0000262', P['b3p_se'])
    printed('n.b3_pull', S29_2, 'pull from -16 pi/15', '-1.26', (P['b3p'] - b3) / P['b3p_se'])

    # Sec 29.3: worker identity, archived-stream replay, thread and CPU checks
    same_src = all(sha(PKG / 'src' / f) == sha(REF / 'src' / f) for f in ('kernel.hpp', 'c7d3_integrate.cpp'))
    check('n.worker', S29_3, 'production worker byte-identical to the previous calculation (src/ = reference/src/)', same_src, 'identical',
          'identical' if same_src else 'DIFFERENT')
    kh = (PKG / 'src/kernel.hpp').read_text()
    check('n.thresholds', S29_3, 'promotion thresholds 1e-9 (binary128) and 1e-23 (GMP)', 'ratio<1e-9L' in kh and 'Q(1e-23L)' in kh, '1e-9, 1e-23',
          'found in src/kernel.hpp' if 'ratio<1e-9L' in kh else 'NOT FOUND')
    ev = res / 'evidence'
    rp = load(ev / 'replay_report.json')
    check('n.replay_rows', S29_3, 'archived production rows replayed (job 566411)', rp['rows'] == 168528, '168,528', rp['rows'], 'evidence/replay_report.json')
    printed('n.replay_bitwise', S29_3, 'share reproduced bit for bit, %', '96', 100 * rp['bitwise_rows'] / rp['rows'])
    printed('n.replay_max', S29_3, 'largest normalized difference of the rest', '1.0e-11', float(Decimal(rp['max_normalized_difference'])))
    prom = not rp['fallback_mismatch_groups'] and all(g['quad_old'] == g['quad_new'] and g['mp_old'] == g['mp_new'] for g in rp['groups'].values())
    check('n.replay_prom', S29_3, 'identical promotion counts (20 groups)', prom and len(rp['groups']) == 20, 'identical', 'identical' if prom else 'DIFFERENT')
    check('n.replay_c7', S29_3, 'rebuilt previous estimator vs published', repr(rp['C7_full']) == '-227.61810947469922'
          and repr(rp['archived_C7_full']) == '-227.61810947469945' == repr(prev['C7_full']), '-227.61810947469922 vs -227.61810947469945',
          f"{rp['C7_full']!r} vs {rp['archived_C7_full']!r} (= verification/C7_full_result.json)")
    cited('n.indep13', S29_3, 'independent high-precision reimplementation reproduced 13 archived rows, L3-L7, both sectors', '13 rows',
          'code review record (REVIEWS.md); script public/indep_rows.py, but the original row list was not archived')
    bt = (ev / 'buildtest-566376.out').read_text()
    mt = re.search(r'THREADCHECK rows=(\d+) mismatches=(\d+) quad=(\d+) mp=(\d+)', bt)
    check('n.threads', S29_3, '64 vs 16 threads: rows, mismatches, binary128 and GMP promotions',
          mt and tuple(map(int, mt.groups())) == (5776, 0, 255396, 20511), '5,776 rows identical; 255,396 / 20,511',
          mt.group(0) if mt else 'not found', 'evidence/buildtest-566376.out')
    it = (ev / 'intelcheck-566410.out').read_text()
    mi = re.search(r'AMD64-vs-INTEL20 rows=(\d+) mismatches=(\d+) quad=(\d+) mp=(\d+)', it)
    check('n.cpu_counts', S29_3, 'AMD vs Intel: same rows and identical promotion counts', mi and int(mi.group(1)) == 5776
          and (int(mi.group(3)), int(mi.group(4))) == (255396, 20511), 'identical promotion counts', mi.group(0) if mi else 'not found',
          'evidence/intelcheck-566410.out (mismatches count rows with any differing field)')
    cited('n.cpu_max', S29_3, 'AMD vs Intel: largest normalized difference', '2.0e-11',
          'CAMPAIGN.md (AMD vs Intel identity) and the code review; the comparison output itself was not archived')
    printed('n.cpu_rel', S29_3, '2.0e-11 relative to SE/|C7| (about 1e-7)', '1e-7', 2.0e-11 / (SE / abs(C7)),
            'order of magnitude: tolerance half a unit of 1e-7')
    cfgs = {n: load(run / 'groups' / n / 'config.json') for n in names}
    check('n.reps', S29_3, '64 randomized replicates for every loop and sector', all(c['replicates'] == 64 for c in cfgs.values()), '64', 'all 64')
    check('n.bits_rates', S29_3, 'campaign a: 52-bit nets, rate .8; b: 60-bit nets, rate .7',
          all((c['net']['bits'], c['rate']) == ((52, '.8') if c['campaign'] == 'a' else (60, '.7')) for c in cfgs.values()), '52/.8, 60/.7', 'all groups')
    alloc = load(REF / 'inputs/allocation.json')
    okc, prim_n, minpts = True, set(), None
    for n, c in cfgs.items():
        rows_ = {r_['id']: r_ for r_ in inv[c['sector']][str(c['L'])]}
        for gid, cntv in c['counts'].items():
            r_ = rows_[int(gid)]
            if r_['points'] != int(alloc[c['sector']][str(c['L'])][gid]):
                okc = False
            if c['sector'] == 'free' and c['L'] == 7 and r_['primitive']:
                prim_n.add(cntv)
            else:
                okc &= cntv == max(4, r_['points']) * 4096
                minpts = r_['points'] if minpts is None else min(minpts, r_['points'])
            okc &= cntv > 0 and cntv & (cntv - 1) == 0
    check('n.alloc', S29_3, 'frozen per-graph allocation of the previous calculation x 2^12, powers of two',
          okc and m['allocation_multiplier'] == 4096, 'x 2^12', f"multiplier {m['allocation_multiplier']}", 'inputs/inventory.json = reference/inputs/allocation.json')
    check('n.alloc_min', S29_3, 'at least 64 points per stratum (before x 2^12)', minpts == 64, '64', minpts)
    check('n.prim', S29_3, '44 seven-loop primitive classes at 2^22 points each per replicate (flat, 1024 x 2^12)',
          prim_n == {2 ** 22} and m['primitive_points'] == 1024 and nprim == 44, '2^22', f'{sorted(prim_n)}, primitive_points {m["primitive_points"]}')
    base = cfgs['a_free_L3']['seed'] - 3 * 1279
    off = lambda c: (0 if c['sector'] == 'free' else 0x156ad267) + (0 if c['campaign'] == 'a' else 0x614ef703)
    seeds_ok = all(c['seed'] == (base + c['L'] * 1279 + off(c)) % 2 ** 64 for c in cfgs.values())
    avoid = {300317001, 307401711, 307901733, 302774989, 2026093003, 481771, 3272672730315656627}
    check('n.seed', S29_3, 'one fresh base seed (delivered arithmetic offsets)', seeds_ok and base not in avoid and base == 4805754955154533039,
          'fresh', f'{base}', 'differs from the archived, README and pilot seeds')
    samples = sum(c['samples'] for c in cfgs.values())
    check('n.samples', S29_3, 'kernel samples in the two campaigns', samples == 867784720384 == sum(load(run / 'groups' / n / 'merged.json')['samples'] for n in names),
          '867,784,720,384', f'{samples:,}')
    models = []
    done = []
    for f in sorted((run / 'lanes').glob('node-*.out')):
        t = f.read_text()
        mm_ = re.search(r'model name\s*:\s*(.+)', t)
        models.append(mm_.group(1).strip() if mm_ else '?')
        done += re.findall(r'node done (\S+)', t)
    n_amd = sum('AMD' in x for x in models)
    n_int = sum('Intel' in x for x in models)
    check('n.nodes', S29_3, '14 AMD and 14 Intel nodes', (n_amd, n_int) == (14, 14), '14 + 14', f'{n_amd} + {n_int}', 'run1 lanes/node-*.out')
    check('n.completed', S29_3, 'completed on 1 October 2026', bool(done) and max(done).startswith('2026-10-01'), '1 October 2026', max(done) if done else '-')
    ca, cb = r['campaigns']['a'], r['campaigns']['b']
    printed('n.ca', S29_3, 'campaign a', '-220.3220', ca['C7'])
    printed('n.ca_se', S29_3, 'campaign a SE', '0.0431', ca['sampling_se'])
    printed('n.cb', S29_3, 'campaign b', '-220.3870', cb['C7'])
    printed('n.cb_se', S29_3, 'campaign b SE', '0.0468', cb['sampling_se'])
    printed('n.h1', S29_3, 'first half stream', '-220.3207', r['half_streams'][0][7])
    printed('n.h2', S29_3, 'second half stream', '-220.3883', r['half_streams'][1][7])
    printed('n.comb', S29_3, 'combined', '-220.3545', C7)
    printed('n.comb_se', S29_3, 'combined SE', '0.0318', SE)
    printed('n.ab_pull', S29_3, 'campaigns differ by (combined SE)', '1.02', abs(ch['campaign_pull']['pull']))
    tab = {'free': ['0.0000', '0.0006', '0.0034', '0.0119', '0.0248'], 'power': ['0.0000', '0.0002', '0.0014', '0.0058', '0.0145']}
    for s in ('free', 'power'):
        for L, q in zip(range(3, 8), tab[s]):
            printed(f'n.err_{s}_L{L}', S29_3, f'error of C7 from {s} L={L}', q, r['error_by_loop'][str(L)][s])

    # Sec 29.4: lower orders, power differences, bootstrap, previous power correction
    lo = {e['order']: e for e in ch['lower_order']}
    quoted = {3: ('-0.3535806960', '3.59e-7', '+2.30'), 4: ('1.2280727249', '8.52e-6', '+1.08'),
              5: ('-5.8503454757', '1.52e-4', '+0.04'), 6: ('33.5738672', '0.0019782', '-0.79')}
    for k, (e, s, p) in quoted.items():
        printed(f'n.C{k}', S29_4, f'C{k}(3) by-product', e, lo[k]['estimate'])
        printed(f'n.C{k}_se', S29_4, f'C{k}(3) sampling SE', s, lo[k]['sampling_se'])
        printed(f'n.C{k}_pull', S29_4, f'C{k}(3) pull (reference {lo[k]["reference"]!r})', p, lo[k]['pull'])
    pdq = {4: ('2.0e-6', '2.1e-6'), 5: ('4.0e-5', '6.4e-5'), 6: ('-3.7e-4', '10.2e-4')}
    for k, (d, s) in pdq.items():
        printed(f'n.pd{k}', S29_4, f'power correction at order {k}', d, r['power_differences'][k])
        printed(f'n.pd{k}_se', S29_4, f'its SE', s, r['power_difference_errors'][k])
    check('n.pd3', S29_4, 'order-3 power difference at rounding level', abs(r['power_differences'][3]) < 1e-14 and r['power_difference_errors'][3] < 1e-13,
          'rounding level', f"{r['power_differences'][3]:.1e} +- {r['power_difference_errors'][3]:.1e}")
    printed('n.pd7', S29_4, 'seventh-order power correction', '0.018', r['power_correction'])
    printed('n.pd7_se', S29_4, 'its SE', '0.016', r['power_correction_se'])
    check('n.boot_n', S29_4, 'bootstrap replicate resamples', r['bootstrap']['replicates'] == 4096, '4,096', r['bootstrap']['replicates'])
    printed('n.boot', S29_4, 'bootstrap SE', '0.03204', r['bootstrap']['full_se'][7])
    printed('n.boot_cov', S29_4, 'covariance SE', '0.03182', SE)
    printed('n.prev_pc', S29_4, 'previous power correction', '-3.836223', prev['power_correction'])
    printed('n.prev_pc_se', S29_4, 'its SE', '2.007117', prev['power_correction_se'])
    printed('n.prev_pc_dist', S29_4, 'distance in previous SE', '1.92', (r['power_correction'] - prev['power_correction']) / prev['power_correction_se'])

    # Sec 26.7 (C6(3) section) quotes the sixth-order by-product of this production
    printed('n.s26_c6', S26, 'C6(3) by-product of the C7(3) production', '33.57387', lo[6]['estimate'])
    printed('n.s26_c6_se', S26, 'its sampling SE', '0.00198', lo[6]['sampling_se'])
    printed('n.s26_pull', S26, 'combined SE from the C6(3) estimator', '-0.79', lo[6]['pull'])

    # The note's README (GFF/note/README.md) repeats these numbers at other roundings
    RM = 'note README'
    printed('r.est', RM, 'estimator', '-220.35448', C7)
    printed('r.se', RM, 'sampling SE', '0.03182', SE)
    printed('r.pf', RM, 'power-free', '-220.37236', r['power_free_C7'])
    printed('r.pf_se', RM, 'power-free SE', '0.02771', r['power_free_se'])
    printed('r.dp', RM, 'power correction', '+0.01788', r['power_correction'])
    printed('r.dp_se', RM, 'power correction SE', '0.01565', r['power_correction_se'])
    printed('r.prev', RM, 'previous estimator', '-227.618', prev['C7_full'])
    printed('r.prev_se', RM, 'previous SE', '3.83', prev['sampling_standard_error'])
    printed('r.samples', RM, 'samples', '8.68e11', samples)

    # ------------------------------------------------------------------ output
    n = {s: sum(r_['status'] == s for r_ in ROWS) for s in ('PASS', 'FAIL', 'SKIP', 'CITED')}
    env = f"python {P['python']}, numpy {P['numpy']}"
    lines = ['# C7(3) replay', '', f'Records: `{run}`. Environment: {env}.', '',
             f"PASS {n['PASS']}, FAIL {n['FAIL']}, SKIP {n['SKIP']}, CITED {n['CITED']}.", '',
             '| status | id | where | quantity | quoted | computed | detail |', '|---|---|---|---|---|---|---|']
    for r_ in ROWS:
        lines.append('| {status} | {id} | {where} | {quantity} | {quoted} | {computed} | {detail} |'.format(**{k: str(v).replace('|', '/') for k, v in r_.items()}))
    (out / 'REPLAY.md').write_text('\n'.join(lines) + '\n')
    (out / 'replay.json').write_text(json.dumps(dict(counts=n, environment=env, rows=ROWS), indent=2) + '\n')
    w = max(len(r_['id']) for r_ in ROWS)
    for r_ in ROWS:
        print(f"{r_['status']:5s}  {r_['id']:<{w}s}  {r_['where']:<26s}  {r_['quantity'][:70]:<70s}  quoted {r_['quoted'][:28]:<28s}  computed {r_['computed'][:44]}")
    print(f"\nC7(3) replay: PASS {n['PASS']}, FAIL {n['FAIL']}, SKIP {n['SKIP']}, CITED {n['CITED']}  ({env}; table in {out / 'REPLAY.md'})")
    return 1 if n['FAIL'] else 0


if __name__ == '__main__':
    sys.exit(main())
