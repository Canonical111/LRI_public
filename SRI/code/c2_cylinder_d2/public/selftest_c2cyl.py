#!/usr/bin/env python3
"""Self-tests of the c2_cylinder_d2 export (new tool, 2026-10-15; seconds). Run from code/c2_cylinder_d2/.

1. MANIFEST.sha256 (verbatim, commit 98e1935) for the shipped tracked files, honouring public/NOT_EXPORTED.txt and
   public/SCRUBBED.txt (public/verify_manifest_public.py); the task SHA256SUMS of the shipped cluster records.
2. The dated snapshot public/SNAPSHOT.sha256 of the cluster records under outputs/ (git-ignored in the source).
3. results/continuum_2026-10/CURRENT names a complete generation (four files, read-only copies of one run).
4. The closed form of c_2 evaluated with mpmath at 30 and 40 digits agrees with the value given to this package.
5. The value(uncertainty) rounding rule used for \\SRtwoCtwoHT on known cases.
6. The scripts the replays run contain no path-substring filter on 'local' (the acceptance tree lives under /local1).
7. The unlisted-file rule of verify_manifest_public.py on a synthetic package: the files the export writes
   (public/SCRUBBED.txt; RE-PINNED.json, RE-PINNED.md, MANIFEST.json at the root) pass, present or not; others fail.
Usage: python3 public/selftest_c2cyl.py [--out FILE]
"""
import argparse, re, sys
from pathlib import Path

from c2cyl_common import L, PKG, RESULTS, C2_CLOSED_TEXT, current_generation, c2_closed, matches_paren, parse_paren
import verify_manifest_public as V


def allowlist_test():
    """The files the public repository's export may write (public/SCRUBBED.txt; RE-PINNED.json, RE-PINNED.md and
    MANIFEST.json at the package root) are tolerated whether present or not; any other unlisted file fails, including
    the same names at other places, an extra public/ file and an outputs/ file missing from the snapshot."""
    import hashlib, tempfile
    with tempfile.TemporaryDirectory() as d:
        pkg = Path(d) / 'pkg'
        (pkg / 'public').mkdir(parents=True)
        (pkg / 'outputs').mkdir()
        (pkg / 'a.txt').write_text('a\n')
        (pkg / 'outputs' / 'r.json').write_text('{}\n')
        (pkg / 'MANIFEST.sha256').write_text(hashlib.sha256(b'a\n').hexdigest() + '  a.txt\n')
        (pkg / 'public' / 'NOT_EXPORTED.txt').write_text('# none\n')
        (pkg / 'public' / 'SNAPSHOT.sha256').write_text(hashlib.sha256(b'{}\n').hexdigest() + '  outputs/r.json\n')
        (pkg / 'public.mk').write_text('#\n')
        res = []
        r = V.check(pkg)
        res.append(('base', not r['bad'] and not r['unlisted'], r['unlisted']))
        for n in sorted(V.EXPORT_FILES):
            (pkg / n).write_text('x\n')
        r = V.check(pkg)
        res.append(('export files present', not r['bad'] and not r['unlisted'], r['unlisted']))
        for n in ('stray.txt', 'public/extra.py', 'outputs/x.json', 'data/RE-PINNED.json', 'public/sub/SCRUBBED.txt',
                  'SCRUBBED.txt', 'public/MANIFEST.json'):
            f = pkg / n
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text('x\n')
            r = V.check(pkg)
            res.append((n, r['unlisted'] == [n], r['unlisted']))
            f.unlink()
    good = all(x[1] for x in res)
    return good, f'{sum(x[1] for x in res)} of {len(res)} cases' + ('' if good else f'; failed {[x for x in res if not x[1]]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(PKG / '.work' / 'selftest_c2cyl.txt'))
    a = ap.parse_args()
    T = L.Table('c2_cylinder_d2 selftest')
    r = V.check()
    T.check('MANIFEST.sha256 (pruned export)', not r['bad'] and not r['unlisted'],
            f"{r['entries']} entries: {r['ok']} match, {r['not_exported']} not exported, {len(r['scrubbed'])} scrubbed, "
            f"{len(r['bad'])} bad {r['bad'][:3]}, {len(r['unlisted'])} unlisted {r['unlisted'][:3]}",
            'all shipped tracked files match', 'public/verify_manifest_public.py (record-bound files never scrubbed)')
    T.check('task SHA256SUMS (outputs/)', not r['sums_bad'], f"{r['sums_checked']} shipped files match; not exported: "
            f"{', '.join(r['sums_absent'])}; bad {r['sums_bad'][:3]}", 'shipped files match', 'per-task checksum lists written on the clusters')
    L.verify_snapshot(PKG, T)
    ok, how = allowlist_test()
    T.check('unlisted-file rule', ok, how, 'export-written files tolerated, any other unlisted file fails',
            'verify_manifest_public on a synthetic package; EXPORT_FILES: public/SCRUBBED.txt, RE-PINNED.json, '
            'RE-PINNED.md, MANIFEST.json (package root), presence optional')
    gen = current_generation()
    files = sorted(p.name for p in gen.iterdir())
    T.check('CURRENT generation', files == ['C2_estimate.json', 'REPORT.md', 'continuum_points.json', 'regulator_fits.json'],
            f'{gen.name}: {", ".join(files)}', 'the four result files', 'results/continuum_2026-10/CURRENT')
    import mpmath as mp
    c30, c40 = c2_closed(30), c2_closed(40)
    T.check('closed form of c_2 (mpmath)', abs(c30 - mp.mpf(C2_CLOSED_TEXT)) < 1e-17 and abs(c30 - c40) < 1e-25,
            mp.nstr(c40, 25), C2_CLOSED_TEXT, '30 and 40 digits; paper appendix (crossover in d = 2)')
    cases = [((-4.0670498, 0.0023580, '-4.0670(24)'), True), ((-4.06705, 0.00245, '-4.0670(24)'), False),
             ((-4.06715, 0.00236, '-4.0670(24)'), False), ((-4.067149, 0.002449, '-4.0671(24)'), True)]
    got = [matches_paren(*x)[0] == want for x, want in cases]
    T.check('value(uncertainty) rule', all(got) and parse_paren('-4.0670(24)')[1] == parse_paren('-4.0670(24)')[1].__class__('0.0024'),
            f'{sum(got)} of {len(got)} cases', 'all', 'half-up to the printed decimals, uncertainty in last-digit units')
    scripts = [PKG / 'scripts' / 'run.py'] + sorted((PKG / 'code' / 'continuum').glob('*.py')) + \
        sorted((PKG / 'code' / 'hamiltonian').glob('*.py'))
    hits = [p.relative_to(PKG).as_posix() for p in scripts if re.search(r"""['"][^'"]*local[^'"]*['"]\s+(not\s+)?in\b""", p.read_text())]
    T.check('no path filters on "local"', not hits, f'{len(scripts)} scripts; hits {hits}', 'none',
            "a substring test such as 'local' in path would drop node-local inputs")
    sys.exit(T.report(a.out))


if __name__ == '__main__':
    main()
