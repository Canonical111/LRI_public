"""Rounding estimate rho(N) in C6 units (PLAN.md rev 3, 4.5).

Usage: python rounding.py LEVELDIR MANIFEST OUT.json   (MANIFEST = data/weights_manifest.json)

Per production degree N (canonical names from tools/merge.py):
  light: L6_H_light_N{N}.dbl.json  vs  L6_H_light_N{N}.dbl.pert1.mod10.json
  hard:  L6_H_hard_N{N}.ld.json    vs  L6_H_hard_N{N}.ld.pert1.mod10.json
  sigma_S = max(10 |sum_S e_s|, sqrt(10 sum_S e_s^2)), e_s = -(2/729)(H6_s(pert) - H6_s(prod)), max over cutoffs.
Calibration (N = 6, 8, 10; all sectors, hard stratum):
  true  = |sum(hard_ld - hard_dbl)|, proxy = |sum(hard_dbl.pert1 - hard_dbl)|   (C6 units, max over cutoffs)
  ratio = true/proxy; 0/0 counts as 0; true > 0 with proxy = 0 makes the calibration invalid.
  cal = max(1, max_N ratio), required finite.
rho(N) = cal (rho_light + rho_hard) + 1e-12.
Every pair is checked: same L, N, mode, stratum, graphs, source; for same-precision pairs also the same executable,
weights and compensation; replicates have perturb = 1 exactly and mod = 10 (subset mod10); calibration replicates
perturb = 1, mod = 1. All weights hashes must match the manifest. The SHA256 of every level file used is recorded,
so that tools/analyze.py can verify that rounding and assembly used the same production records.
"""
import sys, os, json, hashlib
from pathlib import Path
import mpmath as mp
sys.path.insert(0, str(Path(__file__).resolve().parent))
from levelio import validate_level, LevelError  # noqa: E402

mp.mp.dps = 40
IDX = {'maxgap': 5, 'span': 11}
FLOOR = mp.mpf('1e-12')
KIND = {'double8': 'bin_sha256', 'reference-longdouble': 'dd_sha256'}


class Bad(Exception):
    pass


def load(d, name, man, used):
    p = d / name
    if not p.exists():
        return None
    try:
        rec, sha = validate_level(p, with_sha=True)
    except LevelError as e:
        raise Bad(str(e))
    h = rec['header']
    m = man.get(f"L{h['L']}_N{h['N']}")
    if not m or m[KIND[h['kind']]] != h['weights_sha256']:
        raise Bad(f'{name}: weights hash does not match the manifest')
    used[name] = sha
    return rec


def check_pair(prod, other, what, subset, seed, mod, same_precision=True):
    hp, ho = prod['header'], other['header']
    keys = ('L', 'N', 'mode', 'stratum', 'graphs_sha256', 'source_sha256')
    if same_precision:
        keys += ('kind', 'exe_sha256', 'weights_sha256', 'comp')
    for k in keys:
        if hp[k] != ho[k]:
            raise Bad(f'{what}: header field {k} differs ({hp[k]} vs {ho[k]})')
    if int(hp['perturb']) != 0 or int(hp['mod']) != 1 or prod['subset'] != 'all':
        raise Bad(f'{what}: reference record must be unperturbed and complete')
    if int(ho['perturb']) != seed or int(ho['mod']) != mod or other['subset'] != subset:
        raise Bad(f'{what}: expected perturb={seed}, mod={mod}, subset={subset}; got {ho["perturb"]}, {ho["mod"]}, {other["subset"]}')


def sigma_subset(prod, pert):
    worst = mp.mpf(0)
    for cut, i in IDX.items():
        e = [-mp.mpf(2) / 729 * (mp.mpf(pert['per_sector'][s][i]) - mp.mpf(prod['per_sector'][s][i])) for s in pert['per_sector']]
        worst = max(worst, 10 * abs(mp.fsum(e)), mp.sqrt(10 * mp.fsum(x * x for x in e)))
    return worst


def total_diff(a, b):
    return max(abs(-mp.mpf(2) / 729 * (mp.mpf(a['totals'][i]) - mp.mpf(b['totals'][i]))) for i in IDX.values())


def main():
    d, manp, outp = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    man_raw = manp.read_bytes(); man = json.loads(man_raw); used = {}
    res = {'calibration': {}, 'levels': {}, 'weights_manifest_sha256': hashlib.sha256(man_raw).hexdigest()}
    try:
        ratios = []; valid = True
        for N in (6, 8, 10):
            ld, dbl, dblp = (load(d, f'L6_H_hard_N{N}.{s}.json', man, used) for s in ('ld', 'dbl', 'dbl.pert1'))
            if not (ld and dbl and dblp):
                res['calibration'][str(N)] = 'missing'; valid = False
                continue
            check_pair(dbl, ld, f'hard N{N} ld vs dbl', 'all', 0, 1, same_precision=False)
            check_pair(dbl, dblp, f'hard N{N} dbl pert', 'all', 1, 1)
            true, proxy = total_diff(ld, dbl), total_diff(dblp, dbl)
            if proxy == 0:
                ratio = mp.mpf(0) if true == 0 else None
            else:
                ratio = true / proxy
            if ratio is None or not mp.isfinite(ratio):
                valid = False; res['calibration'][str(N)] = {'true_double_error': mp.nstr(true, 6), 'proxy': '0', 'ratio': 'invalid (positive error, zero proxy)'}
                continue
            ratios.append(ratio)
            res['calibration'][str(N)] = {'true_double_error': mp.nstr(true, 6), 'proxy': mp.nstr(proxy, 6), 'ratio': mp.nstr(ratio, 4)}
        cal = max([mp.mpf(1)] + ratios)
        res['cal'] = mp.nstr(cal, 6); res['calibration_complete'] = valid and mp.isfinite(cal)
        Ns = sorted({int(f.name.split('_N')[1].split('.')[0]) for f in d.glob('L6_H_light_N*.dbl.json')})
        for N in Ns:
            row = {}
            for stratum, kind in (('light', 'dbl'), ('hard', 'ld')):
                prod = load(d, f'L6_H_{stratum}_N{N}.{kind}.json', man, used)
                pert = load(d, f'L6_H_{stratum}_N{N}.{kind}.pert1.mod10.json', man, used)
                if prod and pert:
                    check_pair(prod, pert, f'{stratum} N{N}', 'mod10', 1, 10)
                    row[f'rho_{stratum}'] = mp.nstr(sigma_subset(prod, pert), 8)
            if 'rho_light' in row and 'rho_hard' in row and res['calibration_complete']:
                rho = cal * (mp.mpf(row['rho_light']) + mp.mpf(row['rho_hard'])) + FLOOR
                if not (mp.isfinite(rho) and rho >= 0):
                    raise Bad(f'N{N}: non-finite rho')
                row['rho'] = mp.nstr(rho, 8)
            res['levels'][str(N)] = row
    except Bad as e:
        raise SystemExit(f'ROUNDING REFUSED: {e}')
    res['level_identities'] = used
    tmp = Path(outp).with_name(f'.{Path(outp).name}.tmp{os.getpid()}'); tmp.write_text(json.dumps(res, indent=1)); os.replace(tmp, outp)
    print(json.dumps({k: v for k, v in res.items() if k != 'level_identities'}, indent=1))


if __name__ == '__main__':
    main()
