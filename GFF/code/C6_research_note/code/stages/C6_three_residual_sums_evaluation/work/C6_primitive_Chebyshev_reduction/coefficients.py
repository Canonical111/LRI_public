import mpmath as mp,time,sys,json

def gs(x):
    lam=x/(2*(1+mp.sqrt(1-x)))
    K=mp.ellipk(lam); Kc=mp.elliprf(0,lam,1)
    fac=mp.pi**(-mp.mpf('1.5'))
    return [4*fac*K*K,4*fac*K*Kc,2*fac*(Kc*Kc-K*K)]
def gs_pair(u):
    x=u**4/2
    lam=x/(2*(1+mp.sqrt(1-x))); lamp=(1-mp.sqrt(x))/2
    K=mp.ellipk(lam);Kc=mp.elliprf(0,lam,1)
    P=mp.ellipk(lamp);Pc=mp.elliprf(0,lamp,1)
    fac=mp.pi**(-mp.mpf('1.5'))
    return [4*fac*K*K,4*fac*K*Kc,2*fac*(Kc*Kc-K*K)], [4*fac*P*P,4*fac*P*Pc,2*fac*(Pc*Pc-P*P)]

def Cquad(j,n):
    def fun(u):
        if u==0:return mp.mpf(0)
        g,gp=gs_pair(u)
        return 2*mp.sqrt(2)*u/mp.sqrt(1-u**4/2)*mp.chebyt(n,1-u**4)*(g[j-1]+(-1)**n*gp[j-1])/mp.sqrt(mp.pi)
    return mp.quad(fun,[0,mp.mpf('.25'),mp.mpf('.5'),mp.mpf('.75'),1])
def Cbarnes(j,n):
    def fun(t):
        s=mp.mpf('.25')+1j*t
        # M_j * Gamma(.5-s) * Gamma(s+n)/(Gamma(s)*Gamma(n+1-s))
        log=(j-1)*mp.loggamma(s)+mp.loggamma(s+n)+(4-j)*mp.loggamma(mp.mpf('.5')-s)-(3-j)*mp.loggamma(1-s)-j*mp.loggamma(mp.mpf('.5')+s)-mp.loggamma(n+1-s)
        return mp.re(mp.exp(log))/mp.pi
    return mp.quad(fun,[0,1,4,16,mp.inf])
if __name__=='__main__':
    for j in [1,2,3]:
      for n in [0,1,2,3]:
        st=time.time();cq=Cquad(j,n);cb=Cbarnes(j,n)
        print(j,n,mp.nstr(cq,25),mp.nstr(cb,25),mp.nstr(cb-cq,4),'sec',time.time()-st,flush=True)
