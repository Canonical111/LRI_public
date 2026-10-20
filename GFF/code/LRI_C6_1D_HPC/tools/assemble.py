"""Assemble C6^chi(N) = R6^chi + (4/243) J5^chi - (2/729) H6^chi(N) from merged levels (PLAN.md rev 2, 4.4).

Production inputs (canonical names from tools/merge.py, in LEVELDIR):
  L6_H_light_N{N}.dbl.json   light stratum, double engine, all sectors
  L6_H_hard_N{N}.ld.json     hard stratum, long-double engine, all sectors     H6(N) = light + hard
  L5_{H,J}_all_N{M}.ld.json  five-loop inputs, long double, M = 12, 16, ..., 40
  L5_{H,J}_all_N40.ld.pert1.json  perturbed replicate (rounding of the L5 inputs)
Diagnostic inputs (optional): L5_{H,J}_all_N{M}.dbl.json, L6_H_hard_N{N}.dbl.json.
Any other file in LEVELDIR is ignored. Every loaded header must match its name; production levels must share one
source revision; all double levels one executable, all long-double levels one executable; one graph file per L.

R6 comes from reference/assemble6.py's Laurent-MS recursion (lower L2-L4 amplitudes at degree 28, unchanged) with the
five-loop poles A5 = 8 H5 - 3 J5, B5 = 3 H5 - J5 (as reference/five_loop_input_control.py); J5 is the eps^0 entry
of the J level. 'retained_poles_J16ref' reproduces the reference assembly (retained amplitude5_*_18 poles, saved J
at N16). RG predictions of the H6 poles eps^-6..eps^-2 are computed for the same inputs.

Usage: python assemble.py LEVELDIR MANIFEST OUT.json   (MANIFEST = data/weights_manifest.json)
"""
import sys, os, json, re, hashlib
from pathlib import Path
import mpmath as mp

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'reference'
sys.path.insert(0, str(REF))
sys.path.insert(0, str(REF / 'lri_numerical_resolution/verification'))
import assemble6 as A6  # noqa: E402  (sets mp.dps=70)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from levelio import validate_level, LevelError  # noqa: E402
from laurent_assembly import la_add  # noqa: E402

CUTS = ('maxgap', 'span')
KIND = {'dbl': 'double8', 'ld': 'reference-longdouble'}


def five_loop_data(cut, H5=None, J5=None):
    data = A6.inputs(cut, 28)
    if H5 is not None:
        i = CUTS.index(cut)
        for k in range(5):
            H = mp.mpf(H5[5 * i + k]); J = mp.mpf(J5[6 * i + k]); p = str(k - 5)
            data['5'][0][p] = mp.nstr(8 * H - 3 * J, 60); data['5'][1][p] = mp.nstr(3 * H - J, 60)
    return data


def predict_poles(data):
    """reference/pole_checks.py predict(), for explicit input data."""
    a = A6.assemble(data); G = a['G']; Z = a['Z']; b = a['beta']; c = a['gamma']
    gp = {}; zp = {}
    for i in range(1, 6):
        gp = la_add(gp, G[7 - i], b[i - 1] * (7 - i) / 6)
        zp = la_add(zp, Z[6 - i], ((6 - i) * b[i - 1] + c[i - 1]) / 6)
    gp = {k - 1: v for k, v in gp.items()}; zp = {k - 1: v for k, v in zp.items()}
    expect = la_add(la_add(Z[6], G[7], -mp.mpf(1) / 3), la_add(zp, gp, -mp.mpf(1) / 3), -1)
    return {k: 3 * v for k, v in expect.items() if k < -1}


def config(H5=None, J5vec=None, J5ref=None):
    out = {}
    for i, cut in enumerate(CUTS):
        d = five_loop_data(cut, H5, J5vec)
        R6 = A6.assemble(d)['C'][-1]
        J5 = mp.mpf(J5vec[6 * i + 5]) if J5vec is not None else mp.mpf(J5ref[6 * i + 5])
        out[cut] = {'R6': R6, 'J5': J5, 'K': R6 + mp.mpf(4) / 243 * J5, 'poles': predict_poles(d)}
    return out


MANIFEST = {}


def file_sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def load(d, L, mode, stratum, kind, pert=0):
    """{N: record} for files named exactly L{L}_{mode}_{stratum}_N{N}.{kind}[.pert{pert}].json (all sectors, comp 1)."""
    pat = re.compile(rf'L{L}_{mode}_{stratum}_N(\d+)\.{kind}' + (rf'\.pert{pert}' if pert else '') + r'\.json')
    out = {}
    for f in sorted(Path(d).iterdir()):
        m = pat.fullmatch(f.name)
        if not m:
            continue
        try:
            rec, sha = validate_level(f, with_sha=True)
        except LevelError as e:
            raise SystemExit(f'LEVEL INVALID: {e}')
        h = rec['header']; N = int(m.group(1))
        want = {'L': L, 'N': N, 'mode': mode, 'stratum': stratum, 'kind': KIND[kind], 'perturb': pert, 'comp': 1, 'mod': 1}
        got = {k: (h.get(k) if k in ('mode', 'stratum', 'kind') else int(h.get(k, -1))) for k in want}
        if got != want or rec.get('subset') != 'all':
            raise SystemExit(f'{f}: header {got} / subset {rec.get("subset")} does not match the file name and settings {want}')
        man = MANIFEST.get(f'L{L}_N{N}')
        wkey = 'bin_sha256' if kind == 'dbl' else 'dd_sha256'
        if not man or man[wkey] != h['weights_sha256']:
            raise SystemExit(f'{f}: weights_sha256 {h["weights_sha256"][:12]} not the manifest {wkey} for L{L} N{N}')
        rec['_file'] = f.name; rec['_sha256'] = sha
        out[N] = rec
    return dict(sorted(out.items()))


def check_provenance(named_sets):
    recs = [(name, r) for name, s in named_sets.items() for r in s.values()]
    if not recs:
        return
    src = {r['header']['source_sha256'] for _, r in recs}
    if len(src) > 1:
        raise SystemExit(f'levels come from different source revisions: {src}')
    for kind in KIND.values():
        exe = {r['header']['exe_sha256'] for _, r in recs if r['header']['kind'] == kind}
        if len(exe) > 1:
            raise SystemExit(f'{kind} levels come from different executables: {exe}')
    for L in (5, 6):
        g = {r['header']['graphs_sha256'] for _, r in recs if int(r['header']['L']) == L}
        if len(g) > 1:
            raise SystemExit(f'L{L} levels come from different graph files: {g}')


def vadd(a, b):
    with mp.workdps(50):
        return [mp.nstr(mp.mpf(x) + mp.mpf(y), 35) for x, y in zip(a, b)]


def c6(K, Hvec, cut):
    return K - mp.mpf(2) / 729 * mp.mpf(Hvec[6 * CUTS.index(cut) + 5])


def main():
    lvdir, manp, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    man_raw = Path(manp).read_bytes(); MANIFEST.update(json.loads(man_raw)); man_sha = hashlib.sha256(man_raw).hexdigest()
    S = {'L6 light dbl': load(lvdir, 6, 'H', 'light', 'dbl'), 'L6 hard ld': load(lvdir, 6, 'H', 'hard', 'ld'),
         'L5 H ld': load(lvdir, 5, 'H', 'all', 'ld'), 'L5 J ld': load(lvdir, 5, 'J', 'all', 'ld'),
         'L5 H ld pert1': load(lvdir, 5, 'H', 'all', 'ld', 1), 'L5 J ld pert1': load(lvdir, 5, 'J', 'all', 'ld', 1),
         'L5 H dbl': load(lvdir, 5, 'H', 'all', 'dbl'), 'L5 J dbl': load(lvdir, 5, 'J', 'all', 'dbl'),
         'L6 hard dbl': load(lvdir, 6, 'H', 'hard', 'dbl')}
    check_provenance(S)
    for a, b in (('L5 H ld', 'L5 J ld'), ('L5 H ld pert1', 'L5 J ld pert1'), ('L5 H dbl', 'L5 J dbl')):
        if set(S[a]) != set(S[b]):
            raise SystemExit(f'{a} / {b}: H and J degrees differ: {sorted(S[a])} vs {sorted(S[b])}')
    J16ref = json.loads((REF / 'full_J_L5_N16_0_10000.json').read_text(), parse_float=str)['values']
    cfgs = {'retained_poles_J16ref': config(J5ref=J16ref)}
    for M in S['L5 H ld']:
        cfgs[f'L5_M{M}'] = config(S['L5 H ld'][M]['totals'], S['L5 J ld'][M]['totals'])
    for M in S['L5 H ld pert1']:
        cfgs[f'L5pert_M{M}'] = config(S['L5 H ld pert1'][M]['totals'], S['L5 J ld pert1'][M]['totals'])
    for M in S['L5 H dbl']:
        cfgs[f'L5dbl_M{M}'] = config(S['L5 H dbl'][M]['totals'], S['L5 J dbl'][M]['totals'])
    light, hard = S['L6 light dbl'], S['L6 hard ld']
    Ns = sorted(set(light) & set(hard)); incomplete = sorted(set(light) ^ set(hard))
    out = {'configs': {}, 'levels': {}, 'incomplete_degrees': incomplete,
           'level_identities': {r['_file']: r['_sha256'] for v in S.values() for r in v.values()}, 'weights_manifest_sha256': man_sha,
           'diagnostics': {'hard_dbl_minus_ld_C6': {}}}
    for name, cf in cfgs.items():
        out['configs'][name] = {cut: {'R6': mp.nstr(v['R6'], 30), 'J5': mp.nstr(v['J5'], 30), 'K': mp.nstr(v['K'], 30),
                                      'predicted_poles': {str(k): mp.nstr(x, 30) for k, x in sorted(v['poles'].items())}} for cut, v in cf.items()}
    for N in Ns:
        H = vadd(light[N]['totals'], hard[N]['totals'])
        row = {'H6_vector': H, 'light': light[N]['totals'], 'hard': hard[N]['totals'], 'C6': {}, 'pole_errors': {}}
        for name, cf in cfgs.items():
            row['C6'][name] = {cut: mp.nstr(c6(cf[cut]['K'], H, cut), 25) for cut in CUTS}
            row['pole_errors'][name] = {cut: {str(k): mp.nstr(mp.mpf(H[6 * CUTS.index(cut) + (k + 6)]) - x, 12) for k, x in sorted(cf[cut]['poles'].items())} for cut in CUTS}
        out['levels'][str(N)] = row
    for N, rec in S['L6 hard dbl'].items():
        if N in hard:
            out['diagnostics']['hard_dbl_minus_ld_C6'][str(N)] = {cut: mp.nstr(-mp.mpf(2) / 729 * (mp.mpf(rec['totals'][6 * i + 5]) - mp.mpf(hard[N]['totals'][6 * i + 5])), 6) for i, cut in enumerate(CUTS)}
    tmp = Path(outp).with_name(f'.{Path(outp).name}.tmp{os.getpid()}'); tmp.write_text(json.dumps(out, indent=1)); os.replace(tmp, outp)
    prod = [k for k in cfgs if k.startswith('L5_M')]
    best = prod[-1] if prod else 'retained_poles_J16ref'
    for N, row in out['levels'].items():
        print(N, best, row['C6'][best])
    if incomplete:
        print('incomplete degrees (one stratum missing):', incomplete)


if __name__ == '__main__':
    main()
