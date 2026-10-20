#!/usr/bin/env python3
"""Replay of HT_Pert/code/lri_eh_hpc (lri_eh 0.2.0, isolated g^2 D vacuum-window add-on of the d = 1 HT), from the
shipped files. Standard library plus mpmath; a few seconds. No solver run (the solver reruns are `make smoke` and
`make replay-full`, public/g2d_rerun.py, rows a1.eh.g2d5 and a1.eh.g2d7).

Rows (ids = results_map.md; expected values in public/quoted_lri_eh_hpc.json):
  a1.eh.code     integrity: MANIFEST_SHA256.json (102 files; files listed in public/SCRUBBED.txt accepted); the source
                 fingerprint (sha256 over lri_eh/**/*.py, relative path, NUL, bytes, NUL; as lri_eh.runtime.fingerprint)
                 equals BUILD_INFO.json source_sha256 and the supplied receipt's; the receipt
                 benchmarks/validation_local.json is sealed (payload_sha256 = sha256 of its canonical JSON) and its seal
                 equals BUILD_INFO validation_receipt_sha256.                                              exact
  a1.eh.receipt  RECORDED: the supplier's validation (receipt passed; tests log "32 passed"); `make test` reruns it.
  a1.eh.K        K = exact.renormalized_constant() (mpmath, 60 digits): float equal to 0.0616119308426799 (the value
                 the notes quote, eq. K), and the 60-digit string equal to the K of
                 ../lri_hpc_Hamitonian/analysis/eh_review/physics-impact/dc4_exact.json in at least 55 digits.   1e-16
  a1.eh.exact    the exact rational delta C4(g^2 D)(Lambda) (exact.exact) at every even Lambda 2..118: float of it vs
                 exact.fast (<= 1e-16), vs dc4_exact.json rows (<= 1e-16), and vs delta_C[4] of the shipped g^2 D
                 tables d5_all.json (Lambda 4..118) and d7_all.json (4..90) of ../lri_hpc_Hamitonian (<= 1e-15);
                 asymptotics delta C4 - log(Lambda)/17496 - K + 16/(2187 sqrt(pi Lambda)) + 1/(243 Lambda) = O(Lambda^-3/2)
                 shrinks with Lambda (65536 by exact.fast).
  a1.eh.bench    the supplier's degree-5 benchmark outputs at Lambda = 118 (benchmarks/results/new_L118_d5_t4_*.json,
                 3 runs) give the same delta_C as d5_all.json['118'] within 1e-13 relative.
Cross-folder inputs (../lri_hpc_Hamitonian) absent -> those comparisons are SKIP. Verdicts PASS, FAIL, INFO, SKIP,
RECORDED; exit 1 on any FAIL. Table to stdout and to <work>/replay_lri_eh_hpc.txt.
usage: python3 public/replay_eh.py [--hpcham ../lri_hpc_Hamitonian] [--work .work]"""
import argparse
import glob
import hashlib
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROWS = []


def row(rid, verdict, what, quoted, computed):
    ROWS.append(dict(id=rid, verdict=verdict, what=what, quoted=quoted, computed=computed))


def sha(p):
    with open(p, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def canonical_digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hpcham', default=os.path.join(PKG, '..', 'lri_hpc_Hamitonian'))
    ap.add_argument('--work', default=os.path.join(PKG, '.work'))
    a = ap.parse_args()
    sys.dont_write_bytecode = True
    Q = {q['id']: q for q in json.load(open(os.path.join(HERE, 'quoted_lri_eh_hpc.json')))}
    scr = set()
    p = os.path.join(HERE, 'SCRUBBED.txt')
    if os.path.exists(p):
        scr = {ln.strip() for ln in open(p) if ln.strip() and not ln.startswith('#')}
    PI = os.path.join(a.hpcham, 'analysis', 'eh_review', 'physics-impact')
    have_x = os.path.exists(os.path.join(PI, 'd5_all.json'))

    # ------------------------------------------------------------ a1.eh.code
    man = json.load(open(os.path.join(PKG, 'MANIFEST_SHA256.json')))
    bad = [k for k, v in man.items() if k not in scr and (not os.path.exists(os.path.join(PKG, k))
                                                          or sha(os.path.join(PKG, k)) != v)]
    sc = [k for k in man if k in scr]
    h = hashlib.sha256()
    root = os.path.join(PKG, 'lri_eh')
    files = sorted((os.path.relpath(os.path.join(d, f), root).replace(os.sep, '/'), os.path.join(d, f))
                   for d, _, fs in os.walk(root) for f in fs if f.endswith('.py'))
    for rel, full in sorted(files, key=lambda t: t[0].split('/')):
        h.update(rel.encode() + b'\0' + open(full, 'rb').read() + b'\0')
    fp = h.hexdigest()
    build = json.load(open(os.path.join(PKG, 'BUILD_INFO.json')))
    rec = json.load(open(os.path.join(PKG, 'benchmarks', 'validation_local.json')))
    body = dict(rec)
    seal = body.pop('payload_sha256')
    sealed = canonical_digest(body) == seal
    fp_ok = fp == build['source_sha256'] or any(k.startswith('lri_eh/') for k in sc)
    ok = not bad and fp_ok and rec['source_sha256'] == build['source_sha256'] and sealed and \
        seal == build['validation_receipt_sha256']
    row('a1.eh.code', 'PASS' if ok else 'FAIL', Q['a1.eh.code']['what'], Q['a1.eh.code']['quoted'],
        f'MANIFEST_SHA256.json {len(man) - len(bad) - len(sc)}/{len(man)} identical, {len(sc)} scrubbed'
        f'{"; MISMATCH " + str(bad[:4]) if bad else ""}; fingerprint over {len(files)} lri_eh .py files {fp[:16]}... '
        f'= BUILD_INFO {build["source_sha256"][:16]}...: {fp == build["source_sha256"]}; receipt source equal: '
        f'{rec["source_sha256"] == build["source_sha256"]}; receipt sealed: {sealed}; seal {seal[:8]}... = BUILD_INFO '
        f'validation_receipt_sha256: {seal == build["validation_receipt_sha256"]}; source archive '
        f'{build["source_archive"]} sha256 {build["source_archive_sha256"][:16]}... (recorded)')

    log = open(os.path.join(PKG, 'benchmarks', 'validation_local.tests.log')).read().strip().split('\n')
    row('a1.eh.receipt', 'RECORDED', Q['a1.eh.receipt']['what'], Q['a1.eh.receipt']['quoted'],
        f'supplied receipt: passed {rec["passed"]}, Python {rec["environment"]["python"]}, numpy '
        f'{rec["environment"]["numpy"]}, numba {rec["environment"]["numba"]}, {rec["environment"]["threads"]} threads; '
        f'tests log: "{log[-1].strip()}"; recomputed by make test (stage validate)')

    # ------------------------------------------------------------ exact.py (loaded by path; lri_eh/__init__ not run)
    spec = importlib.util.spec_from_file_location('lri_eh_exact_public', os.path.join(PKG, 'lri_eh', 'exact.py'))
    ex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)
    Ks = ex.renormalized_constant()
    K = float(Ks)
    qK = float(Q['a1.eh.K']['quoted'])
    det = f'K = {Ks[:22]}... (60 digits) -> float {K!r}; quoted {qK!r}: |diff| {abs(K - qK):.0e} (<= 1e-16)'
    ok = abs(K - qK) <= 1e-16
    dce = None
    if os.path.exists(os.path.join(PI, 'dc4_exact.json')):
        dce = json.load(open(os.path.join(PI, 'dc4_exact.json')))
        nd = next((i for i, (x, y) in enumerate(zip(Ks, dce['K'])) if x != y), min(len(Ks), len(dce['K'])))
        ok &= nd >= 57   # '0.' + 55 digits
        det += f'; equal to dc4_exact.json K in the first {nd - 2} digits (>= 55)'
    else:
        det += '; dc4_exact.json (../lri_hpc_Hamitonian) absent: SKIP of that comparison'
    row('a1.eh.K', 'PASS' if ok else 'FAIL', Q['a1.eh.K']['what'], Q['a1.eh.K']['quoted'], det)

    Ls = list(range(2, 119, 2))
    exact = {L: ex.exact(L) for L in Ls}
    d_fast = max(abs(float(exact[L]) - ex.fast(L)) for L in Ls)
    parts = [f'float(exact) vs fast at {len(Ls)} cutoffs 2..118: max {d_fast:.0e} (<= 1e-16)']
    ok = d_fast <= 1e-16
    if dce is not None:
        d_rows = max(abs(float(exact[int(k)]) - v['dC4']) for k, v in dce['rows'].items() if int(k) in exact)
        parts.append(f'vs dc4_exact.json rows: max {d_rows:.0e} (<= 1e-16)')
        ok &= d_rows <= 1e-16
    if have_x:
        for name in ('d5_all', 'd7_all'):
            t = json.load(open(os.path.join(PI, f'{name}.json')))
            dd = max(abs(float(exact[int(k)]) - v['delta_C'][4]) for k, v in t.items())
            parts.append(f'vs {name}.json delta_C[4] ({len(t)} cutoffs {min(map(int, t))}..{max(map(int, t))}): max '
                         f'{dd:.0e} (<= 1e-15)')
            ok &= dd <= 1e-15
    else:
        parts.append('g^2 D tables (../lri_hpc_Hamitonian) absent: SKIP of those comparisons')
    asy = lambda L, v: v - (math.log(L) / 17496 + K - 16 / (2187 * math.sqrt(math.pi * L)) - 1 / (243 * L))
    rs = [(L, asy(L, float(exact[L]) if L in exact else ex.fast(L))) for L in (8, 32, 118, 1024, 65536)]
    shrink = all(abs(x[1]) > abs(y[1]) for x, y in zip(rs, rs[1:]))
    ok &= shrink
    parts.append('remainder after log(L)/17496 + K - 16/(2187 sqrt(pi L)) - 1/(243 L): ' +
                 ', '.join(f'{L}: {r:.1e}' for L, r in rs) + f' (shrinking: {shrink})')
    row('a1.eh.exact', 'PASS' if ok else 'FAIL', Q['a1.eh.exact']['what'], Q['a1.eh.exact']['quoted'], '; '.join(parts))

    if have_x:
        ref = json.load(open(os.path.join(PI, 'd5_all.json')))['118']['delta_C']
        fs = sorted(glob.glob(os.path.join(PKG, 'benchmarks', 'results', 'new_L118_d5_t4_*.json')))
        dd = max(abs(x - y) / max(abs(y), 1e-300) for f in fs for x, y in
                 zip(json.load(open(f))['delta_C'], ref) if y != 0)
        row('a1.eh.bench', 'PASS' if len(fs) == 3 and dd <= 1e-13 else 'FAIL', Q['a1.eh.bench']['what'],
            Q['a1.eh.bench']['quoted'], f'{len(fs)} supplied runs vs d5_all.json["118"] delta_C[4..5]: max relative '
            f'{dd:.1e} (<= 1e-13)')
    else:
        row('a1.eh.bench', 'SKIP', Q['a1.eh.bench']['what'], Q['a1.eh.bench']['quoted'],
            '../lri_hpc_Hamitonian/analysis/eh_review/physics-impact/d5_all.json absent')

    w = max(len(r['id']) for r in ROWS)
    lines = [f"{r['id']:{w}s}  {r['verdict']:8s}  {r['what']}\n{'':{w}s}            quoted: {r['quoted']}\n"
             f"{'':{w}s}            computed: {r['computed']}" for r in ROWS]
    cnt = {v: sum(r['verdict'] == v for r in ROWS) for v in ('PASS', 'FAIL', 'INFO', 'SKIP', 'RECORDED')}
    summ = f"# replay lri_eh_hpc: {cnt['PASS']} PASS, {cnt['FAIL']} FAIL, {cnt['INFO']} INFO" + ''.join(
        f', {cnt[k]} {k}' for k in ('SKIP', 'RECORDED') if cnt[k])
    txt = '\n'.join(lines + [summ])
    print(txt)
    os.makedirs(a.work, exist_ok=True)
    open(os.path.join(a.work, 'replay_lri_eh_hpc.txt'), 'w').write(txt + '\n')
    sys.exit(1 if cnt['FAIL'] else 0)


if __name__ == '__main__':
    main()
