"""Integer monomial coefficients of shifted Chebyshev polynomials T_k(2t-1)."""
def chebpoly(N):
    if N < 0: raise ValueError("N must be nonnegative")
    p=[(1,),(-1,2)]
    for k in range(1,N):
        a,b=p[-1],p[-2]
        c=[0]*(len(a)+1)
        for i,v in enumerate(a): c[i]-=2*v;c[i+1]+=4*v
        for i,v in enumerate(b): c[i]-=v
        p.append(tuple(c))
    return p[:N+1]
