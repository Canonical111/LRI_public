"""Independent mpmath re-implementation of reference/src sampler+integrand (d=3), fed with the
ARCHIVED nets/seeds/tasks, compared with archived rows. No C++ needed.

Public edition (2026-10-13): the code review's script (LRI_C7_D3_HPC_review/evidence/indep_rows.py, 2026-09-30) with
one change: the reference folder is C7_REFERENCE (default: reference/ of this package) instead of a fixed local path.
It needs reference/inputs/{free,power} (make -f public.mk setup) and reference/records (hosted; make -f public.mk
fetch-data). The review checked 13 rows across L3-L7 and both sectors; that row list was not archived.
Usage, from the package folder:
  python3 public/indep_rows.py '[["production_a","power",3,0,0],["production_b","free",4,0,5]]'
Each item is (campaign tag, sector, L, block, uid); it prints max |new-old|/max(1,|old|) per row."""
import json,os,struct,sys
from pathlib import Path
import mpmath as mp
mp.mp.dps=40
R=Path(os.environ.get('C7_REFERENCE',str(Path(__file__).resolve().parents[1]/'reference')))
M64=(1<<64)-1
class MT64:
    def __init__(s,seed):
        s.mt=[0]*312;s.mt[0]=seed&M64
        for i in range(1,312):s.mt[i]=(6364136223846793005*(s.mt[i-1]^(s.mt[i-1]>>62))+i)&M64
        s.i=312
    def __call__(s):
        if s.i>=312:
            for k in range(312):
                y=(s.mt[k]&0xFFFFFFFF80000000)|(s.mt[(k+1)%312]&0x7FFFFFFF)
                s.mt[k]=s.mt[(k+156)%312]^(y>>1)^(0xB5026F5AA96619E9 if y&1 else 0)
            s.i=0
        y=s.mt[s.i];s.i+=1
        y^=(y>>29)&0x5555555555555555;y^=(y<<17)&0x71D67FFFEDA60000;y^=(y<<37)&0xFFF7EEE000000000;y^=y>>43
        return y&M64
def ldval(x):  # nearest x87 long double (64-bit mantissa) to decimal string x
    v=mp.mpf(x)
    if v==0:return v
    e=int(mp.floor(mp.log(abs(v),2)))
    return mp.mpf(int(mp.nint(v*mp.mpf(2)**(63-e))))*mp.mpf(2)**(e-63)
def load_graph(p,scale):
    t=p.read_text().split();L=int(t[1]);gid=int(t[2]);wa=ldval(t[3]);wb=ldval(t[4]);M=int(t[5]);T=int(t[6]);i=7;E=2*L
    masks=[int(x)for x in t[i:i+M]];i+=M;terms=[]
    for _ in range(T):
        n=int(t[i]);i+=1;ids=[int(x)for x in t[i:i+n]];i+=n;co=[int(x)for x in t[i:i+E]];i+=E;terms.append((ids,co))
    n=int(t[i]);i+=1;alpha=[mp.mpf(x)*scale for x in t[i:i+n]]
    sz=1<<E;dp=[mp.mpf(0)]*sz;ct=[mp.mpf(0)]*sz;dp[0]=mp.mpf(1)
    for s in range(1,sz):
        sm=mp.fsum(dp[s^(1<<j)] for j in range(E) if s>>j&1);ct[s]=sm;dp[s]=sm/(1 if s==sz-1 else alpha[s])
    return dict(L=L,id=gid,wa=wa,wb=wb,masks=masks,terms=terms,alpha=alpha,dp=dp,ct=ct,Z=dp[-1],E=E)
def gamma(L):
    for line in (R/'inputs/gamma_d3_7.txt').read_text().splitlines():
        t=line.split()
        if int(t[0])==7-L:return ldval(t[1]),[mp.mpf(x)for x in t[2:]]
def sample(g,uu,K,logs):
    E=g['E'];S=(1<<E)-1;fac=mp.mpf(0);order=[];lt=[]
    for pos in range(E):
        u=uu[2*pos]*g['ct'][S];pick=-1
        for j in range(E):
            if S>>j&1:
                u-=g['dp'][S^(1<<j)]
                if u<=0:pick=j;break
        if pick<0:pick=S.bit_length()-1
        order.append(pick);S^=1<<pick
        if S:
            l=mp.log(uu[2*pos+1])/g['alpha'][S];lt.append(l);fac+=(mp.mpf(3)*bin(S).count('1')/4-g['alpha'][S])*l
    lx=[None]*E;cur=mp.mpf(0)
    for j in range(E):
        lx[order[j]]=cur
        if j<E-1:cur+=lt[j]
    x=[mp.exp(v)for v in lx];Ssum=mp.fsum(x)
    mon=[mp.exp(mp.fsum(lx[j] for j in range(E) if m>>j&1)) for m in g['masks']]
    val=mp.fsum(mp.fsum(c*x[j] for j,c in enumerate(co) if c)/mp.fsum(mon[i] for i in ids)**mp.mpf(1.5) for ids,co in g['terms'])
    y=val/Ssum*mp.exp(fac)*g['Z']            # d=3: U^(-3/2), measure x^(3/4) per edge in log variables
    out=[mp.mpf(1)]+[mp.mpf(0)]*K
    if K:
        z=mp.fsum(lx)/4-mp.mpf(g['L'])/2*mp.log(Ssum)
        for n in range(1,K+1):out[n]=mp.fsum(j*(logs[j]+(z if j==1 else 0))*out[n-j] for j in range(1,n+1))/n
    return [o*y for o in out]
def replay_row(tag,sector,L,block,uid):
    cfg=json.load(open(R/f'records/{tag}/config.json'));seed=cfg['seed']+(348612 if sector=='power' else 0)
    rec=json.load(open(R/f'records/{tag}/{sector}_L{L}_block{block:04d}.json'));row=rec['rows'][uid] if rec['rows'][uid]['uid']==uid else next(r for r in rec['rows'] if r['uid']==uid)
    scale=ldval(str(cfg['rate']));g=load_graph(R/f'inputs/{sector}/L{L}/G{row["graph"]}.txt',scale);norm,logs=gamma(L);K=7-L
    raw=(R/f'records/{tag}/{sector}_L{L}.net').read_bytes();B,dim,bits=struct.unpack('<III',raw[:12]);rep=row['rep']
    off=12+rep*dim*bits*8;dirs=struct.unpack(f'<{dim*bits}Q',raw[off:off+dim*bits*8])
    rng=MT64((seed+0x9e3779b97f4a7c15*(rep+1)+0xbf58476d1ce4e5b9*(g['id']+1))&M64);state=[rng()>>(64-bits) for _ in range(dim)]
    acc=[mp.mpf(0)]*(K+1);n=row['total']
    for i in range(row['begin'],row['end']):
        if i>row['begin']:
            k=(i&-i).bit_length()-1
            for j in range(dim):state[j]^=dirs[j*bits+k]
        uu=[(mp.mpf(s)+mp.mpf(0.5))/mp.mpf(2)**bits for s in state]
        v=sample(g,uu,K,logs)
        for j in range(K+1):acc[j]+=v[j]/n
    new=[norm*g['wa']*a for a in acc]+[norm*g['wb']*a for a in acc]
    old=[mp.mpf(v) for v in row['values']]
    err=max(abs(a-b)/max(1,abs(b)) for a,b in zip(new,old))
    print(tag,sector,f'L{L}',f"graph={row['graph']} rep={rep} n={n} quad={row['quad']} mp={row['mp']}",'max |new-old|/max(1,|old|) =',mp.nstr(err,3),flush=True)
    return err
if __name__=='__main__':
    for args in json.loads(sys.argv[1]):replay_row(*args)
