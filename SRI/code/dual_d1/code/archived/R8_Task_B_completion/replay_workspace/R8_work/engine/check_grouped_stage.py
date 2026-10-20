import json,time,hashlib
import scaled_b as sb
import grouped_stage as gs
from hyperlog_core import *
st=time.time();name='n8_f1_b03';folder=sb.OUT/name
items=sb.tb.br.rr.load(folder/'stage3.jsonl')
out=gs.one_stage(items,4,6)
reference=dict(sb.tb.br.rr.load(folder/'stage4.jsonl'))
assert set(out)==set(reference),(len(out),len(reference))
for key,v in out.items():assert v==reference[key],key
report={'status':'complete_eight_kink_grouped_stage_verified','block':name,'stage':4,'input_sha256':hashlib.sha256((folder/'stage3.jsonl').read_bytes()).hexdigest(),'reference_sha256':hashlib.sha256((folder/'stage4.jsonl').read_bytes()).hexdigest(),'input_rows':len(items),'output_rows':len(out),'all_rational_coefficients_equal':True,'seconds':time.time()-st}
(sb.ROOT/'grouped_stage_check.json').write_text(json.dumps(report,indent=2));print('ALL_PASS',report,flush=True)
