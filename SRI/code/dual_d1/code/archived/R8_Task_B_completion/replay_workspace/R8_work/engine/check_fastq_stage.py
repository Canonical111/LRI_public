from pathlib import Path
import time,json
st=time.time()
from install_fastq import install_domain,install_endpoint
install_domain()
import scaled_b as sb
install_endpoint()
import grouped_stage as gs
folder=sb.OUT/'n8_f1_b00'
items=sb.tb.br.rr.load(folder/'stage3.jsonl');out=gs.one_stage(items,4,6)
ref=dict(sb.tb.br.rr.load(folder/'stage4.jsonl'))
assert out==ref,(len(out),len(ref))
value,count,neg=sb.last_two_scaled(list(out.items()),8)
r=json.loads((folder/'result.json').read_text());assert str(value)==r['value'];assert list(map(str,neg))==r['dimensionless_negative_inverse_euler']
data={'status':'exact_complete_eight_kink_fastq_regression_pass','block':folder.name,'stage4_words':len(ref),'boundary':str(value),'negative':list(map(str,neg)),'seconds':time.time()-st}
(sb.ROOT/'fastq_complete_eight_kink_regression.json').write_text(json.dumps(data,indent=2));print('PASS',data,flush=True)
