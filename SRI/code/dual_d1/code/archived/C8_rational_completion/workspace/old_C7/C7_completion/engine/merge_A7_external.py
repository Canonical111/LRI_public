"""External-memory exact sum of penultimate integral blocks."""
from pathlib import Path
import json,subprocess,sys,time,hashlib,itertools,os
from hyperlog_core import K
ROOT=Path(__file__).resolve().parent;LOG=ROOT.parent/'logs';start=time.time()
meta=json.loads((ROOT/'A7_v_external_inputs.json').read_text());assert meta['all_indices_covered_once']
unsorted=ROOT/'A7_stage5_unsorted.tsv';sortedfile=ROOT/'A7_stage5_sorted.tsv';nrows=0;records=[]
with unsorted.open('w') as out:
 for name in meta['files']:
  p=ROOT/name;rows=json.loads(p.read_text());records.append({'file':name,'rows':len(rows),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  for ww,logs,c in rows:
   assert all(not w for w in ww[:-1]);key=json.dumps([ww[-1],sorted(logs)],separators=(',',':'));out.write(key+'\t'+c+'\n');nrows+=1
  print('SERIALIZED',name,len(rows),flush=True)
subprocess.run(['sort','-S','128M','--parallel=2','-t','\t','-k1,1','-o',str(sortedfile),str(unsorted)],check=True,env={**os.environ,'LC_ALL':'C'})
count=zero=groups=0
with sortedfile.open() as inp,(ROOT/'A7_v_stage5.json').open('w') as out:
 out.write('[')
 for key,lines in itertools.groupby(inp,lambda x:x.split('\t',1)[0]):
  co=K.zero
  for line in lines:co+=K.from_expr(line.split('\t',1)[1].strip())
  groups+=1
  if co:
   w,logs=json.loads(key);row=[([[]]*5)+[w],logs,str(co)]
   if count:out.write(',')
   out.write(json.dumps(row));count+=1
  else:zero+=1
  if groups%1000==0:print('GROUP',groups,'nonzero',count,'zero',zero,'seconds',time.time()-start,flush=True)
 out.write(']')
audit={'inputs':records,'input_rows':nrows,'groups':groups,'zero_groups':zero,'output_rows':count,'arithmetic':'exact QQ(e,r,Z2,...,Z6) grouped by full remaining word and scalar logs','seconds':time.time()-start}
(ROOT/'A7_v_external_merge_audit.json').write_text(json.dumps(audit,indent=2));print('MERGED',audit['output_rows'],flush=True)
os.chdir(ROOT);f=open(LOG/'A7_v_final_stage.log','w');os.dup2(f.fileno(),1);os.dup2(f.fileno(),2)
os.execv(sys.executable,[sys.executable,'run_moment.py','7','A','v','--resume','5'])
