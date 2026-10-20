"""Λ follow-up after the pilot: a Λ = 2.5 systematic at every Δσ, and keep convergence of the Λ = 2 shift.

A) Λ = 2.5 for the 10 Δσ not in the pilot: keep 128 and keep 64 (nb = 10; keep check), plus keep 128,
   nb = 16 for Δσ ≥ 0.2 (nb-sensitive near s = 1/2; compare with the Λ = 3 keep 128/nb 16 corner).
B) Λ = 2 at Δσ ∈ {0.2, 0.1, 0.05}: keep 192 and 256 (nb = 10).
Same infrared depth as ds13: N(Λ) = N(3)·ln3/lnΛ.
"""
import json,math
DS=[0.249,0.24,0.225,0.2,0.175,0.15,0.125,0.1,0.075,0.05,0.025,0.01,0.001]
N3={0.249:65,0.24:65,0.225:65,0.2:65,0.175:65,0.15:65,0.125:65,0.1:65,0.075:70,0.05:80,0.025:90,0.01:105,0.001:250}
PILOT={0.2,0.1,0.05}
def threads_for(K,B):
    D=K*B;return 1 if D<=1000 else (2 if D<1600 else 4)
def item(ds,K,B,L):
    s=round(1-2*ds,6);N=round(N3[ds]*math.log(3)/math.log(L))
    return {'id':f'ds{ds:g}_L{L:g}_K{K}_B{B}_N{N}','kind':'critical',
            'config':{'s':s,'Lambda':float(L),'nb':B,'keep':K,'nsites':N,'tunneling':0.1,'nlevels':8,'threads':threads_for(K,B)},
            'bracket':[0.01,2.0],'backend':'ordered','memory_limit_gib':4.0 if K*B<1600 else 8.0,'with_tangent':True}
items=[]
for ds in DS:
    if ds not in PILOT:items+= [item(ds,128,10,2.5),item(ds,64,10,2.5)]
    if ds>=0.2:items.append(item(ds,128,16,2.5))
for ds in sorted(PILOT,reverse=True):items+=[item(ds,192,10,2),item(ds,256,10,2)]
json.dump({'items':items},open('followup_items.json','w'),indent=1)
print(len(items),'items; thread sum',sum(i['config']['threads'] for i in items))
