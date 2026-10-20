#!/usr/bin/env python3
"""Prepare the v2 regression (runs/regress_v2/, run by slurm/regress_symmetry.sbatch on ONE amdq node).

  direct_v1/, direct_v2/  identical cfgs run with the phase-1 binary (legacy/lri_engine_phase1.cpp) and the v2
                          binary, built in the same job with the same compiler: bit-for-bit identity of every
                          phase-1 output field (incl. a 315-sector Q8 chunk, whose OpenMP tasks changed from
                          whole sectors to longest-first (sector, shift) pairs)
  replay5/                the phase-1 pilot5 cfgs (seed 1234567) except the four most expensive groups (Q8, A7_v,
                          Q6_d, A7): v2 outputs vs the stored phase-1 outputs, now with replicates
  strict/                 a subset of replay5 with strict numerical tolerances (same lattice and shifts):
                          numerical systematic -> error-floor calibration
  new/                    a complete 46-group campaign with hashed seeds (tier regress-v2), pilot5 sizes except
                          Q8 N=1009, A7_v 4001, A7 4001, Q6_d 16001, A5_vd 64007: end-to-end through the framework
  replay4/                the phase-1 pilot4 benchmark (sector samples, N = 16001 / 64007): bitwise vs pilot4 and the
                          replicate-based reference errors for py/plan_production.py
usage: python3 tests/regress_prepare.py   (local, seconds)
"""
import json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'py'))
from lri_moments import korobov, atomic_write_json, atomic_write_text

OUT = os.path.join(ROOT, 'runs', 'regress_v2')
P5 = os.path.join(ROOT, 'runs', 'pilot5')
P4 = os.path.join(ROOT, 'runs', 'pilot4')
EXPENSIVE = ('Q8_base_', 'A7_v_', 'Q6_d_', 'A7_base_')
STRICT = ['errTarget 1e-16', 'tailTol 1e-16', 'maxJet 2000000', 'tailMax 0.05']


def cfg_text(path, N=None, sectors=None, extra=(), out=None):
    lines = open(path).read().splitlines()
    n = int(next(l.split()[1] for l in lines if l.startswith('n ')))
    geom = next(l.split()[1] for l in lines if l.startswith('geom '))
    d = (n + 1 if geom == 'full' else n - 1) - 1
    res = []
    for l in lines:
        if l.startswith('out '):
            continue
        if N is not None and l.startswith('N '):
            l = f'N {N}'
        if N is not None and l.startswith('korobov '):
            l = f'korobov {korobov(N, d)}'
        if sectors is not None and l.startswith('sectors '):
            l = f'sectors {sectors[0]} {sectors[1]}'
        res.append(l)
    res += list(extra)
    res.append(f'out {out}')
    return '\n'.join(res) + '\n'


def cpu_of(path):
    try:
        return json.load(open(path + '.json'))['cpu_seconds']
    except Exception:
        return 0.0


def write_dir(name, items, manifest=None):
    """items: [(cfgname, text, est_cost)]"""
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    for c, txt, _ in items:
        atomic_write_text(os.path.join(d, c), txt)
    items = sorted(items, key=lambda x: -x[2])
    atomic_write_text(os.path.join(d, 'cfglist.txt'), ''.join(c + '\n' for c, _, _ in items))
    if manifest is not None:
        atomic_write_json(os.path.join(d, 'manifest.json'), manifest, indent=1)
    print(f'{name}: {len(items)} cfgs, est. {sum(x[2] for x in items) / 3600:.1f} core-h (phase-1 cpu)')


def main():
    if os.path.exists(OUT) and any(f.endswith('.cfg.json') for _, _, fs in os.walk(OUT) for f in fs):
        sys.exit(f'{OUT} already holds outputs; not re-preparing')
    os.makedirs(OUT, exist_ok=True)
    # ---- direct v1 vs v2
    direct = [('D_Q8_s0-315_N1009.cfg', 'Q8_base_k0_c000.cfg', 1009, (0, 315), 10611 / 4),
              ('D_Q6_E_c000.cfg', 'Q6_E_k0_c000.cfg', None, None, 1375),
              ('D_A7_v_s180-240_N1009.cfg', 'A7_v_k0_c003.cfg', 1009, (180, 240), 17508 / 16),
              ('D_A3_vdE.cfg', 'A3_vdE_k0_c000.cfg', None, None, 626),
              ('D_A5_vd_N16001.cfg', 'A5_vd_k0_c000.cfg', 16001, None, 11048 / 16),
              ('D_Q4_dE.cfg', 'Q4_dE_k0_c000.cfg', None, None, 1532)]
    for tag in ('direct_v1', 'direct_v2'):
        write_dir(tag, [(c, cfg_text(os.path.join(P5, src), N, sec, out=c + '.json'), cost)
                        for c, src, N, sec, cost in direct])
    # ---- replay5 / strict (pilot5 cfgs, unchanged apart from the out line)
    man5 = json.load(open(os.path.join(P5, 'manifest.json')))
    keep = [m for m in man5 if not any(c.startswith(EXPENSIVE) for c in m['cfgs'])]
    items = [(c, cfg_text(os.path.join(P5, c), out=c + '.json'), cpu_of(os.path.join(P5, c)))
             for m in keep for c in m['cfgs']]
    write_dir('replay5', items, keep)
    strict_cfgs = ['A3_base_k0_c000.cfg', 'A3_v_k0_c000.cfg', 'A3_vv_k0_c000.cfg', 'A3_d_k0_c000.cfg',
                   'A3_dd_k0_c000.cfg', 'A3_vd_k0_c000.cfg', 'Z4_base_k0_c000.cfg', 'Q4_base_k0_c000.cfg',
                   'Q4_vd_k0_c000.cfg', 'A3_E_k0_c000.cfg', 'A5_base_k0_c000.cfg']
    mst = [dict(m, cfgs=[c for c in m['cfgs'] if c in strict_cfgs]) for m in man5
           if any(c in strict_cfgs for c in m['cfgs'])]
    write_dir('strict', [(c, cfg_text(os.path.join(P5, c), extra=STRICT, out=c + '.json'),
                          10 * cpu_of(os.path.join(P5, c))) for c in strict_cfgs], mst)
    # ---- replay4 (all pilot4 cfgs)
    man4 = json.load(open(os.path.join(P4, 'manifest.json')))
    write_dir('replay4', [(c, cfg_text(os.path.join(P4, c), out=c + '.json'), cpu_of(os.path.join(P4, c)))
                          for m in man4 for c in m['cfgs']], man4)
    # ---- new campaign (hashed seeds)
    spec = os.path.join(ROOT, 'specs', 'regress_v2.json')
    subprocess.run([sys.executable, os.path.join(ROOT, 'py', 'make_spec.py'), '--tier', 'regress-v2', '--out', spec,
                    '--shifts', '8', '--from-spec', os.path.join(ROOT, 'specs', 'pilot5_e2e.json'),
                    '--set', 'Q8_base:N=1009,chunks=2', '--set', 'A7_v:N=4001,chunks=1',
                    '--set', 'A7_base:N=4001,chunks=1', '--set', 'Q6_d:N=16001,chunks=1',
                    '--set', 'A5_vd:N=64007,chunks=1', '--set', 'Q6_E:chunks=2', '--set', 'A5_vE:chunks=1',
                    '--set', 'A5_E:chunks=1'], check=True)
    subprocess.run([sys.executable, os.path.join(ROOT, 'py', 'campaign.py'), 'plan', spec, os.path.join(OUT, 'new')],
                   check=True)


if __name__ == '__main__':
    main()
