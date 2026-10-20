import mpmath as mp
mp.mp.dps = 30
for b in [mp.mpf('0.37'), mp.mpc('0.3', '0.1')]:
    sig = b/2; g = (1-b)/2
    T = lambda l, n: mp.rf(sig, l+n)*mp.rf(1-g, n)/(mp.rf(mp.mpf(1)/2, l+n)*mp.factorial(n))
    e = max(max(abs(T(0, n) - mp.rf(b, 2*n)/mp.factorial(2*n)), abs(T(1, n) - mp.rf(b, 2*n+1)/mp.factorial(2*n+1))) for n in range(0, 40))
    print('b =', b, ' max |T_0n-(b)_2n/(2n)!|,|T_1n-(b)_{2n+1}/(2n+1)!| over n<40:', mp.nstr(e, 3))
    # Dixon with accelerated sum: Euler-Maclaurin style via mpmath sumem on log-smooth term
    f = lambda m: (mp.gamma(b+m)/(mp.gamma(b)*mp.gamma(m+1)))**3
    S = mp.sumem(f, [0, mp.inf]) if False else None
