"""Reconstruct a certificate from several independent prime-field solutions.

Only a final exact rational residual of zero establishes the certificate.
"""
from pathlib import Path
from fractions import Fraction as Q
from math import isqrt,gcd
from collections import Counter
import argparse,json,time
p=argparse.ArgumentParser();p.add_argument('prefix');p.add_argument('solutions',nargs='+');p.add_argument('--verify',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent;start=time.time()
target=json.loads((root/(a.prefix+'.target.json')).read_text());scale=target['scale']
labels=[json.loads(l) for l in (root/(a.prefix+'.labels.jsonl')).read_text().splitlines()]
mods=[];vectors=[]
for name in a.solutions:
 lines=(root/name).read_text().splitlines();mods.append(int(lines[0]));vectors.append({int(i):int(c) for i,c in (l.split() for l in lines[1:])})
if len(set(mods))!=len(mods):raise ValueError('Repeated prime')
M=1;weights=[]
for q in mods:weights.append((M,pow(M,-1,q)));M*=q
bound=isqrt(M//2)
def rr(x):
 r0,r1=M,x;t0,t1=0,1
 while abs(r1)>bound:
  q=r0//r1;r0,r1=r1,r0-q*r1;t0,t1=t1,t0-q*t1
 if t1 and abs(t1)<=bound and gcd(r1,t1)==1:return Q(r1,t1)
 return None
cert=[];counts=Counter();invscale=pow(scale,-1,M)
for i,source in enumerate(labels):
 x=0
 for q,v,(base,inv) in zip(mods,vectors,weights):x+=base*((v.get(i,0)-x)*inv%q)
 x=x*source['scale']*invscale%M;c=rr(x)
 if c is None:counts['failure']+=1
 elif abs(c.numerator)<10**12 and c.denominator<10**12:counts['small']+=1
 else:counts['large']+=1
 cert.append({'coefficient':str(c) if c is not None else None,'relation':source['relation']})
report={'primes':list(map(str,mods)),'modulus_bits':M.bit_length(),'counts':dict(counts),'seconds':time.time()-start}
print(json.dumps(report,indent=2),flush=True)
if not a.verify:raise SystemExit()
if counts['failure']:raise AssertionError('Rational reconstruction incomplete')
from c6_relations import relation
res=Counter({tuple(w):Q(c) for w,c in target['target']})
for i,r in enumerate(cert):
 c=Q(r['coefficient'])
 if not c:continue
 for w,v in relation(r['relation']).items():res[w]-=c*v
 if i%10000==0:print('EXACT_CHECK',i,'seconds',time.time()-start,flush=True)
res={w:c for w,c in res.items() if c}
if res:raise AssertionError(('Exact residual nonzero',len(res),list(res.items())[:2]))
cert=[r for r in cert if Q(r['coefficient'])]
report.update({'weight':target['weight'],'status':'exact rational identity verified','target':target['target'],'certificate':cert,'target_words':len(target['target']),'exact_residual':0,'seconds':time.time()-start})
(root/'C6_certificate_w5.json').write_text(json.dumps(report,indent=2))
print('EXACT WEIGHT FIVE CERTIFICATE PASSED:',len(cert),'relations',flush=True)
print('max numerator digits',max(len(str(abs(Q(r['coefficient']).numerator))) for r in cert),'denominator digits',max(len(str(Q(r['coefficient']).denominator)) for r in cert),flush=True)
