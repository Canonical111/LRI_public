
"""Fresh full-constant evaluation of saved exact period expressions. No fitted basis."""
from pathlib import Path
import ast,re,json,hashlib,time,argparse
import mpmath as mp
from functools import lru_cache
from evaluate_periods_decimal import evaluate
def terms(text):
 depth=0;start=0
 for i,c in enumerate(text):
  if c in '([':depth+=1
  elif c in ')]':depth-=1
  elif c in '+-' and depth==0 and i and text[i-1].isspace():
   if text[start:i].strip():yield text[start:i].strip()
   start=i
 if text[start:].strip():yield text[start:].strip()
def value(text,tab):
 @lru_cache(None)
 def fun(name,args):
  if name=='log':return mp.log(*args)
  if name=='polylog':return mp.polylog(*args)
  if name=='zeta':return mp.zeta(*args)
  if name=='Rational':return args[0]/args[1]
  raise ValueError(name)
 def ev(x):
  if isinstance(x,ast.Constant):return mp.mpf(x.value)
  if isinstance(x,ast.Name):
   nm=x.id
   if nm=='pi':return mp.pi
   if nm.startswith('Z') and nm[1:].isdigit():return mp.zeta(int(nm[1:]))
   if nm.startswith('R_'):return tab[nm]
   raise ValueError(nm)
  if isinstance(x,ast.UnaryOp):return -ev(x.operand) if isinstance(x.op,ast.USub) else ev(x.operand)
  if isinstance(x,ast.BinOp):
   a,b=ev(x.left),ev(x.right)
   if isinstance(x.op,ast.Add):return a+b
   if isinstance(x.op,ast.Sub):return a-b
   if isinstance(x.op,ast.Mult):return a*b
   if isinstance(x.op,ast.Div):return a/b
   if isinstance(x.op,ast.Pow):return a**b
  if isinstance(x,ast.Call):return fun(x.func.id,tuple(ev(a) for a in x.args))
  raise ValueError(ast.dump(x))
 return mp.fsum(ev(ast.parse(term,mode='eval').body) for term in terms(text))
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--out',required=True)
 p.add_argument('--dps',type=int,default=60);p.add_argument('--radius',type=int,default=90);p.add_argument('--taylor',type=int,default=220);p.add_argument('--asymptotic',type=int,default=140);p.add_argument('--step',default='.3')
 p.add_argument('--backend',choices=['decimal','gmp'],default='gmp')
 a=p.parse_args();start=time.time();mp.mp.dps=a.dps
 evaluator=evaluate
 if a.backend=='gmp':
  from evaluate_periods_gmp import evaluate as evaluator
 paths=json.loads(Path(a.manifest).read_text());texts={k:Path(f).read_text() for k,f in paths.items()}
 sy=set().union(*(set(re.findall(r'\bR_[A-Za-z0-9_]+',v)) for v in texts.values()))
 ws={s:tuple(int(t[1:]) if t.startswith('m') else int(t) for t in s.split('_')[1:]) for s in sy}
 assert all(w[-1]!=0 for w in ws.values()),"trailing-zero periods require shuffle reduction"
 print('FRESH_PERIODS',len(ws),max(map(len,ws.values())),flush=True)
 vals=evaluator(set(ws.values()),dps=a.dps,R=a.radius,ntaylor=a.taylor,nasym=a.asymptotic,stepfrac=a.step)
 table={sym:mp.mpf(str(vals[w])) for sym,w in ws.items()}
 out={}
 for key,text in texts.items():
  v=value(text,table);out[key]=mp.nstr(v,a.dps-10);print(key,out[key],flush=True)
 result={'settings':vars(a),'values':out,'period_count':len(vals),'seconds':time.time()-start,'interval_certified':False,
 'input_sha256':{key:hashlib.sha256(text.encode()).hexdigest() for key,text in texts.items()},'no_old_period_table_used':True}
 Path(a.out).write_text(json.dumps(result,indent=2))
 Path(a.out).with_suffix('.periods.json').write_text(json.dumps({','.join(map(str,w)):str(v) for w,v in vals.items()}))
if __name__=='__main__':main()
