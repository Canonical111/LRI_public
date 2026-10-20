"""Acceptance of the direct five-gap check, independent of cutoff faces."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json
root=Path(__file__).resolve().parent.parent;p=root/'direct_Z6_d';manifest=json.loads((p/'manifest.json').read_text());v=F(0);seen=set()
for b in manifest:
 assert b['id'] not in seen;seen.add(b['id']);q=p/b['id'];assert hashlib.sha256((q/'stage1.jsonl').read_bytes()).hexdigest()==b['source_sha256']
 d=json.loads((q/'result.json').read_text());v+=F(d['value'])
arch=json.loads((root/'tail_lower_controls.json').read_text())['archived_base_and_charge_polynomials'];charge=F(arch['Z6_v']['0'][0]);physical=v+charge
boundary=F(json.loads((root/'Task_C_result.json').read_text())['Z6_tail_single_log']);assert physical==boundary
r={'status':'direct_volume_and_cutoff_faces_agree','source_blocks':len(manifest),
'dimensionless_volume_single_log':str(v),'charge_finite_scale_term':str(charge),
'physical_volume_single_log':str(physical),'boundary_single_log':str(boundary),'exact_equal':True}
(root/'direct_Z6_check.json').write_text(json.dumps(r,indent=2));print(r)
