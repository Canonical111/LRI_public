import json, numpy as np
from htb import bubble_S_table, conv
for L in [24,32]:
    d=json.load(open(f'res_L{L}.json'))
    Ec=np.array(d['Evac_conn']); Er=np.array(d['Evac_raw']); g=np.array(d['g_raw']); K=4
    S=bubble_S_table(L+1,K); Sf=np.array([[float(x) for x in row] for row in S]); gg=conv(g,g,K)
    print(f'L={L}: window depth E0 -> W, [Dfull_c - g2D] at eps^3 (=W/27) and eps^4 (row content), eps^4 per odd shell increments')
    prev=None
    for e4 in range(1,4*12+1):   # E0 = e4/4
        E0=e4/4; j=(4*L-e4)//2; up=(4*L-e4)//4
        W=(L+1)//2-(up+1)//2
        D=-(Sf[L]-Sf[up])/6
        g2d=np.array([sum(gg[a]*D[k-a] for a in range(k+1)) for k in range(K+1)])
        x=(Ec[2*L]-Ec[j])-g2d
        if e4%2==0 or e4<=4:
            print(f'   E0={E0:5.2f} W={W}  e3={x[3]:+.10f} (W/27={W/27:.10f})  e4={x[4]:+.8f}')
