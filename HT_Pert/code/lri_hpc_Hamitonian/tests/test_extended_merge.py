"""Review IR-004: the extended analysis refuses a new row that disagrees with a saved row at the same cutoff, and
accepts one that agrees (the saved row is kept). Runs analysis/extended/run_extended.py in a temporary copy."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'analysis' / 'extended'
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp) / 'repo'
    (base / 'analysis').mkdir(parents=True)
    shutil.copytree(SRC, base / 'analysis' / 'extended',
                    ignore=shutil.ignore_patterns('*_new.json', '*_new.csv', 'extended_summary.json', '__pycache__'))
    shutil.copytree(ROOT / 'analysis_original', base / 'analysis_original', ignore=shutil.ignore_patterns('__pycache__'))
    ext = base / 'analysis' / 'extended'
    saved48 = next(r for r in json.loads((ext / 'C7_extension.json').read_text()) if r['cutoff'] == 48)
    run = lambda: subprocess.run([sys.executable, 'run_extended.py'], cwd=ext, capture_output=True, text=True)
    same = dict(saved48, source_sha256='X' * 64)
    (ext / 'thermal_new.json').write_text(json.dumps([same]))
    r = run()
    assert r.returncode == 0, r.stderr[-600:]
    assert json.loads((ext / 'extended_summary.json').read_text())['overlap_checked']['thermal'] == [48]
    bad = dict(same, C=list(same['C'])); bad['C'][4] += 1e-5
    (ext / 'thermal_new.json').write_text(json.dumps([bad]))
    r = run()
    assert r.returncode != 0 and 'disagrees with the saved row' in r.stderr, r.stderr[-600:]
print('PASS test_extended_merge')
