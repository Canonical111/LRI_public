import json, numpy as np, sys
from fitid import load, fit, B
for phase in (0,1):
    D=load(phase); Ls=sorted(D)
    for order in (4,5):
        for key in ('spacing_d1','spacing_d2'):
            for v in ('raw','g2D','g2D+g3W','Dconn','Dfull_raw'):
                dec=[]; lgv=[]
                for lo in (16,24,32):
                    sel=[L for L in Ls if L>=lo]
                    for bn,b in B.items():
                        p,res=fit(sel,[D[L][v][key][order] for L in sel],b)
                        (lgv if bn=='LG' else dec).append(p[0])
                print(f"phase {phase}/4 eps^{order} {key} {v:10s} L<={Ls[-1]}: last {D[Ls[-1]][v][key][order]:+.6f}  decaying-tail fits median {np.median(dec):+.4f} [{min(dec):+.4f},{max(dec):+.4f}]  (+log L basis: {min(lgv):+.3f}..{max(lgv):+.3f})")
