#!/usr/bin/env python3
"""Fast test of c2_closed_d2 (new tool, 2026-10-15). Run from code/c2_closed_d2/ (make -f public.mk test); seconds.

1. public/SNAPSHOT.sha256: the dated snapshot of the verbatim files (the closed-form study and mc/).
2. code/verify_package.py (verbatim): the study's own SHA-256 inventory MANIFEST.json; files listed in
   public/SCRUBBED.txt (placeholders substituted at publication, e.g. outputs/run_manifest.json) count by presence;
   files listed in public/NOT_SHIPPED.txt (the study's TeX note, its PDF and its builder, left out on 2026-10-16/17)
   must be absent; a file of public/RE-PINNED.json (README.md, edited 2026-10-17) passes with its published sha256.
3. The closed form as printed in the appendix, at 50 digits, against outputs/summary.json (|diff| < 1e-45).
4. code/lri_C2_three_4F3.py (verbatim), rerun in a copy at the shipped settings (80 digits, 400 terms, --check
   --symbolic): its JSON equals outputs/raw/three_4f3_80dps.json.
5. mc/: 64 + 64 + 14 chunk outputs of 3e8 samples (4.26e10 in all), empty stderr files; the recombination
   (public/c2lib.py) gives c_2 = -4.075 +- 0.019.
"""
import json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG.parent.parent/'verify'))
sys.path.insert(0, str(HERE))
import sri_lib as L
import c2lib as C
import mpmath as mp

work = PKG/'.work'/'test'
shutil.rmtree(work, ignore_errors=True)
work.mkdir(parents=True)
T = L.Table('c2_closed_d2 test')
L.verify_snapshot(PKG, T)

r = subprocess.run([sys.executable, '-B', str(PKG/'code'/'verify_package.py')], capture_output=True, text=True)
scrubbed = set()
if (HERE/'SCRUBBED.txt').exists():
    scrubbed = {l.strip() for l in (HERE/'SCRUBBED.txt').read_text().splitlines() if l.strip() and not l.startswith('#')}
absent = set()
if (HERE/'NOT_SHIPPED.txt').exists():
    absent = {l.strip() for l in (HERE/'NOT_SHIPPED.txt').read_text().splitlines() if l.strip() and not l.startswith('#')}
repinned = {}
if (HERE/'RE-PINNED.json').exists():
    repinned = {f['path']: f['published_sha256'] for f in json.loads((HERE/'RE-PINNED.json').read_text())['files']}
def _repinned_ok(rel):
    import hashlib
    return rel in repinned and hashlib.sha256((PKG/rel).read_bytes()).hexdigest() == repinned[rel]
fails = [l.strip() for l in r.stdout.splitlines() if l.startswith(('changed: ', 'missing: '))]
other = [f for f in fails if not (f.startswith('changed: ') and (f[len('changed: '):] in scrubbed or _repinned_ok(f[len('changed: '):])))
         and not (f.startswith('missing: ') and f[len('missing: '):] in absent)]
present = sorted(a for a in absent if (PKG/a).exists())
ok = not present and (r.returncode == 0 or (fails and not other and len(fails) == len(r.stdout.strip().splitlines())))
nmiss = sum(f.startswith('missing: ') for f in fails)
T.check('verify_package.py', ok, (r.stdout.strip().splitlines() or [r.stderr.strip()])[-1][:58] if r.returncode == 0 else
        '%d changed (SCRUBBED.txt or RE-PINNED.json), %d not shipped (NOT_SHIPPED.txt)' % (len(fails) - nmiss, nmiss) if ok else
        'differ: %s' % (other[:3] or ['present but listed as not shipped: %s' % present]), 'exit 0',
        "the study's own MANIFEST.json (verbatim verifier; public/SCRUBBED.txt: presence only; public/NOT_SHIPPED.txt: "
        "must be absent; public/RE-PINNED.json: published sha256)")

S = json.loads((PKG/'outputs'/'summary.json').read_text())
v = C.closed_form(50)
with mp.workdps(90):
    d = abs(v['C2'] - mp.mpf(S['C2']))
T.check('c_2 closed form, 50 digits', d < mp.mpf('1e-45'), mp.nstr(v['C2'], 20) + ' |diff| %s' % mp.nstr(d, 2),
        'outputs/summary.json C2', 'appendix eq. cf:cr-c2 evaluated with mpmath at 50 digits; |diff| < 1e-45')

shutil.copytree(PKG/'code', work/'code')
out = work/'three_4f3_80dps.json'
r = subprocess.run([sys.executable, '-B', 'code/lri_C2_three_4F3.py', '--dps', '80', '--terms', '400', '--check',
                    '--symbolic', '--json', str(out)], cwd=work, capture_output=True, text=True)
same = r.returncode == 0 and out.read_bytes() == (PKG/'outputs'/'raw'/'three_4f3_80dps.json').read_bytes()
T.check('lri_C2_three_4F3.py rerun', same, 'exit %d, %s' % (r.returncode, 'byte-identical' if same else 'differs'),
        'outputs/raw/three_4f3_80dps.json', 'verbatim script in a copy, settings of inputs/calculation.json')

mc = PKG/'mc'
counts = {k: len(C.mc_files(mc, k)) for k in C.RUNS}
errs = [p for k in C.RUNS for p in (mc/('run_' + k)).glob('err_*.txt')]
est, N = {}, 0
for k in C.RUNS:
    heads, H, HS, BD = C.mc_load(C.mc_files(mc, k))
    N += sum(nb for nb, _ in H)
    est[k] = C.mc_est(H, C.CUT)
T.check('mc chunks', counts == {'A': 64, 'B': 64, 'C': 14} and N == 42600000000 and len(errs) == 142 and
        all(p.stat().st_size == 0 for p in errs), '%s, %.3g samples, %d empty stderr' % (counts, N, len(errs)),
        '64/64/14 chunks, 4.26e10 samples', 'mc/run_{A,B,C}/out_*.txt (review: 4.26e10 samples)')
m, se, chi2 = C.mc_combine(list(est.values()))
res = C.mc_to_c2(m, se, float(v['b0']), float(v['B31']))
ok, how = L.matches([res['C2'], res['C2_se']], '-4.075\\pm0.019')
T.check('mc recombination', ok, '%.4f +- %.4f [%s]' % (res['C2'], res['C2_se'], how), '-4.075 +- 0.019',
        'cut Lambda > -15, inverse-variance mean of A, B, C; c_2 = -4 z_41/b0^2 (replay: full table)')
sys.exit(T.report(PKG/'.work'/'test_c2_closed_d2.txt'))
