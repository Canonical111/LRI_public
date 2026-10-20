"""Validate frozen evidence and reconstruct the computed sectors, not full C7."""
from pathlib import Path
import hashlib,json,subprocess,sys
W=Path(__file__).resolve().parents[1]
manifest=json.load(open(W/'verification/evidence_sha256.json'))
for name,target in manifest.items():
 p=W/name
 if not p.is_file()or hashlib.sha256(p.read_bytes()).hexdigest()!=target:raise SystemExit('Missing or modified evidence: '+name)
old=json.load(open(W/'verification/C7_d2_progress_result.json'))
subprocess.run([sys.executable,str(W/'code/finalize.py')],check=True)
new=json.load(open(W/'verification/C7_d2_progress_result.json'))
keys=['power_free_C7','power_free_sampling_se','coefficients','sampling_errors','covariance','total_samples']
for k in keys:
 if old[k]!=new[k]:raise SystemExit('Reassembly differs: '+k)
if new['full_C7_2']is not None or new['power_correction']is not None:raise SystemExit('Uncomputed full coefficient was populated')
print('All checksums and exact saved-data reassembly passed. Full C7(2) remains unset.')
