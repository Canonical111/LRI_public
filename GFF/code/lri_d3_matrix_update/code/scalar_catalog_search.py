import itertools,json,time,sys
import mpmath as mp
mp.mp.dps=85
q=mp.mpf;p=mp.pi;g=mp.gamma(q(1)/4)
raw=json.load(open(str(__import__('pathlib').Path(__file__).resolve().parents[1]/'verification/fresh100_input.json')))
def real(s):return mp.mpf(s[1:].split(' + ')[0])
Q=real(raw['Q3']);G=g**10/p**q('3.5')
K=58;N=180
# Exact quarter parameters cache Bernoulli coefficients and Γ values.
parameters=[q(i)/8 for i in range(1,17)]
lcache={a:[q(0)]+[(-1)**(k+1)*mp.bernpoly(k+1,a)/(k*(k+1)) for k in range(1,K+1)] for a in parameters}
gcache={a:mp.gamma(a) for a in parameters};zc={}
def hv(A,B):
 BB=tuple(B)+(q(1),);dec=sum(BB)-sum(A)
 log=[q(0)]+[sum(lcache[a][k] for a in A)-sum(lcache[b][k] for b in BB) for k in range(1,K+1)]
 c=[q(1)]
 for j in range(1,K+1):c.append(sum(h*log[h]*c[j-h] for h in range(1,j+1))/j)
 h=mp.fprod(gcache[a] for a in A)/mp.fprod(gcache[b] for b in BB);pref=1/h;s=q(0)
 for n in range(N):
  s+=h
  h*=mp.fprod(n+a for a in A)/mp.fprod(n+b for b in BB)
 if dec not in zc:zc[dec]=[mp.zeta(dec+j,N) for j in range(K+1)]
 return pref*(s+sum(c[j]*zc[dec][j] for j in range(K+1)))
records=[];counter=0;start=time.time()
H=(Q+G/48)/(4*p*p)
Gt=G/p**2
targets=[('H3',H)]
upper=[q(i)/8 for i in range(1,9)];lower=[q(i)/4 for i in range(2,7)]
for r in [3,4]:
 for A in itertools.combinations_with_replacement(upper,r):
  for B in itertools.combinations_with_replacement(lower,r-1):
   excess=sum(B)-sum(A)
   if excess<=0 or any(a in B for a in A):continue
   val=hv(A,B);counter+=1
   for name,target in targets:
    rel=mp.pslq(mp.matrix([target,1,Gt,val]),tol=q('1e-57'),maxcoeff=10**6,maxsteps=800)
    if rel is not None and rel[0] != 0:
     rec={'r':r,'A':[str(x) for x in A],'B':[str(x) for x in B],'normalization':name,'relation':rel,'H':mp.nstr(val,90)}
     records.append(rec);print('MATCH',rec,flush=True)
   if counter%100==0:print('count',counter,'seconds',time.time()-start,flush=True)
print('DONE',counter,'matches',len(records),'seconds',time.time()-start,flush=True)
json.dump({'count':counter,'precision':85,'tolerance':'1e-57','maxcoeff':10**6,'matches':records,'timing':time.time()-start},open(str(__import__('pathlib').Path(__file__).resolve().parents[1]/'verification/scalar_catalog_search.json'),'w'),indent=2)
