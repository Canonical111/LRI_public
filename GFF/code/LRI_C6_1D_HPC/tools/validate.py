"""Validation gate checks (PLAN.md rev 4, 4.6). Each call adds one gate record to VALIDATION.json, a file owned by a
single job (prepare.json, dbl.json, ld.json, l5.json), replaced atomically. A failed mandatory check exits 1, so a
job running under `set -e` stops at the first failure. `collect` combines the per-job files and exits 1 unless
every required gate passed.

  validate.py VALIDATION.json vector GATE A B --rel TOL [--pole-rel TOL2 --poles i,j,...]
      A, B: merged level files (totals) or reference result files (values); per-entry relative differences.
  validate.py VALIDATION.json same-sectors GATE --a FILE... --b FILE...
      Bitwise equality (decimal text) of the sector values present in the --a JSONL files with the same sectors in
      the --b JSONL files; every --a sector must exist in --b.
  validate.py VALIDATION.json close-sectors GATE --rel TOL --a FILE... --b FILE...
      Per-entry relative agreement |a-b| <= TOL |b| of every --a sector with the same --b sector (reports the maximum).
  validate.py VALIDATION.json partition GATE ALL LIGHT HARD --rel TOL
      ALL totals equal LIGHT + HARD totals entrywise.
  validate.py VALIDATION.json c6diff GATE A B
      Reports (no pass/fail) the C6 difference -(2/729)(H6_A - H6_B) for both cutoffs.
  validate.py VALIDATION.json expect-fail GATE EXITCODE
      Records that a command expected to fail exited with EXITCODE (pass iff nonzero).
  validate.py VALIDATION.json check GATE EXITCODE [INFO]
      Records the outcome of a check performed by the caller (pass iff EXITCODE is 0).
  validate.py VALIDATION.json weights GATE NEW_DIR REF_DIR L N[,N...]
      float64 weights: bitwise equal except entries with |ref| < 1e-40, which must be exactly 0 in NEW (true zeros: the
      80-digit reference leaves residuals up to ~1e-55 at degree 40; the smallest genuine weight is ~3e-15).
  validate.py SUMMARY.json collect - FILE... --require GATE[,GATE...]
      Combines per-job records; passes iff every required gate is present with pass true (c6diff records are
      informational and may be required only for presence).
"""
import os
import sys, json, math
from pathlib import Path
import mpmath as mp
import numpy as np

mp.mp.dps = 50


def vec(path):
    d = json.loads(Path(path).read_text(), parse_float=str)
    return [mp.mpf(x) for x in (d['totals'] if 'totals' in d else d['values'])]


def sectors(files):
    out = {}
    for f in files:
        for ln in Path(f).read_text().splitlines():
            r = json.loads(ln, parse_float=str)
            if r.get('type') == 'sector':
                out[int(r['sector'])] = r['values']
    return out


def record(vfile, gate, ok, info):
    p = Path(vfile); db = json.loads(p.read_text()) if p.exists() else {}
    db[gate] = {'pass': ok, **info}
    tmp = p.with_name(p.name + f'.tmp{os.getpid()}')
    tmp.write_text(json.dumps(db, indent=1, default=str)); os.replace(tmp, p)
    print(('PASS ' if ok else ('INFO ' if ok is None else 'FAIL ')) + gate + ' ' + json.dumps(info, default=str)[:400], flush=True)
    if ok is False:
        sys.exit(1)


def main():
    vfile, cmd, gate = sys.argv[1], sys.argv[2], sys.argv[3]
    args = sys.argv[4:]
    if cmd == 'vector':
        a, b = vec(args[0]), vec(args[1])
        rel = float(args[args.index('--rel') + 1])
        prel = float(args[args.index('--pole-rel') + 1]) if '--pole-rel' in args else rel
        poles = [int(x) for x in args[args.index('--poles') + 1].split(',')] if '--poles' in args else []
        if len(a) != len(b):
            record(vfile, gate, False, {'error': f'lengths {len(a)} vs {len(b)}'}); return
        diffs = [float(abs(x - y) / max(abs(y), mp.mpf('1e-300'))) for x, y in zip(a, b)]
        ok = all(dv <= (prel if i in poles else rel) for i, dv in enumerate(diffs))
        record(vfile, gate, ok, {'A': args[0], 'B': args[1], 'relative_differences': diffs, 'tol': rel, 'pole_tol': prel, 'pole_entries': poles})
    elif cmd == 'same-sectors':
        ia, ib = args.index('--a'), args.index('--b')
        A = sectors(args[ia + 1:ib]); B = sectors(args[ib + 1:])
        missing = sorted(set(A) - set(B)); diff = sorted(s for s in A if s in B and A[s] != B[s])
        record(vfile, gate, bool(A) and not missing and not diff, {'sectors_compared': len(A), 'missing_in_b': missing[:20], 'differing': diff[:20]})
    elif cmd == 'close-sectors':
        rel = float(args[args.index('--rel') + 1]); ia, ib = args.index('--a'), args.index('--b')
        A = sectors(args[ia + 1:ib]); B = sectors(args[ib + 1:])
        missing = sorted(set(A) - set(B)); worst = mp.mpf(0); nd = 0
        for s in A:
            if s in B:
                for x, y in zip(A[s], B[s]):
                    d = abs(mp.mpf(x) - mp.mpf(y)) / max(abs(mp.mpf(y)), mp.mpf('1e-300'))
                    nd += d > 0; worst = max(worst, d)
        record(vfile, gate, bool(A) and not missing and worst <= rel, {'sectors_compared': len(A), 'missing_in_b': missing[:20],
               'entries_differing': nd, 'max_relative_difference': mp.nstr(worst, 4), 'tol': rel})
    elif cmd == 'partition':
        al, li, ha = vec(args[0]), vec(args[1]), vec(args[2]); rel = float(args[args.index('--rel') + 1])
        diffs = [float(abs(x - (y + z)) / max(abs(x), mp.mpf('1e-300'))) for x, y, z in zip(al, li, ha)]
        record(vfile, gate, all(dv <= rel for dv in diffs), {'relative_differences': diffs, 'tol': rel})
    elif cmd == 'c6diff':
        a, b = vec(args[0]), vec(args[1])
        record(vfile, gate, None, {'C6_diff_maxgap': mp.nstr(-2 * (a[5] - b[5]) / 729, 6), 'C6_diff_span': mp.nstr(-2 * (a[11] - b[11]) / 729, 6)})
    elif cmd == 'expect-fail':
        code = int(args[0]); record(vfile, gate, code != 0, {'exit_code': code})
    elif cmd == 'check':
        code = int(args[0]); record(vfile, gate, code == 0, {'exit_code': code, 'info': ' '.join(args[1:])})
    elif cmd == 'weights':
        new, ref, L = Path(args[0]), Path(args[1]), int(args[2]); rows = {}; ok = True
        for N in map(int, args[3].split(',')):
            a = np.fromfile(new / f'w_{L}_{N}.bin'); b = np.fromfile(ref / f'w_{L}_{N}.bin')
            if a.shape != b.shape:
                rows[N] = 'shape mismatch'; ok = False; continue
            d = np.nonzero(a != b)[0]
            bad = [int(i) for i in d if not (abs(b[i]) < 1e-40 and a[i] == 0.0)]
            nz = np.abs(a[a != 0]); rows[N] = {'smallest_nonzero_new': float(nz.min()) if nz.size else None}
            rows[N].update({'entries': int(a.size), 'differing': int(d.size), 'differing_not_residual_zero': bad[:10],
                            'max_residual_ref': float(max((abs(b[i]) for i in d), default=0.0))})
            ok = ok and not bad
        record(vfile, gate, ok, {'L': L, 'per_N': rows})
    elif cmd == 'collect':
        req = args[args.index('--require') + 1].split(',') if '--require' in args else []
        files = [a for a in args[:args.index('--require')] if a != '-'] if '--require' in args else args
        allg = {}
        for f in files:
            for g, r in json.loads(Path(f).read_text()).items():
                allg[g] = {**r, 'source': f}
        failed = [g for g, r in allg.items() if r.get('pass') is False]
        missing = [g for g in req if g not in allg]
        not_passed = [g for g in req if g in allg and allg[g].get('pass') is not True and not g.startswith(('V9', 'V10'))]
        ok = not failed and not missing and not not_passed
        out = {'pass': ok, 'failed': failed, 'missing': missing, 'not_passed': not_passed, 'gates': allg}
        p = Path(vfile); tmp = p.with_name(p.name + '.tmp'); tmp.write_text(json.dumps(out, indent=1, default=str)); os.replace(tmp, p)
        print(('VALIDATION PASSED' if ok else 'VALIDATION FAILED'), {'failed': failed, 'missing': missing, 'not_passed': not_passed})
        sys.exit(0 if ok else 1)
    else:
        raise SystemExit(f'unknown command {cmd}')


if __name__ == '__main__':
    main()
