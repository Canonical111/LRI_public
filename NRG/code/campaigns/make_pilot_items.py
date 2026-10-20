"""Λ-extrapolation pilot: is Δ_E(Λ) smooth toward Λ → 1, and is keep converged at small Λ?

Δσ ∈ {0.2, 0.1, 0.05}; Λ ∈ {1.5, 2, 2.5} with keep ∈ {64, 128} (nb = 10), plus nb = 16 at Λ = 1.5, keep = 64.
keep = 64, Λ = 2 already exists in campaigns/ds13 and is reused. Same infrared depth as ds13: N(Λ) = N(3)·ln3/lnΛ.
"""
import json,math
N3={0.2:65,0.1:65,0.05:80}
def threads_for(K,B):
    D=K*B;return 1 if D<=1000 else (2 if D<1600 else 4)
items=[]
for ds in (0.2,0.1,0.05):
    s=round(1-2*ds,6)
    for K,B,L in [(64,10,1.5),(128,10,1.5),(64,16,1.5),(128,10,2),(64,10,2.5),(128,10,2.5)]:
        N=round(N3[ds]*math.log(3)/math.log(L))
        items.append({'id':f'ds{ds:g}_L{L:g}_K{K}_B{B}_N{N}','kind':'critical',
            'config':{'s':s,'Lambda':float(L),'nb':B,'keep':K,'nsites':N,'tunneling':0.1,'nlevels':8,'threads':threads_for(K,B)},
            'bracket':[0.01,2.0],'backend':'ordered','memory_limit_gib':4.0,'with_tangent':True})
json.dump({'items':items},open('pilot_items.json','w'),indent=1)
for i in items:print(i['id'],'threads',i['config']['threads'])
