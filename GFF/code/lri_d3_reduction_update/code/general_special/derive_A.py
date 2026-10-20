import itertools,json,time,random
from pathlib import Path
import sympy as s
import series_engine as se
z=se.z
vs=s.symbols('da db dc dd de')
mons={0:[s.S(1)],1:list(vs),2:[vs[i]*vs[j] for i in range(5) for j in range(i,5)]}
rows={0:[],1:[],2:[]}; vals={0:[],1:[],2:[]}; samples=[]
rng=random.Random(2411);t0=time.time()
while len(rows[2])<15 or len(rows[1])<5 or len(rows[0])<1:
 slope=[s.Integer(rng.choice([-3,-2,-1,1,2,3])) for _ in range(5)]
 plane=rng.choice([0,1,2])
 if plane==0:slope[4]=-slope[0]-slope[1]
 if plane==1:slope[4]=-slope[2]-slope[3]
 if plane==2:slope[4]=-sum(slope[:4])
 a,b,c,d,e=slope
 if e==0 or a+c+e==0 or b+d+e==0:continue
 args=[r+v*z for r,v in zip(se.TARGET_A,slope)]
 subst=dict(zip(vs,slope)); new={}
 for n in [0,1,2]:
  r=[x.subs(subst) for x in mons[n]]
  if s.Matrix(rows[n]+[r]).rank()>len(rows[n]):new[n]=r
 if not new:continue
 aa,bb,cc,dd,ee=args
 if plane==0:j=se.prod([se.beta(aa,bb),se.beta(s.expand(cc+1-bb),s.expand(dd+1-aa))],2)
 elif plane==1:j=se.prod([se.beta(cc,dd),se.beta(s.expand(aa+1-dd),s.expand(bb+1-cc))],2)
 else:j=se.prod([se.beta(bb,dd),se.beta(cc,s.expand(bb+dd+ee-1))],2)
 diff=se.add(j,se.scale(se.pole_A(args),-1))
 assert not any(k<0 and v!=0 for k,v in diff.items()),(slope,plane,diff)
 for n,row in new.items():rows[n].append(row);vals[n].append(diff.get(n,0))
 samples.append({'slopes':list(map(str,slope)),'plane':plane,'regular':{str(k):str(v)for k,v in diff.items() if k<=2}})
 print('sample',len(samples),[len(rows[n]) for n in range(3)],round(time.time()-t0,2),flush=True)
poly={}
for n in [0,1,2]:
 out=s.Matrix(rows[n]).inv()*s.Matrix(vals[n]);poly[n]=s.expand(sum(x*y for x,y in zip(mons[n],out)))
 print('POLY',n,poly[n],flush=True)
Path(__file__).with_name('A_regular.json').write_text(json.dumps({'polynomials':{str(k):str(v)for k,v in poly.items()},'samples':samples},indent=2))
