from pathlib import Path
from fractions import Fraction as Q
import time,json,argparse
import task_b as tb

def block(name):
 f=tb.OUT/name;n=int(name.split('_')[0][1:]);dst=f/'negative_replay.json'
 if dst.exists():return json.loads(dst.read_text())
 old=json.loads((f/'result.json').read_text());st=time.time()
 if 'dimensionless_negative_inverse_euler' in old:return old
 items=tb.br.rr.load(f/f'stage{n-4}.jsonl')
 residue,count,neg=tb.last_two(items,n)
 assert residue==Q(old['value']),(name,residue,old['value'])
 d={'status':'complete_replay_of_saved_penultimate_stage','id':name,'value':str(residue),'dimensionless_negative_inverse_euler':list(map(str,neg)),'same_finite_part_exact':True,'seconds':time.time()-st}
 dst.write_text(json.dumps(d,indent=2));tb.br.rr.clear();tb.mt.clear();tb.aword.cache_clear()
 return d

def control6():
 import lower_controls as lc
 vals=[Q(0)]*4
 for face in [1,2,3]:
  mult=1 if face==3 else 2
  rows=json.loads((tb.OUT/f'n6_face{face}_manifest.json').read_text())['blocks']
  for r in rows:
   d=block(r['id']);vals=[x+mult*Q(y) for x,y in zip(vals,d['dimensionless_negative_inverse_euler'])]
 base=lc.raw(6,'Q','base',-1);expected=lc.raw(6,'Q','v',-1);report=[]
 for i,p in enumerate([-2,-1]):
  P=base.get(p,());corr=tb.tp.integrate_exp(P,p)
  for m in [0,1]:
   v=vals[2*i+m]+6*(corr[m] if m<len(corr) else 0)-6*(P[m-1] if m and m-1<len(P) else 0)
   ref=expected[p][m] if m<len(expected[p]) else 0
   assert v==ref,(p,m,v,ref)
   report.append({'power':p,'log':m,'actual':str(v),'reference':str(ref),'exact_equal':True})
 (tb.ROOT/'n6_divergence_control.json').write_text(json.dumps({'status':'exact_complete_control','checks':report},indent=2));print('ALL_N6_DIVERGENCES_PASS',report,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--n6',action='store_true');p.add_argument('--block');a=p.parse_args()
 if a.n6:control6()
 else:print(block(a.block),flush=True)
