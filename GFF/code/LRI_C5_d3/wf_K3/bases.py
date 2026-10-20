import itertools, mpmath as mp
def monomials(gens, maxw, minw=0, sqrt2=False, extra=()):
    """gens: list of (name, value, weight). all monomials of total weight in [minw,maxw] (weight-0 monomial '1' included if minw==0)."""
    out=[]
    names=[g[0] for g in gens]; vals=[g[1] for g in gens]; ws=[g[2] for g in gens]
    def rec(i, cur_w, expo):
        if i==len(gens):
            if minw<=cur_w<=maxw:
                nm='*'.join(('%s^%d'%(names[j],e) if e>1 else names[j]) for j,e in enumerate(expo) if e) or '1'
                v=mp.mpf(1)
                for j,e in enumerate(expo):
                    if e: v*=vals[j]**e
                out.append((nm,v,cur_w))
            return
        e=0
        while cur_w+e*ws[i]<=maxw:
            rec(i+1,cur_w+e*ws[i],expo+[e]); e+=1
    rec(0,0,[])
    if sqrt2:
        s2=mp.sqrt(2)
        out=out+[('s2*'+n,s2*v,w) for n,v,w in out]
    return out
