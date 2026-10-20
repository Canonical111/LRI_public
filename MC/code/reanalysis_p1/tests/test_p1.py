"""Amendment P1 §7 verification: python3 -m pytest LRI_2d3d_reanalysis/tests/

1. Switch off (--sigma-rule fixed) reproduces the scientific content of the current evaluations (§1.2):
   (a) bit-for-bit against the frozen evaluators (rev 5 / rev 1, pinned copies in tests/frozen/) run on the same machine and inputs;
   (b) against the pinned baseline evaluations written on Expanse: every string, label, boolean and integer identical, floats to 1e-9 relative
       (the frozen evaluators themselves differ from the Expanse output by ≤ 4e-11 relative on other machines: BLAS rounding).
2. The profiled σ (series, cross-check σ_D, reblocking) equals the reference implementation LRI_2d3d_reanalysis/reanalyse.py to 1e-12.
3. The calibration is deterministic by seed and independent of the worker count.
4. The P1 rule is applied per point and atomically, and every P1-007 binding failure makes the whole calibration invalid (fabricated,
   correctly bound calibration files; they exercise the evaluator's logic only and are never used for an evaluation).
"""
import copy, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent; RE = HERE.parent; ROOT = RE.parent
sys.path.insert(0, str(RE))
EXPANSE = '/expanse/lustre/scratch/zzheng8/temp_project'
FROZEN = {2: (HERE / 'frozen/evaluate_2d_rev5.py', '0fe221e860a0c4f9ac34d9f6f22688d42c182ad52c4804283a2182f6f0012117'),
          3: (HERE / 'frozen/evaluate_3d_rev1.py', '6bd35d7af8a70576782d353a507b9ba6d188d0687c54e47abfa47c9df0a2cd29')}
CFG = {2: dict(ev=ROOT / 'LRI_2d_MC/evaluate_2d.py', plan=ROOT / 'LRI_2d_MC/FIT_MODEL_2D.md', centers=ROOT / 'LRI_2d_MC/production_centers.csv',
               prod=ROOT / 'LRI_2d_MC/prod', tag='', json='evaluation_2d.json', remap=f'{EXPANSE}/lri2d/prod2d/', extra=[]),
       3: dict(ev=ROOT / 'LRI_3d_MC/evaluate_3d.py', plan=ROOT / 'LRI_3d_MC/FIT_MODEL_3D.md', centers=ROOT / 'LRI_3d_MC/production_centers_3d.csv',
               prod=ROOT / 'LRI_3d_MC/prod', tag='54387089_', json='evaluation_3d.json', remap=f'{EXPANSE}/lri3d/prod3d/', extra=['--snapshot', '54387089'])}
AMENDMENT = RE / 'AMENDMENT_PROFILED_SIGMA.md'
ENV = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
NOTE_UNBOUND = 'P1 not applied: calibration not bound to these inputs'

def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def module(dim):
    spec = importlib.util.spec_from_file_location(f'evaluate_{dim}d_test', CFG[dim]['ev']); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def records(dim, b): return sorted(str(p) for p in CFG[dim]['prod'].glob(f"analysis_{CFG[dim]['tag']}b{b}_s*"))

def cmd(dim, out, evaluator=None, extra=(), plan=None):
    c = CFG[dim]
    return [sys.executable, str(evaluator or c['ev']), '--primary', *records(dim, 2000), '--reblock', *records(dim, 1000), *records(dim, 4000),
            '--plan', str(plan or c['plan']), '--manifest', str(c['prod'] / 'manifest.json'), '--centers', str(c['centers']), '--out', str(out), *c['extra'], *extra]

def run(dim, out, evaluator=None, extra=(), plan=None):
    subprocess.run(cmd(dim, out, evaluator, extra, plan), check=True, capture_output=True, env=ENV)
    return json.loads((Path(out) / CFG[dim]['json']).read_text())

def remap(dim): return ['--index-remap', f"{CFG[dim]['remap']}={CFG[dim]['prod']}/"]

# §3.5 fields (and the rule marker) that the revised evaluators add to a point; '*' matches any key. Nothing else may be new.
NEW_FIELDS = [('sigma_rule',), ('series', '*', 'sigma_inf_profiled'), ('series', '*', 'omega_draws'), ('series', '*', 'profiled_error'),
              ('series', '*', 'sigma_inf_fixed_information'),
              ('quoted', 'sigma_stat_profiled'), ('crosscheck', 'sigma_D_profiled'), ('inputs', 'index_path_read')] + \
             [('reblocking', 'comparisons', '*', k) for k in ('sigma_profiled', 'primary_profiled', 'ratio_profiled', 'note_profiled')]
def is_new(path): return any(len(p) == len(path) and all(a == '*' or a == b for a, b in zip(p, path)) for p in NEW_FIELDS)

def compare(new, old, path=(), rtol=None, skip=()):
    """Differences between a point (or report) of a revised evaluation and the old one: every old field must be present and equal (exactly, or
    for floats within rtol); fields only in the new one must be NEW_FIELDS. skip: paths excluded as provenance."""
    out = []
    if path in skip: return out
    if isinstance(old, dict):
        if not isinstance(new, dict): return [(path, 'type')]
        for k in old:
            if k not in new: out.append((path + (k,), 'missing'))
            else: out += compare(new[k], old[k], path + (k,), rtol, skip)
        out += [(path + (k,), 'unexpected new field') for k in new if k not in old and not is_new(path + (k,))]
    elif isinstance(old, list):
        if not isinstance(new, list) or len(new) != len(old): return [(path, 'list')]
        for i, (a, b) in enumerate(zip(new, old)): out += compare(a, b, path + (i,), rtol, skip)
    elif isinstance(old, float) and rtol is not None and isinstance(new, float):
        if not abs(new - old) <= 1e-12 + rtol * abs(old): out.append((path, f'{new!r} != {old!r}'))
    elif type(new) != type(old) or new != old: out.append((path, f'{new!r} != {old!r}'))
    return out

@pytest.fixture(scope='session')
def evals(tmp_path_factory):
    """Evaluations used by several tests, each computed once: frozen and revised (fixed) without the index check; revised fixed with the remap."""
    T = tmp_path_factory.mktemp('evals'); E = {}
    for dim in (2, 3):
        assert sha256(FROZEN[dim][0]) == FROZEN[dim][1], 'frozen evaluator copy is not the baseline evaluator'
        E[('frozen', dim)] = run(dim, T / f'frozen{dim}', FROZEN[dim][0], ['--no-index-check'])
        E[('noidx', dim)] = run(dim, T / f'noidx{dim}', None, ['--no-index-check'])
        E[('fixed', dim)] = run(dim, T / f'fixed{dim}', None, remap(dim))
    return E

def baseline(dim):
    m = module(dim); path, sha = m.BASELINE_EVALUATIONS[dim]; assert sha256(ROOT / path) == sha
    return json.loads((ROOT / path).read_text())

# ---------------------------------------------------------------- 1. switch-off reproduction
@pytest.mark.parametrize('dim', [2, 3])
def test_switch_off_bit_for_bit_vs_frozen(evals, dim):
    new, old = evals[('noidx', dim)], evals[('frozen', dim)]
    assert set(new['points']) == set(old['points']) and len(old['points']) == 8
    d = [(s,) + x for s in old['points'] for x in compare(new['points'][s], old['points'][s])]
    assert not d, d[:10]
    top = {k: v for k, v in old.items() if k not in ('points', 'evaluator_sha256', 'time')}
    d = compare({k: new[k] for k in top}, top); assert not d, d
    assert new['sigma_rule'] == 'fixed' and new['deviations'] == [] and all(P['sigma_rule']['applied'] == 'fixed' for P in new['points'].values())

@pytest.mark.parametrize('dim', [2, 3])
def test_switch_off_reproduces_pinned_baseline(evals, dim):
    new, old = evals[('fixed', dim)], baseline(dim)
    assert set(new['points']) == set(old['points'])
    for s, P in old['points'].items():
        Q = new['points'][s]
        assert Q['decision'] == P['decision'] and Q['eligible'] == P['eligible'] and Q['production'] is True, s
        d = compare(Q, P, rtol=1e-9, skip={('inputs', 'results')}); assert not d, (s, d[:10])
    for k in ('plan_sha256', 'manifest_sha256', 'centers_sha256', 'campaign_id', 'design', 'settings', 'index_check', 'extensions'):
        assert compare(new[k], old[k]) == [], k
    assert new['deviations'] and 'index-remap' in new['deviations'][0]

def test_profiled_information_for_every_fitted_series(evals):
    """P1-013: every series with a central fit records the profiled σ and the per-draw ω′ distribution; one stopped before gate (iii) also
    records the fixed-ω′ σ as information (the frozen sigma_inf stays absent there)."""
    n = 0
    for dim in (2, 3):
        for s, P in evals[('fixed', dim)]['points'].items():
            for q, x in P['series'].items():
                if 'omega' not in x: continue
                assert finite_(x['sigma_inf_profiled']) and 0 <= x['omega_draws']['fraction_on_edge'] <= 1, (dim, s, q)
                if 'sigma_inf' in x: assert 'sigma_inf_fixed_information' not in x
                else: assert finite_(x['sigma_inf_fixed_information']) and x['reason'].startswith(('chi2/dof', "omega' interval")), (dim, s, q); n += 1
    assert n >= 20, n

def finite_(x): return isinstance(x, float) and np.isfinite(x)

def test_index_check_still_enforced(tmp_path):
    R = run(2, tmp_path / 'e', None, ['--index-remap', f"{CFG[2]['remap']}={tmp_path}/nowhere/"])
    assert all(P['decision'].startswith('NON-PRODUCTION') and 'not accessible' in P['decision'] for P in R['points'].values())

# ---------------------------------------------------------------- 2. profiled σ vs the reference implementation
def test_profiled_sigma_matches_reference(evals):
    import reanalyse as R
    n = 0
    for dim in (2, 3):
        m = module(dim); L = np.array(m.PAIRS, float); ev = evals[('fixed', dim)]['points']
        for d in records(dim, 2000):
            res, draws, byL, order = m.load_point(Path(d)); S, _, inputs = m.fit_series(draws, byL, order); P = ev[m.skey(res['s'])]
            per = {}
            for q, (y, D, nser, _) in inputs.items():
                ref, fixed, prof = R.series_fit(np.asarray(y), D, L, nser); per[q] = prof
                if S[q].get('sigma_inf_profiled') is None: continue
                assert abs(S[q]['sigma_inf_profiled'] - ref['sigma_prof']) <= 1e-12, (dim, res['s'], q)
                assert abs(P['series'][q]['sigma_inf_profiled'] - ref['sigma_prof']) <= 1e-12
                assert abs(S[q].get('sigma_inf', S[q].get('sigma_inf_fixed_information')) - ref['sigma_fixed']) <= 1e-12   # loop GLS vs projector at ω′*
                assert S[q]['omega_draws']['median'] == ref['omega_draw_median'] and S[q]['omega_draws']['fraction_on_edge'] == ref['frac_draw_omega_on_edge']
                n += 1
            if 'sigma_D_profiled' in P['crosscheck']:
                assert abs(P['crosscheck']['sigma_D_profiled'] - float((per['U4'] - per['Y']).std(ddof=1))) <= 1e-12; n += 1
            if P['quoted']:
                ref_q = P['quoted']['reference_series']
                for b in (1000, 4000):
                    r2, d2, byL2, order2 = m.load_point(Path(d.replace('_b2000_', f'_b{b}_').replace('analysis_b2000', f'analysis_b{b}')))
                    _, _, in2 = m.fit_series(d2, byL2, order2); y2, D2, nser2, _ = in2[ref_q]
                    assert abs(P['reblocking']['comparisons'][str(b)]['sigma_profiled'] - R.series_fit(np.asarray(y2), D2, L, nser2)[0]['sigma_prof']) <= 1e-12; n += 1
    assert n >= 60, n; print(f"{n} profiled quantities compared")

# ---------------------------------------------------------------- 3. calibration determinism
def test_calibration_deterministic(tmp_path):
    import calibrate_p1 as K
    only = {(3, '1.6'), (2, '1.2')}
    a = K.calibrate(tmp_path / 'a', sets=6, draws=40, only=only, workers=1, chunk=4, log=lambda m: None)
    b = K.calibrate(tmp_path / 'b', sets=6, draws=40, only=only, workers=2, chunk=3, log=lambda m: None)
    c = K.calibrate(tmp_path / 'c', sets=6, draws=40, only=only, entropy=K.ENTROPY + 1, workers=1, log=lambda m: None)
    assert a['strata'] == b['strata'] and a['information'] == b['information']
    A, B, C = (np.load(tmp_path / x / 'sets.npz') for x in 'abc')
    assert set(A.files) == set(B.files) and A.files and all(np.array_equal(A[k], B[k], equal_nan=True) for k in A.files)
    assert any(not np.array_equal(A[k], C[k], equal_nan=True) for k in A.files if k.endswith('_Delta'))
    m = module(3); d = next(x for x in records(3, 2000) if x.endswith('_s1.6')); res, dr, byL, order = m.load_point(Path(d))
    S, _, inputs = m.fit_series(dr, byL, order)
    assert a['header']['dims']['3']['points']['1.6']['truth'] == json.loads(json.dumps(m.truths(S, inputs)))
    assert not os.access(tmp_path / 'a' / 'CALIBRATION.json', os.W_OK)

# ---------------------------------------------------------------- 4. P1 rule: atomic per point, binding
@pytest.fixture(scope='session')
def fabricated(tmp_path_factory):
    """A correctly bound calibration header (from a tiny real calibration run) with fabricated strata that all PASS and satisfy A3."""
    import calibrate_p1 as K
    T = tmp_path_factory.mktemp('fab'); cal = K.calibrate(T / 'tiny', sets=2, draws=20, workers=1, log=lambda m: None)
    cal = json.loads(json.dumps(cal))
    for Hd in cal['header']['dims'].values(): Hd['settings'].update(n_sets=2000, n_draws=500)
    for pts in cal['strata'].values():
        for st in pts.values():
            for q in st:
                st[q] = (dict(n_sets=2000, n_both_eligible=2000, n_fail_profiled=100, n_fail_fixed=400) if q == 'crosscheck' else
                         dict(n_sets=2000, n_eligible=2000, n_cov1_profiled=1400, n_cov2_profiled=1900, n_cov1_fixed=800, n_cov2_fixed=1200))
    return finish(cal)

def finish(cal):
    m = module(2)
    for pts in cal['strata'].values():
        for st in pts.values():
            for q, x in st.items(): x['status'] = m.stratum_status('A2' if q == 'crosscheck' else 'A1', x)
    cal['A3'] = m.a3_pooled(cal['strata']); return cal

def run_p1(dim, tmp, cal, amendment=AMENDMENT, plan=None):
    f = tmp / 'CALIBRATION.json'; f.write_text(json.dumps(cal))
    return run(dim, tmp / 'e', None, remap(dim) + ['--sigma-rule', 'profiled', '--calibration', str(f), '--amendment', str(amendment)], plan)

def rule_independent_equal(P, Q):
    """Everything not governed by the σ rule is identical between a profiled-mode point P and its fixed-mode twin Q."""
    for k in Q:
        if k in ('sigma_rule', 'quoted', 'crosscheck', 'reblocking', 'decision'): continue
        assert compare(P[k], Q[k]) == [], k
    if Q['quoted']:
        assert {k: v for k, v in P['quoted'].items() if k not in ('sigma_stat', 'sigma_stat_fixed', 'sigma_stat_profiled', 'sigma_rule')} == \
               {k: v for k, v in Q['quoted'].items() if k not in ('sigma_stat', 'sigma_stat_profiled')}

EXPECTED_S5 = {('3', '1.6'): 'ACCEPTED [sigma_stat above target]'}   # §5: the only changed label

@pytest.mark.parametrize('dim', [2, 3])
def test_profiled_all_pass_is_atomic_and_matches_s5(evals, fabricated, tmp_path, dim):
    R = run_p1(dim, tmp_path, fabricated); F = evals[('fixed', dim)]['points']; A = R['amendment_P1']
    assert A['calibration_valid'] and A['adopted'] and all(c['passed'] for c in A['binding_checks']) and A['amendment_sha256'] == AMENDMENT_SHA
    for s, P in R['points'].items():
        Q = F[s]; rule = P['sigma_rule']; rule_independent_equal(P, Q)
        if not P['eligible']:
            assert rule['applied'] == 'fixed' and 'no eligible series' in rule['note']
            assert compare(P, Q, skip={('sigma_rule',)}) == []; continue
        assert rule['applied'] == 'profiled' and rule['p1_calibrated'] and rule['fixed_rule_decision'] == Q['decision'] and rule['A4']['satisfied']
        ref = P['quoted']['reference_series']
        assert P['quoted']['sigma_stat'] == P['series'][ref]['sigma_inf_profiled'] and P['quoted']['sigma_stat_fixed'] == Q['quoted']['sigma_stat']
        if 'U4' in P['eligible'] and 'Y' in P['eligible']:
            assert P['crosscheck']['sigma_D'] == Q['crosscheck']['sigma_D_profiled'] and P['crosscheck']['sigma_D_fixed'] == Q['crosscheck']['sigma_D']
        for b, c in P['reblocking']['comparisons'].items():
            assert c['ratio'] == Q['reblocking']['comparisons'][b]['ratio_profiled'] and c['ratio_fixed'] == Q['reblocking']['comparisons'][b]['ratio']
        assert P['decision'] == EXPECTED_S5.get((str(dim), s), Q['decision']), (s, P['decision'])
    if dim == 3:
        q = R['points']['1.6']['quoted']; x = R['points']['1.6']['crosscheck']
        assert (round(q['Delta_epsilon'], 5), round(q['sigma_stat'], 5), round(q['sigma_sys'], 5)) == (1.47314, 0.00118, 0.0023)
        assert round(x['difference'] / x['sigma_D'], 2) == -0.45
        import reanalyse as RA   # §6 R4 reported with the changed label, equal to the reference cutoff() at each series' own ω′*
        m = module(3); d = next(r for r in records(3, 2000) if r.endswith('_s1.6')); res, dr, byL, order = m.load_point(Path(d)); _, _, inputs = m.fit_series(dr, byL, order)
        R4 = R['points']['1.6']['sigma_rule']['R4_drop_smallest']; assert set(R4) == {'U4', 'Y'}
        for qq in ('U4', 'Y'):
            ref = RA.cutoff(np.asarray(inputs[qq][0]), inputs[qq][1], np.array(m.PAIRS, float), R['points']['1.6']['series'][qq]['omega'])['drop_smallest']
            assert abs(R4[qq]['Delta_inf'] - ref['Delta_inf']) <= 1e-12 and abs(R4[qq]['sigma'] - ref['sigma']) <= 1e-12 and abs(R4[qq]['chi2'] - ref['chi2']) <= 1e-9
        assert (round(R4['U4']['Delta_inf'], 4), round(R4['Y']['Delta_inf'], 4)) == (1.4724, 1.4746)
        assert all('R4_drop_smallest' not in R['points'][s]['sigma_rule'] for s in R['points'] if s != '1.6')
        z = {s: round(R['points'][s]['crosscheck']['difference'] / R['points'][s]['crosscheck']['sigma_D'], 2) for s in ('1.55', '1.7', '1.85')}
        assert (z['1.55'], z['1.7'], round(z['1.85'], 1)) == (2.49, -4.9, -28.1), z
    else:
        assert [round(R['points'][s]['quoted']['sigma_stat'], 4) for s in ('1.05', '1.1', '1.2')] == [0.0177, 0.0101, 0.0018]

AMENDMENT_SHA = '2a18c0ae3ae7b3f4fa5db8b83df0fb5a1d57eecd79d1603bdf04bcc7207574d0'

def _hdr(c): return c['header']['dims']['3']
TAMPER = {
    'amendment hash': lambda c: c['header'].update(amendment_sha256='0' * 64),
    'record hash': lambda c: _hdr(c)['points']['1.9'].update(results_sha256='0' * 64),
    'draws hash': lambda c: _hdr(c)['points']['1.55'].update(draws_sha256='0' * 64),
    'truth': lambda c: _hdr(c)['points']['1.75']['truth']['U6'].update(Delta=_hdr(c)['points']['1.75']['truth']['U6']['Delta'] + 1e-6),
    'truth omega': lambda c: _hdr(c)['points']['1.6']['truth']['J'].update(omega=_hdr(c)['points']['1.6']['truth']['J']['omega'] + 0.01),
    'setting': lambda c: _hdr(c)['settings'].update(omega_margin=0.03),
    'set count': lambda c: _hdr(c)['settings'].update(n_sets=200),
    'missing script hash': lambda c: c['header'].pop('calibration_script_sha256'),
    'protocol hash': lambda c: _hdr(c).update(protocol_sha256='0' * 64),
    'baseline hash': lambda c: _hdr(c).update(baseline_sha256='0' * 64),
    'missing point': lambda c: _hdr(c)['points'].pop('1.95'),
    'threshold': lambda c: c['header']['adoption'].update(A1_cov1_min=0.5),
    'script hash (P1-008)': lambda c: c['header'].update(calibration_script_sha256='0' * 64),
    'own evaluator hash (P1-008)': lambda c: c['header']['evaluators']['3'].update(sha256='0' * 64),
    'other evaluator hash (P1-008)': lambda c: c['header']['evaluators']['2'].update(sha256='0' * 64),
    'missing dimension (P1-009)': lambda c: c['header']['dims'].pop('2'),
    'missing strata dimension (P1-009)': lambda c: c['strata'].pop('2'),
    'partial calibration (P1-009)': lambda c: c['header'].update(only=[[3, '1.6']]),
    'only not recorded (P1-009)': lambda c: c['header'].pop('only'),
    'other-dimension record hash (P1-009)': lambda c: c['header']['dims']['2']['points']['1.05'].update(results_sha256='0' * 64),
    'other-dimension truth (P1-009)': lambda c: c['header']['dims']['2']['points']['1.2']['truth']['J'].update(Delta=c['header']['dims']['2']['points']['1.2']['truth']['J']['Delta'] + 1e-6),
    'other-dimension settings (P1-009)': lambda c: c['header']['dims']['2']['settings'].update(chi2_dof_max=3.0),
    'strata point missing (P1-009)': lambda c: c['strata']['2'].pop('1.7'),
    'stratum missing (P1-009)': lambda c: c['strata']['2']['1.3'].pop('U6'),
    'NaN truth (P1-010)': lambda c: _hdr(c)['points']['1.8']['truth']['Y'].update(Delta=float('nan')),
    'NaN amplitude (P1-010)': lambda c: _hdr(c)['points']['1.8']['truth']['U4']['c'].__setitem__(0, float('inf')),
    'count out of range (P1-010)': lambda c: c['strata']['3']['1.6']['J'].update(n_cov1_profiled=5000),
    'non-integer count (P1-010)': lambda c: c['strata']['3']['1.6']['U4'].update(n_eligible=1999.5),
    'dimension null (P1-011)': lambda c: c['header']['dims'].update({'3': None}),
    'header null (P1-011)': lambda c: c.update(header=None),
    'strata null (P1-011)': lambda c: c.update(strata=None),
    'other-dimension point header null (P1-014)': lambda c: c['header']['dims']['2']['points'].update({'1.05': None}),
    'other-dimension point header not an object (P1-014)': lambda c: c['header']['dims']['2']['points'].update({'1.2': [1, 2]}),
    'other-dimension strata entry null (P1-014)': lambda c: c['strata']['2'].update({'1.3': None}),
    'own-dimension strata entry null (P1-014)': lambda c: c['strata']['3'].update({'1.95': None}),
}

@pytest.mark.parametrize('name', sorted(TAMPER))
def test_binding_failure_invalidates_whole_calibration(evals, fabricated, tmp_path, name):
    cal = copy.deepcopy(fabricated); TAMPER[name](cal)
    R = run_p1(3, tmp_path, cal); F = evals[('fixed', 3)]['points']
    assert R['amendment_P1']['calibration_valid'] is False and not all(c['passed'] for c in R['amendment_P1']['binding_checks'])
    for s, P in R['points'].items():
        assert P['sigma_rule']['applied'] == 'fixed' and P['sigma_rule']['note'] == NOTE_UNBOUND
        assert compare(P, F[s], skip={('sigma_rule',)}) == [], s

def test_misspecified_truths_meet_their_target(fabricated):
    """P1-012: every constructed misspecified family reproduces the recorded U4 − Y difference within its tolerance; the rest are reported."""
    built = 0
    for dim, Hd in fabricated['header']['dims'].items():
        for s, h in Hd['points'].items():
            t = (h['ensembles'].get('misspecified') or {}).get('truth') or {}
            if 'a' in t: assert abs(t['achieved_difference'] - t['target_difference']) <= t['tolerance'] <= max(1e-6, 0.02 * abs(t['target_difference'])) + 1e-15; built += 1
            else: assert 'reason' in t and 'reachable_difference_ranges' in t
    assert built >= 3, built

def test_misspecified_accepts_scanned_amplitude_within_tolerance(monkeypatch):
    """P1-015: a target just outside the reachable range but within tolerance (no sign change to bisect) is still constructed."""
    import calibrate_p1 as K, types
    cap = 0.995   # the fitted U4 value saturates 0.5 % below the target: no root, but within the 2 % tolerance
    monkeypatch.setattr(K, 'central_delta', lambda E, y, C, nser: float(min(y[-1], cap)))
    mu, t = K.misspecified_truth(types.SimpleNamespace(PAIRS=[8, 16, 32, 64]), dict(Delta=0.0, c=[0.0, 0.0], omega=1.0), 1.0, np.eye(8))
    assert mu is not None and t['second_correction_in'] == 'U4' and abs(t['achieved_difference'] - 1.0) <= t['tolerance'] == 0.02

def test_status_inconsistent_with_counts_invalidates(evals, fabricated, tmp_path):
    cal = copy.deepcopy(fabricated); cal['strata']['3']['1.55']['U8']['status'] = 'FAIL'
    R = run_p1(3, tmp_path, cal); assert R['amendment_P1']['calibration_valid'] is False
    assert all(P['sigma_rule']['note'] == NOTE_UNBOUND for P in R['points'].values())

def test_unapproved_amendment_invalidates(fabricated, tmp_path):
    other = tmp_path / 'AMENDMENT_edited.md'; other.write_text(AMENDMENT.read_text() + '\nedited\n')
    cal = copy.deepcopy(fabricated); cal['header']['amendment_sha256'] = sha256(other)
    R = run_p1(3, tmp_path, cal, other); assert R['amendment_P1']['calibration_valid'] is False
    assert any(c['check'] == 'amendment file is the approved revision' and not c['passed'] for c in R['amendment_P1']['binding_checks'])

def test_unfrozen_plan_invalidates(fabricated, tmp_path):
    other = tmp_path / 'FIT_MODEL_3D_edited.md'; other.write_text(CFG[3]['plan'].read_text() + '\nedited\n')
    cal = copy.deepcopy(fabricated); cal['header']['dims']['3']['protocol_sha256'] = sha256(other)
    R = run_p1(3, tmp_path, cal, plan=other); assert R['amendment_P1']['calibration_valid'] is False
    assert any(c['check'] == 'the --plan given is the frozen protocol' and not c['passed'] for c in R['amendment_P1']['binding_checks'])

def test_a3_failure_withdraws_amendment(evals, fabricated, tmp_path):
    cal = copy.deepcopy(fabricated)
    for pts in cal['strata'].values():
        for st in pts.values():
            for q, x in st.items():
                if q != 'crosscheck': x['n_cov1_fixed'] = 1500
    R = run_p1(3, tmp_path, finish(cal)); F = evals[('fixed', 3)]['points']
    assert R['amendment_P1']['calibration_valid'] and not R['amendment_P1']['adopted']
    for s, P in R['points'].items():
        assert P['sigma_rule']['applied'] == 'fixed' and 'amendment withdrawn' in P['sigma_rule']['note'] and compare(P, F[s], skip={('sigma_rule',)}) == []

@pytest.mark.parametrize('stratum,counts,expect', [('J', dict(n_cov1_profiled=1000), 'A1 stratum J: FAIL'),
                                                   ('U6', dict(n_eligible=150, n_cov1_profiled=140, n_cov2_profiled=150, n_cov1_fixed=60, n_cov2_fixed=90), 'A1 stratum U6: UNCALIBRATED'),
                                                   ('crosscheck', dict(n_fail_profiled=300), 'A2 cross-check: FAIL'),
                                                   ('crosscheck', dict(n_both_eligible=150, n_fail_profiled=5, n_fail_fixed=40), 'A2 cross-check: UNCALIBRATED')])
def test_one_failed_stratum_keeps_that_point_fixed(evals, fabricated, tmp_path, stratum, counts, expect):
    cal = copy.deepcopy(fabricated); cal['strata']['3']['1.6'][stratum].update(counts)
    R = run_p1(3, tmp_path, finish(cal)); F = evals[('fixed', 3)]['points']
    assert R['amendment_P1']['calibration_valid'] and R['amendment_P1']['adopted']
    P = R['points']['1.6']
    assert P['sigma_rule']['applied'] == 'fixed' and expect in P['sigma_rule']['note'] and compare(P, F['1.6'], skip={('sigma_rule',)}) == []
    assert P['decision'] == F['1.6']['decision'] and 'CROSS-CHECK FAILED' in P['decision']
    others = [s for s, Q in R['points'].items() if s != '1.6' and Q['eligible']]
    assert others and all(R['points'][s]['sigma_rule']['applied'] == 'profiled' for s in others)

def test_cli_requires_calibration_and_amendment(tmp_path):
    for extra in (['--sigma-rule', 'profiled'], ['--sigma-rule', 'profiled', '--calibration', str(tmp_path / 'x.json')],
                  ['--calibration', str(AMENDMENT)]):
        r = subprocess.run(cmd(3, tmp_path / 'e', None, extra), capture_output=True, env=ENV)
        assert r.returncode == 2 and not (tmp_path / 'e').exists(), extra
