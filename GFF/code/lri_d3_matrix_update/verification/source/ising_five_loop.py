#!/usr/bin/env python3
"""Five-loop thermal exponent of the one-dimensional long-range Ising theory.

Companion to long_range_ising_C5.tex, September 2026.
Requires Python >= 3.10, NumPy, mpmath, SymPy, and a C++17 compiler with OpenMP.
The companion ising_five_engine.cpp must be next to this file.

Example:
  python ising_five_loop.py --orders 10 14 18 22 --lower-order 24 \
      --output ising_five_loop_results.json

The numerical integration is spectral interpolation followed by exact
meromorphic integration of the interpolation polynomial. This is not a
rigorous error enclosure. Coefficients are checked using the RG pole
identities, two infrared cutoffs, and numerical convergence. The --workdir
contains generated caches; no network access is used.
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import itertools, math, collections, json, pickle, time
from fractions import Fraction

def graphs(n):
    pairs=list(itertools.combinations(range(n),2))
    E=2*n-2
    deg=[0]*n; vals=[0]*len(pairs)
    remaining=[[0]*n for _ in range(len(pairs)+1)]
    for k in range(len(pairs)-1,-1,-1):
        remaining[k]=remaining[k+1].copy()
        i,j=pairs[k];remaining[k][i]+=1;remaining[k][j]+=1
    def rec(k,total):
        if total>E or total+sum(4-v for v in deg)//2<E:return
        if k==len(pairs):
            if total!=E or min(deg)<2:return
            # Every nontrivial cut must have at least two edges for connected 1PI.
            for mask in range(1,1<<(n-1)):
                cross=0
                for v,(i,j) in zip(vals,pairs):
                    if ((mask>>i)^(mask>>j))&1:cross+=v
                if cross<2:return
            denom=math.prod(math.factorial(4-v) for v in deg)*math.prod(math.factorial(v) for v in vals)
            wa=Fraction(24,denom)
            wb=wa*Fraction(sum((4-v)*(3-v) for v in deg),12)
            yield tuple(vals),wa,wb
            return
        i,j=pairs[k]
        for v in range(min(3,4-deg[i],4-deg[j],E-total)+1):
            vals[k]=v;deg[i]+=v;deg[j]+=v
            if all(deg[q]+3*remaining[k+1][q]>=2 for q in range(n)):
                yield from rec(k+1,total+v)
            deg[i]-=v;deg[j]-=v
    return list(rec(0,0))

def sectors(n,gg):
    L=n-1;pairs=list(itertools.combinations(range(n),2))
    out=collections.defaultdict(lambda:[Fraction(0),Fraction(0)])
    masks=tuple(i for i in range(1,1<<L) if i.bit_count()>1)
    maskidx={m:k for k,m in enumerate(masks)}
    for perm in itertools.permutations(range(L)):
        rank=[0]*L
        for r,p in enumerate(perm):rank[p]=r
        edge_masks=[sum(1<<rank[k] for k in range(i,j)) for i,j in pairs]
        mins=[(m & -m).bit_length()-1 for m in edge_masks]
        for vals,wa,wb in gg:
            bm=[0]*(L-1);qm=[0]*len(masks)
            for v,m,r in zip(vals,edge_masks,mins):
                for j in range(r):bm[j]+=v
                if m in maskidx:qm[maskidx[m]]+=v
            key=tuple(bm+qm)
            out[key][0]+=wa;out[key][1]+=wb
    return masks,dict(out)


import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
LD=np.longdouble
import mpmath as mp
import math,itertools,pickle,time,collections,sys
from functools import lru_cache

@lru_cache(None)
def chebpoly(N):
    p=[(1,),( -1,2)]
    for k in range(1,N):
        a=p[-1];b=p[-2]
        c=[0]*(len(a)+1)
        for i,v in enumerate(a): c[i]-=2*v;c[i+1]+=4*v
        for i,v in enumerate(b):c[i]-=v
        p.append(tuple(c))
    return p[:N+1]

@lru_cache(None)
def qweights(N,a2,b2):
    mp.mp.dps=max(80,N*2+30)
    a=mp.mpf(a2)/2;b=mp.mpf(b2)/2
    log=(a2==-2)
    moments=[]
    for poly in chebpoly(N):
        mm=[]
        for r in range(-1 if log else 0,4 if log else 5):
            if r==-1: val=mp.mpf(poly[0])/b
            else:
                val=mp.fsum(mp.mpf(c)*(-b)**r/(mp.mpf(j)+a+1)**(r+1) for j,c in enumerate(poly) if mp.mpf(j)+a+1!=0)
            mm.append(val)
        moments.append(mm)
    out=np.zeros((5,N+1),dtype=LD)
    for i in range(N+1):
        fact=mp.mpf(2)/N * (mp.mpf('.5') if i in (0,N) else 1)
        for r in range(5):
            out[r,i]=LD(str(fact*mp.fsum((mp.mpf('.5') if k in (0,N) else 1)*mp.cos(mp.pi*k*i/N)*moments[k][r] for k in range(N+1))))
    if log:
        out[0,:]=0.;out[0,-1]=LD(str(1/b))
    return out

def tensor_poly(w,maxp):
    D=len(w)
    out=[]
    for k in range(maxp+1):
        arr=np.zeros((w[0].shape[1],)*D,dtype=LD)
        for orders in itertools.product(range(k+1),repeat=D):
            if sum(orders)!=k:continue
            z=1
            for j,o in enumerate(orders):
                shape=[1]*D;shape[j]=-1
                z=z*w[j][o].reshape(shape)
            arr+=z
        out.append(arr.ravel())
    return np.array(out)

def setup_logs(n,masks,N):
    D=n-2
    nodes=(1+np.cos(np.arccos(LD(-1))*np.arange(N+1,dtype=LD)/N))/2
    nodes[0]=1.;nodes[-1]=0.
    coords=np.meshgrid(*([nodes]*D),indexing='ij')
    logs=[]
    for mask in masks:
        ranks=[i for i in range(n-1) if mask&(1<<i)]
        q=np.ones_like(coords[0])
        for r in ranks[1:]:
            term=np.ones_like(q)
            for j in range(ranks[0],r):term*=coords[j]
            q+=term
        logs.append(np.log(q).ravel())
    logs=np.array(logs)
    logH=logs[masks.index((1<<(n-1))-1)]
    return logs,logH

def integrate(n,N,cutoff="span"):
    """Return the Laurent coefficients needed at four loops."""
    L=n-1;D=n-2
    masks,sec=SECTOR_CACHE[n]
    if n==2:return ({-1:3.},{-1:1.})
    t0=time.time();groups=collections.defaultdict(list)
    for key,wab in sec.items():groups[key[:D]].append((key[D:],[LD(v.numerator)/LD(v.denominator) for v in wab]))
    logs,logH=setup_logs(n,masks,N)
    ans=np.zeros((2,5),dtype=LD) # powers -L..(3-L)
    for ig,(b2,entries) in enumerate(groups.items()):
        a2=tuple(2*(L-2-j)-v for j,v in enumerate(b2))
        p=a2.count(-2); maxp=5-L+p
        w=[qweights(N,a,b) for a,b in zip(a2,b2)]
        tensors=tensor_poly(w,maxp)
        qq=np.array([r[0] for r in entries],dtype=LD)
        wab=np.array([r[1] for r in entries],dtype=LD)
        for start in range(0,len(entries),64):
            end=min(start+64,len(entries))
            logM=.5*(qq[start:end]@logs)
            base=np.exp(-logM)
            K=logM-(L*logH[None,:] if cutoff=="span" else 0)
            powers=[base]
            for k in range(1,maxp+1):powers.append(powers[-1]*K/k)
            for k in range(maxp+1):
                integral=np.zeros(end-start,dtype=LD)
                for j in range(k+1):
                    integral+=powers[j]@tensors[k-j]
                expo=k-p-1
                ans[:,expo+L]+=(wab[start:end].T@integral)/L
        if n>=5 and (ig+1)%10==0:print('group',ig+1,'/',len(groups),'time',time.time()-t0,flush=True)
    print('INTEGRATED',n,N,'time',time.time()-t0, 'A',ans[0], 'B',ans[1],flush=True)
    res=({k-L:ans[0,k] for k in range(5)}, {k-L:ans[1,k] for k in range(5)})

    return res


import sympy as s,pickle,sys
from pathlib import Path
e,g=s.symbols('e g')

def K(p):
    p=s.expand(p)
    return s.Add(*[term for term in p.as_ordered_terms() if term.as_powers_dict().get(e,0)<0])

def laurent(vals):return s.Add(*[s.Float(float(v),17)*e**k for k,v in vals.items()])


@lru_cache(None)
def cpp_weights(N,a2,b2):
 mp.mp.dps=max(70,2*N+30)
 a=mp.mpf(int(a2))/2;b=mp.mpf(int(b2))/2
 jr=int(-a-1) if a2<=-2 and a2%2==0 else -1
 pol=chebpoly(N);mom=[]
 for poly in pol:
  mm=[]
  for r in (-1,0,1,2,3):
   if r==-1:
    val=mp.mpf(poly[jr])/b if 0<=jr<len(poly) else mp.mpf(0)
   else:val=mp.fsum(mp.mpf(c)*(-b)**r/(mp.mpf(j)+a+1)**(r+1) for j,c in enumerate(poly) if j!=jr)
   mm.append(val)
  mom.append(mm)
 out=np.zeros((5,N+1))
 for i in range(N+1):
  fac=mp.mpf(2)/N*(mp.mpf('.5') if i in (0,N) else 1)
  for r in range(5):
   out[r,i]=float(fac*mp.fsum((mp.mpf('.5') if k in (0,N) else 1)*mp.cos(mp.pi*k*i/N)*mom[k][r] for k in range(N+1)))
 if jr==0:out[0,:]=0.;out[0,-1]=float(1/b)
 return out

def derive(amplitudes,maxL=5):
 AA={1:3/e};BB={1:1/e}
 for L in range(2,maxL+1):
  a,b=amplitudes[L];AA[L]=laurent(a);BB[L]=laurent(b)
 # Formal power series multiplication in g, retaining Laurent polynomials in e.
 def conv(a,b,n):
  out=[s.S(0)]*(n+1)
  for i in range(min(len(a),n+1)):
   for j in range(min(len(b),n+1-i)):
    out[i+j]+=a[i]*b[j]
  return [s.expand(v) for v in out]
 GG=[s.S(0),s.S(1)]+[s.S(0)]*maxL
 for n in range(2,maxL+2):
  pw=GG[:];v=s.S(0)
  for L in range(1,min(maxL,n-1)+1):
   pw=conv(pw,GG,n);v+=(-1)**L*AA[L]*pw[n]
  GG[n]=-K(v)
 G={i:GG[i] for i in range(1,maxL+2)}
 H=[s.S(1)]+[s.S(0)]*maxL
 pw=[s.S(1)]+[s.S(0)]*maxL
 for L in range(1,maxL+1):
  pw=conv(pw,GG,maxL)
  for i in range(maxL+1):H[i]+=(-1)**L*BB[L]*pw[i]
 Z={0:s.S(1)}
 for n in range(1,maxL+1):Z[n]=-K(sum(H[n-i]*Z[i] for i in range(n)))
 beta=[];gamma=[]
 for L in range(1,maxL+1):
  bv=L*s.expand(G[L+1]).coeff(e,-1);cv=L*s.expand(Z[L]).coeff(e,-1)
  beta.append(float(bv));gamma.append(float(cv))
  print('LOOP',L,'beta',bv,'gamma',cv,flush=True)
 b=s.symbols('b1:'+str(maxL+1));c=s.symbols('c1:'+str(maxL+1))
 # Lagrange-Buermann: [eps^n] gamma(g*) = [g^(n-1)] gamma'(g) B(g)^(-n)/n.
 B=sum(b[i]*g**i for i in range(maxL));der=sum((i+1)*c[i]*g**i for i in range(maxL))
 co=[];form=[];sub=dict(zip(b,beta))|dict(zip(c,gamma))
 for n in range(1,maxL+1):
  se=s.series(B**(-n),g,0,n).removeO();cof=s.expand(der*se).coeff(g,n-1)/n
  if n==1:cof-=s.Rational(1,2)
  form.append(s.factor(cof));co.append(float(cof.subs(sub)))
 print('DIMENSION',co,flush=True)
 be=[0,-e]+[s.Float(v,17) for v in beta];ga=[0]+[s.Float(v,17) for v in gamma]
 ze=[Z[i] for i in range(maxL+1)]
 dg=[i*GG[i] for i in range(1,len(GG))];dz=[i*ze[i] for i in range(1,len(ze))]
 rg=[s.expand(x+e*GG[i]) for i,x in enumerate(conv(be,dg,maxL+1))]
 rz=[s.expand(x+y) for x,y in zip(conv(be,dz,maxL),conv(ga,ze,maxL))]
 def norm(a):
  return max(abs(float(t.as_coeff_Mul()[0])) for v in a for t in s.expand(v).as_ordered_terms())
 checks={'coupling_pole_residual':norm(rg),'mass_pole_residual':norm(rz)}
 print('CHECKS',checks,flush=True)
 return dict(beta=beta,gamma=gamma,dimension_coefficients=co,checks=checks,
             G={str(i):str(v) for i,v in G.items()},Z={str(i):str(v) for i,v in Z.items()},
             formula_C5=str(form[-1]))



def prepare_graph_data(workdir: Path) -> None:
    graph_file = workdir / "graphs6.bin"
    if graph_file.exists():
        expected = 59145 * 17 * 4
        if graph_file.stat().st_size != expected:
            raise ValueError(f"Unexpected graph cache size: {graph_file}")
        return
    gg = graphs(6)
    if len(gg) != 59145:
        raise AssertionError(f"Unexpected ordered-label graph count: {len(gg)}")
    scale = math.lcm(*(v.denominator for _, a, b in gg for v in (a, b)))
    if scale != 144:
        raise AssertionError(f"Unexpected weight denominator: {scale}")
    data = np.asarray([list(m) + [int(144*a), int(144*b)] for m, a, b in gg], dtype="<i4")
    data.tofile(graph_file)
    print(f"Enumerated {len(gg)} five-loop graphs.", flush=True)


def prepare_weights(workdir: Path, N: int) -> None:
    path = workdir / f"qweights5_{N}.bin"
    expected = 4 * 11 * 5 * (N + 1) * 8
    if path.exists() and path.stat().st_size == expected:
        return
    # Unused exponent combinations cost little and avoid enumerating millions
    # of sectors merely to learn the small set of possible exponents.
    wt = np.zeros((4, 11, 5, N + 1), dtype="<f8")
    for j in range(4):
        for b in range(11):
            wt[j, b] = cpp_weights(N, 2*(3-j)-b, b)
    wt.tofile(path)


def main() -> None:
    import argparse
    import shutil
    import subprocess
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--orders", type=int, nargs="+", default=[18])
    parser.add_argument("--lower-order", type=int, default=24)
    parser.add_argument("--threads", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--compiler", default="g++")
    parser.add_argument("--workdir", type=Path, default=Path(".ising_five_cache"))
    parser.add_argument("--output", type=Path, default=Path("ising_five_loop_results.json"))
    parser.add_argument("--force", action="store_true", help="Recompute cached amplitude files.")
    args = parser.parse_args()
    if any(n < 4 or n > 28 for n in args.orders):
        parser.error("Use five-loop interpolation degrees from 4 through 28.")
    if not 8 <= args.lower_order <= 64:
        parser.error("Use a lower-loop degree from 8 through 64.")
    if args.threads < 1:
        parser.error("The thread count must be positive.")
    compiler = shutil.which(args.compiler)
    if compiler is None:
        parser.error(f"Compiler not found: {args.compiler}")
    source = Path(__file__).resolve().with_name("ising_five_engine.cpp")
    if not source.is_file():
        parser.error(f"Missing companion C++ source: {source}")
    workdir = args.workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    executable = workdir / "ising_five_engine"
    if not executable.exists() or executable.stat().st_mtime < source.stat().st_mtime:
        subprocess.run([compiler, "-O3", "-march=native", "-std=c++17", "-fopenmp", str(source), "-o", str(executable)], check=True)
    prepare_graph_data(workdir)

    global SECTOR_CACHE
    SECTOR_CACHE = {}
    lowers = {}
    for cutoff in ("span", "maxgap"):
        path = workdir / f"lower5_{cutoff}_{args.lower_order}_extended.json"
        if args.force or not path.is_file():
            if not SECTOR_CACHE:
                for n in range(3, 6):
                    SECTOR_CACHE[n] = sectors(n, graphs(n))
            data = {L: integrate(L+1, args.lower_order, cutoff) for L in range(2, 5)}
            data = {L: [{k: float(v) for k, v in d.items()} for d in pair] for L, pair in data.items()}
            path.write_text(json.dumps(data, indent=2) + "\n")
        raw = json.loads(path.read_text())
        lowers[cutoff] = {int(L): [{int(k): float(v) for k, v in d.items()} for d in pair] for L, pair in raw.items()}

    results = []
    for N in args.orders:
        prepare_weights(workdir, N)
        files = {cut: workdir / f"amplitude5_{cut}_{N}.json" for cut in ("span", "maxgap")}
        if args.force or any(not p.is_file() for p in files.values()):
            subprocess.run([str(executable), str(N), str(workdir), str(args.threads)], check=True)
        order_results = []
        for cutoff, path in files.items():
            hi = json.loads(path.read_text())
            amplitudes = dict(lowers[cutoff])
            amplitudes[5] = [{int(k): float(v) for k, v in hi[ab].items()} for ab in ("A", "B")]
            result = derive(amplitudes)
            result.update(cutoff=cutoff, N=N, lower_N=args.lower_order, lower_precision="numpy.longdouble", amplitudes=amplitudes)
            result["D5"] = 3*result["gamma"][4] - result["beta"][4]
            result["five_loop_contribution"] = result["D5"]/729
            result["lower_loop_contribution"] = result["dimension_coefficients"][4] - result["five_loop_contribution"]
            result["checks"]["C4_error"] = result["dimension_coefficients"][3] - 45.42488010355675540615
            order_results.append(result)
        difference = abs(order_results[0]["dimension_coefficients"][4] - order_results[1]["dimension_coefficients"][4])
        for result in order_results:
            result["checks"]["C5_cutoff_difference"] = difference
        results.extend(order_results)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Saved {args.output.resolve()}")


if __name__ == "__main__":
    main()
