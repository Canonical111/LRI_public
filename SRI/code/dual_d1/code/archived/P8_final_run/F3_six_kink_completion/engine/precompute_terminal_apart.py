"""Canonical rational partial fractions of all repeated terminal prefactors.
Equality is checked in the exact coefficient field for every prefactor.
"""
from full_runner import *
from fractions import Fraction as F
folder=Path(sys.argv[1]);src=folder/'prefactors.json';dst=folder/'prefactor_apart.json'
if dst.exists():
 r0=json.loads((folder/'prefactor_apart_report.json').read_text());assert r0['input_sha256']==hashlib.sha256(src.read_bytes()).hexdigest();print('APART_REUSED');sys.exit(0)
ps=json.loads(src.read_text());out=[];st=time.time()
def split_constant(c):
 assert all(not any(mon) for mon in c.denom),c
 den=F(str(c.denom[(0,)*len(K.ring.gens)]))
 out={}
 for mon,cf in c.numer.items():
  assert not any(mon[:8]),(c,mon)
  zm=(mon[8]+2*mon[10]+3*mon[12],mon[9],mon[11],0)
  v=F(str(cf))/den*F(2,5)**mon[10]*F(8,35)**mon[12]
  out[zm]=out.get(zm,F(0))+v
 return [(z,c) for z,c in out.items() if c]

for i,ct in enumerate(ps):
 val=rm.parseK(ct);pp,po=apart(val,6);row=[];rebuilt=K.zero
 for p,c in pp.items():
  for zz,cc in split_constant(c):row.append(['poly',0,p,zz,str(cc)])
  rebuilt+=c*GEN[6]**p
 for (a,p),c in po.items():
  aa=F(str(a))
  for zz,cc in split_constant(c):row.append(['pole',str(aa),p,zz,str(cc)])
  rebuilt+=c/(GEN[6]-a)**p
 assert not val-rebuilt,(i,ct)
 out.append(row)
 if i%2000==0:print('APART',i,len(ps),time.time()-st,flush=True)
 if i%200==0:clear()
dst.write_text(json.dumps(out,separators=(',',':')))
(folder/'prefactor_apart_report.json').write_text(json.dumps({'prefactors':len(ps),'all_exact_reconstruction_checks':True,'input_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'seconds':time.time()-st},indent=2))
print('APART_COMPLETE',len(ps),time.time()-st,flush=True)
