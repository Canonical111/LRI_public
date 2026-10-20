"""Residue series gs:Kseries, per spin: I_l(q) = sum_n [M^2 S_{ln}^2/8 - T_{ln}^2 R_{ln}/4]  (n continuous for Euler-Maclaurin).
K_d = -A U/4 + sum_l d_l I_l   (spin sum in the note's order: n inside, l outside)."""
import mpmath as mp
from emsum import emsum

def consts(q):
    q=mp.mpf(q)
    c=dict(q=q)
    c['M']=-mp.gamma(1-q)*mp.gamma(2*q)**2/(q*mp.gamma(3*q))
    c['psiq']=[mp.psi(j,q) for j in range(5)]
    c['psi1mq']=[mp.psi(j,1-q) for j in range(5)]
    c['psi1']=[mp.psi(j,1) for j in range(5)]
    c['cstar']=mp.psi(0,1)+mp.psi(0,2*q)
    c['lgq']=mp.loggamma(q);c['lg1mq']=mp.loggamma(1-q);c['lg2q']=mp.loggamma(2*q);c['lg3q']=mp.loggamma(3*q);c['lg1pq']=mp.loggamma(1+q)
    A=mp.psi(0,2*q)+mp.psi(0,1)-2*mp.psi(0,q);U=mp.psi(2,q)
    c['A']=A;c['U']=U
    return c

def summand(c,l,n):
    q=c['q'];m=l+n
    a=m+q;b=m+2*q
    lT=(mp.loggamma(q+m)-c['lgq'])+(mp.loggamma(1-q+n)-c['lg1mq'])-(mp.loggamma(2*q+m)-c['lg2q'])-mp.loggamma(n+1)
    lS=(mp.loggamma(2*q+m)-c['lg2q'])+mp.loggamma(n+1)-(mp.loggamma(3*q+m)-c['lg3q'])-(mp.loggamma(1+q+n)-c['lg1pq'])
    T2=mp.exp(2*lT);S2=mp.exp(2*lS)
    pa=[mp.psi(j,a) for j in range(4)];pb=[mp.psi(j,b) for j in range(4)]
    pn1=[mp.psi(j,n+1) for j in range(4)];pnq=[mp.psi(j,n+1-q) for j in range(4)]
    chi=[(-1)**j*pnq[j]+c['psiq'][j]-(-1)**j*c['psi1mq'][j] for j in range(4)]
    lam={}
    for j in range(1,5):
        lam[j]=pa[j-1]-pb[j-1]-(-1)**j*chi[j-1]+(1+(-1)**j)*c['psi1'][j-1]-pn1[j-1]
    r=[lam[j+1]/2+pb[j]+pn1[j]-(1-(-1)**j)*c['psi1'][j] for j in range(4)]
    l1,l2,l3,l4=lam[1],lam[2],lam[3],lam[4]
    R=((r[0]-c['cstar'])/2*(l1**3+3*l1*l2+l3)+mp.mpf(3)/4*r[1]*(l1**2+l2)-(l1*r[2]+r[3])/4
       -l1**4/12+l1**2*l2/8+mp.mpf(7)/24*l1*l3+l2**2/8+l4/12)
    return c['M']**2*S2/8-T2*R/4

def spin(c,l,N=None,verbose=False):
    N=N or max(40,int(mp.mp.dps))
    return emsum(lambda n:summand(c,l,n),0,N,verbose=verbose)

def dl(d,l):
    d=mp.mpf(d)
    if l==0:return mp.mpf(1)
    return (2*l+d-2)*mp.gamma(l+d-2)/(mp.gamma(d-1)*mp.gamma(l+1))

if __name__=='__main__':
    import sys,time
    mp.mp.dps=int(sys.argv[1]) if len(sys.argv)>1 else 25
    # d=1 check: d_l=(1,1,0,...)
    c=consts(mp.mpf(1)/4)
    t=time.time()
    I0=spin(c,0);I1=spin(c,1)
    K1=-c['A']*c['U']/4+I0+I1
    pi,G,z3,l2=mp.pi,mp.catalan,mp.zeta(3),mp.log(2)
    print('d=1 K =',K1,' diff exact',mp.nstr(K1-(128*G**2+24*pi**2*G-4*pi**3*l2-28*(pi+4*l2)*z3),3),'%.1fs'%(time.time()-t))
