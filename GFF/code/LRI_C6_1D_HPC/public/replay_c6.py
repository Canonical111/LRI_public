#!/usr/bin/env python3
"""Public checks for LRI_C6_1D_HPC: C6(1) of the 1D long-range Ising model from exact all-graph sums.

Run from GFF/code/LRI_C6_1D_HPC (public.mk does this):
  python public/replay_c6.py test         integrity: every hash binding between the shipped records, level and run files
  python public/replay_c6.py replay       test + recompute every record and every quoted number from the shipped data
  python public/replay_c6.py smoke        build the engines and rerun the five-loop degree-12 levels (x86-64 Linux, g++, OpenMP)
  python public/replay_c6.py rerun-lower  rerun the RR-001 lower-amplitude precision check (x86-64: 80-bit long double)
  python public/replay_c6.py compare-rerun --rerun FILE   compare a production rerun's final analysis (C6_N<N*>.json
                                          written by cluster/analyze_stage.sh) with the shipped C6_final.json
Options: --results DIR (default ../../results/C6_1), --data DIR (../../data/C6_1), --work DIR (.work),
         --c7-final FILE (C7_final.json of LRI_C7_HPC; default: searched, see C7_CANDIDATES), --threads N (smoke).
Prints a table and writes it to WORK/<target>_table.txt and .json. Status: PASS, FAIL, SKIP (optional input absent),
FLAG (the record and the condensed-note wording disagree; the record is authoritative, the note text needs a fix;
not a failure). Exit code 1 if any row is FAIL.

Nothing in the package, results or data folders is written; all outputs go to WORK. The shipped tools are run
unchanged as subprocesses (python -B). Tolerances: 'bitwise' for records that the tools regenerate (sha256 equality);
'printed' = the record value rounds to the number as printed in the note or report (|value - printed| <= half a
unit in its last printed digit); other tolerances are stated in the row.
"""
import argparse, hashlib, json, os, platform, re, shutil, subprocess, sys
from decimal import Decimal, ROUND_CEILING
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
PY = sys.executable

# sha256 of the shipped records (results/2026-09_symmetry of LRI_C6_1D_HPC at cef6fa7, shipped as GFF/results/C6_1).
EXPECT = {
    'C6_final.json': '3ff496c2fd6a00507011ba228ae08bc990999ee7a09efc52c7788bedca2ee717',
    'assembled.json': 'dd46b44c1d4e983f6e968a1915023df5ff9dc538405efeeb378086dd37b76647',
    'rounding.json': '7ac55e46a5edea1c3c79ea75f5907ebbe6320f9c9eaf490a8294693fa93bf2ab',
    'weights_manifest.json': '79ccc09592b719a62ef6ae9b4c5eaf4cfaa8dee32952d72e5a68ac4c59bb7ba0',
    'resources_N22.json': '048079f7fd5652c7ada690a3b891658c3ddcf74ea46acce76de1e5dd499fbe02',
    'decisions/decision_N16.json': '9907e43114eb87e51abfa3e5ea176487e5bab72caa90bd0d93d1e8a623eef753',
    'decisions/decision_N18.json': '45d076f8e7217c4463e4231a7fb6a3af65e86d9c0f0d017f0c3e96d054b32d62',
    'decisions/decision_N20.json': 'f8fc45e57df6376b35c4fd9d1c3fb1c3e8a3b42366ed8974cbf635d764c44c4f',
    'decisions/decision_N22.json': 'aefc16007e2888297acfcc9b4fce31136dc063bde37c4c0b848f027eb250f681',
    'validation/APPROVED.json': '6ebf7270b7b2d6cf9a05541b6a01d254f1743aea5a19b3adb76bc51a046c8294',
    'validation/summary.json': '245deef8e461824c0da5301b0fb9adfa7431c83188c385ec102f15e4b802f667',
    'C7_crosscheck.json': '51d12afea01dbe5cbe7c0f5182ef899fab017e47ae5e39d943b4ec713e4b6b4b',
    'lower_amplitude_precision/R6_comparison.json': 'c44c2f8b912e8e18629af3862d6cf241033302166153128f8927262bfade98e7',
    'lower_amplitude_precision/lower28_ld.json': 'f0c88c14e1988d03126233f076d2725b776668c120de70d899a9a46fdb84e7e0',
    'lower_amplitude_precision/lower28_f64.json': '3253d916a187c96fbbfcd26187e3a8d7fb64658ab23d0abbf4cbb6e2e83d03e0',
}
C7_FINAL_SHA = 'b44b3a134e561d0bc6ca4b4ab83cbf56f21cc147633b7b5e8e75c59b5d2004b8'
# C7_crosscheck.json names its inputs by these project-relative labels (paths in the authors' working tree).
C7_LABEL = 'LRI_C7_HPC/results/2026-09_expanse_v2/C7_final.json'
C6_LABEL = 'LRI_C6_1D_HPC/results/2026-09_symmetry/C6_final.json'
C7_CANDIDATES = ['../../results/C7_1/C7_final.json', '../LRI_C7_HPC/results/2026-09_expanse_v2/C7_final.json']
RUNS_PREFIX = '/mnt/beegfs/zzheng1/lri_c6_1d/runs/'   # where the level records' input files lived on symmetry
STAGES = (16, 18, 20)
CUTS = ('maxgap', 'span')


# --------------------------------------------------------------------------------------------------- utilities
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, cwd=None, check=True):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1')
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'command failed ({r.returncode}): {" ".join(map(str, cmd))}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}')
    return r


class Table:
    def __init__(self):
        self.rows = []

    def add(self, rid, what, status, expected='', got='', tol=''):
        self.rows.append({'id': rid, 'check': what, 'status': status, 'expected': str(expected), 'got': str(got), 'tolerance': tol})
        line = f'{status:4s} {rid:7s} {what}'
        if expected != '' or got != '':
            line += f'  [expected {expected}; got {got}; {tol}]'
        print(line, flush=True)

    def check(self, rid, what, ok, expected='', got='', tol='bitwise'):
        self.add(rid, what, 'PASS' if ok else 'FAIL', expected, got, tol)
        return ok

    def guard(self, rid, what, fn):
        """Run fn(); an exception becomes a FAIL row instead of aborting the replay."""
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            self.add(rid, what, 'FAIL', '', f'{type(e).__name__}: {str(e)[:400]}', 'exception')

    def write(self, work, target):
        work.mkdir(parents=True, exist_ok=True)
        n = {s: sum(r['status'] == s for r in self.rows) for s in ('PASS', 'FAIL', 'SKIP', 'FLAG')}
        head = (f'LRI_C6_1D_HPC public {target}: {n["PASS"]} PASS, {n["FAIL"]} FAIL, {n["SKIP"]} SKIP, {n["FLAG"]} FLAG '
                f'(python {platform.python_version()}, {platform.machine()})')
        txt = [head] + [f"{r['status']:4s} {r['id']:7s} {r['check']}" + (f"  [expected {r['expected']}; got {r['got']}; {r['tolerance']}]"
                                                                           if r['expected'] or r['got'] else '') for r in self.rows]
        (work / f'{target}_table.txt').write_text('\n'.join(txt) + '\n')
        (work / f'{target}_table.json').write_text(json.dumps({'summary': n, 'rows': self.rows}, indent=1))
        print(head)
        print(f'table written to {work / (target + "_table.txt")}')
        return n['FAIL'] == 0


def mpf(x):
    import mpmath as mp
    return mp.mpf(str(x))


def printed_ok(value, text):
    """True if value rounds to the printed decimal text (half a unit in its last printed digit)."""
    import mpmath as mp
    with mp.workdps(60):
        d = Decimal(text)
        half = Decimal(5).scaleb(d.as_tuple().exponent - 1)
        return abs(mpf(value) - mp.mpf(str(d))) <= mp.mpf(str(half)) * (1 + mp.mpf('1e-12'))


def ceil_2sf(x):
    x = Decimal(str(x))
    q = Decimal(1).scaleb(x.adjusted() - 1)
    return (x / q).to_integral_value(rounding=ROUND_CEILING) * q


def pnum(T, rid, what, value, text, where):
    T.check(rid, f'{what} ({where})', printed_ok(value, text), text, value, 'printed')


def find_c7(args):
    cands = [args.c7_final] if args.c7_final else []
    if os.environ.get('C7_FINAL'):
        cands.append(os.environ['C7_FINAL'])
    cands += [str((PKG / c).resolve()) for c in C7_CANDIDATES]
    for c in cands:
        if c and Path(c).is_file():
            return Path(c)
    return None


# --------------------------------------------------------------------------------------------------- integrity
def integrity(T, R, D, args):
    sys.path.insert(0, str(PKG / 'tools'))
    from levelio import validate_level  # shipped validator (header/name/width/finite/sum checks)
    for rel, h in EXPECT.items():
        p = R / rel
        T.check('I01', f'sha256 of results/{rel}', p.is_file() and sha(p) == h, h[:16] + '...', (sha(p)[:16] + '...') if p.is_file() else 'missing')
    F = json.loads((R / 'C6_final.json').read_bytes()); A = json.loads((R / 'assembled.json').read_bytes())
    Rn = json.loads((R / 'rounding.json').read_bytes()); AP = json.loads((R / 'validation/APPROVED.json').read_bytes())
    S = json.loads((R / 'validation/summary.json').read_bytes()); man_sha = sha(R / 'weights_manifest.json')
    man = json.loads((R / 'weights_manifest.json').read_bytes())
    pv = F['provenance']
    T.check('I02', 'C6_final.provenance.assembled_sha256 = sha256(assembled.json)', pv['assembled_sha256'] == sha(R / 'assembled.json'))
    T.check('I03', 'C6_final.provenance.rounding_sha256 = sha256(rounding.json)', pv['rounding_sha256'] == sha(R / 'rounding.json'))
    T.check('I04', 'weights manifest hash: C6_final = assembled = rounding = APPROVED = sha256(weights_manifest.json)',
            pv['weights_manifest_sha256'] == A['weights_manifest_sha256'] == Rn['weights_manifest_sha256'] == AP['identities']['weights_manifest'] == man_sha)
    T.check('I05', 'C6_final level identities = assembled.json and rounding.json level identities',
            pv['assembly_level_identities'] == A['level_identities'] and pv['rounding_level_identities'] == Rn['level_identities'])
    ids = {**A['level_identities'], **Rn['level_identities']}
    lv = D / 'levels'; files = sorted(p.name for p in lv.glob('*.json'))
    T.check('I06', 'data/levels holds exactly the 62 level records named by assembled.json and rounding.json',
            set(files) == set(ids) and len(files) == 62, 62, len(files))
    bad = [f for f, h in ids.items() if not (lv / f).is_file() or sha(lv / f) != h]
    T.check('I07', 'sha256 of every level record = its identity in assembled.json / rounding.json', not bad, 'all 62', f'{len(bad)} mismatched {bad[:3]}')
    # decisions
    for n in STAGES + (22,):
        d = json.loads((R / f'decisions/decision_N{n}.json').read_bytes())
        okl = all((lv / f).is_file() and sha(lv / f) == h for f, h in d['levels_at_N_star'].items())
        T.check('I08', f'decision_N{n}: N* level hashes match the shipped level records', okl)
        want = ('continue', n + 2) if n < 22 else ('stop', None)
        T.check('I09', f'decision_N{n}: decision and next degree', (d['decision'], d['next_degree']) == want, want, (d['decision'], d['next_degree']))
        rp = (R / 'resources_N22.json') if n == 22 else (D / f'analysis/resources_N{n}.json')
        T.check('I10', f'decision_N{n}: embedded resources = {rp.name}', rp.is_file() and json.loads(rp.read_bytes()) == d['resources'])
    d22 = json.loads((R / 'decisions/decision_N22.json').read_bytes())
    T.check('I11', 'decision_N22 assembled/rounding hashes = the shipped final records',
            d22['assembled_sha256'] == sha(R / 'assembled.json') and d22['rounding_sha256'] == sha(R / 'rounding.json'))
    T.check('I12', 'decision_N22 reason is stopping rule (a)', d22['reasons'] == ['(a) converged to the floating-point floor'], '(a)', d22['reasons'])
    # validation approval and level headers
    ident = AP['identities']
    T.check('I13', 'validation: APPROVED.pass and summary.json pass with no failed/missing gates',
            AP['pass'] is True and S['pass'] is True and not S['failed'] and not S['missing'] and not S['not_passed'])
    T.check('I14', 'sha256(src/c6sum.cpp) = APPROVED source identity', sha(PKG / 'src/c6sum.cpp') == ident['source'], ident['source'][:16], sha(PKG / 'src/c6sum.cpp')[:16])
    problems = []
    for f in files:
        try:
            rec = validate_level(lv / f)
        except Exception as e:  # noqa: BLE001
            problems.append(f'{f}: {e}'); continue
        h = rec['header']; L = int(h['L'])
        exe = ident['c6sum'] if h['kind'] == 'double8' else ident['c6sum_ld']
        wkey = 'bin_sha256' if h['kind'] == 'double8' else 'dd_sha256'
        if h['source_sha256'] != ident['source'] or h['exe_sha256'] != exe or h['graphs_sha256'] != ident[f'graphs{L + 1}'] \
                or man.get(f'L{L}_N{h["N"]}', {}).get(wkey) != h['weights_sha256'] or h.get('git') != '8680864':
            problems.append(f'{f}: header identities')
    T.check('I15', 'every level record validates (levelio) and its header names the approved source, executable, graphs, '
            'weights (manifest) and git 8680864', not problems, 'none', problems[:3])
    # run files named by the level records
    runs = D / 'runs'; missing = []; badr = []; nrun = 0
    for f in files:
        rec = json.loads((lv / f).read_bytes())
        for path, h in rec['inputs_sha256'].items():
            nrun += 1
            if not path.startswith(RUNS_PREFIX):
                badr.append(path); continue
            q = runs / path[len(RUNS_PREFIX):]
            if not q.is_file():
                missing.append(path[len(RUNS_PREFIX):])
            elif sha(q) != h:
                badr.append(path[len(RUNS_PREFIX):])
    T.check('I16', 'every run file named by a level record ships (data/runs) with that sha256', not missing and not badr and nrun == 84,
            '84 files', f'{nrun} named, {len(missing)} missing, {len(badr)} mismatched')
    # cross-check record
    X = json.loads((R / 'C7_crosscheck.json').read_bytes())
    T.check('I17', 'C7_crosscheck.json binds C6_final.json by sha256', X['inputs_sha256'].get(C6_LABEL) == sha(R / 'C6_final.json'))
    T.check('I18', 'C7_crosscheck.json binds the C7 package C7_final.json (sha256 b44b3a13...)', X['inputs_sha256'].get(C7_LABEL) == C7_FINAL_SHA)
    c7 = find_c7(args)
    if c7 is None:
        T.add('I19', 'C7_final.json found and equal to the bound hash', 'SKIP', C7_FINAL_SHA[:16], 'not found (set C7_FINAL=...)', 'bitwise')
    else:
        where = os.path.relpath(c7, PKG) if str(c7).startswith(str(PKG.parents[1])) else str(c7)
        T.check('I19', f'C7_final.json at {where} has the bound sha256', sha(c7) == C7_FINAL_SHA, C7_FINAL_SHA[:16], sha(c7)[:16])
    return F, A, Rn, S


# --------------------------------------------------------------------------------------------------- recompute
def substitute_byproduct(raw_cur):
    """analyze.py at cef6fa7 differs from the production revision 8680864 in one diagnostic only (commit ee2e013,
    results review RR-002): diagnostics.C7_package_byproduct (hardcoded 14331.62055 +- 0.30500) became the string
    diagnostics.C7_package_crosscheck. Put the 8680864 entry back in the same position, then serialize as analyze.py."""
    import mpmath as mp
    mp.mp.dps = 40
    d = json.loads(raw_cur)
    head = mp.mpf(d['headline']['C6_unrounded'])
    c7, se = mp.mpf('14331.62055'), mp.mpf('0.30500')
    d['diagnostics'] = {('C7_package_byproduct' if k == 'C7_package_crosscheck' else k):
                        ({'value': mp.nstr(c7, 10), 'SE': mp.nstr(se, 3), 'z': mp.nstr((head - c7) / se, 4)} if k == 'C7_package_crosscheck' else v)
                        for k, v in d['diagnostics'].items()}
    return json.dumps(d, indent=1, default=str)


def pipeline(levels, R, D, out, n, T, rid):
    """assemble.py, rounding.py, analyze.py (final mode, with resources and decision dir) on one level directory."""
    out.mkdir(parents=True, exist_ok=True)
    man = R / 'weights_manifest.json'
    run([PY, '-B', PKG / 'tools/assemble.py', levels, man, out / 'assembled.json'])
    run([PY, '-B', PKG / 'tools/rounding.py', levels, man, out / 'rounding.json'])
    res = (R / 'resources_N22.json') if n == 22 else (D / f'analysis/resources_N{n}.json')
    run([PY, '-B', PKG / 'tools/analyze.py', out / 'assembled.json', out / 'rounding.json', out / f'C6_N{n}.json',
         '--resources', res, '--decision-dir', out / 'decisions'])
    dec = out / f'decisions/decision_N{n}.json'
    T.check(rid, f'stage N*={n}: regenerated decision_N{n}.json = shipped (binds the stage assembled/rounding hashes)',
            sha(dec) == sha(R / f'decisions/decision_N{n}.json'), sha(R / f'decisions/decision_N{n}.json')[:16], sha(dec)[:16])
    return json.loads((out / f'C6_N{n}.json').read_text())


def recompute(T, R, D, W, args):
    lv = D / 'levels'
    fin = W / 'final'
    shutil.rmtree(fin, ignore_errors=True)
    F = pipeline(lv, R, D, fin, 22, T, 'B01')
    T.check('B02', 'regenerated assembled.json = shipped (degree sequence, L5 configurations, pole errors)',
            sha(fin / 'assembled.json') == EXPECT['assembled.json'], EXPECT['assembled.json'][:16], sha(fin / 'assembled.json')[:16])
    T.check('B03', 'regenerated rounding.json = shipped (rho(N), calibration)', sha(fin / 'rounding.json') == EXPECT['rounding.json'],
            EXPECT['rounding.json'][:16], sha(fin / 'rounding.json')[:16])
    sub = substitute_byproduct((fin / 'C6_N22.json').read_text())
    (fin / 'C6_final_8680864_form.json').write_text(sub)
    T.check('B04', 'regenerated C6_final.json, with the documented RR-002 diagnostic change undone, = shipped C6_final.json',
            hashlib.sha256(sub.encode()).hexdigest() == EXPECT['C6_final.json'], EXPECT['C6_final.json'][:16], hashlib.sha256(sub.encode()).hexdigest()[:16])
    cur = json.loads((fin / 'C6_N22.json').read_text()); old = json.loads((R / 'C6_final.json').read_bytes())
    T.check('B05', 'headline, components and level table identical (fields)', cur['headline'] == old['headline'] and cur['levels'] == old['levels'])
    # stage replays: the level directory as it was when the decision at N* = n was taken (L6 degrees <= n)
    heads = {}
    for n in STAGES:
        sd = W / f'stage_N{n}'; shutil.rmtree(sd, ignore_errors=True); (sd / 'levels').mkdir(parents=True)
        for f in lv.glob('*.json'):
            m = re.match(r'L6_.*_N(\d+)\.', f.name)
            if not m or int(m.group(1)) <= n:
                shutil.copy2(f, sd / 'levels' / f.name)
        heads[n] = pipeline(sd / 'levels', R, D, sd, n, T, 'B06')['headline']
    for n, (c, u) in {16: ('14331.687033', '0.000058'), 18: ('14331.6870328', '0.0000036'), 20: ('14331.68703273', '3.0E-7')}.items():
        T.check('B07', f'stage headline at N*={n} (driver log, review log)', (heads[n]['C6'], heads[n]['allowance_U']) == (c, u),
                f'{c} +- {u}', f"{heads[n]['C6']} +- {heads[n]['allowance_U']}", 'exact string')
    # re-merge every level from its run files
    sys.path.insert(0, str(PKG / 'tools'))
    rm = W / 'remerge'; shutil.rmtree(rm, ignore_errors=True); rm.mkdir(parents=True)
    bad = []
    for f in sorted(lv.glob('*.json')):
        rec = json.loads(f.read_bytes())
        parts = [D / 'runs' / p[len(RUNS_PREFIX):] for p in rec['inputs_sha256']]
        out = rm / f.name
        run([PY, '-B', PKG / 'tools/merge.py', out] + parts + ['--subset', rec['subset']])
        new = json.loads(out.read_bytes())
        norm = lambda dct: {k[len(RUNS_PREFIX):] if k.startswith(RUNS_PREFIX) else os.path.relpath(k, D / 'runs'): v for k, v in dct.items()}
        same = all(new[k] == rec[k] for k in rec if k not in ('inputs_sha256', 'attempts')) and set(new) == set(rec) \
            and norm(new['inputs_sha256']) == norm(rec['inputs_sha256']) and norm(new['attempts']) == norm(rec['attempts'])
        if not same:
            bad.append(f.name)
    T.check('B08', 'tools/merge.py on the shipped run files reproduces all 62 level records (per-sector values, totals, header; '
            'input paths compared relative to runs/)', not bad, 'all 62', bad[:3])
    # weights tables: regenerate all 21 with tools/weights.py and compare with the manifest
    wd = W / 'weights'; shutil.rmtree(wd, ignore_errors=True); wd.mkdir(parents=True)
    man = json.loads((R / 'weights_manifest.json').read_bytes())
    for L in (5, 6):
        Ns = sorted(int(k.split('_N')[1]) for k in man if k.startswith(f'L{L}_'))
        run([PY, '-B', PKG / 'tools/weights.py', wd, L, ','.join(map(str, Ns))])
    new = json.loads((wd / 'weights_manifest.json').read_text())
    diff = [k for k in man if {x: man[k][x] for x in ('bin_sha256', 'dd_sha256', 'dps')} != {x: new.get(k, {}).get(x) for x in ('bin_sha256', 'dd_sha256', 'dps')}]
    T.check('B09', 'tools/weights.py regenerates all 21 weight tables (float64 and double-double) with the manifest sha256',
            not diff and len(man) == 21, '21 tables', f'{len(man)} in manifest, {len(diff)} differ {diff[:3]}')
    # RR-001 propagation from the saved lower-amplitude reruns
    r = run([PY, '-B', PKG / 'tools/lowercmp.py', PKG / 'reference', R / 'lower_amplitude_precision', lv])
    (W / 'R6_comparison.json').write_text(r.stdout)
    T.check('B10', 'tools/lowercmp.py output = lower_amplitude_precision/R6_comparison.json (RR-001)',
            hashlib.sha256(r.stdout.encode()).hexdigest() == EXPECT['lower_amplitude_precision/R6_comparison.json'])
    # RR-002: C7 cross-check, run where the recorded input labels resolve
    c7 = find_c7(args)
    if c7 is None or sha(c7) != C7_FINAL_SHA:
        T.add('B11', 'tools/c7_crosscheck.py regenerates C7_crosscheck.json (RR-002)', 'SKIP', '', 'C7_final.json not found or other hash', 'bitwise')
    else:
        xd = W / 'c7x'; shutil.rmtree(xd, ignore_errors=True)
        for lab, src in ((C7_LABEL, c7), (C6_LABEL, R / 'C6_final.json')):
            (xd / lab).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, xd / lab)
        run([PY, '-B', PKG / 'tools/c7_crosscheck.py', C7_LABEL, C6_LABEL, 'C7_crosscheck.json'], cwd=xd)
        T.check('B11', 'tools/c7_crosscheck.py regenerates C7_crosscheck.json (RR-002)', sha(xd / 'C7_crosscheck.json') == EXPECT['C7_crosscheck.json'])
    # exact RG-assembly algebra (sympy) and the lower-degree assembly records of reference/
    ad = W / 'algebra'; shutil.rmtree(ad, ignore_errors=True); ad.mkdir(parents=True)
    shutil.copy2(PKG / 'reference/verify_algebra.py', ad)
    run([PY, '-B', ad / 'verify_algebra.py'])
    what = 'reference/verify_algebra.py (exact rational check of the sixth-order RG assembly) reproduces six_loop_algebra_checks.json'
    if sha(ad / 'six_loop_algebra_checks.json') == sha(PKG / 'reference/six_loop_algebra_checks.json'):
        T.check('B12', what, True)
    else:  # another sympy version may print the same polynomial in another term order
        import sympy
        a = json.loads((ad / 'six_loop_algebra_checks.json').read_text()); b = json.loads((PKG / 'reference/six_loop_algebra_checks.json').read_text())
        same = set(a) == set(b) and all(a[k] == b[k] or (isinstance(a[k], str) and sympy.simplify(sympy.sympify(a[k]) - sympy.sympify(b[k])) == 0)
                                        for k in b if k != 'method') and a['exact_checks_passed'] is True
        T.check('B12', what, same, 'bytes or equal expressions', 'bytes differ' + (', expressions equal' if same else ''), 'symbolic (sympy printing)')
    # same loop order and serialization as the __main__ block of assemble6.py, printed instead of written into reference/
    code = ("import sys,json;r=sys.argv[1];sys.path[:0]=[r,r+'/lri_numerical_resolution/verification'];"
            "import assemble6 as A;from laurent_assembly import serial;"
            "o={f'{c}_{n}':A.baseline(c,n) for n in [16,22,28] for c in ['maxgap','span']};"
            "print(json.dumps(serial(o),indent=2),end='')")
    r = run([PY, '-B', '-c', code, PKG / 'reference'])
    (W / 'assembly_lower6.json').write_text(r.stdout)
    T.check('B13', 'reference/assemble6.py baseline() reproduces assembly_lower6.json (R6 at lower degree 16/22/28; asserts the '
            'unit sensitivities -2/729 and 4/243)', r.stdout == (PKG / 'reference/assembly_lower6.json').read_text())
    return F


# --------------------------------------------------------------------------------------------------- quoted numbers
def quoted(T, R, F, A, Rn, S):
    import mpmath as mp
    mp.mp.dps = 50
    H = F['headline']; C = H['components']
    T.check('Q01', 'headline C6(1) = 14331.68703277 +- 4.9E-7 (note Sec 22.1, abstract of REPORT.md)',
            (H['C6'], H['allowance_U'], H['N_star'], H['L5_M_star'], H['f']) == ('14331.68703277', '4.9E-7', 22, 40, 1),
            '14331.68703277 4.9E-7 N*=22 M*=40 f=1', f"{H['C6']} {H['allowance_U']} N*={H['N_star']} M*={H['L5_M_star']} f={H['f']}", 'exact string')
    pnum(T, 'Q02', 'unrounded headline 14331.68703276838', H['C6_unrounded'], '14331.68703276838', 'note Sec 1, 1.2, 22.9')
    pnum(T, 'Q03', 'short form 14331.6870328(5)', H['C6_unrounded'], '14331.6870328', 'note Sec 1, 1.2')
    s = sum(mpf(v) for v in C.values())
    T.check('Q04', 'U = ceil_2sf(sum of the six components)', str(ceil_2sf(mp.nstr(s, 20))) == H['allowance_U'] == '4.9E-7', '4.9E-7', ceil_2sf(mp.nstr(s, 20)), 'exact')
    for k, txt in (('U_conv', '8.0e-8'), ('U_cut', '2.5e-9'), ('U_round', '3.5e-7'), ('U5', '8.7e-9'), ('U5_round', '4.1e-8'), ('Ulow', '3.1e-9')):
        pnum(T, 'Q05', f'allowance term {k}', C[k], txt, 'note Sec 22.5, REPORT')
    pnum(T, 'Q06', 'calibration factor', H['cal'], '1.03', 'note Sec 22.5')
    table = {6: ('14334.549146861', '14332.554509427', '1.99', '5.5e-10'), 8: ('14331.816869671', '14331.694925294', '0.122', '1.9e-10'),
             10: ('14331.694513177', '14331.686134511', '8.4e-3', '7.4e-10'), 12: ('14331.687501161', '14331.686917319', '5.8e-4', '1.9e-9'),
             14: ('14331.687061994', '14331.687022076', '4.0e-5', '4.1e-9'), 16: ('14331.687034432', '14331.687031833', '2.6e-6', '2.9e-9'),
             18: ('14331.687032845', '14331.687032694', '1.5e-7', '3.3e-8'), 20: ('14331.687032736', '14331.687032727', '9.1e-9', '4.5e-9'),
             22: ('14331.687032770', '14331.687032767', '2.5e-9', '8.8e-8')}
    lev = {r['N']: r for r in F['levels']}
    T.check('Q07', 'degree sequence N = 6, 8, ..., 22 complete', sorted(lev) == list(range(6, 23, 2)), '6..22', sorted(lev), 'exact')
    for N, (cm, cs, dd, rho) in table.items():
        r = lev[N]
        ok = printed_ok(r['C6_maxgap'], cm) and printed_ok(r['C6_span'], cs) and printed_ok(r['maxgap_minus_span'], dd) and printed_ok(r['rho'], rho)
        T.check('Q08', f'degree table N={N}: maxgap, span, maxgap-span, rho (note Sec 22.5, REPORT)', ok, f'{cm} {cs} {dd} {rho}',
                f"{r['C6_maxgap']} {r['C6_span']} {r['maxgap_minus_span']} {r['rho']}", 'printed')
    r22 = lev[22]
    pnum(T, 'Q09', 'last change maxgap at N=22', r22['delta_maxgap'], '3.3e-8', 'note Sec 22.5')
    pnum(T, 'Q09', 'last change span at N=22', r22['delta_span'], '4.0e-8', 'note Sec 22.5')
    pnum(T, 'Q09', '2 rho(22)', 2 * mpf(r22['rho']), '1.8e-7', 'note Sec 22.5')
    T.check('Q10', 'stopping rule (a) holds at N=22 and not at N=16, 18, 20', r22.get('stop_a_converged_to_floor') is True and
            all(lev[n].get('stop_a_converged_to_floor') is False for n in STAGES), 'True at 22 only')
    rat = {c: [mpf(lev[n]['ratio'][c]) for n in (12, 14, 16, 18, 20)] for c in CUTS}
    T.check('Q11', 'step ratios N=12..20 near 0.06 (maxgap) and 0.1 (span) (note Sec 22.5: "about")',
            all(mpf('0.04') <= x <= mpf('0.08') for x in rat['maxgap']) and all(mpf('0.03') <= x <= mpf('0.14') for x in rat['span']),
            'maxgap 0.04-0.08, span 0.03-0.14', {c: [mp.nstr(x, 3) for x in v] for c, v in rat.items()}, 'range')
    cf = A['configs']['L5_M40']
    for c, (r6, j5, k) in {'maxgap': ('39814.47028245011', '-231603.7671545272', '36002.06259266366'),
                           'span': ('81364.48627171610', '-1836182.1032583138', '51139.26646499489')}.items():
        ok = printed_ok(cf[c]['R6'], r6) and printed_ok(cf[c]['J5'], j5) and printed_ok(cf[c]['K'], k)
        T.check('Q12', f'assembly inputs R6, J5, K ({c}) (note Sec 22.4 table)', ok, f'{r6} {j5} {k}', f"{cf[c]['R6']} {cf[c]['J5']} {cf[c]['K']}", 'printed')
    seq = F['diagnostics']['L5_sequence_at_Nstar']
    steps = {c: {M: mpf(seq[f'L5_M{M}'][c]) - mpf(seq[f'L5_M{M - 4}'][c]) for M in range(16, 41, 4)} for c in CUTS}
    mx = max(abs(v) for c in CUTS for M, v in steps[c].items() if M >= 28)
    T.check('Q13', 'U5 = 2 max|C6(M=40) - C6(M=36)|', printed_ok(2 * max(abs(steps[c][40]) for c in CUTS), '8.7e-9'), '8.7e-9',
            mp.nstr(2 * max(abs(steps[c][40]) for c in CUTS), 3), 'printed')
    T.check('Q14', 'note Sec 22.4 (public edition 97dd353): "From M=28 onward, successive changes of C6 are at most 4.4e-9, '
            'below the measured five-loop rounding sensitivity of 1.0e-8"', mx <= mpf('4.4e-9') and mx < mpf('1.0e-8'),
            '<= 4.4e-9', mp.nstr(mx, 3), 'bound')
    ac = json.loads((PKG / 'reference/additional_checks.json').read_text())['lower_order_degree_controls']
    pnum(T, 'Q15', 'lower amplitudes degree 28 minus 22, maxgap', ac['maxgap']['N28_minus_N22'], '-1.54e-9', 'note Sec 22.4')
    pnum(T, 'Q15', 'lower amplitudes degree 28 minus 22, span', ac['span']['N28_minus_N22'], '4.14e-10', 'note Sec 22.4')
    T.check('Q15', 'Ulow = 2 max|degree 28 - 22| (analyze.py ulow)', abs(2 * max(abs(mpf(ac[c]['N28_minus_N22'])) for c in CUTS) - mpf(C['Ulow'])) < mpf('1e-14'),
            C['Ulow'], mp.nstr(2 * max(abs(mpf(ac[c]['N28_minus_N22'])) for c in CUTS), 6), '1e-14 absolute')
    a5 = json.loads(Path(PKG / 'reference/assembly_lower6.json').read_text())
    T.check('Q15', 'additional_checks.json N28-N22 = assembly_lower6.json C6_lower(28) - C6_lower(22)',
            all(abs(mpf(a5[f'{c}_28']['C6_lower']) - mpf(a5[f'{c}_22']['C6_lower']) - mpf(ac[c]['N28_minus_N22'])) < mpf('1e-40') for c in CUTS), '', '', '1e-40 absolute')
    rr = json.loads((R / 'lower_amplitude_precision/R6_comparison.json').read_text())
    f64 = max(abs(mpf(rr[c]['R6_f64_minus_ld'])) for c in CUTS)
    pnum(T, 'Q16', 'RR-001: float64 minus long double of the L2-L4 amplitudes, in C6', f64, '6.0e-8', 'note Sec 22.4; REPORT -5.95e-8, -5.90e-8')
    pnum(T, 'Q16', 'RR-001: implied long-double rounding f64 * 2^-11', f64 / 2 ** 11, '3e-11', 'note Sec 22.4, REPORT 2.9e-11')
    pnum(T, 'Q16', 'RR-001: long-double rerun reproduces the saved amplitudes (max relative)', max(rr[c]['max_rel_amplitude_diff']['ld'] for c in CUTS), '4.7e-17', 'REPORT')
    pnum(T, 'Q16', 'RR-001: R6 change of the long-double rerun, maxgap', rr['maxgap']['R6_ld_minus_saved'], '1.3e-13', 'REPORT')
    pnum(T, 'Q16', 'RR-001: R6 change of the long-double rerun, span', rr['span']['R6_ld_minus_saved'], '2.7e-13', 'REPORT')
    T.check('Q16', 'RR-001: U unchanged with Ulow_round = 4 f64 2^-11; 5.5e-7 with the full float64 difference',
            str(ceil_2sf(mp.nstr(s + 4 * f64 / 2 ** 11, 20))) == '4.9E-7' and str(ceil_2sf(mp.nstr(s + f64, 20))) == '5.5E-7', '4.9E-7, 5.5E-7',
            f'{ceil_2sf(mp.nstr(s + 4 * f64 / 2 ** 11, 20))}, {ceil_2sf(mp.nstr(s + f64, 20))}', 'exact')
    pe = F['diagnostics']['pole_errors']
    for N, txt in ((10, '9.2e-2'), (14, '8.0e-4'), (18, '5.2e-6'), (22, '6.9e-8')):
        pnum(T, 'Q17', f'RG double-pole error, maxgap, N={N}', pe[str(N)]['maxgap']['-2'], txt, 'note Sec 22.6')
    pnum(T, 'Q17', 'RG triple-pole error, maxgap, N=22', pe['22']['maxgap']['-3'], '2.7e-9', 'note Sec 22.6')
    mc = F['diagnostics']['light_stratum_vs_reference_MC']
    for key, fld, (zm, zs) in (('8-6, light', 'z', ('-0.57', '-0.60')), ('10-8, light', 'z', ('0.86', '1.33')), ('12-10', 'z_all', ('0.09', '1.26'))):
        ok = printed_ok(mc[key]['maxgap'][fld], zm) and printed_ok(mc[key]['span'][fld], zs)
        T.check('Q18', f'exact vs old Monte Carlo level, z in old SE, {key} (note Sec 22.6, REPORT)', ok, f'{zm} {zs}', f"{mc[key]['maxgap'][fld]} {mc[key]['span'][fld]}", 'printed')
    ok = printed_ok(mc['12-10']['maxgap']['z_light'], '0.43') and printed_ok(mc['12-10']['span']['z_light'], '0.80')
    T.check('Q18', 'light 12-10 z (results dossier)', ok, '0.43 0.80', f"{mc['12-10']['maxgap']['z_light']} {mc['12-10']['span']['z_light']}", 'printed')
    old = F['diagnostics']['old_result']
    T.check('Q19', 'old estimate 14331.77075 (SE 0.14344) was high by 0.084 = 0.58 old SE (note Sec 22.1)',
            printed_ok(old['old'], '14331.77075') and printed_ok(old['old_SE'], '0.14344') and printed_ok(mpf(old['old']) - mpf(H['C6_unrounded']), '0.084')
            and printed_ok(old['z_using_old_SE'], '-0.58'), '14331.77075 0.14344 0.084 -0.58',
            f"{old['old']} {old['old_SE']} {mp.nstr(mpf(old['old']) - mpf(H['C6_unrounded']), 4)} {old['z_using_old_SE']}", 'printed')
    hd = A['diagnostics']['hard_dbl_minus_ld_C6']
    T.check('Q20', 'hard stratum binary64 minus extended, in C6, N=6, 8, 10 (maxgap) (note Sec 22.3)',
            printed_ok(abs(mpf(hd['6']['maxgap'])), '5e-9') and printed_ok(abs(mpf(hd['8']['maxgap'])), '7.6e-8') and printed_ok(abs(mpf(hd['10']['maxgap'])), '1.5e-7'),
            '5e-9 7.6e-8 1.5e-7', f"{hd['6']['maxgap']} {hd['8']['maxgap']} {hd['10']['maxgap']}", 'printed (magnitude)')
    ld = F['diagnostics']['L5_double_minus_longdouble_C6_at_Nstar']; rp = F['diagnostics']['retained_pole_config']
    pnum(T, 'Q21', 'L5 binary64 minus long double at M=40, maxgap', ld['maxgap'], '1.2e-6', 'REPORT')
    T.check('Q21', 'old retained five-loop inputs move C6 by -1.4e-5 and -6.6e-6 (REPORT)', printed_ok(rp['maxgap'], '-1.4e-5') and printed_ok(rp['span'], '-6.6e-6'),
            '-1.4e-5 -6.6e-6', f"{rp['maxgap']} {rp['span']}", 'printed')
    ref6 = json.loads((PKG / 'reference/full_H_L6_N6_0_10000.json').read_text(), parse_float=str)['values']
    H6 = A['levels']['6']['H6_vector']
    dv = [-mpf(2) / 729 * (mpf(ref6[i]) - mpf(H6[i])) for i in (5, 11)]
    T.check('Q22', 'earlier degree-six value minus present, in C6 (note Sec 22.3, public edition: "about 1e-5")',
            all(mpf('5e-6') <= abs(x) <= mpf('1.5e-5') for x in dv), 'about 1e-5', [mp.nstr(x, 3) for x in dv], '5e-6..1.5e-5')
    rl = [mpf(r['rho_light']) for r in Rn['levels'].values()]
    T.check('Q23', 'light-stratum perturbation estimate for all N (note, public edition: "at most 7e-10")', max(rl) <= mpf('7e-10'),
            '<= 7e-10 for all N', mp.nstr(max(rl), 3), 'bound')
    g = S['gates']
    v1 = {nv: g[f'V1_enumeration_nv{nv}']['info'] for nv in (6, 7)}
    T.check('Q24', 'graph counts 59,145 / 49,605 (five loops) and 2,427,005 / 2,137,415 (six loops), sum w_H -133,200 and -5,519,062.5 (V1, note Sec 22.2)',
            'total=59145 nonzero=49605' in v1[6] and 'sumH=-133200' in v1[6] and 'total=2427005 nonzero=2137415' in v1[7] and 'sumH=-5519062.5' in v1[7], '', '')
    a6 = json.loads((PKG / 'reference/additional_checks.json').read_text())
    sc = {k: (a6[k]['sum_scaled_A'] / 1728, a6[k]['sum_scaled_B'] / 1728, a6[k]['sum_scaled_H'] / 1728, a6[k]['zero_H'], a6[k]['positive_H']) for k in ('graphs6', 'graphs7')}
    T.check('Q24', 'weight sums and zero counts of the note table (reference/additional_checks.json; every surviving w_H negative)',
            sc == {'graphs6': (197887.5, 21562.5, -133200.0, 9540, 0), 'graphs7': (7716476.25, 732471.25, -5519062.5, 289590, 0)}, '', sc, 'exact')
    x = [g['V11_xarch_hard_ld_N6'], g['V11_xarch_L5_J16_ld']]
    T.check('Q25', 'V11: binary64 bitwise equal AMD vs Intel; extended precision agrees to 1.7e-16 (note Sec 22.3)',
            not g['V11_xarch_light_dbl_N8']['differing'] and printed_ok(max(mpf(y['max_relative_difference']) for y in x), '1.7e-16'),
            '1.7e-16', max(y['max_relative_difference'] for y in x), 'printed')
    res = F['diagnostics']['stopping']['resources']
    T.check('Q26', 'production cost about 45 node-hours (note Sec 22.3; REPORT 44.5)', printed_ok(res['production_node_hours'], '44.5'), '44.5', res['production_node_hours'], 'printed')
    T.check('Q27', 'record vs PLAN constants: old value 14331.77075 / SE 0.14344 equal reference/C6_result_original.json',
            json.loads((PKG / 'reference/C6_result_original.json').read_text())['underlying_control_estimate'] == float(old['old']), '', '', 'exact')


def quoted_c7(T, R):
    X = json.loads((R / 'C7_crosscheck.json').read_bytes())
    st = X['stages']
    se, s6, s7, ref = X['C7_package_SE'], X['refine6_level'], X['step7'], X['exact_C6']
    r = s7 / s6; tail = s7 * r / (1 - r)
    d6 = st['degree6']['value']
    ok = abs(X['tail_ratio'] - r) == 0 and abs(X['tail'] - tail) == 0 and st['degree6_plus_step7']['value'] == d6 + s7 \
        and st['degree6_plus_step7_plus_tail']['value'] == d6 + s7 + tail and all(v['z'] == (v['value'] - ref) / se and v['minus_exact'] == v['value'] - ref for v in st.values())
    T.check('Q28', 'C7_crosscheck.json internal arithmetic (stages, tail, z) recomputed from its own fields', ok, '', '', 'bitwise (float64)')
    F = json.loads((R / 'C6_final.json').read_bytes())
    T.check('Q28', 'C7_crosscheck.json exact_C6 = C6_final headline (unrounded)', X['exact_C6'] == float(F['headline']['C6_unrounded']), '', '', 'float64')
    for k, (v, z) in {'degree6': ('14332.43593', '2.46'), 'degree6_plus_step7': ('14331.98210', '0.97'), 'degree6_plus_step7_plus_tail': ('14331.62055', '-0.22')}.items():
        T.check('Q29', f'C7-package six-loop stage {k}: value and z (note Sec 22.6, REPORT)', printed_ok(st[k]['value'], v) and printed_ok(st[k]['z'], z),
                f'{v} z {z}', f"{st[k]['value']:.5f} z {st[k]['z']:.3f}", 'printed')
    T.check('Q29', 'C7-package SE 0.30500, step -0.45383, tail ratio 0.443, tail -0.36156 (note Sec 22.6, REPORT)',
            printed_ok(se, '0.30500') and printed_ok(s7, '-0.45383') and printed_ok(X['tail_ratio'], '0.443') and printed_ok(X['tail'], '-0.36156'),
            '0.30500 -0.45383 0.443 -0.36156', f"{se:.5f} {s7:.5f} {X['tail_ratio']:.3f} {X['tail']:.5f}", 'printed')


# --------------------------------------------------------------------------------------------------- smoke, rerun-lower
def smoke(T, R, D, W, args):
    """Build the engines (package Makefile) in a scratch copy, enumerate the five-loop graphs, generate the degree-12
    five-loop weights, and rerun the L5 M=12 levels (H and J) in long double and double; compare with the shipped
    production levels. Expected: about 1-3 minutes on an x86-64 Linux node with g++ >= 11 (not timed)."""
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'AMD64'):
        T.add('S00', 'smoke needs x86-64 Linux (AVX2 engine, 80-bit long double)', 'SKIP', 'x86_64 Linux', f'{platform.system()} {platform.machine()}', '')
        return
    import mpmath as mp
    mp.mp.dps = 50
    sd = W / 'smoke'; shutil.rmtree(sd, ignore_errors=True); (sd / 'pkg').mkdir(parents=True)
    for p in ('Makefile', 'src', 'tools', 'reference/enumerate.cpp'):
        (sd / 'pkg' / p).parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if (PKG / p).is_dir() else shutil.copy2)(PKG / p, sd / 'pkg' / p)
    (sd / 'pkg/GIT_SHA').write_text('public\n')
    r = subprocess.run(['make', '-B', 'all'], cwd=sd / 'pkg', capture_output=True, text=True)
    if not T.check('S01', 'make all builds bin/c6sum, bin/c6sum_ld, bin/enumerate', r.returncode == 0, 0, r.returncode, (r.stderr or '')[-200:]):
        return
    data = sd / 'data'; data.mkdir()
    run([sd / 'pkg/bin/enumerate', 6, data / 'graphs6.bin'])
    AP = json.loads((R / 'validation/APPROVED.json').read_bytes())['identities']
    T.check('S02', 'bin/enumerate 6 reproduces graphs6.bin (approved sha256)', sha(data / 'graphs6.bin') == AP['graphs6'], AP['graphs6'][:16], sha(data / 'graphs6.bin')[:16])
    run([PY, '-B', sd / 'pkg/tools/weights.py', data, 5, 12, '--check'])
    man = json.loads((R / 'weights_manifest.json').read_bytes())['L5_N12']
    T.check('S03', 'tools/weights.py 5 12 reproduces w_5_12.bin and w_5_12.dd.bin (manifest sha256)',
            sha(data / 'w_5_12.bin') == man['bin_sha256'] and sha(data / 'w_5_12.dd.bin') == man['dd_sha256'])
    threads = args.threads or os.cpu_count() or 1
    lvd = sd / 'levels'; lvd.mkdir()
    for kind, exe in (('ld', 'c6sum_ld'), ('dbl', 'c6sum')):
        for mode in ('H', 'J'):
            stem = f'L5_{mode}_all_N12.{kind}'; out = sd / 'runs' / stem; out.mkdir(parents=True)
            run([sd / f'pkg/bin/{exe}', 5, 12, threads, data, mode, '--out', out / 'part_000_060.jsonl', '--first', 0, '--stop', 60,
                 '--mod', 1, '--stratum', 'all', '--perturb', 0])
            run([PY, '-B', sd / 'pkg/tools/merge.py', '--leveldir', lvd, out / 'part_000_060.jsonl', '--subset', 'all'])
    for mode in ('H', 'J'):
        ref = json.loads((D / f'levels/L5_{mode}_all_N12.ld.json').read_bytes())['totals']
        for kind, tol in (('ld', '1e-14'), ('dbl', '1e-9')):
            new = json.loads((lvd / f'L5_{mode}_all_N12.{kind}.json').read_bytes())['totals']
            rel = max(abs(mpf(a) - mpf(b)) / max(abs(mpf(b)), mpf('1e-300')) for a, b in zip(new, ref))
            T.check('S04', f'L5 {mode} M=12 ({kind}) vs the production long-double level (V11 / V4b tolerances)', rel <= mpf(tol),
                    f'<= {tol}', mp.nstr(rel, 3), 'max relative per entry')


def rerun_lower(T, R, D, W):
    """RR-001 rerun: tools/lowercheck.py at degree 28 in long double and float64 (about 15 s each), then lowercmp."""
    import numpy as np, mpmath as mp
    mp.mp.dps = 50
    ld_ok = np.finfo(np.longdouble).nmant >= 63
    od = W / 'rerun_lower'; shutil.rmtree(od, ignore_errors=True); od.mkdir(parents=True)
    modes = ('ld', 'f64') if ld_ok else ('f64',)
    if not ld_ok:
        T.add('L00', 'numpy long double is 80-bit (needed for the ld rerun)', 'SKIP', '64-bit mantissa', f'{np.finfo(np.longdouble).nmant + 1}-bit', 'run on x86-64')
    for m in modes:
        run([PY, '-B', PKG / 'tools/lowercheck.py', PKG / 'reference', m, 28, od / f'lower28_{m}.json'])
        a = json.loads((od / f'lower28_{m}.json').read_text())['result']; b = json.loads((R / f'lower_amplitude_precision/lower28_{m}.json').read_text())['result']
        rel = mpf(0)
        for c in CUTS:
            for L in a[c]:
                for x, y in zip(a[c][L], b[c][L]):
                    for k in y:
                        rel = max(rel, abs(mpf(x[k]) - mpf(y[k])) / abs(mpf(y[k])) if mpf(y[k]) else abs(mpf(x[k])))
        tol = '1e-15' if m == 'ld' else '1e-10'
        T.check('L01', f'lowercheck {m} degree 28 vs the symmetry rerun (lower28_{m}.json)', rel <= mpf(tol), f'<= {tol}', mp.nstr(rel, 3),
                'max relative' + ('' if m == 'ld' else '; float64 sums are platform dependent'))
    if not ld_ok:  # propagate this platform's float64 rerun against the shipped long-double record
        shutil.copy2(R / 'lower_amplitude_precision/lower28_ld.json', od / 'lower28_ld.json')
    r = run([PY, '-B', PKG / 'tools/lowercmp.py', PKG / 'reference', od, D / 'levels'])
    (od / 'R6_comparison.json').write_text(r.stdout)
    rr = json.loads(r.stdout); f = max(abs(mpf(rr[c]['R6_f64_minus_ld'])) for c in CUTS)
    F = json.loads((R / 'C6_final.json').read_bytes()); s = sum(mpf(v) for v in F['headline']['components'].values())
    T.check('L02', "U unchanged with this platform's float64 sensitivity: ceil_2sf(sum + 4 |f64 - ld| 2^-11) = 4.9E-7 "
            '(symmetry: |f64 - ld| = 5.95e-8)', str(ceil_2sf(mp.nstr(s + 4 * f / 2 ** 11, 20))) == '4.9E-7', '4.9E-7',
            f'|f64-ld| = {mp.nstr(f, 3)}', 'exact')


def compare_rerun(T, R, path):
    """A rerun with other executables (compiler, CPU) changes the sums at the rounding level only: require each
    C6^chi(N) within 4 rho(N) + 1e-12 of the shipped value (rho of the shipped run), the same stopping degree, and the
    headline within the shipped allowance U."""
    import mpmath as mp
    mp.mp.dps = 40
    new = json.loads(Path(path).read_text()); old = json.loads((R / 'C6_final.json').read_bytes())
    if new.get('headline') is None:
        T.add('C01', 'rerun analysis is final (has a headline)', 'FAIL', 'headline', 'provisional or refused', ''); return
    lo = {r['N']: r for r in old['levels']}; ln = {r['N']: r for r in new['levels']}
    T.check('C01', 'rerun stopped at the same degree N* = 22 by rule (a)', new['headline']['N_star'] == 22 and
            new['diagnostics']['stopping']['reasons'] == old['diagnostics']['stopping']['reasons'], 22, new['headline']['N_star'], 'exact')
    for N in sorted(lo):
        if N not in ln:
            T.add('C02', f'rerun has degree N={N}', 'FAIL', 'present', 'missing', ''); continue
        tol = 4 * mpf(lo[N]['rho']) + mpf('1e-12')
        d = max(abs(mpf(ln[N][f'C6_{c}']) - mpf(lo[N][f'C6_{c}'])) for c in CUTS)
        T.check('C02', f'C6^chi(N={N}) of the rerun vs the shipped run', d <= tol, f'<= 4 rho = {mp.nstr(tol, 3)}', mp.nstr(d, 3), 'per cutoff')
    d = abs(mpf(new['headline']['C6_unrounded']) - mpf(old['headline']['C6_unrounded']))
    T.check('C03', 'rerun headline within the shipped allowance U = 4.9e-7', d <= mpf(old['headline']['allowance_U']),
            '<= 4.9e-7', mp.nstr(d, 3), 'absolute')
    T.add('C04', f"rerun headline {new['headline']['C6']} +- {new['headline']['allowance_U']} (shipped 14331.68703277 +- 4.9E-7)", 'PASS', '', '', 'info')


# --------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', choices=('test', 'replay', 'smoke', 'rerun-lower', 'compare-rerun'))
    ap.add_argument('--rerun', default='', help='compare-rerun: C6_N<N*>.json of the rerun')
    ap.add_argument('--results', default=str(PKG / '../../results/C6_1'))
    ap.add_argument('--data', default=str(PKG / '../../data/C6_1'))
    ap.add_argument('--work', default=str(PKG / '.work'))
    ap.add_argument('--c7-final', default='')
    ap.add_argument('--threads', type=int, default=0)
    a = ap.parse_args()
    R, D, W = Path(a.results).resolve(), Path(a.data).resolve(), Path(a.work).resolve()
    W.mkdir(parents=True, exist_ok=True)
    T = Table()
    need = ((R / 'C6_final.json', 'results'),) + (((D / 'levels', 'data/levels'), (D / 'runs', 'data/runs')) if a.target in ('test', 'replay') else ())
    for p, what in need:
        if not p.exists():
            T.add('P00', f'{what} found at {p}', 'FAIL', 'present', 'missing', '')
            T.write(W, a.target); sys.exit(1)
    if a.target in ('test', 'replay'):
        F = A = Rn = S = None
        def _i():
            nonlocal F, A, Rn, S
            F, A, Rn, S = integrity(T, R, D, a)
        T.guard('I00', 'integrity checks', _i)
        if a.target == 'replay':
            T.guard('B00', 'recomputation', lambda: recompute(T, R, D, W, a))
            if F is not None:
                T.guard('Q00', 'quoted numbers', lambda: quoted(T, R, F, A, Rn, S))
            T.guard('Q00', 'C7 cross-check numbers', lambda: quoted_c7(T, R))
    elif a.target == 'smoke':
        T.guard('S00', 'smoke', lambda: smoke(T, R, D, W, a))
    elif a.target == 'rerun-lower':
        T.guard('L00', 'rerun-lower', lambda: rerun_lower(T, R, D, W))
    else:
        T.guard('C00', 'compare-rerun', lambda: compare_rerun(T, R, a.rerun))
    sys.exit(0 if T.write(W, a.target) else 1)


if __name__ == '__main__':
    main()
