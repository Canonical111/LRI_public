# check g_l(s)^2 R_tau(s) at s=a_l+n+t equals c(t) rho_tau(t) Phi1(x) Phi1(y) (x=l+n+t+5/8, y=n+t+1/8), and the k(-s) analogue
import mpmath as mp
mp.mp.dps=30
q=mp.mpf(3)/4
def k(l,s,tau):
    a=(l+q)/2;b=a+q
    g=mp.gamma(a+s)*mp.gamma(a-s)/(mp.gamma(b+s)*mp.gamma(b-s))
    R=mp.gamma(a+s)*mp.gamma(b-tau-s)/(mp.gamma(a+tau+s)*mp.gamma(b-s))
    return g**2*R
def Phi1(w,tau): return mp.gamma(w+0.125)**3/(mp.gamma(w+0.875)**2*mp.gamma(w+0.125+tau))
def Phi2(w,tau): return mp.gamma(w+0.125)**2*mp.gamma(w+0.875-tau)/mp.gamma(w+0.875)**3
for (l,n,t,tau) in ((0,0,mp.mpc(0.13,0.2),mp.mpf(0.3)),(3,-2,mp.mpc(-0.31,0.05),mp.mpc(0.1,0.2)),(5,4,mp.mpf(0.21),mp.mpf(-0.17))):
    a=(l+q)/2; s=a+n+t; x=l+n+t+mp.mpf(5)/8; y=n+t+mp.mpf(1)/8
    c=mp.sin(mp.pi*(0.75-t))**2/mp.sin(mp.pi*t)**2
    rho=mp.sin(mp.pi*(0.75-t))/mp.sin(mp.pi*(0.75-t-tau))
    sig=mp.sin(mp.pi*(t-tau))/mp.sin(mp.pi*t)
    print(mp.nstr(k(l,s,tau)/(c*rho*Phi1(x,tau)*Phi1(y,tau)),15), mp.nstr(k(l,-s,tau)/(c*sig*Phi2(x,tau)*Phi2(y,tau)),15))
