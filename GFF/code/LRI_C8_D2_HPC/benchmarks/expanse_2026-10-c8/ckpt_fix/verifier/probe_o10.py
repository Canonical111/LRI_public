#!/usr/bin/env python3
"""O10 break attempts against tools/verify_result.py of the checkout (as tests/verify_result_tamper.py imports it)."""
import copy, json, math, sys
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2])
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tests')]
import numpy as np, verify_result as vr, combine
from assembly_checks import synthetic_ar
b1 = dict(label='x', design_sha256='d' * 64, inputs_manifest_sha256='i' * 64, numerics='exact', rates_identity='default', seeds=list(range(24)),
          ar=synthetic_ar(np.random.default_rng(7), R=6))
b2 = dict(b1, label='y', seeds=list(range(100, 124)), ar=synthetic_ar(np.random.default_rng(8), R=6))
fin = json.loads(json.dumps(combine.combine_batches([b1, b2], planned=2, bootstrap=0)))
out = {'untouched': vr.verify(fin)}; held = out['untouched'] == []
def case(name, f, expect_reject=True):
    global held
    t = copy.deepcopy(fin); f(t); p = vr.verify(t); out[name] = p[:2] if p else 'accepted'
    if bool(p) != expect_reject: held = False
case('per_batch_sampling_se_doubled', lambda t: t['batches']['per_batch'][0].__setitem__('sampling_se', t['batches']['per_batch'][0]['sampling_se'] * 2))
case('planned_3_with_final_true', lambda t: t['batches'].__setitem__('planned', 3))
case('a_batch_duplicated', lambda t: t['batches']['per_batch'].append(copy.deepcopy(t['batches']['per_batch'][0])))
case('dof_as_float', lambda t: t['batches'].__setitem__('dof', 1.0))
case('chi2_as_string', lambda t: t['batches'].__setitem__('chi2_about_combined', str(t['batches']['chi2_about_combined'])))
case('status_with_trailing_space', lambda t: t.__setitem__('status', t['status'] + ' '))
case('power_correction_se_changed_alone', lambda t: t.__setitem__('power_correction_se', t['power_correction_se'] * 1.01))
def coordinated(t):
    d = 0.01 * t['power_free_se'] ** 2
    t['power_free_se'] = math.sqrt(t['power_free_se'] ** 2 + 2 * d); t['power_free_correction_covariance'] -= d
case('coordinated_pfse_and_cross_keep_identity_(documented_limit)', coordinated, expect_reject=False)
out['held'] = held
OUT.write_text(json.dumps(out, indent=1, default=str) + '\n'); print(json.dumps(out, indent=1, default=str)[:3000]); sys.exit(0 if held else 1)
