import json, numpy as np, sys
for L in [8,16,24,32]:
    a=json.load(open(f'res_L{L}.json')); b=json.load(open(f'big_L{L}.json'))
    m=0
    for v in a['variants']:
        for key in ['C','spacing_d1','spacing_d2','spacing_d3','r','g']:
            x=np.array(a['variants'][v][key]); y=np.array(b['variants'][v][key])
            m=max(m,np.max(np.abs(x-y)/np.maximum(1,np.abs(x))))
    print(L,'max rel diff htb vs htb_big over all variants/quantities: %.2e'%m)
