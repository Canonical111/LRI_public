"""Acceptance gates (review LRI-001): failing results are refused by the validator, the CLI and the exporter."""
import sys, json, copy, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lri_hpc.validate import check_result, ResultError
from lri_hpc.solver import compute, source_fingerprint
good = compute(8, 'thermal', 7)
check_result(good)
def refused(r):
    try:
        check_result(r); return False
    except ResultError:
        return True
bad = copy.deepcopy(good); bad['tuning_residual'] = 1e-3; assert refused(bad)
bad = copy.deepcopy(good); bad['C'][7] = float('nan'); assert refused(bad)
bad = copy.deepcopy(good); bad['second_order_shell_residual'] = 1e-8; assert refused(bad)
g6 = compute(8, 'phi6', 5); check_result(g6)
bad = copy.deepcopy(g6); bad['vacuum_subtracted']['tuning_residual'] = 1.0; assert refused(bad)
bad = copy.deepcopy(g6); bad['raw']['D6'] = bad['raw']['D6'][:-1]; assert refused(bad)
# CLI reuse and export refuse a completed-but-failing output.
with tempfile.TemporaryDirectory() as td:
    td = Path(td); out = td / 'res'; out.mkdir()
    bad = copy.deepcopy(good); bad['tuning_residual'] = 1e-3
    (out / 'thermal_d7_L8.json').write_text(json.dumps(bad))
    r = subprocess.run([sys.executable, '-m', 'lri_hpc', '--task', 'thermal', '--degree', '7', '--cutoffs', '8', '--threads', '2',
                        '--output-dir', str(out), '--resume'], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode != 0 and 'tuning residual' in (r.stderr + r.stdout), r.stderr[-400:]
    r = subprocess.run([sys.executable, str(ROOT / 'export_results.py'), str(out), '--task', 'thermal', '--degree', '7', '--prefix', str(td / 'x')],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode != 0 and 'tuning residual' in (r.stderr + r.stdout), r.stderr[-400:]
# Export with --source refuses a gated row from another solver source (review IR-003) and accepts matching rows.
with tempfile.TemporaryDirectory() as td:
    td = Path(td); out = td / 'res'; out.mkdir()
    ok = copy.deepcopy(good); ok['source_sha256'] = 'A' * 64
    (out / 'thermal_d7_L8.json').write_text(json.dumps(ok))
    other = copy.deepcopy(good); other['cutoff'] = 10; other['source_sha256'] = 'B' * 64
    (out / 'thermal_d7_L10.json').write_text(json.dumps(other))
    cmd = [sys.executable, str(ROOT / 'export_results.py'), str(out), '--task', 'thermal', '--degree', '7', '--prefix', str(td / 'x')]
    r = subprocess.run(cmd + ['--source', 'A' * 64], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode != 0 and 'required' in (r.stderr + r.stdout), r.stderr[-400:]
    (out / 'thermal_d7_L10.json').unlink()
    (out / 'thermal_d7_L12.json').write_text(json.dumps(ok))      # L8 result under the L12 name (review IR2-002)
    r = subprocess.run(cmd + ['--source', 'A' * 64], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode != 0 and 'does not match the result identity' in (r.stderr + r.stdout), r.stderr[-400:]
    (out / 'thermal_d7_L12.json').unlink()
    r = subprocess.run(cmd + ['--source', 'A' * 64], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and json.loads((td / 'x.json').read_text())[0]['source_sha256'] == 'A' * 64, r.stderr[-400:]
print('PASS test_validate', flush=True)
