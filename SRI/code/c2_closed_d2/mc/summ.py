import sys, numpy as np
NBIN=120; BLO=-58.0; BW=0.5
def load(files):
    H=[]; HS=[]; BD=[]; N=0
    for f in files:
        for line in open(f):
            t=line.split()
            if not t: continue
            if t[0]=='B': H.append((int(t[2]), np.array(list(map(float,t[3:])))))
            elif t[0]=='BS': HS.append((int(t[2]), np.array(list(map(float,t[3:])))))
            elif t[0]=='BD': BD.append((int(t[2]), np.array(list(map(float,t[3:])))))
    return H, HS, BD
def est(B, cut_idx=None):
    # batch means of sum over bins above cut
    vals=[]; ws=[]
    for nb, h in B:
        s = h[cut_idx:].sum() if cut_idx is not None else h.sum()
        vals.append(s/nb); ws.append(nb)
    vals=np.array(vals); ws=np.array(ws,float)
    m=(vals*ws).sum()/ws.sum(); se=np.sqrt(((vals-m)**2*ws).sum()/ws.sum()/(len(vals)-1))
    return m, se
if __name__=='__main__':
    H,HS,BD = load(sys.argv[1:])
    edges = BLO + BW*np.arange(NBIN+1)
    print('nbatches', len(H), 'Nsamples', sum(nb for nb,_ in H))
    for lmin in [-16,-15,-14,-13,-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2]:
        ci = int(round((lmin-BLO)/BW))
        m,se = est(H, ci); mS,seS = est(HS, ci)
        D = [(nb, hs - h) for (nb, h), (_, hs) in zip(H, HS)]
        mD, seD = est(D, ci)
        print('Lambda > %5.1f : I0 = %10.4f +- %.4f   IS0 = %10.4f +- %.4f   IS0-I0 = %9.4f +- %.4f' % (lmin, m, se, mS, seS, mD, seD))
    dl=[0.05,0.1,0.15,0.2,0.3,0.5]
    for j,dd in enumerate(dl):
        v=np.array([b[1][j]/b[0] for b in BD]); vS=np.array([b[1][len(dl)+j]/b[0] for b in BD])
        print('delta %.2f : I = %10.4f +- %.4f   IS = %10.4f +- %.4f' % (dd, v.mean(), v.std(ddof=1)/np.sqrt(len(v)), vS.mean(), vS.std(ddof=1)/np.sqrt(len(vS))))
    # histogram rho(lambda)
    tot = sum(nb for nb,_ in H)
    h = sum(x for _,x in H)/tot
    print('rho(lambda) per bin (Lambda bin center: sum):')
    for i in range(NBIN):
        if abs(h[i])>0: print('  %6.2f %12.5f' % (edges[i]+BW/2, h[i]))
