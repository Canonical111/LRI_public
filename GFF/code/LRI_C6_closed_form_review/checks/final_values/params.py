# Independent parameter definitions, transcribed from the note (Sections 2-4).
# Written from scratch for the review; no package code used.
import mpmath as mp

def setup(dps=60):
    mp.mp.dps = dps
    P = {}
    pi = mp.pi
    ell = mp.log(2)
    A = pi + 4*ell
    Q = mp.gamma(mp.mpf(1)/4)**4/pi
    G = mp.catalan
    P.update(pi=pi, ell=ell, A=A, Q=Q, G=G)
    # lower block
    X4 = 42*A**2 + 18*A*pi + 1227*pi**2 - 96*Q
    Y4 = mp.mpf(105)/4*A**2 + 9*A*pi + mp.mpf(2469)/4*pi**2 - 60*Q
    rho4 = mp.sqrt(X4**2 + Y4**2)
    alpha4 = mp.atan(Y4/X4)/pi
    P.update(X4=X4, Y4=Y4, rho4=rho4, alpha4=alpha4)
    # sixth
    alpha6 = mp.atan(mp.mpf(11)/13)/pi
    P.update(alpha6=alpha6)
    # eighth
    s2 = mp.sqrt(2)
    rho8 = mp.sqrt(2177203 - 1028322*s2)
    d8 = mp.atan(556/(1233 - 417*s2))/(2*pi)
    e8 = mp.acosh((1233 - 139*s2)/rho8)/(2*pi)
    P.update(rho8=rho8, d8=d8, e8=e8, a8p=mp.mpc(d8, e8), a8m=mp.mpc(d8, -e8))
    # seventh
    q72 = 259*A - 49*pi
    q71 = 481*A - 539*pi
    q70 = 407*A - 1127*pi
    d7 = mp.sqrt(q71**2 - 4*q72*q70)
    rho7 = mp.sqrt((q72 - q70)**2 + q71**2)
    eta7p = mp.atan((q71 + d7)/(2*q72))/pi
    eta7m = mp.atan((q71 - d7)/(2*q72))/pi
    beta7 = mp.atan(mp.mpc(13, mp.sqrt(139))/14)/pi
    P.update(q72=q72, q71=q71, q70=q70, d7=d7, rho7=rho7, eta7p=eta7p,
             eta7m=eta7m, beta7=beta7)
    # wheel
    alphaW = mp.atan(mp.mpf(5)/8)/pi
    P.update(alphaW=alphaW)
    # primitive
    lam = (28 + mp.sqrt(409)*mp.cos(mp.acos(mp.mpf(7298)/(409*mp.sqrt(409)))/3))/3
    P['lam_trig'] = lam
    lam_root = mp.findroot(lambda x: 4*x**3 - 112*x**2 + 909*x - 2250, mp.mpf('15.5'))
    P['lam_root'] = lam_root
    lam = lam_root
    rad1 = 40*lam - 279
    es = mp.sqrt(rad1)/20
    chi = 2*(21*lam - 150)/(40*lam - 279)
    P.update(lam=lam, es=es, chi=chi, rad1=rad1)
    for sg, name in ((1, 'p'), (-1, 'm')):
        B = mp.mpf(21)/20 + sg*es
        C = lam/10 + sg*es*chi
        rad2 = C - B**2/4
        beta = mp.atan(B/2 + 1j*mp.sqrt(rad2))/pi
        P['B'+name] = B; P['C'+name] = C; P['rad2'+name] = rad2; P['beta'+name] = beta
    return P

if __name__ == '__main__':
    P = setup(50)
    for k, v in P.items():
        print(k, mp.nstr(v, 30))
