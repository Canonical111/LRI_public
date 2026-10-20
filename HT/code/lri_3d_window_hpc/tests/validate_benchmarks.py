"""Audit measured records, preserved reference identity and numerical gates."""
from pathlib import Path
import json,hashlib,math,sys,subprocess
if sys.flags.optimize:raise RuntimeError("Validation requires assertions enabled")
import numpy as np
R=Path(__file__).resolve().parents[1]
# Historical performance records remain immutable. Verify them against the exact
# archived implementation that produced them, not against a patched basis.py.
# This is not an 'expected stale' bypass: every source byte and record still has
# to match, AND fresh current-source numerical checks must pass below.
SNAPSHOT_MANIFEST_SHA256='890f1a07fd54abd51501aca7684c3563fdf14774311c2ee406c07d1035c7f97b'
ref=R/'reference/performance_0_2_0'
manifest=(ref/'SNAPSHOT.sha256').read_bytes()
assert hashlib.sha256(manifest).hexdigest()==SNAPSHOT_MANIFEST_SHA256
for line in manifest.decode().splitlines():
 expected,name=line.split('  ',1)
 assert not Path(name).is_absolute() and '..' not in Path(name).parts
 assert hashlib.sha256((ref/name).read_bytes()).hexdigest()==expected,name
rows=[dict(json.loads(p.read_text()),record=p.name) for p in sorted((R/'results/benchmarks').glob('*.json'))]
assert rows,'No benchmark records'
counts={}
for r in rows:
 category='profile' if r.get('profile_file') else ('cache' if r.get('cache_dir') else r['task'])
 counts[category]=counts.get(category,0)+1
 code=R/'reference/baseline/code' if r['implementation']=='baseline' else R/'reference/performance_0_2_0/code'
 for name,dig in r['source_sha256'].items():
  assert hashlib.sha256((code/name).read_bytes()).hexdigest()==dig,(r['record'],name)
 assert r['runtime']['blas'] and all(q['num_threads']==1 for q in r['runtime']['blas'] if q['user_api']=='blas'),r['record']
 assert r['threads'] in (1,2,4)
 assert r['setup_seconds']>=0 and r['peak_rss_kib']>0
 if r['task']=='solve':
  s=r['solve']
  for key in ('theta','even_gaps','odd_gaps'):assert np.all(np.isfinite(s[key]))
  assert len(s['even_gaps'])==5 and len(s['odd_gaps'])==5
  assert s['tuning_residual']<=1.5e-10 and s['max_eigenvector_residual']<=1e-8
  assert s['max_orthogonality_residual']<=1e-9
  w=s['window_correction'];assert max([w['top_fixed_point_residual'],*w['sublevel_fixed_point_residuals'].values()])<=1e-11
  if r['implementation']=='optimized':assert s['calibration_root_counts']==[1,2] and s['final_root_counts']==[5,5]
  if category=='solve' and r['implementation']=='optimized':
   baseline=next(b for b in rows if b['record']==r['record'].replace('optimized_','baseline_',1))
   assert r['seed']==baseline['seed'] and r['teacher_sha256']==baseline['teacher_sha256'] and r['seed_file_sha256']==baseline['seed_file_sha256']
   for key in ('even_gaps','odd_gaps'):np.testing.assert_allclose(s[key],baseline['solve'][key],rtol=1e-10,atol=1e-9)
assert counts.get('solve')==24,counts
assert counts.get('operator')==30,counts
assert counts.get('setup')==18,counts
assert counts.get('cache')==9,counts
assert counts.get('profile')==2,counts
subprocess.run([sys.executable,'-E',str(R/'tests/validate_l18_fix.py')],check=True)
fresh=json.loads((R/'validation/l18_fix/current_checks.json').read_text())
sys.path.insert(0,str(R/'code'))
from ht3d.hpc import source_hash
assert fresh.get('passed') is True and fresh['source_sha256']==source_hash()
report={'historical_source_snapshot_sha256':SNAPSHOT_MANIFEST_SHA256,
        'fresh_current_checks':fresh,'passed':True,'records':len(rows),'counts':counts,'scope':'historical benchmark provenance plus fresh current-source regression; no new performance claim or L18/L20 full-solve claim'}
(R/'validation/benchmark_audit.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='fresh_current_checks'})
