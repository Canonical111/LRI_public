"""Independent local Cauchy-residue verification of the two K pole families."""
import mpmath as m,json,time
from pathlib import Path
m.mp.dps=55

def predicted(d,ell,n):
    d=m.mpf(d);q=d/4;Aarg=ell+q+n;Barg=ell+2*q+n
    psi=m.polygamma
    lam=[];pp=[]
    for j in range(4):
        cc=(-1)**j*psi(j,n+1-q)+psi(j,q)-(-1)**j*psi(j,1-q)
        pole=(1+(-1)**(j+1))*psi(j,1)-psi(j,n+1)
        lam.append(psi(j,Aarg)-psi(j,Barg)-(-1)**(j+1)*cc+pole)
        pp.append((psi(j,Aarg)+psi(j,Barg)+(-1)**j*cc-pole)/2)
    l1,l2,l3,l4=lam;p0,p1,p2,p3=pp;c=psi(0,1)+psi(0,2*q)
    R=((p0-c)/2*(l1**3+3*l1*l2+l3)+3*p1/4*(l1*l1+l2)-(l1*p2+p3)/4
      -l1**4/12+l1*l1*l2/8+7*l1*l3/24+l2*l2/8+l4/12)
    T=m.rf(q,ell+n)*m.rf(1-q,n)/(m.rf(2*q,ell+n)*m.factorial(n))
    S=m.rf(2*q,ell+n)*m.factorial(n)/(m.rf(3*q,ell+n)*m.rf(1+q,n))
    M=m.gamma(-q)*m.gamma(2*q)**2/m.gamma(3*q)
    return -T*T*R/4,M*M*S*S/8

def contour(d,ell,n,which,nodes=128):
    d=m.mpf(d);q=d/4;a=ell/2+q/2;b=a+q
    r=min(q,1-q)/5;s0=[a,b][which]+n
    def f(s):
        ap,am,bp,bm=a+s,a-s,b+s,b-s
        vals=[m.digamma(x)for x in [ap,am,bp,bm]]
        v1=[m.polygamma(1,x)for x in [ap,am,bp,bm]]
        v2=[m.polygamma(2,x)for x in [ap,am,bp,bm]]
        p=sum(vals)/2;L=vals[0]-vals[1]-vals[2]+vals[3]
        Lp=v1[0]+v1[1]-v1[2]-v1[3]
        pp=(v1[0]-v1[1]+v1[2]-v1[3])/2;ppp=sum(v2)/2
        c=m.digamma(1)+m.digamma(2*q)
        F=(c-p)*(L*L/8-5*Lp/16)+L*pp/4-5*ppp/32
        g=m.gamma(2*q)**2*(m.gamma(ap)*m.gamma(am)/(m.gamma(bp)*m.gamma(bm)))**2
        return g*F/4
    # minus residue: the right closure of an upward Barnes contour is clockwise.
    return -sum(r*m.exp(2j*m.pi*k/nodes)*f(s0+r*m.exp(2j*m.pi*k/nodes))for k in range(nodes))/nodes

rows=[]
for d,ell,n in [('1',0,0),('2',2,3),('2.6',1,2),('3.3',3,1)]:
    t=time.time();pr=predicted(d,ell,n)
    for i in [0,1]:
        co=contour(d,ell,n,i)
        rows.append(dict(d=d,ell=ell,n=n,family='a'if i==0 else'b',predicted=m.nstr(pr[i],50),cauchy=m.nstr(co,50),difference=m.nstr(co-pr[i],20)))
    print(d,ell,n,'seconds',time.time()-t,'diffs',[x['difference']for x in rows[-2:]],flush=True)
Path(__file__).with_name('local_residue_checks.json').write_text(json.dumps(rows,indent=2))
