from pathlib import Path
from fractions import Fraction as F
import json,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parent.parent;folder=ROOT/'aggregate_control'
source=folder/'control_spec.json';spec=folder/'parallel_control_spec.json';spec.write_bytes(source.read_bytes())
subprocess.run([sys.executable,'aggregate_stage4_parallel.py',str(spec),'--buckets','8','--workers','2'],cwd=ROOT/'engine',check=True)
work=folder/'parallel_control_spec_work';old=folder/'control_spec_work'
assert (work/'combined_stage4.jsonl').read_bytes()==(old/'combined_stage4.jsonl').read_bytes()
subprocess.run([sys.executable,'evaluate_aggregate_parallel.py',str(work),'--rows','500','--workers','2'],cwd=ROOT/'engine',check=True)
r=json.loads((work/'result_parallel.json').read_text());ref=json.loads((old/'result.json').read_text());assert F(r['value'])==F(ref['value']) and list(map(F,r['negative']))==list(map(F,ref['negative']))
d={'exact_parallel_linear_sum_matches_serial':True,'source_coefficients_byte_identical':True,'all_seven_functionals_agree':True,'workers':2,'chunk_rows':500,'value':r['value'],'negative':r['negative']};(ROOT/'parallel_aggregate_control.json').write_text(json.dumps(d,indent=2));print('PARALLEL_CONTROL_PASS',json.dumps(d),flush=True)
