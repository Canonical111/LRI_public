"""High-precision constant library (mpmath), cached to consts_<dps>.json."""
import mpmath as mp, json, sys, os, time
def build(dps):
    fn='consts_%d.json'%dps
    if os.path.exists(fn):
        d=json.load(open(fn)); 
        with mp.workdps(dps): return {k:mp.mpf(v) for k,v in d.items()}
    mp.mp.dps=dps+20
    c={}
    t=time.time()
    c['pi']=+mp.pi; c['l2']=mp.log(2); c['G']=+mp.catalan; c['z3']=mp.zeta(3); c['s2']=mp.sqrt(2)
    c['lam']=mp.log(1+mp.sqrt(2))
    h=(1+1j)/mp.mpf(2)
    c['ImLi3h']=mp.im(mp.polylog(3,h)); c['Li4h']=mp.polylog(4,mp.mpf(1)/2)
    c['ImLi4h']=mp.im(mp.polylog(4,h)); c['ReLi4h']=mp.re(mp.polylog(4,h))
    c['b4']=mp.dirichlet(4,[0,1,0,-1])
    c['L8_2']=mp.dirichlet(2,[0,1,0,1,0,-1,0,-1]); c['L8_3']=mp.dirichlet(3,[0,1,0,-1,0,-1,0,1]); c['L8_4']=mp.dirichlet(4,[0,1,0,1,0,-1,0,-1])
    c['G14']=mp.gamma(mp.mpf(1)/4)
    print('consts built %.1fs'%(time.time()-t))
    json.dump({k:mp.nstr(v,dps+10) for k,v in c.items()},open(fn,'w'))
    return c
if __name__=='__main__':
    c=build(int(sys.argv[1]))
    print({k:mp.nstr(v,15) for k,v in c.items()})
