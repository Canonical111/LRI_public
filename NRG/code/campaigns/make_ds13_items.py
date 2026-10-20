"""13-point Δσ campaign for the spin-boson NRG, matched to the phi4 HT Δσ table (d=1: s = 1 - 2Δσ).

Every point: base keep=64, nb=10, Λ=3, plus convergence scans
  keep ∈ {48, 64, 96, 128} (nb=10, Λ=3); nb ∈ {8, 12, 16} (keep=64, Λ=3);
  Λ ∈ {2, 4} (keep=64, nb=10); corner keep=128, nb=16, Λ=3.
Endpoint extras: Δσ ≥ 0.2 (s → 1/2, near-Gaussian, boson truncation hardest): nb ∈ {20, 24} at keep=64;
  Δσ ≤ 0.05 (s → 1, slow flows, dense low spectrum): keep ∈ {160, 192} at nb=10.
nsites at Λ=3 follows the original study (65 for s ≤ 0.8, 80 at s = 0.9, 105 at s = 0.98),
i.e. about the depth a 5e-14 bisection keeps critical (n ≈ ln(1/5e-14)/(y_t ln Λ));
other Λ keep the same infrared depth: N(Λ) = N(3)·ln3/lnΛ.
"""
import json,math,sys
DS=[0.249,0.24,0.225,0.2,0.175,0.15,0.125,0.1,0.075,0.05,0.025,0.01,0.001]
N3={0.249:65,0.24:65,0.225:65,0.2:65,0.175:65,0.15:65,0.125:65,0.1:65,0.075:70,0.05:80,0.025:90,0.01:105,0.001:250}

def cfg(s,L,K,B,N,threads):
    return {'s':s,'Lambda':float(L),'nb':B,'keep':K,'nsites':N,'tunneling':0.1,'nlevels':8,'threads':threads}

def threads_for(K,B):
    D=K*B
    return 1 if D<=1000 else (2 if D<1600 else 4)

items=[];seen=set()
for ds in DS:
    s=round(1-2*ds,6)
    grid={(64,10,3)}
    grid|={(K,10,3) for K in (48,64,96,128)}
    grid|={(64,B,3) for B in (8,12,16)}
    grid|={(64,10,L) for L in (2,4)}
    grid.add((128,16,3))
    if ds>=0.2:grid|={(64,B,3) for B in (20,24)}
    if ds<=0.05:grid|={(K,10,3) for K in (160,192)}
    for K,B,L in sorted(grid,key=lambda t:(t[2],t[0]*t[1],t[0])):
        N=round(N3[ds]*math.log(3)/math.log(L))
        t=threads_for(K,B)
        item={'id':f'ds{ds:g}_L{L:g}_K{K}_B{B}_N{N}','kind':'critical','config':cfg(s,L,K,B,N,t),
              'bracket':[0.01,2.0],'backend':'ordered','memory_limit_gib':4.0 if K*B<1600 else 8.0,'with_tangent':True}
        assert item['id'] not in seen;seen.add(item['id']);items.append(item)
json.dump({'items':items},open('ds13_items.json','w'),indent=1)

# Rough cost model from amdq smoke timings: flow ≈ 0.066 s/site at D=keep·nb=640 (1 thread), ∝ D^3 above,
# tangent ≈ 1.75× flow; a critical item ≈ 49 flow trials (observers off ≈ 0.9×) + final flow + tangent.
# Extra threads: assume speedup 1.0 (D ≤ 1000), 1.2 (2 threads), 1.5 (4 threads).
def hours(it):
    c=it['config'];D=c['keep']*c['nb'];site=0.0355*(D/480)**2.2 if D<640 else 0.066*(D/640)**3
    speed={1:1.0,2:1.2,4:1.5}[c['threads']]
    return (48*0.9+1+1.75)*site*c['nsites']/speed/3600
h=[(hours(i),i['id'],i['config']['threads']) for i in items]
tot=sum(x*t for x,_,t in h)
print(len(items),'items; core-hours ≈',round(tot,1),'; longest items:')
for x,n,t in sorted(h,reverse=True)[:6]:print(f'  {x:5.2f} h  {n}  ({t} threads)')
print('thread sum',sum(t for _,_,t in h))
