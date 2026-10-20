import task_b as tb
from pathlib import Path
import json,time,subprocess,os
from fractions import Fraction as F
st=time.time()
for face in [1,2,3]:tb.sources(6,face)
rows=[]
for face in [1,2,3]:rows+=json.loads((tb.OUT/f'n6_face{face}_manifest.json').read_text())['blocks']
for row in rows:
 log=(tb.ROOT/f"control_{row['id']}.log").open('w')
 subprocess.run(['python','-u',str(Path(__file__).with_name('task_b.py')),'--block',row['id']],check=True,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
 vals={}
 for f in [1,2,3]:
  rs=[r for r in rows if r['face']==f]
  if all((tb.OUT/r['id']/'result.json').exists() for r in rs):
   vals[f]=str(sum((F(json.loads((tb.OUT/r['id']/'result.json').read_text())['value']) for r in rs),F(0)))
 print('CONTROL_COMPLETE',row['id'],vals,time.time()-st,flush=True)
vals={f:sum((F(json.loads((tb.OUT/r['id']/'result.json').read_text())['value']) for r in rows if r['face']==f),F(0)) for f in [1,2,3]}
expected={1:F(2729,3),2:F(13717,12),3:F(2069,2)}
assert vals==expected,(vals,expected)
d={'status':'exact_complete_n6_control','face_values':{str(k):str(v) for k,v in vals.items()},'residue':str(-2*vals[1]-2*vals[2]-vals[3]),'expected':'-5140','all_equal':True,'seconds':time.time()-st}
(tb.ROOT/'n6_control.json').write_text(json.dumps(d,indent=2));print(d,flush=True)
