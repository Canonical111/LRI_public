import mpmath as mp
mp.mp.dps=30
sg=mp.mpf('0.41')
def res(k,r):
    f=lambda t: mp.cos(2*mp.pi*k*(t+sg/2))/(mp.sin(mp.pi*t)*mp.sin(mp.pi*(t+sg)))**r
    rho=mp.mpf('0.1')
    g=lambda th: f(rho*mp.expj(th))*rho*mp.expj(th)
    return mp.quad(g,[0,mp.pi,2*mp.pi])/(2*mp.pi)
s,c=mp.sin(mp.pi*sg),mp.cos(mp.pi*sg)
for k,F in ((0,4*c*(3+2*c**2)/(mp.pi*s**7)),(1,4*(1+4*c**2)/(mp.pi*s**7)),(2,20*c/(mp.pi*s**7))):
    print(k, -res(k,4), F, -res(k,4)/F)
