#!/usr/bin/env python3
"""A-ORC-13 (real Slurm), second analysis of the J-SMK-4 rchar records: thru_report.py's "own bytes" assumed that the
native reads each staged graph file once; the L8 runs show more. Here, per run: M = the bytes of the pack members the
index stages (sum over its blocks of the distinct graphs' member lengths), K = the bytes of its checkpoint payloads
(native.json read back), T = its task file; a least-squares fit rchar = a + b*M + c*K over the 62 runs, and the
residual non-own bytes a_i = rchar_i - b*M_i - c*K_i compared between the smallest and the largest group by
tasks.sqlite size (within 10% or 2 MB), with fingerprint_bytes kept separately.
  rchar_fit.py PACKAGE RUN RCHAR_DIR OUT.json"""
import glob,json,sys
from pathlib import Path
pkg,run,rd,out=map(Path,sys.argv[1:5]);sys.path.insert(0,str(pkg/'tools'))
import production as prod
import numpy as np
m=json.loads((run/'manifest.json').read_text());inv=json.loads((pkg/'inputs/inventory.json').read_text())
length={(s,int(L),r['id']):int(r['length'])for s in('free','power')for L,rows in inv[s].items()for r in rows}
rows=[]
for f in rd.glob('rchar.*.json'):
    r=json.loads(f.read_text());i=int(r['index']);j=m['jobs'][i];cfg=json.loads((run/'groups'/j['group']/'config.json').read_text());M=0;K=0
    for k in range(j['blocks']):
        c=json.loads((run/'groups'/j['group']/'checkpoints'/f'{prod.block_name(j["shard"],k)}.json').read_text());n=c['native']
        M+=sum(length[(cfg['sector'],cfg['L'],g)]for g in {int(x['graph'])for x in n['rows']});K+=len(json.dumps(n))
    rows.append({'index':i,'group':j['group'],'rchar':r['rchar'],'M':M,'K':K,'T':j['tasks_bytes'],'fp':c['runtime']['fingerprint_bytes']})
A=np.array([[1,x['M'],x['K']]for x in rows],float);y=np.array([x['rchar']-x['T']for x in rows],float)
coef,*_=np.linalg.lstsq(A,y,rcond=None);a,b,cc=(float(v)for v in coef)
for x in rows:x['non_own']=float(x['rchar']-x['T']-b*x['M']-cc*x['K']);x['non_own_without_fp']=x['non_own']-x['fp']
sq={g['name']:(run/'groups'/g['name']/'tasks.sqlite').stat().st_size for g in m['groups']};gs={x['group']for x in rows}
small=min(gs,key=sq.get);large=max(gs,key=sq.get)
def med(g,k):
    v=sorted(x[k]for x in rows if x['group']==g);return v[len(v)//2]
cmp={}
for k in('non_own','non_own_without_fp'):
    s_,l_=med(small,k),med(large,k);d=abs(s_-l_);tol=max(0.10*max(abs(s_),abs(l_)),2*2**20);cmp[k]={'smallest':s_,'largest':l_,'difference':d,'tolerance':tol,'agree':bool(d<=tol)}
doc={'rule':__doc__.split('\n')[0],'fit':{'a_bytes':a,'b_per_member_byte':b,'c_per_payload_byte':cc},'smallest_group':small,'largest_group':large,
     'tasks_sqlite_bytes':[sq[small],sq[large]],'comparison':cmp,'non_own_range':[min(x['non_own']for x in rows),max(x['non_own']for x in rows)],'runs':rows}
out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:v for k,v in doc.items()if k!='runs'},indent=1))
