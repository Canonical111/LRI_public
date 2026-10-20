#!/usr/bin/env python3
"""Audit combined rational weights and all sector exponent groups exactly."""
from pathlib import Path
import itertools,json
import numpy as np
from kernel_inputs import ROOT,graph_file
cache=ROOT/'work'/'enumeration'
graph_file(cache,False)
g=np.fromfile(cache/'graphs6.bin',dtype='<i4').reshape(-1,17)
pairs=list(itertools.combinations(range(6),2))
deg=np.zeros((len(g),6),dtype=np.int32)
for e,(i,j)in enumerate(pairs):deg[:,i]+=g[:,e];deg[:,j]+=g[:,e]
external=4-deg;wh=3*g[:,16]-g[:,15]
assert np.all(4*wh==g[:,15]*(np.sum(external*(external-1),axis=1)-4))
allkeys=set();combinedkeys=set();sectors=0;bad=0
for perm in itertools.permutations(range(5)):
    rev=tuple(4-i for i in perm)
    if perm>rev:continue
    sectors+=1;rank=np.argsort(perm)
    matrix=np.zeros((15,4),dtype=np.int32)
    for e,(i,j)in enumerate(pairs):matrix[e,:min(rank[i:j])]=1
    bm=g[:,:15]@matrix
    key=((bm[:,0]*11+bm[:,1])*11+bm[:,2])*11+bm[:,3]
    allkeys.update(np.unique(key).tolist());combinedkeys.update(np.unique(key[wh!=0]).tolist())
    exponents2=2*np.array([3,2,1,0])-bm
    bad+=np.count_nonzero(np.any(exponents2==-4,axis=1)&(wh!=0))
def decode(key):
    b=[]
    for _ in range(4):b.append(key%11);key//=11
    return list(reversed(b))
record={'ordered_graphs':len(g),'nonzero_combined_graphs':int(np.count_nonzero(wh)),
        'zero_combined_graphs':int(np.count_nonzero(wh==0)),'reversal_reduced_sectors':sectors,
        'all_groups':len(allkeys),'combined_groups':len(combinedkeys),
        'nonzero_combined_derivative_sectors':int(bad),
        'integer_weight_identity_checked':True,
        'active_groups_all':[decode(k)for k in sorted(allkeys)],
        'active_groups_combined':[decode(k)for k in sorted(combinedkeys)]}
assert (sectors,len(allkeys),len(combinedkeys),bad)==(60,342,335,0)
(ROOT/'records'/'enumeration_audit.json').write_text(json.dumps(record,indent=2))
print({k:v for k,v in record.items()if not k.startswith('active_')})
