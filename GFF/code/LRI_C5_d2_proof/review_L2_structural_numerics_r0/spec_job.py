# Direct spectral evaluation of I_l(x) = (1/pi) Int_0^inf |Gamma(l/2+a+i nu)/Gamma(l/2+1-a+i nu)|^8 d nu, a=x/2
# (W_4(2;2x) = gamma(1-x)^4 * sum_l d_l I_l, d_0=1, d_l=2).  Independent of the proof's lattice/residue steps.
import sys, json, mpmath as mp
from multiprocessing import Pool
DPS=int(sys.argv[3]) if len(sys.argv)>3 else 75
def I(args):
    l, xs, dps = args
    with mp.workdps(dps):
        x=mp.mpf(xs.split('/')[0])/mp.mpf(xs.split('/')[1]); a=x/2; lam=mp.mpf(l)/2
        f=lambda nu: mp.exp(8*mp.re(mp.loggamma(lam+a+1j*nu)-mp.loggamma(lam+1-a+1j*nu)))
        L=lam+1
        v=mp.quad(f,[0,L/4,L,4*L,16*L,64*L,mp.inf])/mp.pi
        return l, mp.nstr(v, dps-5)
if __name__=='__main__':
    xs=sys.argv[1]; N=int(sys.argv[2])
    ls=list(range(0,N+1))+list(range(N+200,3*N+1,200))
    with Pool(int(sys.argv[4]) if len(sys.argv)>4 else 32) as p:
        res=dict(p.map(I,[(l,xs,DPS) for l in ls],chunksize=4))
    # precision probe: recompute a few at higher dps
    probe={}
    for l in [0,1,7,N]:
        probe[l]=I((l,xs,DPS+20))[1]
    json.dump({'x':xs,'N':N,'dps':DPS,'I':{str(k):v for k,v in res.items()},'probe':{str(k):v for k,v in probe.items()}},open('spec_%s.json'%xs.replace('/','_'),'w'))
    print('done',xs)
