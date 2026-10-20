#!/usr/bin/env python3
"""Tests of the arbitrary-N continuum analysis (PLAN_ANALYSIS.md rev 7; built at rev 4).

  python code/continuum/test_continuum.py [-v] [--output report.json]

Covers: production science-source hash unchanged (A2); legacy mode (A1);
fractional windows (N=384 -> 240/288); Nmix/2 rule (4096 -> 2048); M3 against
the historical analyze_extended.py on the same machine; rank/dof guards;
deduplication; every outcome-table branch; planted synthetic sequences
recovered (spectral, regulator, joint); the auxiliary-input functions against
an archived record; the scripts/run.py sub-command; no proposed closed form in
the code. Only small computations (seconds) run here.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PKG / 'cluster'))

import continuum_analysis as ca          # noqa: E402
import continuum_legacy as cl            # noqa: E402
import continuum_records as cr           # noqa: E402

RAW = PKG / 'data' / 'hamiltonian' / 'raw'


def raw(name: str) -> dict:
    obj = json.loads((RAW / name).read_text())
    return obj.get('data', obj)


class Provenance(unittest.TestCase):
    def test_production_science_hash_unchanged(self):
        """A2: code/hamiltonian is unchanged, so the 16 production records keep their source identity."""
        import hashlib
        import run_task
        digest = hashlib.sha256(json.dumps(run_task.source_hashes(), sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, cr.PRODUCTION_SOURCES_SHA256)
        self.assertFalse(any((PKG / 'code' / 'hamiltonian').glob('*continuum*')))

    def test_no_proposed_closed_form_in_code(self):
        needle = '06' + '627'
        for p in sorted(HERE.glob('*.py')):
            if p.name != Path(__file__).name:
                self.assertNotIn(needle, p.read_text(), p.name)

    def test_run_py_subcommand(self):
        r = subprocess.run([sys.executable, str(PKG / 'scripts' / 'run.py'), '--help'], capture_output=True, text=True)
        for c in ['validate', 'analyze', 'analyze-recorded', 'certify', 'formula-checks', 'second-order', 'demo',
                  'hamiltonian', 'full-hamiltonian', 'original-study', 'legacy-checks', 'continuum']:
            self.assertIn(c, r.stdout)
        r = subprocess.run([sys.executable, str(PKG / 'scripts' / 'run.py'), 'continuum', '--', '--help'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn('{run,sync,check,legacy}', r.stdout)
        r = subprocess.run([sys.executable, str(PKG / 'scripts' / 'run.py'), 'continuum', '--output', 'x'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


class Rules(unittest.TestCase):
    def test_window_scaling(self):
        sel = lambda N: tuple(ca.nmin_windows(N)[l] for l in ca.SELECTED['nmin_labels'])
        self.assertEqual(sel(384), (240, 288))
        self.assertEqual(sel(256), (160, 192))
        self.assertEqual(sel(768), (480, 576))
        self.assertEqual(sel(1024), (640, 768))
        self.assertEqual(ca.nmin_windows(384), {'N/2': 192, '5N/8': 240, '3N/4': 288, '7N/8': 336})
        self.assertEqual(ca.prefix_sizes(384), [192, 256, 288, 384])
        self.assertEqual(ca.prefix_sizes(1024), [512, 683, 768, 1024])

    def test_mixed_rule_reproduces_2048(self):
        import analyze_fine
        for name in ['fine_k1_a0.1.json', 'extended_k3_a0.2.json', 'large_lambda_k3_a0.5.json']:
            d = raw(name)
            m = ca.mixed_select(d['mixed']['fits'], d['mixed']['Nmax'])
            self.assertEqual(d['mixed']['Nmax'], 4096)
            hist = [f for f in d['mixed']['fits'] if len(f['powers']) >= 3 and f['Nmin'] >= 2048]
            self.assertEqual(m['selected'], hist)
            self.assertEqual(m['median'], analyze_fine.analyze(d)['mixed_limit'])
        fits = [dict(powers=[1, 2, 3], Nmin=n, limit=float(n)) for n in (4096, 6553, 8192, 10240, 12288)]
        self.assertEqual([f['Nmin'] for f in ca.mixed_select(fits, 16384)['selected']], [8192, 10240, 12288])

    def test_assemble_reproduces_analyze_fine(self):
        """With the record's own inputs and the 4096 rule the new assembly is analyze_fine.analyze bit for bit."""
        import analyze_fine
        d = raw('fine_k2_a0.175.json')
        m = ca.mixed_select(d['mixed']['fits'], 4096)
        seq, asm = ca.assemble(d, d['two_point'], m['selected'])
        self.assertEqual(seq.tolist(), analyze_fine.analyze(d)['sequence'])


class Guards(unittest.TestCase):
    def test_rank_and_dof_guards(self):
        N, lam, k = 64, 0.3, 1
        n = np.arange(1, N + 1)
        y = -3.5 + 0.2 * (n / N) ** -2.75
        ok = ca.spectral_fit(y, N, lam, k, (2.75, 3.75, 4.75), 1, 40, 0.0)
        self.assertTrue(ok['accepted'])
        dup = ca.spectral_fit(y, N, lam, k, (2.75, 2.75, 3.75), 1, 40, 0.0)
        self.assertLess(dup['rank'], dup['columns'])
        self.assertFalse(dup['accepted'])
        tight = ca.spectral_fit(y, N, lam, k, (2.75, 3.5, 3.75, 4.75), 2, N - 9, 0.0)   # 10 points, 9 columns
        self.assertEqual(tight['dof'], 1)
        self.assertFalse(tight['accepted'])

    def test_regulator_dof_guard_and_saturation(self):
        pts = [dict(id=f'p{i}', order=1, lam=l, h=-3.4 + l * l, eps_spec=1e-6) for i, l in enumerate([0.1, 0.15, 0.2, 0.25])]
        f = ca.reg_fit(pts, ('2', '2log', '3'), False)
        self.assertEqual(f['dof'], 0)
        self.assertTrue(f['saturated'])
        self.assertFalse(f['admissible'])
        self.assertIn('dof < 2', f['rejection_reasons'])


class Dedup(unittest.TestCase):
    def test_windows_selecting_the_same_points_are_one_fit(self):
        lams = [0.1, 0.15, 0.2, 0.25]
        pts = [dict(id=f'p{i}', order=1, lam=l, h=-3.4 + 0.5 * l * l + 0.1 * l ** 3, eps_spec=1e-6)
               for i, l in enumerate(lams)]
        reg = ca.regulator_order(pts, 1)
        keys = [ca.dedup_key(f) for f in reg['fits']]
        self.assertEqual(len(keys), len(set(keys)))
        two = [f for f in reg['fits'] if f['terms'] == ['2', '2log'] and not f['weighted']]
        self.assertEqual(len(two), 2)                        # 4 and 3 points; 2-point windows are underdetermined
        full = [f for f in two if f['number_of_points'] == 4][0]
        self.assertEqual(sorted(full['windows']), ['all', 'lam<=0.25'])
        three = [f for f in two if f['number_of_points'] == 3][0]
        self.assertEqual(sorted(three['windows']), ['drop1', 'lam<=0.2'])


class Outcome(unittest.TestCase):
    def test_branches(self):
        self.assertEqual(ca.outcome({}, None)['branch'], 1)
        one = ca.outcome({1: dict(h0=-3.41, E=0.002)}, None)
        self.assertEqual((one['branch'], one['h0'], one['E']), (2, -3.41, 0.002))
        bad = ca.outcome({1: dict(h0=-3.41, E=0.001), 2: dict(h0=-3.42, E=0.001)}, None)
        self.assertEqual(bad['branch'], 3)
        self.assertAlmostEqual(bad['envelope']['low'], -3.421)
        self.assertAlmostEqual(bad['envelope']['high'], -3.409)
        self.assertAlmostEqual(bad['h0'], -3.415)
        self.assertAlmostEqual(bad['E'], 0.006)
        good = {1: dict(h0=-3.410, E=0.003), 2: dict(h0=-3.412, E=0.002), 3: dict(h0=-3.411, E=0.004)}
        joint_ok = dict(validated=True, preferred=dict(h0=-3.4111), E=0.0015)
        r = ca.outcome(good, joint_ok)
        self.assertEqual((r['branch'], r['h0'], r['E']), (4, -3.4111, 0.0015))
        r = ca.outcome(good, dict(joint_ok, validated=False))
        self.assertEqual(r['branch'], 5)
        self.assertAlmostEqual(r["h0"], (-3.415 + -3.407) / 2)   # envelope [min(h0-E), max(h0+E)]
        self.assertEqual(ca.outcome(good, None)['branch'], 5)


class Planted(unittest.TestCase):
    def test_spectral_recovery(self):
        """A known h(lambda), a known leading tail and power/exponential corrections are recovered by M3."""
        N, lam, k, h, A = 768, 0.1, 1, -3.599, -2.0e5
        n = np.arange(1, N + 1, dtype=float)
        u = n / N
        y = (h - A * n ** -1.75 + 3e-3 * u ** -2.75 - 2e-3 * u ** -3.75 + 4e-4 * u ** -4.75
             + 1e-3 * np.exp(-lam * n) * u ** (k - 1))
        r = ca.m3(y, N, lam, k, A)
        self.assertEqual(r['n_selected_accepted'], 8)
        self.assertLess(abs(r['h'] - h), 1e-8)

    def test_regulator_recovery(self):
        h0, a, b, c = -3.4137, 2.1, -0.8, 1.7
        rng = np.random.default_rng(1)
        lams = [0.05, 0.0625, 0.075, 0.0875, 0.1, 0.125, 0.15, 0.2, 0.25]
        pts = [dict(id=f'p{i}', order=1, lam=l, h=h0 + a * l * l + b * l * l * np.log(l) + c * l ** 3
                    + 1e-7 * rng.standard_normal(), eps_spec=2e-6, eps_mix=0.0, eps_coll=0.0, eps_grid=0.0,
                    eps_round=0.0, eps_tailcut=0.0, half_spread=2e-6, prefix_d34=0.0, eps_cross=None)
               for i, l in enumerate(lams)]
        reg = ca.regulator_order(pts, 1)
        self.assertEqual(reg['selection_status'], 'preferred admissible')
        self.assertTrue(reg['validated'])
        self.assertLess(abs(reg['S']['h0'] - h0), 1e-5)
        b_ = ca.order_budget(reg, {p['id']: p for p in pts})
        self.assertAlmostEqual(b_['components']['eps_prop'], 2e-6 * b_['sum_abs_influence'])

    def test_joint_recovery(self):
        h0 = -3.4137
        coef = {1: (2.1, -0.8, 1.7), 2: (-1.0, 0.3, 4.0), 3: (0.5, 1.1, -2.0)}
        grids = {1: [0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25], 2: [0.0625, 0.075, 0.1, 0.125, 0.15, 0.175, 0.25],
                 3: [0.1, 0.125, 0.15, 0.175, 0.2, 0.25, 0.35]}
        points, by_order, regs = {}, {}, {}
        for k, ls in grids.items():
            a, b, c = coef[k]
            by_order[k] = [dict(id=f'k{k}_{l}', order=k, lam=l, h=h0 + a * l * l + b * l * l * np.log(l) + c * l ** 3,
                                eps_spec=1e-6, eps_mix=1e-7, eps_coll=0.0, eps_grid=0.0, eps_round=0.0,
                                eps_tailcut=0.0, half_spread=1e-6, prefix_d34=0.0, eps_cross=None) for l in ls]
            points.update({p['id']: p for p in by_order[k]})
            regs[k] = ca.regulator_order(by_order[k], k)
        j = ca.joint_analysis(regs, [1, 2, 3], points, by_order)
        self.assertTrue(j['preferred']['accepted'])
        self.assertTrue(j['validated'])
        self.assertLess(abs(j['preferred']['h0'] - h0), 1e-9)


class Historical(unittest.TestCase):
    """The new M3 implementation equals the historical analyze_extended.py at N=384 on the same machine."""

    def test_m3_matches_analyze_extended(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d) / 'w'
            cl._stage(work)
            cl._run(sys.executable, work, 'analyze_extended.py')
            hist = {(r['order'], r['lam']): r for r in json.loads((work / 'extended_analysis.json').read_text())}
        for name in ['extended_k1_a0.1.json', 'extended_k3_a0.2.json']:
            d = raw(name)
            t = json.loads((PKG / 'data/hamiltonian/auxiliary' / f"leading_N384_k{d['order']}_a{d['lam']}.json").read_text())
            m = ca.mixed_select(d['mixed']['fits'], 4096)
            seq, _ = ca.assemble(d, d['two_point'], m['selected'])
            r = ca.m3(seq, 384, d['lam'], d['order'], t['asymptotic_tail_coefficient'])
            h = hist[(d['order'], d['lam'])]
            self.assertEqual([f['limit'] for f in r['fits']], [f['limit'] for f in h['fits']])
            self.assertEqual([f['Nmin'] for f in r['fits']], [f['Nmin'] for f in h['fits']])
            self.assertEqual(r['h'], h['selected']['median'])
            self.assertEqual(r['half_spread'], h['selected']['half_spread'])


class Legacy(unittest.TestCase):
    """A1 (rev 6 A6-2, rev 7 R6-001). Same platform: the legacy outputs are byte-identical to the identical
    11-case policy run on the scripts and data of the pristine commit 474487c. Cross platform (shipped
    reference): every leaf classified; exact / 1e-4 / 1e-8 / condition numbers gated at 10% relative;
    unclassified leaves fail. Byte identity with the reference only with C2_LEGACY_EXPECT_BITWISE=1."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        have_git = subprocess.run(['git', '-C', str(PKG), 'cat-file', '-e', cl.PRISTINE_COMMIT + '^{commit}'],
                                  capture_output=True).returncode == 0
        cls.have_git = have_git
        cls.rep = cl.run_legacy(Path(cls.tmp.name) / 'legacy', sys.executable, pristine=have_git)
        cls.out = Path(cls.tmp.name) / 'legacy'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_same_platform_pristine_byte_identity(self):
        if not self.have_git:
            self.skipTest('needs the git checkout (pristine commit 474487c)')
        self.assertEqual(self.rep['same_platform_pristine']['bytes_identical'],
                         {n: True for n in cl.FILES})

    def test_cross_platform_categories(self):
        s = self.rep['summary']
        self.assertTrue(all(s['structure_identical'].values()), s)
        for c in self.rep['comparisons']:
            self.assertTrue(c['passed'], (c['file'], c.get('failures')))
            self.assertNotIn('unclassified', c['categories'])
        self.assertLess(s['max_abs_representative_C2_difference'], 1e-8)
        cases = [tuple(c) for c in self.rep['policy']['tail_transseries_cases']]
        self.assertEqual(len(cases), 11)
        self.assertNotIn((3, 0.35), cases)
        self.assertFalse(self.rep['policy']['guards_applied'])
        fin = json.loads((self.out / 'FINAL_NUMERICAL_RESULTS.json').read_text())
        self.assertEqual([p['number_of_points'] - p['number_of_parameters'] for p in fin['representative_regulator_fits']],
                         [2, 0, 0])                     # the saturated order-2/3 fits are kept
        if os.environ.get('C2_LEGACY_EXPECT_BITWISE') == '1':
            self.assertTrue(all(s['bytes_identical_to_reference'].values()), s)

    def test_IR2_003_inherited_tail_cutoff_does_not_leak(self):
        """An inherited non-historical LRI_TAIL_CUTOFF must not change the recorded-legacy policy; the historical
        commands keep inheriting it, as before."""
        if not self.have_git:
            self.skipTest('needs the git checkout (pristine commit 474487c)')
        saved = os.environ.get('LRI_TAIL_CUTOFF')
        os.environ['LRI_TAIL_CUTOFF'] = '8192'
        try:
            self.assertEqual(cl._legacy_env(Path('.'))['LRI_TAIL_CUTOFF'], '2048')
            self.assertEqual(cl._env(Path('.'))['LRI_TAIL_CUTOFF'], '8192')      # historical commands unchanged
            with tempfile.TemporaryDirectory() as d:
                rep = cl.run_legacy(Path(d) / 'legacy', sys.executable, pristine=True)
                self.assertEqual(rep['same_platform_pristine']['bytes_identical'], {n: True for n in cl.FILES})
                for n in cl.FILES:
                    self.assertEqual((Path(d) / 'legacy' / n).read_bytes(), (self.out / n).read_bytes(), n)
        finally:
            if saved is None:
                os.environ.pop('LRI_TAIL_CUTOFF', None)
            else:
                os.environ['LRI_TAIL_CUTOFF'] = saved

    def test_categorizer_fails_unknown_and_gates(self):
        self.assertEqual(cl.categorize('/data_points[3]/lam', 0.1), 'exact')
        self.assertEqual(cl.categorize('/model_sensitivity[2]/terms[0]', '2log'), 'exact')
        self.assertEqual(cl.categorize('[0]/fits[5]/condition', 3.0), 'condition')
        self.assertEqual(cl.categorize('/representative_regulator_fits[1]/C2', -4.0), 'representative_C2')
        self.assertEqual(cl.categorize('/something_new', 1.5), 'unclassified')
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.json', Path(d) / 'b.json'
            a.write_text(json.dumps([dict(limit=1.0, condition=10.0, unknown=2.0, N=4)]))
            b.write_text(json.dumps([dict(limit=1.0 + 5e-5, condition=10.5, unknown=2.0, N=4)]))
            r = cl.compare(a, b)
            self.assertFalse(r['passed'])                      # the unclassified leaf fails
            self.assertEqual(r['n_failures'], 1)
            b.write_text(json.dumps([dict(limit=1.0 + 2e-4, condition=12.0, unknown=2.0, N=5)]))
            r = cl.compare(a, b)
            self.assertEqual(r['n_failures'], 4)               # value, condition (20%), unknown, exact N

    def test_same_machine_historical_commands(self):
        """Command preservation (separate from legacy identity): the legacy outputs equal the unchanged
        `scripts/run.py analyze` outputs on this machine."""
        with tempfile.TemporaryDirectory() as d:
            outs = cl.historical_commands(sys.executable, Path(d))
            self.assertEqual((outs['analyze'] / 'extended_analysis.json').read_bytes(),
                             (self.out / 'extended_analysis.json').read_bytes())
            full = json.loads((outs['analyze'] / 'tail_transseries_fits.json').read_text())
            mine = json.loads((self.out / 'tail_transseries_fits.json').read_text())
            self.assertEqual(full[:11], mine)
            self.assertEqual((full[11]['order'], full[11]['lam']), (3, 0.35))


class GridSplit(unittest.TestCase):
    """Rev 6/7 (A5-1): epsilon_grid = |v.s| + sum|v||rho| on a measured full-coverage profile."""

    @classmethod
    def setUpClass(cls):
        N, lam, k, A = 512, 0.15, 2, -1.5e5
        n = np.arange(1, N + 1, dtype=float)
        u = n / N
        y = -3.57 - A * n ** -1.75 + 3e-3 * u ** -2.75 - 2e-3 * u ** -3.75 + 4e-4 * u ** -4.75
        cls.N, cls.n = N, n
        cls.res = ca.m3(y, N, lam, k, A, full=False)
        cls.chosen = cls.res['_chosen']

    def test_smooth_profile_gives_signed_shift(self):
        n = self.n
        delta = 2e-6 + 3e-9 * n - 4e-12 * n ** 2 + 5e-15 * n ** 3          # a cubic in n is a cubic in x on W
        g = ca.grid_split(self.chosen, delta)
        for r in g['per_fit']:
            self.assertLess(r['rough'], 1e-9 * r['smooth'] + 1e-15)
            self.assertAlmostEqual(r['eps'], r['signed_shift'], delta=1e-9 * r['signed_shift'])
            self.assertLessEqual(r['eps'], r['rev4_l1'] * (1 + 1e-12))     # never above the rev-4 L1 here
        self.assertAlmostEqual(g['eps_grid'], max(r['signed_shift'] for r in g['per_fit']),
                               delta=1e-9 * g['eps_grid'])

    def test_rough_component_bounded(self):
        n = self.n
        rough = 1e-9 * (-1.0) ** n
        delta = 2e-6 + 3e-9 * n + rough
        g = ca.grid_split(self.chosen, delta)
        for f, r in zip(self.chosen, g['per_fit']):
            s, rho = ca.split_profile(f['_n'], delta[f['_n'] - 1])
            self.assertAlmostEqual(r['rough'], float(np.sum(np.abs(f['_v']) * np.abs(rho))))
            self.assertLessEqual(abs(f['_v'] @ rho), r['rough'] * (1 + 1e-12))
            self.assertLessEqual(r['signed_shift'], r['eps'] * (1 + 1e-12))      # never below the signed shift
            self.assertGreater(r['rough'], 0.5e-9 * float(np.sum(np.abs(f['_v']))))
            self.assertLess(r['max_abs_rho'], 1.2e-9)

    def test_partial_profile_refused(self):
        an = ca.PointAnalysis.__new__(ca.PointAnalysis)
        an.N, an.main = self.N, self.res
        with self.assertRaises(ValueError):
            an.grid_split(np.zeros(self.N - 1))

    def test_rev4_exception_fallback(self):
        import continuum_driver as cd
        rev4 = {'P': dict(eps=dict(eps_grid=0.25), extraction=dict(status='inherited', donor='D', kind=None,
                                                                    donor_eps_grid=0.5, sum_abs_v_ratio=0.5,
                                                                    flags=['inherited extraction error']))}
        x = cd.extraction_status('P', {}, rev4, 'evidence/rev4/continuum_points.json')
        self.assertEqual(x['status'], 'rev-4 exception')
        self.assertEqual(x['eps_grid'], 0.25)
        self.assertEqual(x['flags'], ['extraction comparison missing: rev-4 exception'])
        self.assertEqual(x['frozen_rev4']['donor'], 'D')
        self.assertEqual(x['frozen_rev4']['status'], 'inherited')
        m = {'P': dict(comparisons=[{}], eps_grid=1e-5, n_full_coverage=1, from_check='C', smooth=8e-6, rough=2e-6,
                       rev4_l1=0.1, signed_shift=8e-6, max_abs_rho=1e-9)}
        y = cd.extraction_status('P', m, rev4, '')
        self.assertEqual((y['status'], y['eps_grid'], y['flags']), ('measured', 1e-5, []))
        with self.assertRaises(ValueError):
            cd.extraction_status('Q', {}, rev4, '')


class FixRound1(unittest.TestCase):
    """Codex inspection 1 (R001-R007)."""

    @staticmethod
    def rec(**kw):
        base = dict(order=1, lam=0.1, N=768, oversample=4, radius_cost=4.5, mixed_cutoff=16384, tail_cutoff=8192,
                    collapsed_cutoff=800000, sources='s' * 64, site='expanse', pool='primary', origin='production',
                    path='a.json', sha256='0' * 64, data={})
        base.update(kw)
        return cr.Record(**base)

    def test_R001_same_grid_or_same_record_refused(self):
        p = self.rec()
        with self.assertRaises(ValueError):                          # the record itself
            cr.check_comparison(p, p)
        same_grid = self.rec(pool='diagnostic', origin='m4d', path='b.json', sha256='1' * 64, site='symmetry')
        with self.assertRaises(ValueError):                          # a different record on the same grid
            cr.check_comparison(p, same_grid)
        cr.check_comparison(p, self.rec(pool='diagnostic', origin='m4d', path='c.json', sha256='2' * 64, N=1024))
        cr.check_comparison(p, self.rec(pool='diagnostic', origin='m4d', path='d.json', sha256='3' * 64,
                                        radius_cost=4.0))

    def test_R001_record_in_both_pools_refused(self):
        a = self.rec()
        b = self.rec(pool='diagnostic', origin='m4d', path='other.json')            # same content (sha256)
        with self.assertRaises(ValueError):
            cr.check_pools([a, b])
        cr.check_pools([a, self.rec(pool='diagnostic', origin='m4d', path='x.json', sha256='9' * 64, N=1024)])

    SOURCE_HASHES = {'analyze_fine.py': 'a' * 64, 'mixed_sequence.py': 'b' * 64}

    def _planted_index(self, d: Path, plan_name: str, plan_sha: str, index_plan: str, receipt_sha: str | None = None,
                       lams=(0.1,), sidecar_of=None, index_sources=None, receipt_sources=None):
        task = d / 'task'
        task.mkdir(parents=True)
        for lam in lams:
            rec = dict(order=1, lam=lam, N=8, raw=dict(Xchain=[0.0] * 8), two_point=dict(N=800000),
                       mixed=dict(Nmax=16384))
            (task / f'cluster_k1_a{lam!r}_N8.json').write_text(json.dumps(rec))
            (task / f'cluster_k1_a{lam!r}_N8_analysis.json').write_text(json.dumps(dict(
                order=1, lam=lam, N=8, leading_tail=dict(order=1, lam=lam, N=8192))))
        job = dict(id='X', cutoff=8, order=1, **{'lambda': list(lams)}, oversample=4, radius_cost=4.5,
                   mixed_cutoff=16384, collapsed_cutoff=800000, tail_cutoff=8192)
        (task / 'task_receipt.json').write_text(json.dumps(dict(
            plan_name=plan_name, plan_sha256=receipt_sha or plan_sha, job=job,
            source_hashes=receipt_sources or self.SOURCE_HASHES)))
        sums = ''.join(f'{cr.sha256(task / n)}  {n}\n' for n in sorted(x.name for x in task.iterdir()))
        (task / 'SHA256SUMS').write_text(sums)
        digest = index_sources or cr.sources_digest(self.SOURCE_HASHES)
        records = []
        for lam in lams:
            path = task / f'cluster_k1_a{lam!r}_N8.json'
            side = f'cluster_k1_a{(sidecar_of or {}).get(lam, lam)!r}_N8_analysis.json'
            records.append(dict(
                path=str(path), sha256=cr.sha256(path), task_dir='task', order=1, lam=lam, N=8, sources_sha256=digest,
                site='expanse', plan_sha256=plan_sha, plan_name=plan_name, analysis_sidecar=side,
                config=dict(cutoff=8, oversample=4, radius_cost=4.5, mixed_cutoff=16384, collapsed_cutoff=800000,
                            tail_cutoff=8192)))
        (d / 'index.json').write_text(json.dumps(dict(plan=index_plan, all_verified_and_compatible=True,
                                                      records=records)))
        return d / 'index.json'

    def test_IR2_001_sidecar_and_sources_bound(self):
        diag_sha = 'b2435b4e8dadd838498a5b652df4a188d258c9e49693f45295ac4be29d72b7a8'
        name = cr.APPROVED_PLANS['diagnostic'][diag_sha]['name']
        with tempfile.TemporaryDirectory() as d:
            ok = self._planted_index(Path(d) / 'ok', name, diag_sha, 'analysis_checks_plan', lams=(0.05, 0.0625))
            self.assertEqual(len(cr.load_merged(ok, 'diagnostic', 'm4d', {}, None)), 2)
            swap = self._planted_index(Path(d) / 'swap', name, diag_sha, 'analysis_checks_plan', lams=(0.05, 0.0625),
                                       sidecar_of={0.05: 0.0625})
            with self.assertRaises(ValueError):                    # the lambda=0.0625 sidecar for the 0.05 entry
                cr.load_merged(swap, 'diagnostic', 'm4d', {}, None)
            idx = self._planted_index(Path(d) / 'tamper', name, diag_sha, 'analysis_checks_plan', index_sources='c' * 64)
            with self.assertRaises(ValueError):                    # index sources disagree with the receipt
                cr.load_merged(idx, 'diagnostic', 'm4d', {}, None)
            other = {'analyze_fine.py': 'd' * 64}
            idx = self._planted_index(Path(d) / 'receipt', name, diag_sha, 'analysis_checks_plan',
                                      receipt_sources=other)
            with self.assertRaises(ValueError):                    # receipt sources disagree with the index
                cr.load_merged(idx, 'diagnostic', 'm4d', {}, None)
            idx = self._planted_index(Path(d) / 'expect', name, diag_sha, 'analysis_checks_plan')
            with self.assertRaises(ValueError):                    # consistent, but not the expected source set
                cr.load_merged(idx, 'diagnostic', 'm4d', {}, cr.PRODUCTION_SOURCES_SHA256)

    def test_IR2_001_real_production_index(self):
        real = PKG / 'outputs/merged_production_plan_20261013.json'
        if not real.is_file():
            self.skipTest('needs the local production records (outputs/ is not in git)')
        idx = json.loads(real.read_text())
        self.assertEqual(len(cr.load_merged(real, 'primary', 'production', {}, cr.PRODUCTION_SOURCES_SHA256)), 15)
        with tempfile.TemporaryDirectory() as d:
            for field, value in (('analysis_sidecar', 'cluster_k1_a0.0625_N1024_analysis.json'),
                                 ('sources_sha256', '0' * 64)):
                bad = json.loads(json.dumps(idx))
                e = [r for r in bad['records'] if r['order'] == 1 and r['lam'] == 0.05][0]
                e[field] = value
                for r in bad['records']:
                    r['path'] = str((PKG / r['path']).resolve())
                path = Path(d) / f'{field}.json'
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError, msg=field):
                    cr.load_merged(path, 'primary', 'production', {}, cr.PRODUCTION_SOURCES_SHA256)

    def test_R001_plan_identity_checked(self):
        diag_sha = 'b2435b4e8dadd838498a5b652df4a188d258c9e49693f45295ac4be29d72b7a8'
        diag = cr.APPROVED_PLANS['diagnostic'][diag_sha]
        with tempfile.TemporaryDirectory() as d:
            idx = self._planted_index(Path(d) / 'ok', diag['name'], diag_sha, 'analysis_checks_plan')
            self.assertEqual(len(cr.load_merged(idx, 'diagnostic', 'm4d', {}, None)), 1)
            with self.assertRaises(ValueError):                      # a diagnostic plan offered as the primary pool
                cr.load_merged(idx, 'primary', 'production', {}, None)
            bad = self._planted_index(Path(d) / 'bad', diag['name'], 'f' * 64, 'analysis_checks_plan')
            with self.assertRaises(ValueError):                      # unknown plan sha256
                cr.load_merged(bad, 'diagnostic', 'm4d', {}, None)
            lie = self._planted_index(Path(d) / 'lie', diag['name'], diag_sha, 'analysis_checks_plan', receipt_sha='e' * 64)
            with self.assertRaises(ValueError):                      # the task receipt names another plan
                cr.load_merged(lie, 'diagnostic', 'm4d', {}, None)
        for sha, v in cr.APPROVED_PLANS['diagnostic'].items():       # the repository plans are the approved ones
            self.assertEqual(cr.sha256(PKG / v['file']), sha)
        self.assertEqual(cr.sha256(PKG / 'cluster/production_plan.json'),
                         'c8a9023db5df34916f71708b298e38255029574436e0a432aae3a9eea47059ba')

    def test_R002_preferred_unavailable_goes_to_fallback(self):
        lams = [0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]           # only three points with lambda <= 0.25
        pts = [dict(id=f'p{i}', order=1, lam=l, h=-3.4 + 0.5 * l * l + 0.1 * l ** 3, eps_spec=1e-6)
               for i, l in enumerate(lams)]
        reg = ca.regulator_order(pts, 1)
        self.assertEqual(reg['selection_status'], 'preferred unavailable')
        self.assertFalse(reg['preferred']['available'])
        self.assertIn('unavailable', reg['preferred']['rejection_reasons'][0])
        self.assertIsNotNone(reg['S'])
        few = [dict(id=f'q{i}', order=1, lam=l, h=-3.4 + l, eps_spec=1e-6) for i, l in enumerate([0.3, 0.4, 0.5])]
        reg = ca.regulator_order(few, 1)                              # nothing admissible at all
        self.assertEqual((reg['selection_status'], reg['validated']), ('no admissible fit', False))
        self.assertEqual(reg['validation_status'], 'insufficiently validated')

    def _no_estimate_points(self):
        pts = {}
        for k in (1, 2, 3):
            for i, l in enumerate([0.3, 0.4, 0.5]):
                pid = f'k{k}_{i}'
                pts[pid] = dict(id=pid, order=k, lam=l, h=-3.4 + l, eps_spec=1e-6, eps_mix=0.0, eps_coll=0.0,
                                eps_grid=0.0, eps_round=0.0, eps_tailcut=0.0, half_spread=1e-6, prefix_d34=0.0,
                                eps_cross=None)
        return pts

    def _write(self, out, **kw):
        import continuum_driver as cd
        return cd.estimate_and_write(self._no_estimate_points(), [], [], [], {}, {}, {}, 'now', out, None, **kw)

    def test_R003_branch1_end_to_end(self):
        import continuum_driver as cd
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'res'
            est = self._write(out)
            self.assertEqual(est['outcome']['branch'], 1)
            self.assertIsNone(est['final'])
            gen = cd.current_generation(out)
            rep = (gen / 'REPORT.md').read_text()
            self.assertIn('**No estimate**', rep)
            self.assertIn('EXCLUDED: no admissible fit', rep)
            self.assertIn('legacy validation was not performed for this run', rep)
            self.assertEqual(json.loads((gen / 'C2_estimate.json').read_text())['outcome']['branch'], 1)
            self.assertEqual(cd.check_top_level(out), [])

    def test_IR2_002_generations_pointer_and_writer_lock(self):
        import continuum_driver as cd
        import continuum_report as crep
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'res'
            self._write(out)
            first = cd.current_generation(out)
            first_bytes = {f: (first / f).read_bytes() for f in cd.TOP_FILES}
            top = {f: (out / f).read_bytes() for f in cd.TOP_FILES}

            # an interruption after a partial write (the report fails after the JSON files exist)
            saved = crep.write_report

            def boom(gen, *a, **k):
                self.assertTrue((gen / 'C2_estimate.json').is_file())          # the JSON files were written
                raise RuntimeError('planted interruption')
            crep.write_report = boom
            try:
                with self.assertRaises(RuntimeError):
                    self._write(out)
            finally:
                crep.write_report = saved
            self.assertEqual(cd.current_generation(out), first)               # the previous generation stays current
            self.assertEqual([g.name for g in (out / cd.GENERATIONS).iterdir()], [first.name])   # partial removed
            self.assertEqual({f: (out / f).read_bytes() for f in cd.TOP_FILES}, top)
            self.assertFalse((out / cd.WRITER_LOCK).exists())                  # lock released

            # a hard kill leaves a hidden partial generation: readers never see it
            (out / cd.GENERATIONS / '.dead.partial').mkdir()
            self.assertEqual(cd.current_generation(out), first)
            (out / cd.POINTER).write_text(f'{cd.GENERATIONS}/.dead.partial\n')
            with self.assertRaises(ValueError):
                cd.current_generation(out)
            cd.switch_current(out, first.name)

            # a second concurrent writer is refused and changes nothing
            (out / cd.WRITER_LOCK).write_text('{"pid": 1}\n')
            with self.assertRaises(RuntimeError):
                self._write(out)
            self.assertEqual(cd.current_generation(out), first)
            (out / cd.WRITER_LOCK).unlink()

            # a successful run publishes a new generation; the old one is unchanged
            self._write(out)
            second = cd.current_generation(out)
            self.assertNotEqual(second, first)
            self.assertEqual({f: (first / f).read_bytes() for f in cd.TOP_FILES}, first_bytes)
            self.assertEqual(cd.check_top_level(out), [])
            m = json.loads((out / 'C2_estimate.json').read_text())['meta']['generation']
            self.assertEqual(m, second.name)
            (out / 'REPORT.md').write_text('stale copy\n')                      # a damaged copy is detected
            self.assertEqual(cd.check_top_level(out), ['REPORT.md'])
            cd.sync_top_level(out)
            self.assertEqual(cd.check_top_level(out), [])

    def test_IR2_004_legacy_receipt_schema(self):
        import continuum_driver as cd
        self.assertEqual(cd.legacy_validation(None)['status'], 'NOT PERFORMED')
        real = json.loads((PKG / 'results/continuum_2026-10/evidence/legacy_macos/legacy_reproduction.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            r = Path(d) / 'legacy_reproduction.json'

            def status(obj):
                r.write_text(json.dumps(obj) if not isinstance(obj, str) else obj)
                return cd.legacy_validation(r)['status']
            self.assertEqual(status(real), 'PASSED')
            bad = json.loads(json.dumps(real))
            bad['summary']['cross_platform_passed']['extended_analysis.json'] = False
            self.assertEqual(status(bad), 'FAILED')
            variants = []
            v = json.loads(json.dumps(real)); v['summary']['same_platform_pristine_bytes_identical'] = {'a': True}
            v['summary']['cross_platform_passed'] = {'a': True}; variants.append(v)              # the old loophole
            v = json.loads(json.dumps(real)); del v['summary']['cross_platform_passed']['FINAL_NUMERICAL_RESULTS.json']
            variants.append(v)                                                                    # a missing file
            v = json.loads(json.dumps(real)); v['summary']['cross_platform_passed']['FINAL_NUMERICAL_RESULTS.json'] = 'yes'
            variants.append(v)                                                                    # not a boolean
            v = json.loads(json.dumps(real)); v['same_platform_pristine']['commit'] = 'fa3858a'; variants.append(v)
            v = json.loads(json.dumps(real)); del v['tolerances']; variants.append(v)
            v = json.loads(json.dumps(real)); v['policy']['tail_transseries_cases'].append([3, 0.35]); variants.append(v)
            v = json.loads(json.dumps(real)); del v['platform']['numpy']; variants.append(v)
            v = json.loads(json.dumps(real)); v['comparisons'] = v['comparisons'][:2]; variants.append(v)
            for k, v in enumerate(variants):
                self.assertEqual(status(v), 'INCOMPLETE', k)
            self.assertEqual(status('not json'), 'INCOMPLETE')
            self.assertEqual(status([1, 2]), 'INCOMPLETE')
            out = Path(d) / 'res'                                             # the report never says PASSED for it
            r.write_text(json.dumps(variants[0]))
            self._write(out, legacy_path=r)
            rep = (out / 'REPORT.md').read_text()
            self.assertIn('**INCOMPLETE**', rep)
            self.assertNotIn('PASSED', rep)

    def test_R004_non_finite_leaf_fails(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / 'a.json', Path(d) / 'b.json'
            a.write_text(json.dumps([dict(limit=1.0, condition=10.0, N=4)]))
            for bad in ('NaN', 'Infinity', '-Infinity'):
                b.write_text('[{"limit": %s, "condition": 10.0, "N": 4}]' % bad)
                r = cl.compare(a, b)
                self.assertFalse(r['passed'], bad)
                self.assertIn('non-finite', r['failures'][0])
            b.write_text('[{"limit": 1.0, "condition": NaN, "N": 4}]')
            self.assertFalse(cl.compare(a, b)['passed'])

    def test_R006_replica_differences_serialized(self):
        r = self.rec(replicas=[dict(site='symmetry', path='p', sha256='s', max_abs_raw_chain_difference=6.9e-11,
                                    finite_cutoff_h_difference=1.0e-9)])
        rep = r.describe()['replicas'][0]
        self.assertEqual((rep['max_abs_raw_chain_difference'], rep['finite_cutoff_h_difference']), (6.9e-11, 1.0e-9))

    def test_R007_pipes_escaped(self):
        import continuum_report as crep
        t = crep.table(['|difference|', 'b'], [['sum |w| eps', '|v.s| + sum|v||rho|'], ['x', 'y']])
        for line in t.splitlines():
            self.assertEqual(len(re.findall(r'(?<!\\)\|', line)), 3, line)
        with self.assertRaises(ValueError):
            crep.table(['a', 'b'], [['only one']])


class AuxInputs(unittest.TestCase):
    def test_aux_functions_reproduce_an_archived_record(self):
        """aux_inputs.compute at the archived cutoffs (mixed 4096, collapsed 200000, tail 2048) reproduces
        the archived fine record and its archived tail coefficient."""
        import aux_inputs as ai
        saved = (ai.MIXED_CUTOFF, ai.COLLAPSED_CUTOFFS, ai.TAIL_CUTOFF, ai.TAIL_CUTOFF_COARSE)
        try:
            ai.MIXED_CUTOFF, ai.COLLAPSED_CUTOFFS, ai.TAIL_CUTOFF, ai.TAIL_CUTOFF_COARSE = 4096, (100000, 200000), 2048, 1024
            out = ai.compute(dict(order=1, lam=0.25, archived=True, new=False))
        finally:
            ai.MIXED_CUTOFF, ai.COLLAPSED_CUTOFFS, ai.TAIL_CUTOFF, ai.TAIL_CUTOFF_COARSE = saved
        d = raw('fine_k1_a0.25.json')
        x_new, x_old = np.asarray(out['mixed']['Xmixed']), np.asarray(d['mixed']['Xmixed'])
        self.assertLess(np.max(np.abs(x_new - x_old)) / np.max(np.abs(x_old)), 1e-12)
        for key in ('Xdisc', 'Dmixed', 'X2', 't2', 'k2'):
            self.assertAlmostEqual(out['two_point']['200000'][key], d['two_point'][key], delta=1e-10 * abs(d['two_point'][key]) + 1e-14)
        tails = json.loads((PKG / 'data/hamiltonian/auxiliary/exact_leading_tail.json').read_text())
        a_old = [t for t in tails if t['order'] == 1 and t['lam'] == 0.25 and t['N'] == 2048][0]['asymptotic_tail_coefficient']
        a_new = out['a_face']['tail2048_collapsed200000']['asymptotic_tail_coefficient']
        self.assertLess(abs(a_new - a_old) / abs(a_old), 1e-10)
        self.assertEqual(len(out['mixed']['prefix_fits']), 30)


def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path)
    p.add_argument('-v', action='store_true')
    a = p.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(verbosity=2 if a.v else 1).run(suite)
    if a.output:
        import platform
        a.output.write_text(json.dumps(dict(
            suite='code/continuum/test_continuum.py', run=res.testsRun, failures=len(res.failures),
            errors=len(res.errors), skipped=len(res.skipped), python=sys.version, platform=platform.platform(),
            ok=res.wasSuccessful()), indent=2) + '\n')
    sys.exit(0 if res.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
