# Reliable Euler-Maclaurin summation: sum_{k=a}^inf f(k) = sum_{k=a}^{N-1} f(k) + int_N^inf f + f(N)/2
#   - sum_{j>=1} B_{2j}/(2j)! f^{(2j-1)}(N), truncated at the smallest term.
# robust(g) wraps g so it is evaluated with extra precision ~ log10(x): Gamma/polygamma differences at large x
# (which tanh-sinh samples up to ~1e30+) otherwise cancel catastrophically.
import mpmath as mp
def robust(g):
    def f(x):
        extra=int(mp.log10(abs(x)+10))+15
        with mp.workdps(mp.mp.dps+extra):
            v=g(mp.mpf(x))
        return +v
    return f
def emsum(g,a,N,J=None,verbose=False):
    f=robust(g)
    head=mp.fsum(f(k) for k in range(a,N))
    I=mp.quad(f,[N,2*N,4*N,16*N,64*N,mp.inf])
    J=J or max(6,int(mp.mp.dps*0.45))
    ders=list(mp.diffs(f,N,2*J))
    corr=mp.mpf(0);last=None
    for j in range(1,J+1):
        term=mp.bernoulli(2*j)/mp.factorial(2*j)*ders[2*j-1]
        if last is not None and abs(term)>abs(last):break
        corr+=term;last=term
    if verbose:print('last EM term',mp.nstr(abs(last),3))
    return head+I+ders[0]/2-corr
if __name__=='__main__':
    import sys
    mp.mp.dps=int(sys.argv[1]) if len(sys.argv)>1 else 40;h=mp.mpf(1)/2
    g=lambda k:(mp.exp(mp.loggamma(k+h)-mp.loggamma(k+1)))**2/mp.pi-1/(mp.pi*k)
    v=1+emsum(g,1,max(60,mp.mp.dps),verbose=True)
    print('diff from 4log2/pi:',mp.nstr(v-4*mp.log(2)/mp.pi,3))
