"""Independent check of L_sub = 2 sum_{n>=2}[log(1-v_n)+v_n+v_n^2/2], v_n = 3 p0 Gamma(n+1/4)/Gamma(n+3/4).
Direct float partial sums to N, plus a tail from the large-n expansion v_n = c n^{-1/2}(1 + a1/n + ...)."""
import numpy as np, mpmath as mp
from scipy.special import gammaln
p0 = float(mp.gamma(0.75)/mp.gamma(0.25))
def v(n): return 3*p0*np.exp(gammaln(n+0.25)-gammaln(n+0.75))
def partial(N, chunk=10**6):
    s = 0.0; n0 = 2
    while n0 <= N:
        n = np.arange(n0, min(N, n0+chunk-1)+1, dtype=np.float64); x = v(n)
        s += np.sum(np.log1p(-x) + x + x*x/2); n0 += chunk
    return 2*s
# tail: summand ~ -(x^3/3 + x^4/4 + ...) with x ~ c n^{-1/2}; fit the tail by Richardson on N, 2N, 4N
for N in (10**5, 10**6, 10**7):
    print(N, partial(N))
S1, S2, S3 = partial(10**6), partial(4*10**6), partial(16*10**6)
# leading tail ~ C N^{-1/2}: Richardson with ratio 2 in N^{-1/2}
R1 = (2*S2 - S1); R2 = (2*S3 - S2)
print('Richardson (N^-1/2 removed):', R1, R2, ' second-level:', (4*R2 - R1)/3 if False else (R2*2**1 - R1)/(2**1-1))
