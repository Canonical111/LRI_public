#!/usr/bin/env python3
"""Campaign specs for the C8 extension (py/campaign.py plan <spec> <rundir>).

  make_spec_C8.py val   --out specs/val_C8.json   [--tier c8val]
      validation run: every (new atom, eps power) that the C8 pole-cancellation targets
      (../spec/out/C8/poles_C8.json, raw windows of all 74 normalized jets) or the C8 production jobs
      (specs/production_C8.json) need and that no earlier engine run (prod_6digit results_final, poles1, kplus1,
      conv1) has with all log powers; ALL log powers (jmin 0), ALL sectors, modest N by dimension.  Exceptions
      (too expensive for a check run with all sectors) are sampled: A9 eps^0.
  make_spec_C8.py conv  --out specs/conv_C8.json  [--tier c8conv]
      cost/convergence pilot of every C8 production job of dimension >= 4: the production configuration
      (eps power, jmin) at two lattice sizes on a sector sample (stride ~ sectors/60; all sectors when <= 60).
  make_spec_C8.py kplus1 --out specs/kplus1_C8.json [--tier c8kplus1]
      eps^1 (all logs) of the new 1-4 dimensional atoms: complete K = 1 series for the direct comparison.
  make_spec_C8.py tier  --plan results/plan_C8.json --tier-name A|B|C --out specs/production_C8_tier<X>.json
      production spec of one tier from the planner output (py/plan_C8.py).
  make_spec_C8.py probe --plan results/plan_C8_alt_TB0.01_T3.json --out specs/probe_C8_BC.json [--tier c8probeBC]
      [--groups Q8_v,A7_d,...]
      budget-guard probe (tiers B/C, 2026-10-04): every heavy 5-7D production job at its PLANNED N on exactly the
      sector sample of the conv pilot (same 'sectorstride S S/2' as runs/c8conv, whose N = 1009 and 4001 entries
      cover the same sectors), production jmin and coeffs.  Gives sigma vs N on identical sectors (rate in the
      production range) and the amdq cost per point; tests/budget_guard_C8.py replan feeds it to py/plan_C8.py.
  make_spec_C8.py checks --out specs/checks_C8_BC.json [--tier c8chkBC]
      deferred archive-free checks: A9 and Z8 at eps^-1, ALL logs, ALL sectors, N = 1009 (the C9[v0d0] pole check at
      eps^-1, tests/validate_C8.py), as in the val run.

Entries carry 'coeffs' (needed eps^k log^j), so campaign.py collect writes explicit structural zeros and
fails on genuinely missing coefficients.  Seeds are hashed by campaign.py from (tier, entry name, k, chunk):
every tier name gets its own random shifts (campaign.py seedcheck).
"""
import argparse, json, os, re, sys
from math import factorial
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PROD_C8 = os.path.join(ROOT, 'specs', 'production_C8.json')
POLES = os.path.join(ROOT, '..', 'spec', 'out', 'C8', 'poles_C8.json')
EXISTING = ['runs/prod_6digit/results_final.json', 'runs/poles1/results.json', 'runs/kplus1/results.json',
            'runs/conv1/results.json']
# Pilot sizes (revised 2026-10-03 after the first personal-desktop timings: the jets of the high-insertion-degree atoms cost
# 10-100x the old sector-cost estimate per unit; symmetry was down, the pilot runs on 16 personal-desktop cores)
VAL_N = {0: 262139, 1: 262139, 2: 262139, 3: 64007, 4: 16001, 5: 4001, 6: 1009, 7: 1009}
VAL_N_GROUP = {'A7_d': 1009, 'A7_base': 1009, 'A7_v': 1009}           # 7-kink 5D atoms: N=1009 at every power
VAL_N_K0 = {5: 1009, 6: 1009, 7: 1009}         # eps^0, all logs, all sectors of the 5-7D atoms
SAMPLED = {}
# Checks that would cost > ~20 core-h with all sectors are NOT in the validation run (a sector sample cannot be
# used for a pole or log check): A9 eps^0 and eps^-1, Q8_v and Z8 eps^0, A7_E eps^0 (personal-desktop timings 2026-10-03:
# ~1300, ~20, ~120, ~15, ~100 core-h at N = 1009).  Their pole checks (A9, A7_E eps^-1) and log checks come with
# production (the tier runs compute every log power >= jmin) or from a later symmetry run.
# Also left out (no check uses them; their planning references are in the conv pilot): A7_v and Z6_E eps^0; and Z8
# eps^-1, which only enters the C9 check at eps^-1 that needs A9 eps^-1 anyway.
VAL_DEFER = {('A9_base', 0), ('A9_base', -1), ('Q8_v', 0), ('Z8_base', 0), ('A7_E', 0), ('A7_v', 0), ('Z6_E', 0),
             ('Z8_base', -1)}
# (group, k) whose all-sector data come from the conv pilot (4D, all sectors at N = 4001 and 16001), not from val
VAL_SKIP = {('Q6_vd', 0), ('Q6_vv', 0), ('Z6_d', 0), ('Z6_v', 0), ('Q6_base', 1)}
CONV_N = {4: (4001, 16001), 5: (1009, 4001), 6: (1009, 4001), 7: (1009, 4001)}
CONV_STRIDE = {'A9_base': 672, 'A7_E': 336, 'Q8_v': 84, 'Z8_base': 84, 'Q6_vE': 42, 'Z6_E': 42,
               'A7_d': 12, 'A7_base': 12, 'A7_v': 12, 'A5_E': 6, 'A5_dE': 6}


def done_entries(rundir):
    """{(moment, k): manifest entry} of the entries of an earlier plan of `rundir` whose outputs are all complete
    (kept unchanged when the spec is regenerated, so that their cfgs and outputs stay valid)"""
    mf = os.path.join(ROOT, rundir, 'manifest.json')
    out = {}
    if not os.path.exists(mf):
        return out
    for m in json.load(open(mf)):
        ok = True
        for c in m['cfgs']:
            p = os.path.join(ROOT, rundir, c + '.json')
            try:
                ok = ok and json.load(open(p)).get('complete', False)
            except (OSError, ValueError):
                ok = False
        if ok:
            out[(m['moment'], m['job']['k'])] = m
    return out


def spec_atom_to_group(a):
    """spec name (EA3_dd, Q4_vvv, Z8_base) -> engine group (A3_ddE, Q4_vvv, Z8_base)"""
    E = a.startswith('E')
    b = a[1:] if E else a
    base, der = re.match(r'([AZQ]\d+)_(\w+)', b).groups()
    der = ('' if der == 'base' else der) + ('E' if E else '')
    return f'{base}_{der or "base"}'


def group_info(g):
    m = re.match(r'([AZQ])(\d+)_(\w+)', g)
    kind, n, der = m.group(1), int(m.group(2)), m.group(3)
    der = '' if der == 'base' else der
    nv, nd, ne = der.count('v'), der.count('d'), der.count('E')
    geom = 'full' if ne else 'angular'
    M = n + 1 if geom == 'full' else n - 1
    return {'kind': kind, 'n': n, 'nv': nv, 'nd': nd, 'ne': ne, 'geom': geom, 'dim': M - 1,
            'sectors': factorial(M) // 2 if M >= 2 else 1}


def existing_coverage():
    cov = {}
    for src in EXISTING:
        p = os.path.join(ROOT, src)
        if not os.path.exists(p):
            continue
        for g, co in json.load(open(p))['results'].items():
            g = re.sub(r'_N\d+$', '', g)
            for key in co:
                k, j = map(int, key.split(','))
                cov.setdefault(g, {}).setdefault(k, set()).add(j)
    return cov


def val_spec(tier, keep=None):
    done = done_entries(keep) if keep else {}
    prod = json.load(open(PROD_C8))['groups']
    poles = json.load(open(POLES))['raw_needed_for_all_jets']
    want = {}
    for a, ps in poles.items():
        g = spec_atom_to_group(a)
        if group_info(g)['n'] <= 2:
            continue
        for p in ps:
            want.setdefault(g, set()).add(p)
    # below-tight-bound scalars that must vanish (spec raw_requirements_C8.json, safe minus tight): computed so that
    # the vanishing is checked numerically where the engine's pole analysis does not already make them exact zeros
    rq = json.load(open(os.path.join(ROOT, '..', 'spec', 'out', 'C8', 'raw_requirements_C8.json')))
    for sname in rq['safe_minus_tight']['below_tight_bound_must_vanish']:
        a, pk = sname.split(' ', 1)
        g = spec_atom_to_group(a)
        if group_info(g)['n'] > 2:
            want.setdefault(g, set()).add(int(re.match(r'\[eps\^(-?\d+)', pk).group(1)))
    # the framework's structural lowest power of an endpoint Z moment is the safe one (-n/2); EC5_d at eps^-2 then
    # needs Z4_dE[eps^-2], below the tight bound and not a structural zero of the engine's pole analysis
    want.setdefault('Z4_dE', set()).add(-2)
    want.setdefault('Z6_E', set()).add(-3)      # likewise EC7 at eps^-3 needs Z6_E[eps^-3] (tight bound: eps^-2)
    for o in prod:
        for p in o['powers']:
            if o['dim'] >= 5 and int(p) > 0:
                continue          # positive powers of the 5-7 dimensional atoms: production only (no check uses them)
            want.setdefault(o['name'], set()).add(int(p))
    cov = existing_coverage()
    moms = []
    for g in sorted(want, key=lambda x: (group_info(x)['dim'], x)):
        gi = group_info(g)
        for p in sorted(want[g]):
            have = cov.get(g, {}).get(p)
            if have and min(have) == 0:
                continue                          # all logs already computed by an earlier run
            if (g, p) in VAL_SKIP or (g, p) in VAL_DEFER:
                continue
            N = VAL_N_K0.get(gi['dim'], VAL_N[gi['dim']]) if p >= 0 else VAL_N[gi['dim']]
            N = VAL_N_GROUP.get(g, N)
            m = {'name': g, 'kind': gi['kind'], 'n': gi['n'], 'nv': gi['nv'], 'nd': gi['nd'], 'ne': gi['ne'],
                 'powers': [p], 'jmin': {str(p): 0}, 'N': N, 'shifts': 6, 'chunks': 1}
            if (g, p) in SAMPLED:
                st = SAMPLED[(g, p)]
                m['name'] = f'{g}_S{st}'
                m['extra'] = [f'sectorstride {st} {st // 2}']
            for (dn, dk), dm in done.items():          # an entry that already ran keeps its configuration
                if re.sub(r'_S\d+$', '', dn) == g and dk == p:
                    m.update({'name': dn, 'N': dm['N'], 'shifts': dm['shifts']})
                    m.pop('extra', None)
                    if dm.get('extra'):
                        m['extra'] = dm['extra']
            moms.append(m)
    return {'tier': tier, 'defaults': {'transform': 3, 'prec': 'auto'}, 'moments': moms,
            'note': 'C8 validation run (py/make_spec_C8.py val): all log powers, all sectors unless _S<stride>'}


def conv_spec(tier, keep=None):
    done = done_entries(keep) if keep else {}
    prod = json.load(open(PROD_C8))['groups']
    moms = []
    names = set()
    for (dn, dk), dm in sorted(done.items()):       # entries that already ran stay in the campaign unchanged
        j = dm['job']
        g = re.sub(r'(_N\d+)?(_S\d+)?$', '', dn)
        o = next(x for x in prod if x['name'] == g)
        m = {'name': dn, 'kind': o['kind'], 'n': o['n'], 'nv': o['nv'], 'nd': o['nd'], 'ne': o['ne'], 'powers': [dk],
             'jmin': {str(dk): o['jmin'][str(dk)]}, 'coeffs': {str(dk): o['coeffs'][str(dk)]}, 'N': dm['N'],
             'shifts': dm['shifts'], 'chunks': 1}
        if dm.get('extra'):
            m['extra'] = dm['extra']
        moms.append(m)
        names.add((dn, dk))
    for o in prod:
        if o['dim'] < 4:
            continue
        stride = CONV_STRIDE.get(o['name'], max(1, o['sectors'] // 60))
        for p in o['powers']:
            for N in CONV_N[o['dim']]:
                m = {'name': f"{o['name']}_N{N}" + (f'_S{stride}' if stride > 1 else ''), 'kind': o['kind'],
                     'n': o['n'], 'nv': o['nv'], 'nd': o['nd'], 'ne': o['ne'], 'powers': [int(p)],
                     'jmin': {str(p): o['jmin'][str(p)]}, 'coeffs': {str(p): o['coeffs'][str(p)]}, 'N': N,
                     'shifts': 6, 'chunks': 1}
                if stride > 1:
                    m['extra'] = [f'sectorstride {stride} {stride // 2}']
                if (m['name'], int(p)) in names:
                    continue
                moms.append(m)
    return {'tier': tier, 'defaults': {'transform': 3, 'prec': 'auto'}, 'moments': moms,
            'note': 'C8 cost/convergence pilot (py/make_spec_C8.py conv): production jmin, sector samples'}


KPLUS1 = ['A3_ddd', 'A3_vdd', 'A3_ddE', 'Q4_vvv', 'Q4_vvd', 'Q4_vdd', 'Z4_dd', 'Q4_vvE', 'Q4_vdE', 'Z4_dE', 'A5_dd']


def kplus1_spec(tier):
    """eps^1 (all logs, all sectors) of the new 1-4 dimensional atoms, so that their series are complete through
    K = 1 for the direct finite-cutoff comparison (the K = 0 tests of 3-4 kink endpoint atoms are tail-model
    dependent; the C6/C7 analogue is runs/kplus1)"""
    cov = existing_coverage()
    moms = []
    for g in KPLUS1:
        gi = group_info(g)
        have = cov.get(g, {}).get(1)
        if have and min(have) == 0:
            continue
        moms.append({'name': g, 'kind': gi['kind'], 'n': gi['n'], 'nv': gi['nv'], 'nd': gi['nd'], 'ne': gi['ne'],
                     'powers': [1], 'jmin': {'1': 0}, 'N': VAL_N[gi['dim']], 'shifts': 6, 'chunks': 1})
    return {'tier': tier, 'defaults': {'transform': 3, 'prec': 'auto'}, 'moments': moms,
            'note': 'C8 eps^1 check run (py/make_spec_C8.py kplus1) for the direct comparison'}


def tier_spec(planfile, tname, tier):
    plan = json.load(open(planfile))
    moms = []
    for j in plan['jobs']:
        if j['tier'] != tname:
            continue
        gi = group_info(j['group'])
        moms.append({'name': j['group'], 'kind': gi['kind'], 'n': gi['n'], 'nv': gi['nv'], 'nd': gi['nd'],
                     'ne': gi['ne'], 'powers': [j['k']], 'jmin': {str(j['k']): j['jmin']},
                     'coeffs': {str(j['k']): j['coeffs']}, 'N': j['N'], 'shifts': j['shifts'],
                     'chunks': j['chunks']})
    return {'tier': tier, 'defaults': {'transform': 3, 'prec': 'auto'}, 'moments': moms,
            'note': f'C8 production, tier {tname} (py/plan_C8.py -> py/make_spec_C8.py tier); seeds hashed from '
                    f'the tier name {tier!r}'}


# heavy production jobs of tiers B and C (5-7D, > ~50 amdq core-h in the plans) that get a budget-guard probe
PROBE_GROUPS = ['Q8_v', 'A7_d', 'Q6_vE', 'A9_base', 'A7_E', 'Z8_base', 'Z6_E']


def probe_spec(planfile, tier, groups=None):
    plan = json.load(open(planfile))
    groups = groups or PROBE_GROUPS
    prod = {o['name']: o for o in json.load(open(PROD_C8))['groups']}
    moms = []
    for j in plan['jobs']:
        if j['group'] not in groups or j['tier'] not in 'BC':
            continue
        o = prod[j['group']]
        st = CONV_STRIDE.get(j['group'], max(1, o['sectors'] // 60))
        p = str(j['k'])
        m = {'name': f"{j['group']}_N{j['N']}" + (f'_S{st}' if st > 1 else ''), 'kind': o['kind'], 'n': o['n'],
             'nv': o['nv'], 'nd': o['nd'], 'ne': o['ne'], 'powers': [j['k']], 'jmin': {p: o['jmin'][p]},
             'coeffs': {p: o['coeffs'][p]}, 'N': j['N'], 'shifts': 6, 'chunks': 1}
        if st > 1:
            m['extra'] = [f'sectorstride {st} {st // 2}']
        moms.append(m)
    missing = sorted(set(groups) - {re.sub(r'_N\d+(_S\d+)?$', '', m['name']) for m in moms})
    if missing:
        sys.exit(f'probe: groups not in the plan as tier B/C jobs: {missing}')
    return {'tier': tier, 'defaults': {'transform': 3, 'prec': 'auto'}, 'moments': moms,
            'note': f'C8 tiers B/C budget-guard probe (py/make_spec_C8.py probe, plan {os.path.basename(planfile)}): '
                    'planned production N on the conv-pilot sector samples'}


def checks_spec(tier):
    moms = []
    for g, k in (('A9_base', -1), ('Z8_base', -1)):
        gi = group_info(g)
        moms.append({'name': g, 'kind': gi['kind'], 'n': gi['n'], 'nv': gi['nv'], 'nd': gi['nd'], 'ne': gi['ne'],
                     'powers': [k], 'jmin': {str(k): 0}, 'N': 1009, 'shifts': 6, 'chunks': 1})
    return {'tier': tier, 'defaults': {'transform': 3, 'prec': 'auto'}, 'moments': moms,
            'note': 'C8 deferred checks (py/make_spec_C8.py checks): A9, Z8 eps^-1, all logs, all sectors, N = 1009 '
                    '(C9[v0d0] pole check at eps^-1)'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['val', 'conv', 'kplus1', 'tier', 'probe', 'checks'])
    ap.add_argument('--groups', help='probe: comma-separated heavy groups (default: PROBE_GROUPS)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--tier')
    ap.add_argument('--plan')
    ap.add_argument('--tier-name')
    ap.add_argument('--keep-done', help='run directory of an earlier plan: entries with complete outputs are kept')
    a = ap.parse_args()
    if a.mode == 'val':
        spec = val_spec(a.tier or 'c8val', a.keep_done)
    elif a.mode == 'conv':
        spec = conv_spec(a.tier or 'c8conv', a.keep_done)
    elif a.mode == 'kplus1':
        spec = kplus1_spec(a.tier or 'c8kplus1')
    elif a.mode == 'probe':
        spec = probe_spec(a.plan, a.tier or 'c8probeBC', a.groups.split(',') if a.groups else None)
    elif a.mode == 'checks':
        spec = checks_spec(a.tier or 'c8chkBC')
    else:
        spec = tier_spec(a.plan, a.tier_name, a.tier or f'c8tier{a.tier_name}')
    json.dump(spec, open(a.out, 'w'), indent=1)
    print(f"{len(spec['moments'])} entries -> {a.out} (tier {spec['tier']})")
    for m in spec['moments']:
        print(f"  {m['name']:22s} k={m['powers']} jmin={list(m['jmin'].values())} N={m['N']} {m.get('extra', '')}")


if __name__ == '__main__':
    main()
