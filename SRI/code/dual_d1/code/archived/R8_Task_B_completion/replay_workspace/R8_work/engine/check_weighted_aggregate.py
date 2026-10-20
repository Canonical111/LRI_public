from pathlib import Path
from fractions import Fraction as F
import json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parent.parent
folder=ROOT/'aggregate_control';folder.mkdir(exist_ok=True)
inputs=[('n8_f1_b00',F(2)),('n8_f1_b02',F(-3,2))]
sources=[];expected=[F(0)]*7
for name,w in inputs:
 p=ROOT/'scaled_blocks'/name/'stage4.jsonl';d=json.loads((p.parent/'result.json').read_text());sources.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'weight':str(w)})
 vals=[F(d['value'])]+list(map(F,d['dimensionless_negative_inverse_euler']));expected=[a+w*b for a,b in zip(expected,vals)]
spec=folder/'control_spec.json';spec.write_text(json.dumps({'sources':sources},indent=2))
subprocess.run([sys.executable,'aggregate_stage4.py',str(spec),'--buckets','8'],cwd=ROOT/'engine',check=True)
resultroot=folder/'control_spec_work'
subprocess.run([sys.executable,'evaluate_aggregate.py',str(resultroot)],cwd=ROOT/'engine',check=True)
d=json.loads((resultroot/'result.json').read_text());actual=[F(d['value'])]+list(map(F,d['negative']));assert actual==expected,(actual,expected)
report={'exact_weighted_eight_kink_control':True,'blocks':[{'name':n,'weight':str(w)} for n,w in inputs],'values':list(map(str,actual)),'all_seven_functionals_agree':True}
(ROOT/'weighted_aggregate_control.json').write_text(json.dumps(report,indent=2));print('EXACT_WEIGHTED_CONTROL_PASS',report,flush=True)
