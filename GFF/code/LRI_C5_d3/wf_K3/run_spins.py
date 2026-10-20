import json, sys, mpmath as mp
from flint import arb
from kspin import spins
prec=int(sys.argv[1]); N0=int(sys.argv[2]); KN=int(sys.argv[3])
res={}
for name,q in (('d1',arb(1)/4),('d3',arb(3)/4)):
    v=spins(q,[0,1,2],prec,N0,KN)
    res[name]={str(l):v[l].mid().str(int(prec*0.301)+3,radius=False) for l in v}
    res[name+'_rad']={str(l):v[l].rad().str(3,radius=False) for l in v}
json.dump(res,open(sys.argv[4],'w'),indent=1)
print(json.dumps(res['d1_rad']),json.dumps(res['d3_rad']))
