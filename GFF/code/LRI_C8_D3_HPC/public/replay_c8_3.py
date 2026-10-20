#!/usr/bin/env python3
"""Replay and verify every C8(3) number the condensed note quotes (GFF/code/LRI_C8_D3_HPC/public/replay_c8_3.py).

Run from the package folder (code/LRI_C8_D3_HPC), normally through `make -f public.mk replay`:

  python3 -B public/replay_c8_3.py [--results ../../results/C8_3] [--data ../../data/C8_3] [--out .public_out/replay]
                                   [--bootstrap 4096] [--skip-verify-result]

Nothing is written outside --out. The steps (each row of the PASS/FAIL table names its source and tolerance):

  P  package integrity: the shipped files against the package's own SHA256SUMS (verbatim at 4fbd1bae; a listed file may
     be absent only under the export entry's excludes, NOT_EXPORTED below, or if public/dropped_paths.txt names it, and
     those must be absent), the 6dd4a75a evidence files against public/SHA256SUMS.evidence_6dd4a75a,
     the tools, vendored assembly, inputs and references the result pins by sha256.
  R  record integrity: results/C8_3 against SHA256SUMS.symmetry and the hashes C8_result.json and manifest.json bind
     (merged.json of every group, config.json, cost model, design bundle); every merged.json's self-hash and plan binding;
     every group's scientific identity (assemble.group_science) against C8_result.json science_sha256.
  A  assembly replay: the 24 merged batch arrays reassembled with the package's own tools/assemble.combine (the vendored
     order-8 assembly; bootstrap 4096, seed 70530413) and compared field by field with C8_result.json; then
     tools/verify_result.py on the result file (file mode; OPENBLAS_CORETYPE=Zen as on the production host).
  T  the tail N-trend (tail_ntrend/ntrend.py rerun on the committed pilot report, prod_tails.csv and the result) against
     the committed ntrend.json, exactly.
  H  hosted data, only when fetched (else NOT RUN): graph_replicates.csv against its pins; the per-graph a/b split
     (ab_split/ab_split.py rerun) against the committed report.txt; the tail monitor's variance shares recomputed.
  N  every number Sections 1, 32 and 33 quote, recomputed or read from its record and compared at the printed precision
     (half a unit of the last printed digit unless the row says otherwise).

Exit status 0 when no row FAILs (NOT RUN rows do not fail), 1 otherwise. Writes REPLAY.md and replay.json to --out.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import assemble  # noqa: E402  (the package's own assembly; imports the vendored order8_assembly.py after its pin check)
from common import object_hash  # noqa: E402

EV = ROOT / 'benchmarks/symmetry_2026-10-c8'
PROD = EV / 'production'
PROD1 = PROD / 'prod1'
PILOT = EV / 'pilot'
GROUPS = [f'{c}_{s}_L{L}' for c in 'ab' for s in ('free', 'power') for L in range(3, 9)]
STORED_EST = '1602.6052229663408'          # Sec 1 table and README: the estimator, all digits
STORED_SE = '0.9516489064069612'

ROWS: list[dict] = []

# Numbers of the note (edition fa71533) that the records do not support at the printed precision. The replay checks the
# corrected text strictly and reports the printed one as ERRATUM (not a failure) until the note is corrected; then the
# entry can be deleted. Reported to the coordinator on 2026-10-13.
ERRATA = {
    '32.4ah.free4': ('0.011', '0.010', 'Sec 32.4 error table, power-free L=4: error_by_loop.free.4.se = 0.010477'),
    '32.5u': ('0.88', '0.87', 'Sec 32.5 "to medians of 0.82 to 0.88": the three extrapolated medians are 0.823, 0.875 and 0.871 '
                              '(ntrend.json by_n 65536), so the upper end prints as 0.87'),
}


def row(step, what, status, detail='', source='', tol=''):
    ROWS.append(dict(step=step, what=what, status=status, detail=str(detail), source=source, tol=tol))
    mark = {'PASS': 'PASS', 'FAIL': 'FAIL', 'NOT RUN': 'SKIP', 'INFO': 'info', 'KNOWN': 'KNWN', 'ERRATUM': 'ERRT'}[status]
    print(f'[{mark:4s}] {step:6s} {what}: {detail}', flush=True)


def ok(step, what, cond, detail='', source='', tol=''):
    row(step, what, 'PASS' if cond else 'FAIL', detail, source, tol)
    return cond


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jload(p: Path):
    return json.loads(Path(p).read_text())


def decimals(s: str) -> int:
    s = s.replace(',', '').replace('+', '').replace('−', '-')
    m = re.match(r'^-?\d*\.?(\d*)(?:[eE]([+-]?\d+))?$', s)
    if not m:
        raise ValueError(s)
    d = len(m.group(1))
    return d - int(m.group(2) or 0)


def qnum(sid, where, quoted: str, value, source, tol=None, rel=False):
    """quoted (as printed) against value: |value - quoted| <= half a unit of the last printed digit (or tol)."""
    if sid in ERRATA and quoted == ERRATA[sid][0]:
        row('N', f'{sid} [{where}] {quoted}', 'ERRATUM', f'the record gives {value:.6g}; corrected text {ERRATA[sid][1]} checked next. {ERRATA[sid][2]}', source)
        return qnum(sid + '*', where + ', corrected', ERRATA[sid][1], value, source, tol)
    q = float(quoted.replace(',', '').replace('−', '-').replace('+', ''))
    if tol is None:
        tol = 0.5 * 10 ** (-decimals(quoted)) * (1 + 1e-9)
    if value is None:
        return row('N', f'{sid} [{where}] {quoted}', 'FAIL', 'no value', source, tol)
    good = abs(value - q) <= tol + 1e-15 * abs(q)
    return ok('N', f'{sid} [{where}] {quoted}', good, f'computed {value:.12g}', source, f'|x-q| <= {tol:.3g}')


def qint(sid, where, quoted, value, source):
    q = int(str(quoted).replace(',', ''))
    return ok('N', f'{sid} [{where}] {quoted}', value == q, f'computed {value}', source, 'exact')


def qtrue(sid, where, text, cond, detail, source):
    return ok('N', f'{sid} [{where}] {text}', bool(cond), detail, source, 'logical')


# ------------------------------------------------------------------------------------------------- comparison
REL = 1e-10      # the package's own re-verification tolerance (tools/verify_result.py REL)
ABS = 1e-13      # floor for rounding-level fields (gate deviations ~1e-16, bootstrap biases of exact orders ~1e-15)
NTREND_REL = 1e-9  # tail_ntrend floats (Hill estimates, power fits) across Python/numpy versions; the note prints 2-3 digits


GATE_DIAG = re.compile(r'(hard_gates|gates\.hard)\.(top_slot\.rows\[\d+\]\.rel_deviation|loop7\.rel_deviation|'
                       r'affinity\.rows\[\d+\]\.rel_deviation|affinity\.linear_response_residual\[\d+\])$')
GATE_LIMIT = {'top_slot': 1e-12, 'loop7': 1e-12, 'rows': 1e-10, 'linear_response_residual': 1e-10}   # the vendored gates' rtol


class Cmp:
    """Field-by-field comparison. Rounding-level gate diagnostics (the deviations of the hard gates from their exact
    values, about 1e-16 to 1e-12) depend on the BLAS kernels (C62d F6: OPENBLAS_CORETYPE=Zen reproduces the production
    bits on x86-64); they are collected apart and checked against the gates' own thresholds instead of for equality."""
    def __init__(self):
        self.n = 0
        self.worst = (0.0, '')
        self.bad = []
        self.gate = []

    def cmp(self, a, b, where, scale=0.0):
        if GATE_DIAG.search(where) and isinstance(a, (int, float)) and isinstance(b, (int, float)):
            key = 'top_slot' if 'top_slot' in where else 'loop7' if 'loop7' in where else 'linear_response_residual' if 'linear' in where else 'rows'
            self.gate.append((where, a, b, GATE_LIMIT[key]))
            return
        if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
            if a != b:
                self.bad.append(f'{where}: {a!r} != {b!r}')
            return
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            self.n += 1
            d = abs(a - b)
            s = max(abs(a), abs(b), scale)
            r = d / s if s > 0 else 0.0
            if d > max(REL * s, ABS):
                self.bad.append(f'{where}: stored {a!r}, recomputed {b!r}')
            if s > 1e-9 and r > self.worst[0]:
                self.worst = (r, where)
            return
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                self.bad.append(f'{where}: keys differ {sorted(set(a) ^ set(b))[:4]}')
            for k in set(a) & set(b):
                self.cmp(a[k], b[k], f'{where}.{k}')
            return
        if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
            if len(a) != len(b):
                self.bad.append(f'{where}: length {len(a)} != {len(b)}')
                return
            flat = [abs(x) for x in list(a) + list(b) if isinstance(x, (int, float)) and not isinstance(x, bool)]
            sc = max(flat, default=0.0)
            for i, (x, y) in enumerate(zip(a, b)):
                self.cmp(x, y, f'{where}[{i}]', sc)
            return
        self.bad.append(f'{where}: types {type(a).__name__} / {type(b).__name__}')


def jsonable(x):
    return json.loads(json.dumps(x, allow_nan=False, default=lambda o: o.tolist() if hasattr(o, 'tolist') else float(o)))


# ------------------------------------------------------------------------------------------------- steps
def scrubbed_paths():
    """Files the public export's privacy scrub changed (public/SCRUBBED.txt, one package-relative path per line, '#'
    comments). They are bound only by checksum lists (never by a result, manifest or code hash), so a listed file is
    counted as scrubbed instead of compared; any other mismatch still fails."""
    f = ROOT / 'public/SCRUBBED.txt'
    if not f.is_file():
        return set()
    return {ln.split('#', 1)[0].strip() for ln in f.read_text().splitlines() if ln.split('#', 1)[0].strip()}


# The listed paths that the export leaves out on purpose: the excludes of the GFF/code/LRI_C8_D3_HPC entry at 4fbd1bae
# (benchmarks/ ships only the evidence that public/SHA256SUMS.evidence_6dd4a75a and the tests need; the L7 packs and L7
# payloads and the archived C7(3) records are hosted; reference/verification/ ships only C7_full_result.json).
NOT_EXPORTED = ('benchmarks/', 'experiments/', 'inputs/packs/free_L7.pack', 'inputs/packs/power_L7.pack',
                'reference/inputs/free/L7/', 'reference/inputs/power/L7/', 'reference/records/pilot/',
                'reference/records/production_a/', 'reference/records/production_b/', 'reference/verification/',
                'reference/c8d1_inputs8/verification/')


def dropped_paths():
    """Listed files that the release drops (public/dropped_paths.txt, one package-relative path per line, '#' comments):
    reference/reference/C7_d2_complete.tex, a copy of the earlier d = 2 method note, merged into the condensed note
    (author rule 2026-10-16: one TeX note per direction). They must be absent; SHA256SUMS keeps their lines."""
    f = ROOT / 'public/dropped_paths.txt'
    if not f.is_file():
        return set()
    return {ln.split('#', 1)[0].strip() for ln in f.read_text().splitlines() if ln.split('#', 1)[0].strip()}


def step_package():
    # P1: the package's own checksum list (4fbd1bae, verbatim); absent only under NOT_EXPORTED or public/dropped_paths.txt
    lines = (ROOT / 'SHA256SUMS').read_text().splitlines()
    present = not_exported = scrubbed = 0
    scrub = scrubbed_paths()
    dropped = dropped_paths()
    bad, missing, gone, listed = [], [], [], set()
    for ln in lines:
        h, rel = ln.split('  ', 1)
        listed.add(rel)
        p = ROOT / rel
        if rel in dropped:
            if p.exists():
                bad.append(rel + ' (named in public/dropped_paths.txt but present)')
            else:
                gone.append(rel)
            continue
        if not p.exists():
            if rel.startswith(NOT_EXPORTED):
                not_exported += 1
            else:
                missing.append(rel)
            continue
        present += 1
        if rel in ('SHA256SUMS', 'DELIVERY_MANIFEST.json'):
            continue
        if rel in scrub:
            scrubbed += 1
            continue
        if sha(p) != h:
            bad.append(rel)
    bad += [f'{d} (in public/dropped_paths.txt, not in SHA256SUMS)' for d in sorted(dropped - listed)]
    ok('P', 'SHA256SUMS (4fbd1bae) of every shipped file', not bad and not missing,
       f'{present} listed files present and equal, {not_exported} listed files not exported (export excludes), '
       f'{len(gone)} merged notes dropped (public/dropped_paths.txt), {scrubbed} scrubbed (public/SCRUBBED.txt), '
       f'missing {missing[:5]}, mismatches {bad[:5]}',
       'SHA256SUMS', 'sha256; absent only under NOT_EXPORTED or public/dropped_paths.txt')
    if dropped:
        row('P', 'merged notes not shipped (public/dropped_paths.txt)', 'INFO',
            f'{len(gone)} listed file(s) absent as declared: {", ".join(gone)}', 'SHA256SUMS',
            'not a check: the condensed note (GFF/note) carries their substance')
    # P2: the 6dd4a75a evidence additions, against the pruned lines of 6dd4a75a's SHA256SUMS
    ev = ROOT / 'public/SHA256SUMS.evidence_6dd4a75a'
    bad = []
    n = 0
    for ln in ev.read_text().splitlines():
        h, rel = ln.split('  ', 1)
        n += 1
        p = ROOT / rel
        if p.exists() and rel in scrub:
            continue
        if not p.exists() or sha(p) != h:
            bad.append(rel)
    ok('P', 'evidence files of 6dd4a75a', not bad, f'{n} files, mismatches/missing {bad[:5]}', 'public/SHA256SUMS.evidence_6dd4a75a', 'sha256')


def step_records(R: Path, D: Path):
    r = jload(R / 'C8_result.json')
    m = jload(R / 'manifest.json')
    # R1: SHA256SUMS.symmetry (written on symmetry after the run)
    bad = []
    n = hosted = 0
    for ln in (R / 'SHA256SUMS.symmetry').read_text().splitlines():
        h, rel = ln.split('  ', 1)
        p = R / rel
        if not p.exists():
            p = D / 'results' / rel
            if not p.exists():
                hosted += 1
                continue
        n += 1
        if sha(p) != h:
            bad.append(rel)
    ok('R', 'SHA256SUMS.symmetry', not bad, f'{n} files equal, {hosted} hosted files not fetched, mismatches {bad[:4]}',
       'results/C8_3/SHA256SUMS.symmetry', 'sha256')
    # R2: the bindings of the result
    mh = sha(R / 'manifest.json')
    ok('R', 'result -> manifest.json', r['source_manifest_sha256'] == mh, mh[:16], 'C8_result.json source_manifest_sha256', 'sha256')
    bad = [g for g in GROUPS if r['merged_sha256'][g] != sha(R / 'groups' / g / 'merged.json')]
    ok('R', 'result -> 24 merged.json', not bad and len(r['merged_sha256']) == 24, f'mismatches {bad}', 'C8_result.json merged_sha256', 'sha256')
    pins = {g['name']: g['sha256'] for g in m['groups']}
    bad = [g for g in GROUPS if pins[g] != sha(R / 'groups' / g / 'config.json')]
    ok('R', 'manifest -> 24 config.json', not bad, f'mismatches {bad}', 'manifest.json groups[].sha256', 'sha256')
    ok('R', 'manifest -> cost_model.json', m['cost_model_sha256'] == sha(R / 'cost_model.json'), m['cost_model_sha256'][:16],
       'manifest.json cost_model_sha256', 'sha256')
    dm = PROD1 / 'production/design_prod/design_meta.json'
    ok('R', 'manifest/result -> design bundle', m['allocation']['meta_sha256'] == r['allocation']['meta_sha256'] == sha(dm),
       m['allocation']['meta_sha256'][:16], 'manifest.json allocation.meta_sha256', 'sha256')
    # R3: merged.json self-hash, plan binding, shape; R4: scientific identity
    ar = {s: {t: {} for t in 'ab'} for s in ('free', 'power')}
    cfgs = {}
    bad = []
    sci_bad = []
    for g in GROUPS:
        d = jload(R / 'groups' / g / 'merged.json')
        cfg = jload(R / 'groups' / g / 'config.json')
        cfgs[g] = cfg
        if not (d.get('complete') is True and d['manifest_sha256'] == mh and d['config_hash'] == object_hash(cfg)
                and object_hash({k: v for k, v in d.items() if k != 'payload_sha256'}) == d['payload_sha256']
                and d['sector'] == cfg['sector'] and d['L'] == cfg['L'] and d['campaign'] == cfg['campaign']
                and d['replicates'] == cfg['replicates'] == len(d['batches'])):
            bad.append(g)
        x = np.asarray(d['batches'], float)
        if x.shape != (cfg['replicates'], 2 * (9 - cfg['L'])):
            bad.append(g + ' shape')
        ar[cfg['sector']][cfg['campaign']][cfg['L']] = x
        if assemble.group_science(d) != r['science_sha256'][g]:
            sci_bad.append(g)
    ok('R', 'merged.json: complete, self-hash, plan and config binding, shape', not bad, f'bad {bad}', 'groups/*/merged.json', 'exact')
    ok('R', 'scientific identity of every group', not sci_bad, f'bad {sci_bad}', 'C8_result.json science_sha256', 'exact')
    return r, m, ar, cfgs


def step_pins(r, m):
    for n, h in r['tool_sha256'].items():
        ok('P', f'tools/{n} is the production tool', sha(ROOT / 'tools' / n) == h, h[:16], 'C8_result.json tool_sha256', 'sha256')
    a = r['assembly']
    ok('P', 'vendored assembly module', sha(ROOT / a['module']) == a['module_sha256'], a['module_sha256'][:16], 'C8_result.json assembly', 'sha256')
    ok('P', 'vendored HANDOFF', sha(ROOT / 'vendor/c8_assembly/HANDOFF_assembly.json') == a['handoff_sha256'], a['handoff_sha256'][:16],
       'C8_result.json assembly', 'sha256')
    pp = r['power_protocol']
    ok('P', 'POWER_PROTOCOL.md', sha(ROOT / pp['path']) == pp['sha256'], pp['sha256'][:16], 'C8_result.json power_protocol', 'sha256')
    im = sha(ROOT / 'inputs/manifest.json')
    ok('P', 'inputs/manifest.json is the plan\'s', im == m['inputs_manifest_sha256'], im[:16], 'manifest.json inputs_manifest_sha256', 'sha256')
    imj = jload(ROOT / 'inputs/manifest.json')
    tl = sha(ROOT / 'inputs/two_loop.json')
    ok('P', 'inputs/two_loop.json', tl == r['two_loop_sha256'] == imj['sha256']['two_loop.json'], tl[:16], 'C8_result.json two_loop_sha256', 'sha256')
    rs = sha(ROOT / 'references/lower_order_d3.json')
    ok('P', 'references/lower_order_d3.json', rs == r['references_sha256'], rs[:16], 'C8_result.json references_sha256', 'sha256')
    bad = [k for k, h in imj['sha256'].items() if (ROOT / 'inputs' / k).exists() and sha(ROOT / 'inputs' / k) != h]
    absent = [k for k in imj['sha256'] if not (ROOT / 'inputs' / k).exists()]
    ok('P', 'inputs/ files against inputs/manifest.json', not bad, f'mismatches {bad}; not in git (hosted, fetch-data): {absent}',
       'inputs/manifest.json sha256', 'sha256')


def step_assembly(r, ar, bootstrap: int, out: Path, skip_vr: bool):
    B2, _ = assemble.two_loop(8)
    c = assemble.combine(ar, 8, assemble.HALF_D, bootstrap, B2)
    c = jsonable(c)
    cm = Cmp()
    keys = [k for k in c if k not in ('schema', 'dimension', 'order', 'epsilon', 'scope')]
    for k in keys:
        if k == 'gates':
            sg = dict(r['gates'])
            cov = dict(sg['coverage'])
            cov.pop('campaign', None)
            sg['coverage'] = cov
            cm.cmp(sg, c['gates'], 'gates')
        elif k == 'bootstrap' and bootstrap != r['bootstrap']['replicates']:
            continue
        else:
            cm.cmp(r[k], c[k], k)
    ok('A', 'assemble.combine on the 24 merged batches = C8_result.json (every field)', not cm.bad,
       f'{cm.n} numbers compared, worst relative difference {cm.worst[0]:.2e} at {cm.worst[1]}; differences {cm.bad[:3]}',
       'tools/assemble.py combine (vendored order-8 assembly)', f'rel {REL:g}, abs floor {ABS:g}')
    gd = [g for g in cm.gate if not g[0].startswith('gates.hard')]
    same = sum(1 for g in gd if abs(g[1] - g[2]) <= ABS)
    ok('A', 'hard-gate rounding diagnostics below their gate thresholds (stored and recomputed)',
       all(g[1] <= g[3] and g[2] <= g[3] for g in cm.gate),
       f'{len(gd)} fields, {same} equal to 1e-13 here; largest stored {max(g[1] for g in gd):.2e}, recomputed {max(g[2] for g in gd):.2e} '
       f'(platform rounding; the note quotes the production values)', 'C8_result.json hard_gates', 'top-slot/loop-7 1e-12, affinity 1e-10')
    for k, tol in (('C8_full', 1e-12), ('sampling_standard_error', 1e-12), ('power_free_C8', 1e-12), ('power_correction', 1e-10)):
        d = abs(c[k] - r[k]) / abs(r[k])
        ok('A', f'{k} reproduced', d <= tol, f'recomputed {c[k]!r}, stored {r[k]!r}, rel {d:.1e}', 'assemble.combine', f'rel {tol:g}')
    ok('A', 'estimator digits as printed in Sec 1', repr(r['C8_full']) == STORED_EST and repr(r['sampling_standard_error']) == STORED_SE,
       f'{r["C8_full"]!r} +- {r["sampling_standard_error"]!r}', 'C8_result.json', 'repr equality')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'C8_recombined.json').write_text(json.dumps(c, indent=1) + '\n')
    # verify_result.py, file mode (directory mode needs the run tree's CSV tables, which are not shipped)
    if skip_vr:
        row('A', 'tools/verify_result.py C8_result.json', 'NOT RUN', '--skip-verify-result')
    else:
        env = dict(os.environ, OPENBLAS_CORETYPE='Zen', OPENBLAS_NUM_THREADS='1')
        p = subprocess.run([sys.executable, '-B', 'tools/verify_result.py', str(ARGS.results / 'C8_result.json')], cwd=ROOT,
                           capture_output=True, text=True, env=env)
        msg = (p.stdout.strip() or p.stderr.strip())[-300:]
        m_ = re.search(r'REJECTED: (\S+): ([0-9.e+-]+) differs from the recomputed ([0-9.e+-]+)', msg)
        if p.returncode == 0:
            row('A', 'tools/verify_result.py C8_result.json (file mode)', 'PASS', msg, 'tools/verify_result.py', 'exit 0 (its own REL 1e-10)')
        elif m_ and GATE_DIAG.search(m_.group(1).rstrip(':')) and max(float(m_.group(2)), float(m_.group(3))) <= 1e-10:
            row('A', 'tools/verify_result.py C8_result.json (file mode)', 'KNOWN',
                f'stopped at a rounding-level gate diagnostic ({m_.group(1)} {m_.group(2)} vs {m_.group(3)} on this platform); '
                'on x86-64 with OPENBLAS_CORETYPE=Zen it reproduces the production bits (C62d F6). Every other field is checked above.',
                'tools/verify_result.py', 'exit 0 on the production CPU class')
        else:
            row('A', 'tools/verify_result.py C8_result.json (file mode)', 'FAIL', msg, 'tools/verify_result.py', 'exit 0 (its own REL 1e-10)')
    return c


def step_ntrend(R: Path, out: Path):
    t = PROD1 / 'tail_ntrend'
    o = out / 'ntrend.json'
    p = subprocess.run([sys.executable, '-B', str(t / 'ntrend.py'), str(PILOT / 'evidence/pilot_report.json'), str(t / 'prod_tails.csv'),
                        str(R / 'C8_result.json'), str(o)], capture_output=True, text=True)
    if p.returncode:
        return ok('T', 'tail_ntrend/ntrend.py rerun', False, p.stderr[-300:], 'tail_ntrend/ntrend.py', 'exit 0')
    new, old = jload(o), jload(t / 'ntrend.json')
    if new == old:
        ok('T', 'tail_ntrend/ntrend.py rerun = committed ntrend.json', True, 'every row and summary equal (bitwise)',
           'tail_ntrend/ntrend.json', f'structure and non-floats exact; floats rel {NTREND_REL:g}')
    else:
        # The Hill estimates, power fits and medians are float64 results whose last bits depend on the Python and numpy
        # versions. The committed file was written with Python 3.10 and numpy 1.24 and reproduces bitwise there. With
        # Python 3.12 (whose sum() of floats rounds differently) and numpy 2.5, four floats move by up to 3.0e-15 relative,
        # on the same Mac and on Intel. Structure, counts and strings stay exact; floats get NTREND_REL, far below the
        # printed 2-3 digits.
        bad, dev = [], [0.0]
        def walk(a, b, path=''):
            if isinstance(b, dict):
                if not isinstance(a, dict) or set(a) != set(b):
                    bad.append(f'{path}: keys differ')
                else:
                    for k in b:
                        walk(a[k], b[k], f'{path}.{k}')
            elif isinstance(b, list):
                if not isinstance(a, list) or len(a) != len(b):
                    bad.append(f'{path}: length differs')
                else:
                    for i, (x, y) in enumerate(zip(a, b)):
                        walk(x, y, f'{path}[{i}]')
            elif isinstance(b, float) and isinstance(a, (int, float)) and not isinstance(a, bool):
                d = abs(a - b) / max(abs(b), 1e-300) if b else abs(a)
                dev[0] = max(dev[0], d)
                if d > NTREND_REL and abs(a - b) > 1e-15:
                    bad.append(f'{path}: {a!r} vs {b!r}')
            elif a != b:
                bad.append(f'{path}: {a!r} vs {b!r}')
        walk(new, old)
        ok('T', 'tail_ntrend/ntrend.py rerun = committed ntrend.json', not bad,
           f'not bitwise; max rel dev of floats {dev[0]:.1e}' + (f'; {bad[:3]}' if bad else ''),
           'tail_ntrend/ntrend.json', f'structure and non-floats exact; floats rel {NTREND_REL:g}')
    s = jload(o)['summary']
    ok('T', 'prod_tails.csv reproduces the tail monitor\'s listed rows', s['cross_check_vs_tail_monitor']['pass'],
       f"{s['cross_check_vs_tail_monitor']['listed_rows']} rows, max |dxi| {s['cross_check_vs_tail_monitor']['max_abs_diff_xi']:.1e}",
       'ntrend.py cross_check_vs_tail_monitor', '< 1e-12')
    return jload(o)


def linearized_split(r, ar):
    B2, _ = assemble.two_loop(8)
    oa = assemble.vendored()
    loops = range(3, 9)
    J = oa.jacobians({L: np.asarray(r['means']['free'][str(L)]) + np.asarray(r['means']['power'][str(L)]) for L in loops}, B2, 8, assemble.HALF_D)
    j8 = {L: np.asarray(J[L])[8] for L in loops}
    out = {}
    tot = tv = 0.0
    for s in ('free', 'power'):
        for L in loops:
            ya, yb = ar[s]['a'][L] @ j8[L], ar[s]['b'][L] @ j8[L]
            d = ya.mean() - yb.mean()
            v = ya.var(ddof=1) / len(ya) + yb.var(ddof=1) / len(yb)
            out[(s, L)] = (d, math.sqrt(v))
            tot += d
            tv += v
    return out, tot, math.sqrt(tv), j8


def step_hosted(R: Path, D: Path, r, out: Path, j8):
    hr = D / 'results/groups'
    have = all((hr / g / 'graph_replicates.csv').exists() for g in GROUPS if g.endswith('L8'))
    if not have:
        for what in ('graph_replicates.csv pins', 'ab_split.py rerun = committed report.txt', 'tail monitor variance shares'):
            row('H', what, 'NOT RUN', f'hosted graph_replicates.csv not fetched ({hr}); make -f public.mk fetch-data', 'GFF/data/C8_3')
        return None
    bad = [g for g in GROUPS if (hr / g / 'graph_replicates.csv').exists()
           and sha(hr / g / 'graph_replicates.csv') != jload(R / 'groups' / g / 'merged.json')['graph_replicates_sha256']]
    ok('H', 'graph_replicates.csv pins', not bad, f'mismatches {bad}', 'merged.json graph_replicates_sha256', 'sha256')
    # a view of the run with the hosted tables beside the shipped records, then the committed script, unchanged
    with tempfile.TemporaryDirectory(prefix='c8_3_ab_') as td:
        v = Path(td)
        (v / 'groups').mkdir()
        os.symlink((R / 'C8_result.json').resolve(), v / 'C8_result.json')
        for g in GROUPS:
            (v / 'groups' / g).mkdir()
            for f in ('merged.json', 'config.json'):
                os.symlink((R / 'groups' / g / f).resolve(), v / 'groups' / g / f)
            if (hr / g / 'graph_replicates.csv').exists():
                os.symlink((hr / g / 'graph_replicates.csv').resolve(), v / 'groups' / g / 'graph_replicates.csv')
        p = subprocess.run([sys.executable, '-B', str(PROD1 / 'ab_split/ab_split.py'), str(v), str(PROD1 / 'tail_ntrend/prod_tails.csv')],
                           cwd=ROOT, capture_output=True, text=True)
        (out / 'ab_split_report.txt').write_text(p.stdout)
        ok('H', 'ab_split.py rerun = committed report.txt', p.returncode == 0 and p.stdout == (PROD1 / 'ab_split/report.txt').read_text(),
           'identical text' if p.stdout == (PROD1 / 'ab_split/report.txt').read_text() else (p.stderr[-200:] or 'text differs (see ab_split_report.txt)'),
           'prod1/ab_split/report.txt', 'byte-identical text')
    # tail monitor shares (assemble.tail_monitor's formula, L8 graph_replicates only)
    shares = {}
    for c in 'ab':
        for s in ('free', 'power'):
            vals = {}
            with open(hr / f'{c}_{s}_L8' / 'graph_replicates.csv') as f:
                for x in csv.DictReader(f):
                    vals.setdefault(int(x['graph']), []).append(float(np.dot(j8[8], [float(x['jet_0']), float(x['jet_1'])])))
            var = {g: float(np.var(v, ddof=1)) if len(v) > 1 else 0. for g, v in vals.items()}
            tot = sum(var.values())
            for g, v in var.items():
                shares[(c, s, g)] = v / tot if tot > 0 else None
    worst = 0.0
    for x in r['tail_monitor']['listed']:
        for c in 'ab':
            a, b = x['share'][c], shares.get((c, x['sector'], x['graph']))
            if a is None or b is None:
                worst = math.inf if a != b else worst
            else:
                worst = max(worst, abs(a - b) / max(abs(a), 1e-300))
    ok('H', 'tail monitor variance shares recomputed', worst <= 1e-10, f'{len(r["tail_monitor"]["listed"])} listed rows, worst rel {worst:.1e}',
       'C8_result.json tail_monitor.listed[].share', 'rel 1e-10')
    return True


# ------------------------------------------------------------------------------------------------- note numbers
def step_note(r, m, cfgs, c, split, nt):
    res = 'results/C8_3/C8_result.json'
    C8, SE = r['C8_full'], r['sampling_standard_error']
    refs = {e['order']: e for e in jload(ROOT / 'references/lower_order_d3.json')['coefficients']}
    # --- abstract, Section 1 tables, the allowance rule
    qnum('S1.1', 'abstract, Sec 1 table, 32.1 box', '1602.6', C8, res)
    allow = math.ceil(round(4 * SE / 0.1, 9)) * 0.1
    qnum('S1.2', 'abstract, Sec 1 table, 32.1 box: allowance = 4 SE rounded up to 0.1', '3.9', allow, res + ' (4 x sampling_standard_error)', tol=1e-9)
    ok('N', 'S1.3 [Sec 1 estimator table] 1602.6052229663408, 0.9516489064', repr(C8) == STORED_EST and abs(SE - 0.9516489064) < 5e-11,
       f'{C8!r}, {SE!r}', res, 'repr / 10 digits')
    hs = [h[8] for h in r['half_streams']]
    dev = [abs(h - C8) for h in hs]
    qnum('S1.4', '32.1: 4 SE', '3.81', 4 * SE, res)
    qnum('S1.5', '32.1, Sec 1 allowance text: half-stream deviations', '0.046', max(dev), res + ' half_streams[*][8]')
    qtrue('S1.6', 'Sec 1, 32.1', '4 SE exceeds both half-stream deviations', 4 * SE > max(dev), f'4 SE {4*SE:.4f} > {max(dev):.4f}', res)
    qnum('S1.7', '32.1: the record quotes', '1.0', SE, res)
    # the paper quotes the same 4 SE rounded by the PDG rule (three leading digits 100-354: two significant digits,
    # 355-949: one, 950-999: up to 1000 with two), the value rounded to the error's last digit
    e = 4 * SE
    k = math.floor(math.log10(e))
    lead = int(e / 10 ** (k - 2))
    nsig, ee, kk = (2, e, k) if lead <= 354 else (1, e, k) if lead <= 949 else (2, 10 ** (k + 1), k + 1)
    dec = nsig - 1 - kk
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal(1).scaleb(-dec)
    pdg = f"{Decimal(repr(C8)).quantize(q, rounding=ROUND_HALF_UP)} +- {Decimal(repr(ee)).quantize(q, rounding=ROUND_HALF_UP)}"
    ok('N', 'S1.8 [paper \\CeightThree, PDG rounding of 4 SE] 1603 +- 4', pdg == '1603 +- 4', f'{pdg} (4 SE = {e:.4f})', res, 'string equality')
    # --- 32.1 table
    for sid, q, v in (('32.1a', '1601.9999290', r['power_free_C8']), ('32.1b', '0.7279030', r['power_free_se']),
                      ('32.1c', '0.6052940', r['power_correction']), ('32.1d', '0.6129303', r['power_correction_se']),
                      ('32.1e', '1602.6052230', C8), ('32.1f', '0.9516489', SE)):
        qnum(sid, '32.1 table', q, v, res)
    pr = jload(PILOT / 'evidence/pilot_report.json')
    pc8, pse = pr['cost_table']['c8_pilot'], pr['cost_table']['c8_pilot_se']
    qnum('32.1g', '32.1, 32.3: pilot', '1619', pc8, 'pilot/evidence/pilot_report.json cost_table.c8_pilot')
    qnum('32.1h', '32.1, 32.3: pilot SE', '16', pse, 'pilot_report.json cost_table.c8_pilot_se')
    qnum('32.1i', '32.1: pilot vs production (combined SE)', '1.05', (pc8 - C8) / math.hypot(pse, SE), 'pilot_report.json + ' + res)
    c7 = refs[7]['value']
    qnum('32.1j', '32.1: C8(3)/C7(3)', '-7.27', C8 / c7, res + ' + references/lower_order_d3.json (C7(3) estimator)')
    seq = [r['coefficients'][2]] + [refs[k]['value'] for k in (3, 4, 5, 6, 7)]
    for i, q in enumerate(('-1.95', '-3.47', '-4.76', '-5.74', '-6.56')):
        qnum(f'32.1k{i+3}', f'32.1: C{i+3}/C{i+2}', q, seq[i + 1] / seq[i], 'references/lower_order_d3.json; C2 = coefficients[2] (exact input)')
    row('N', '32.1l [32.1, Sec 1, Sec 32.7] independent code 1600.98 +- 3.97, -0.40', 'INFO', 'covered by GFF/code C8_3_check (other package)', '')
    # --- 32.2
    cnt = {(cfg['sector'], cfg['L']): len(cfg['counts']) for g, cfg in cfgs.items() if cfg['campaign'] == 'a'}
    same = all(len(cfgs[f'b_{s}_L{L}']['counts']) == cnt[(s, L)] for (s, L) in cnt)
    for s, qs in (('free', ('5', '16', '76', '395', '2,441', '16,064')), ('power', ('1', '3', '20', '107', '709', '4,336'))):
        for L, q in zip(range(3, 9), qs):
            qint(f'32.2a.{s}{L}', '32.2 integrated classes', q, cnt[(s, L)], 'results/C8_3/groups/a_*/config.json counts (b equal: %s)' % same)
    qint('32.2b', '32.2', '24,173', sum(cnt.values()), 'group configs; = inputs/manifest.json kernels')
    qint('32.2b2', '32.2 (inputs)', '24,173', jload(ROOT / 'inputs/manifest.json')['kernels'], 'inputs/manifest.json')
    b = r['build']
    qtrue('32.2c', '32.2', 'sixteen propagators, 31-dimensional nets, 350-digit GMP', b['emax'] == 16 and b['dimmax'] == 31 and b['mp_digits10'] == 350,
          f"emax {b['emax']}, dimmax {b['dimmax']}, mp_digits10 {b['mp_digits10']}", res + ' build')
    v2 = jload(EV / 'stage6_a914db2/val2/validate_full.json')
    gc7 = [t for t in v2['tests'] if t.get('test') == 'G-C7'][0]
    qtrue('32.2d', '32.2', 'order 7 bit for bit with the C7(3) worker on the L2 graph and the 3,511 C7(3) kernels',
          v2['status'] == 'passed' and gc7['l2_graph'] and gc7['kernels_c7d3'] >= 3511,
          f"J-VAL-2 570904 on the final code: {v2['status']}, G-C7 exact over {gc7['kernels_c7d3']} L<=7 kernels (the 3,511 C7(3) ones and the 262 new L7 ones) + L2",
          'benchmarks/symmetry_2026-10-c8/stage6_a914db2/val2/validate_full.json')
    sr = jload(EV / 'stage5_3cbe7a4/run1/archived_stream_replay.json')
    qtrue('32.2e', '32.2', 'replays the archived seventh-order production', sr['status'] == 'passed' and sr['rows'] == sr['rows_expected'] == 168528,
          f"{sr['rows']} rows, C7 rebuilt rel {sr['relative_C7_difference']:.1e}", 'benchmarks/symmetry_2026-10-c8/stage5_3cbe7a4/run1/archived_stream_replay.json')
    num = (ROOT / 'docs/NUMERICS.md').read_text()
    qtrue('32.2f', '32.2', 'AMD vs Intel at most 2.0e-11 normalized', '≤ 2.0e-11 normalized' in num, 'symmetry job 566410 as recorded', 'docs/NUMERICS.md "CPU dependence (measured)"')
    cv = jload(ARGS.results / 'cpu_vendor.json')
    qtrue('32.2g', '32.2', 'every production job on one processor model (AMD EPYC 7543)', cv['vendor'] == 'amd' and m.get('fingerprint') is not None,
          f"cpu_vendor.json vendor {cv['vendor']}; the CPU pin (slurm/site.sh c8_cpu_guard, EPYC 7543) and prod1/README.md", 'results/C8_3/cpu_vendor.json')
    tl = jload(ROOT / 'inputs/two_loop.json')['B2']
    ok('N', '32.2h [32.2] b_{2,6}(3) = -29.258124480916806558671227221989158045345...', tl[6].startswith('-29.258124480916806558671227221989158045345'),
       tl[6][:45], 'inputs/two_loop.json B2[6]', 'printed digits')
    ck = jload(ROOT / 'vendor/c8_assembly/inputs_d3/checks.json')
    qnum('32.2i', '32.2: two contours at 65 digits agree to', '2.7e-56', float(ck['two_loop']['two_contour_max']), 'vendor/c8_assembly/inputs_d3/checks.json', tol=0.05e-56)
    qtrue('32.2i2', '32.2', 'the contours are at 65 digits; reference at 95 digits', ck['settings']['dps'] == 65 and ck['settings']['reference_contour']['dps'] == 95,
          f"dps {ck['settings']['dps']}, reference dps {ck['settings']['reference_contour']['dps']}", 'checks.json settings')
    qnum('32.2j', '32.2: reference confirms stored entries to', '1.7e-57', float(ck['two_loop']['stored_vs_reference_max']), 'checks.json', tol=0.05e-57)
    gch = ck['gamma']['cauchy_check']
    qtrue('32.2k', '32.2', '42 Gamma jets correctly rounded, two contours at 100 digits', gch['jets_checked'] == 42 and gch['all_printed_tokens_correctly_rounded']
          and '100 digits' in gch['method'], f"{gch['jets_checked']} jets, {gch['method'][:60]}", 'checks.json gamma.cauchy_check')
    qtrue('32.2l', '32.2', 'b_3^p(0) = -16 pi/15', abs(r['b3p_control']['reference'] + 16 * math.pi / 15) < 1e-15, r['b3p_control']['reference_text'], res)
    qnum('32.2m', '32.2: b_3^p(0) estimate', '-3.3509158', r['b3p_control']['estimate'], res)
    qnum('32.2n', '32.2: its SE', '0.0000894', r['b3p_control']['se'], res)
    qnum('32.2o', '32.2: its pull', '+1.30', r['b3p_control']['pull'], res)
    hg = r['hard_gates']
    ts = hg['top_slot']['rows']
    qtrue('32.2p', '32.2', 'dC8/d(b,c)_{L,8-L} = (-1,3)/3^(L+1)', all(abs(x['dC_db'] + 1 / 3 ** (x['L'] + 1)) <= 1e-15 and abs(x['dC_dc'] - 3 / 3 ** (x['L'] + 1)) <= 1e-15 for x in ts),
          'six rows', res + ' hard_gates.top_slot')
    qnum('32.2q', '32.2: top-slot gate holds to', '4e-16', max(x['rel_deviation'] for x in ts), res, tol=0.5e-16)
    qnum('32.2r', '32.2: A_3 = -b_{2,0}/6', '1.6309960686', hg['loop7']['A_d'], res + ' hard_gates.loop7')
    qnum('32.2r2', '32.2: A_3 from inputs/two_loop.json', '1.6309960686', -float(tl[0]) / 6, 'inputs/two_loop.json B2[0]')
    A3 = hg['loop7']['A_d']
    qtrue('32.2s', '32.2', 'loop 7 enters through (-16 A3, 42 A3)/19683', abs(hg['loop7']['expected'][0] + 16 * A3 / 19683) < 1e-15 and abs(hg['loop7']['expected'][1] - 42 * A3 / 19683) < 1e-15,
          f"expected {hg['loop7']['expected']}", res)
    qnum('32.2t', '32.2: loop-7 gate holds to', '8e-16', hg['loop7']['rel_deviation'], res, tol=0.5e-16)
    qnum('32.2u', '32.2: response to loops 5-8 linear to', '3e-13', max(hg['affinity']['linear_response_residual']), res, tol=0.5e-13)
    qtrue('32.2v', '32.2', 'the three hard gates pass', not r['gates']['pp8'] and all(x['rel_deviation'] <= 1e-10 for x in ts), 'gates block', res)
    # --- 32.3 pilot and design
    a2 = jload(PILOT / 'campaigns/pilotA2-s6-20261007/subset_summary.json')
    qint('32.3a', '32.3: screen graphs', '2,732', a2['graphs'] // 2, 'pilot/campaigns/pilotA2-s6-20261007/subset_summary.json (graphs over both campaigns / 2)')
    a2m = jload(PILOT / 'campaigns/pilotA2-s6-20261007/manifest.json')['allocation']
    qint('32.3b', '32.3: screen points per replicate', '4,096', a2m['points'], 'pilotA2 manifest.json allocation')
    pfm = jload(PILOT / 'campaigns/pilotF-s6-20261007/manifest.json')['allocation']
    qtrue('32.3c', '32.3', 'full pilot: 8 replicates of 4,096 points, 16 for power L8', pfm['points'] == 4096 and pfm['replicates'] == 8 and pfm['group_replicates'] == {'power:8': 16},
          json.dumps(pfm)[:120], 'pilotF manifest.json allocation')
    pcs = jload(PILOT / 'campaigns/pilotC-s6-20261008/subset_summary.json')
    qint('32.3d', '32.3: confirmation graphs', '710', pcs['graphs'] // 2, 'pilotC subset_summary.json')
    qnum('32.3e', '32.3: cap a quarter of the full pilot L8 cost', '0.25', pr['pc_cap']['fraction'], 'pilot_report.json pc_cap', tol=0)
    qtrue('32.3e2', '32.3', 'the confirmation stayed within its cap', pr['pc_cap']['within_cap_at_current'], f"used {pr['pc_cap']['used_seconds']:.0f} s of {pr['pc_cap']['recorded_pf_l8_seconds']*0.25:.0f} s", 'pilot_report.json pc_cap')
    bud = (PROD1 / 'c8d3_prod1_budget.txt').read_text()
    pil = float(re.search(r'pilot\s+spent\s+([\d.]+)', bud).group(1))
    qnum('32.3f', '32.3: the pilot used', '422', pil, 'prod1/c8d3_prod1_budget.txt (pilot line)')
    qint('32.3g', '32.3: replicates per group', '128', min(cfg['replicates'] for cfg in cfgs.values()), 'group configs (all 24 equal: %s)' % (len({cfg['replicates'] for cfg in cfgs.values()}) == 1))
    qint('32.3h', '32.3: at least points per graph', '4,096', min(min(cfg['counts'].values()) for cfg in cfgs.values()), 'group configs counts')
    fz = jload(PROD1 / 'production/design_freeze.json')
    qnum('32.3i', '32.3: predicted SE', '0.87', fz['prediction']['se_total'], 'prod1/production/design_freeze.json')
    qnum('32.3j', '32.3: with the safety factor 1.5', '1.31', 1.5 * fz['prediction']['se_total'], 'design_freeze.json x 1.5')
    qnum('32.3k', '32.3: estimated cost (core-h)', '15,492', fz['prediction']['cost_total_core_hours'], 'design_freeze.json')
    dmeta = jload(PROD1 / 'production/design_prod/design_meta.json')
    qnum('32.3l', '32.3: target SE', '1', dmeta['target_se'], 'design_prod/design_meta.json', tol=0)
    qnum('32.3l2', '32.3: about 6e-4 of C8(3)', '6e-4', dmeta['target_se'] / C8, 'target / C8', tol=0.5e-4)
    pv = {}
    for f, k in (('se1_pc_m10', 'A'), ('se115_pc_m15', 'B'), ('se1_pc_m15', 'C')):
        pv[k] = jload(PROD / 'price' / f'{f}.json')['rows'][-1]['cost_total_core_hours']
    qtrue('32.3m', '32.3', 'the cheapest of three power-of-two designs', pv['A'] < pv['B'] < pv['C'] and abs(pv['A'] - fz['prediction']['cost_total_core_hours']) < 1e-6,
          f"A {pv['A']:.1f}, B {pv['B']:.1f}, C {pv['C']:.1f} core-h", 'production/price/*.json (last row of each)')
    rates = {cfg['campaign']: (cfg['rate'], cfg['net']['bits']) for cfg in cfgs.values()}
    one = all((cfg['rate'], cfg['net']['bits']) == rates[cfg['campaign']] for cfg in cfgs.values())
    qtrue('32.3n', '32.3', 'campaigns a, b: rates x0.8, x0.7; 52- and 60-bit nets', one and rates == {'a': ('.8', 52), 'b': ('.7', 60)}, str(rates), 'group configs rate, net.bits')
    pilot_seeds = {jload(PILOT / f'campaigns/{d}/manifest.json')['seed'] for d in ('pilotA2-s6-20261007', 'pilotF-s6-20261007', 'pilotC-s6-20261008')}
    qtrue('32.3o', '32.3', 'fresh base seed (not a pilot seed)', m['seed'] not in pilot_seeds, f"seed {m['seed']}", 'manifest.json seed; pilot manifests')
    qint('32.3p', '32.3: kernel samples in the design', '365,441,318,912', sum(cfg['samples'] for cfg in cfgs.values()), 'group configs samples (sum)')
    # --- 32.4 production
    jobs = list(csv.DictReader(open(PROD1 / 'jobs_sacct.psv'), delimiter='|'))
    lanes = [j for j in jobs if 'prod_lane' in j['JobName']]
    merges = [j for j in jobs if 'prod_merge' in j['JobName']]
    ch = lambda js: sum(int(j['ElapsedRaw']) * int(j['AllocCPUS']) for j in js) / 3600  # noqa: E731
    ran = [j for j in lanes if int(j['ElapsedRaw']) > 0]
    qtrue('32.4a', '32.4', '9 to 12 October 2026', min(j['Start'] for j in ran)[:10] == '2026-10-09' and max(j['End'] for j in ran)[:10] == '2026-10-12',
          f"{min(j['Start'] for j in ran)} .. {max(j['End'] for j in ran)}", 'prod1/jobs_sacct.psv')
    qint('32.4b', '32.4: lanes of threads', '8', m['threads'], 'manifest.json threads')
    ev = sorted([(j['Start'], 1) for j in ran] + [(j['End'], -1) for j in ran])
    k = mx = 0
    for _, d in ev:
        k += d
        mx = max(mx, k)
    qint('32.4c', '32.4: at most nodes at a time', '8', mx, 'jobs_sacct.psv (overlapping lane jobs, one whole node each)')
    nodes = {n for j in ran for n in j['NodeList'].split(',')}
    if any(n.startswith('<') for n in nodes):   # a privacy scrub replaced the node names: the count is not recoverable
        row('N', '32.4d [32.4: nodes in all] 10', 'NOT RUN', 'node names scrubbed in jobs_sacct.psv', 'jobs_sacct.psv NodeList', 'exact')
    else:
        qint('32.4d', '32.4: nodes in all', '10', len(nodes), 'jobs_sacct.psv NodeList')
    qtrue('32.4d2', '32.4', 'whole nodes (64 CPUs) of the AMD partition', all(int(j['AllocCPUS']) == 64 and j['Partition'] == 'amdq' for j in ran), '', 'jobs_sacct.psv')
    qint('32.4e', '32.4: work indices', '1,941', len(m['jobs']), 'manifest.json jobs')
    qint('32.4f', '32.4: checkpoint blocks', '25,714', sum(j['blocks'] for j in m['jobs']), 'manifest.json jobs[].blocks')
    st = (PROD1 / 'c8d3_prod1_status.txt').read_text()
    qtrue('32.4g', '32.4', 'all indices and blocks completed', 'complete: every checkpoint block is committed' in st and st.count('merged') == 24, '24 groups merged', 'prod1/c8d3_prod1_status.txt')
    qnum('32.4h', '32.4: lane core-hours', '14,970', ch(lanes), 'jobs_sacct.psv (ElapsedRaw x AllocCPUS)')
    qnum('32.4i', '32.4: of the design estimate', '0.97', ch(lanes) / fz['prediction']['cost_total_core_hours'], 'jobs_sacct.psv / design_freeze.json')
    qnum('32.4j', '32.4: merges (core-h)', '106', ch(merges), 'jobs_sacct.psv')
    prod_line = float(re.search(r'production\s+spent\s+([\d.]+)', bud).group(1))
    qnum('32.4k', '32.4: production in all (core-h)', '15,102', prod_line, 'prod1/c8d3_prod1_budget.txt (production line)')
    ca, cb = r['campaigns']['a'], r['campaigns']['b']
    for sid, q, v in (('32.4l', '1604.684', ca['C8']), ('32.4m', '1.239', ca['sampling_se']), ('32.4n', '1600.527', cb['C8']),
                      ('32.4o', '1.445', cb['sampling_se']), ('32.4p', '1602.651', hs[0]), ('32.4q', '1602.559', hs[1]),
                      ('32.4r', '1602.605', C8), ('32.4s', '0.952', SE)):
        qnum(sid, '32.4 table', q, v, res)
    qnum('32.4t', '32.4: campaigns differ by (combined SE)', '2.18', (ca['C8'] - cb['C8']) / math.hypot(ca['sampling_se'], cb['sampling_se']), res)
    sp, tot, tse, _ = split
    qnum('32.4u', '32.4: linearized a - b', '4.16', tot, 'replay (ab_split.py method: j8 . batch means)')
    qnum('32.4v', '32.4: its SE', '1.90', tse, 'replay')
    qnum('32.4w', '32.4: total exact a - b', '4.16', ca['C8'] - cb['C8'], res)
    qnum('32.4x', '32.4: power-free L8', '+1.36', sp[('free', 8)][0], 'replay')
    qnum('32.4y', '32.4: power L8', '+1.39', sp[('power', 8)][0], 'replay')
    qnum('32.4z', '32.4: power-free L7', '+0.90', sp[('free', 7)][0], 'replay')
    qnum('32.4aa', '32.4: power-free L5', '+0.19', sp[('free', 5)][0], 'replay')
    qnum('32.4ab', '32.4: its SE', '0.10', sp[('free', 5)][1], 'replay')
    mp = max(abs(d / s) for d, s in sp.values())
    qtrue('32.4ac', '32.4', 'no term above two of its own SEs (to the printed 2.00)', round(mp, 2) <= 2.0,
          f'largest |pull| {mp:.4f} (free L5; ab_split/report.txt prints +2.00)', 'replay')
    rep = (PROD1 / 'ab_split/report.txt').read_text()
    g1 = re.search(r'free: sum over 16064 graphs.*?ratio ([\d.]+)\); top-10 sum ([+-][\d.]+)', rep, re.S)
    g2 = re.search(r'power: sum over 4336 graphs.*?ratio ([\d.]+)\); top-10 sum ([+-][\d.]+)', rep, re.S)
    src_rep = 'prod1/ab_split/report.txt (recomputed by step H when the hosted graph_replicates.csv are fetched)'
    qnum('32.4ad', '32.4: chi2 per graph, 16,064 power-free', '0.994', float(g1.group(1)), src_rep)
    qnum('32.4ae', '32.4: chi2 per graph, 4,336 power', '1.010', float(g2.group(1)), src_rep)
    qnum('32.4af', '32.4: ten largest carry (free)', '+0.19', float(g1.group(2)), src_rep)
    qnum('32.4ag', '32.4: ten largest carry (power)', '-0.07', float(g2.group(2)), src_rep)
    ebl = r['error_by_loop']
    for s, qs in (('free', ('0.001', '0.011', '0.048', '0.160', '0.362', '0.609')), ('power', ('0.000', '0.003', '0.018', '0.079', '0.220', '0.566'))):
        for L, q in zip(range(3, 9), qs):
            qnum(f'32.4ah.{s}{L}', '32.4 error table', q, ebl[s][str(L)]['se'], res + ' error_by_loop')
    qnum('32.4ai', '32.4: realized SE / design prediction', '1.09', SE / fz['prediction']['se_total'], res + ' + design_freeze.json')
    # --- 32.5 tails
    tm = r['tail_monitor']
    qint('32.5a', '32.5: listed eight-loop graphs', '10,034', len(tm['listed']), res + ' tail_monitor')
    qnum('32.5b', '32.5: largest variance share (%)', '1.65', 100 * max(v for x in tm['listed'] for v in x['share'].values() if v is not None), res)
    qint('32.5c', '32.5: flagged above 3%', '0', len(tm['flags']), res)
    sh = {(s, cc): sum((x['share'][cc] or 0) for x in tm['listed'] if x['sector'] == s) for s in ('free', 'power') for cc in 'ab'}
    qnum('32.5d', '32.5: listed share of power-free L8 variance (%), campaign a', '62', 100 * sh[('free', 'a')], res + f" (campaign b: {100*sh[('free','b')]:.1f})")
    qnum('32.5e', '32.5: listed share of power L8 variance (%), campaign a', '99.5', 100 * sh[('power', 'a')], res + f" (campaign b: {100*sh[('power','b')]:.1f})")
    p1 = jload(PROD / 'margin_probe1/margin_report_571479.json')
    p2 = jload(PROD / 'margin_probe2/margin_report_571516.json')
    qint('32.5f', '32.5: rates re-derived on graphs', '48', len(p1['graphs']) + len(p2['graphs']), 'production/margin_probe{1,2}/margin_report_*.json')
    roles = [g['role'] for g in p1['graphs']] + [g['role'] for g in p2['graphs']]
    qint('32.5g', '32.5: the two controls (per sector) + ', '4', roles.count('control'), 'margin_report_571479.json roles (2 per sector)')
    steady = [g['key'] for g in p2['graphs']] + [g['key'] for g in p1['graphs'] if g['key'].startswith('power:8:') and int(g['key'].split(':')[2]) in
                                                 (10091, 14810, 20760, 3974, 5008, 6987, 9992, 10044, 11017, 11840, 14775, 14792, 19545, 21810, 26175, 26482)]
    qint('32.5h', '32.5: power L8 graphs whose xi did not fall', '16', len(set(steady)), 'margin reports (14 in probe 2, the others in probe 1)')
    qint('32.5i', '32.5: apparent deficits', '5', p1['deficits'] + p2['deficits'], 'margin_report_571479.json deficits')
    ld = jload(PROD / 'margin_ladder/ladder_571518.json')
    e0 = [lv['ladder'][0]['exponent'] for lv in ld['levels']]
    e1 = [lv['ladder'][-1]['exponent'] for lv in ld['levels']]
    flips = [sum(1 for a, b2 in zip(lv['ladder'], lv['ladder'][1:]) if (a['sign_lo'], a['sign_hi']) != (b2['sign_lo'], b2['sign_hi'])) for lv in ld['levels']]
    qtrue('32.5j', '32.5', 'crossovers t^1.5 -> t^1.0 with a zero in between; asymptotic exponent 1.0', all(abs(x - 1.5) < 1e-5 for x in e0) and all(abs(x - 1.0) < 1e-9 for x in e1) and all(f >= 1 for f in flips),
          f'{len(ld["levels"])} deficit levels: start {min(e0):.6f}..{max(e0):.6f}, end {min(e1):.12f}..{max(e1):.12f}, sign changes {min(flips)}..{max(flips)}',
          'production/margin_ladder/ladder_571518.json')
    s = nt['summary']
    piv = {(x['sector'], x['graph']) for x in pr['action2_confirm']['possible_infinite_variance']}
    qint('32.5k', '32.5: confirmed possible infinite-variance graphs', '441', len(piv), 'pilot_report.json action2_confirm')
    qint('32.5l', '32.5: of them power-free', '246', sum(1 for x in piv if x[0] == 'free'), 'pilot_report.json')
    qint('32.5m', '32.5: power', '195', sum(1 for x in piv if x[0] == 'power'), 'pilot_report.json')
    rows_nt = nt['rows']
    for sec, q in (('free', '-0.23'), ('power', '-0.18')):
        meds = [s[f'piv_{sec}_{cc}']['beta_pf_pc']['median'] for cc in 'ab']
        lo_, hi_ = min(meds) - 0.005, max(meds) + 0.005
        qtrue(f'32.5n.{sec}', f'32.5: pilot exponent PF->PC ({sec}), "about N^{q}"', f'{q} within the two campaigns\' medians',
              lo_ <= float(q) <= hi_, f'medians over the confirmed graphs: a {meds[0]:.3f}, b {meds[1]:.3f} (pilot log: "{q} (a)")',
              'ntrend.json summary.piv_*.beta_pf_pc (pilot PF 4,096 -> PC 32,768)')
    inter = [v for sec in ('free', 'power') for cc in 'ab' for n, v in s[f'piv_{sec}_{cc}']['new_n']['by_n'].items() if v['role'] == 'interpolation']
    extra = [v for sec in ('free', 'power') for cc in 'ab' for n, v in s[f'piv_{sec}_{cc}']['new_n']['by_n'].items() if v['role'] == 'extrapolation']
    lo = min(v['ratio_to_trend']['median'] for v in inter)
    hi = max(v['ratio_to_trend']['median'] for v in inter)
    qnum('32.5o', '32.5: interpolation medians / trend, low', '0.996', lo, 'ntrend.json summary.*.new_n.by_n')
    qnum('32.5p', '32.5: high', '1.031', hi, 'ntrend.json')
    lo = min(v['ratio_to_xi_32768']['median'] for v in inter)
    hi = max(v['ratio_to_xi_32768']['median'] for v in inter)
    qnum('32.5q', '32.5: above the pilot 32,768 value, low (%)', '13', 100 * (lo - 1), 'ntrend.json')
    qnum('32.5r', '32.5: high (%)', '38', 100 * (hi - 1), 'ntrend.json')
    qint('32.5s', '32.5: graph-campaigns at 65,536', '13', sum(v['graph_campaigns'] for v in extra), 'ntrend.json')
    qnum('32.5t', '32.5: their medians / xi(32,768), low', '0.82', min(v['ratio_to_xi_32768']['median'] for v in extra), 'ntrend.json')
    qnum('32.5u', '32.5: high', '0.88', max(v['ratio_to_xi_32768']['median'] for v in extra), 'ntrend.json')
    qnum('32.5v', '32.5: / extrapolated trend, low', '0.94', min(v['ratio_to_trend']['median'] for v in extra), 'ntrend.json')
    qnum('32.5w', '32.5: high', '1.02', max(v['ratio_to_trend']['median'] for v in extra), 'ntrend.json')
    fs = s['ab_shift_free']
    tab = [k for k in fs if k.startswith('prod_N') and fs[k]['observed_xi_b_minus_a']['n'] >= 10]   # the tabulated lengths (README)
    matched = [fs[k]['observed_xi_b_minus_a']['median'] for k in tab]
    qnum('32.5x', '32.5: free campaign shift at matched length, low', '+0.03', min(matched), 'ntrend.json ab_shift_free (production lengths)')
    qnum('32.5y', '32.5: high', '+0.05', max(matched), 'ntrend.json ab_shift_free')
    face = [fs[k]['face_model_median'] for k in tab]
    qtrue('32.5z', '32.5', 'opposite in sign to the rate-limited prediction', all(x > 0 for x in matched) and all(y < 0 for y in face), f'observed {matched}, model {face}', 'ntrend.json')
    # --- 32.6 checks
    lo_ = {x['order']: x for x in r['lower_order_checks']}
    for o, qe, qs, qp in ((3, '-0.3535809354', '1.38e-6', '+0.43'), (4, '1.2280445577', '3.88e-5', '-0.49'), (5, '-5.8499922821', '4.86e-4', '+0.74'),
                          (6, '33.5763740', '0.0050853', '+0.19'), (7, '-220.3847628', '0.0528950', '-0.49')):
        qnum(f'32.6a{o}', f'32.6 table: C{o} estimate', qe, lo_[o]['estimate'], res + ' lower_order_checks')
        qnum(f'32.6b{o}', f'32.6 table: C{o} SE', qs, lo_[o]['sampling_se'], res)
        qnum(f'32.6c{o}', f'32.6 table: C{o} pull', qp, lo_[o]['pull'], res)
    qtrue('32.6d', '32.6', 'no pull above three', all(abs(x['pull']) <= 3 for x in r['lower_order_checks']), '', res)
    pd, pe = r['power_differences'], r['power_difference_errors']
    for o, q1, q2 in ((4, '8.6e-6', '7.3e-6'), (5, '9.2e-5', '13.1e-5'), (6, '3.3e-4', '19.5e-4'), (7, '0.009', '0.024'), (8, '0.61', '0.61')):
        qnum(f'32.6e{o}', f'32.6: power correction at order {o}', q1, pd[o], res + ' power_differences')
        qnum(f'32.6f{o}', f'32.6: its SE', q2, pe[o], res + ' power_difference_errors')
    qtrue('32.6g', '32.6', 'order 3 difference at rounding level', abs(pd[3]) < 1e-12, f'{pd[3]!r}', res)
    qint('32.6h', '32.6: bootstrap resamples', '4,096', r['bootstrap']['replicates'], res)
    qnum('32.6i', '32.6: bootstrap SE', '0.940', r['bootstrap']['full_se'][8], res)
    qnum('32.6j', '32.6: covariance SE', '0.952', SE, res)
    if c is not None:
        qnum('32.6k', '32.6: bootstrap SE (replayed)', '0.940', c['bootstrap']['full_se'][8], 'replay (assemble.combine, seed 70530413)')


def write_report(out: Path, args):
    out.mkdir(parents=True, exist_ok=True)
    n = {s: sum(1 for r in ROWS if r['status'] == s) for s in ('PASS', 'FAIL', 'NOT RUN', 'KNOWN', 'ERRATUM', 'INFO')}
    lines = ['# C8(3) replay', '',
             f'Package: {ROOT}', f'Results: {args.results}', f'Data: {args.data}',
             f'Python {sys.version.split()[0]}, NumPy {np.__version__}, platform {sys.platform}', '',
             f'**{n["PASS"]} PASS, {n["FAIL"]} FAIL, {n["NOT RUN"]} NOT RUN, {n["KNOWN"]} KNOWN, {n["ERRATUM"]} ERRATUM, {n["INFO"]} INFO**', '',
             'KNOWN: a platform-dependent rounding difference of a zero-level diagnostic, explained in the row. ERRATUM: a number of the note '
             'that the record does not support at the printed precision; the corrected text is checked in the next row. NOT RUN: needs hosted '
             'data (make -f public.mk fetch-data). Only FAIL fails.', '',
             '| step | check | status | detail | source | tolerance |', '|---|---|---|---|---|---|']
    for r in ROWS:
        cell = lambda x: str(x).replace('|', '/').replace('\n', ' ')  # noqa: E731
        lines.append(f"| {r['step']} | {cell(r['what'])} | {r['status']} | {cell(r['detail'])} | {cell(r['source'])} | {cell(r['tol'])} |")
    (out / 'REPLAY.md').write_text('\n'.join(lines) + '\n')
    (out / 'replay.json').write_text(json.dumps({'counts': n, 'rows': ROWS}, indent=1) + '\n')
    print(f'\nREPLAY: {n["PASS"]} PASS, {n["FAIL"]} FAIL, {n["NOT RUN"]} NOT RUN, {n["KNOWN"]} KNOWN, {n["ERRATUM"]} ERRATUM, {n["INFO"]} INFO -> {out / "REPLAY.md"}')
    return n['FAIL']


def main(argv=None):
    global ARGS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results', type=Path, default=ROOT / '../../results/C8_3')
    ap.add_argument('--data', type=Path, default=ROOT / '../../data/C8_3')
    ap.add_argument('--out', type=Path, default=ROOT / '.public_out/replay')
    ap.add_argument('--bootstrap', type=int, default=4096)
    ap.add_argument('--skip-verify-result', action='store_true')
    ARGS = ap.parse_args(argv)
    ARGS.results, ARGS.data, ARGS.out = ARGS.results.resolve(), ARGS.data.resolve(), ARGS.out.resolve()
    if ARGS.out.exists():
        shutil.rmtree(ARGS.out)
    ARGS.out.mkdir(parents=True)
    try:
        step_package()
        r, m, ar, cfgs = step_records(ARGS.results, ARGS.data)
        step_pins(r, m)
        c = step_assembly(r, ar, ARGS.bootstrap, ARGS.out, ARGS.skip_verify_result)
        nt = step_ntrend(ARGS.results, ARGS.out)
        split = linearized_split(r, ar)
        step_hosted(ARGS.results, ARGS.data, r, ARGS.out, split[3])
        step_note(r, m, cfgs, c, split, nt)
    except Exception as e:  # a crash is a FAIL row, and the table is still written
        import traceback
        row('X', 'replay crashed', 'FAIL', f'{type(e).__name__}: {e}', traceback.format_exc().splitlines()[-3][:200])
    return 1 if write_report(ARGS.out, ARGS) else 0


ARGS = None
if __name__ == '__main__':
    sys.exit(main())
