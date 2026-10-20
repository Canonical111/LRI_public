from pathlib import Path
import sys,json,hashlib
from fractions import Fraction as F
sys.path.insert(0,'/mnt/data/P8_final_run');import period_algebra as pa
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');old=Path('/mnt/data/P8_final_run/old_C7/C7_completion/engine/series')
for name,tag,arg in [('EZ6','Z6',F(8,15)),('EA7','A7',F(16,5))]:
 folder=R/('F4_'+name);inp=folder/(name+'_Gonly.expr')
 if not inp.exists():continue
 basepath=old/(tag+'_base_p0.expr');base=pa.parse_expr(basepath.read_text());base={m:c for m,c in base.items() if not dict(m).get('ell',0)}
 out=pa.parse_expr(inp.read_text());pa.add(out,pa.mul(pa.log(arg),base),F(2));dest=folder/(name+'_full.expr');dest.write_text(pa.dump(out))
 (folder/'offset_restoration.json').write_text(json.dumps({'definition':name+'_full = '+name+'_Gonly + 2 log('+str(arg)+') '+tag+'_finite','Gonly_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'base_sha256':hashlib.sha256(basepath.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'terms':len(out),'rational_projection':str(out.get((),0)),'constant_not_projected':True},indent=2));print('RESTORED',name,len(out),out.get((),0),flush=True)
