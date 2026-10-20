import mpmath as mp, json, time
from pathlib import Path
mp.mp.dps=35

def bell(x):
    b=[mp.mpc(1)]
    for n in range(1,len(x)+1):
        b.append(sum(mp.binomial(n-1,k-1)*x[k-1]*b[n-k] for k in range(1,n+1)))
    return b[-1]/mp.factorial(len(x))

def sample_fixed(q,r,l,t):
    a=(l+q)/2
    def A(t):
        v=(mp.gamma(l+q+t)*mp.gamma(-t)/mp.gamma(l+2*q+t)/mp.gamma(q-t))**r
        return v*mp.hyper([1]+[l+q+t]*r+[1-q+t]*r,[l+2*q+t]*r+[1+t]*r,1)
    middle=sum((mp.gamma(l+q-j+t)*mp.gamma(j-t)/mp.gamma(l+2*q-j+t)/mp.gamma(q+j-t))**r for j in range(1,l+1))
    s=A(t)+A(1-q-t)+middle
    return (mp.sin(mp.pi*t)*mp.sin(mp.pi*(t+q)))**r*s

def residue_weights(q,r):
    xx=[]
    for j in range(1,r):
        lj=(-1)**(j+1)*mp.polygamma(j-1,1-q)-mp.polygamma(j-1,q)
        xx.append(r*((1+(-1)**j)*mp.polygamma(j-1,1)-lj))
    return [mp.re(mp.exp(mp.j*mp.pi*k*q)*bell([xx[0]+2j*mp.pi*k]+xx[1:])) for k in range(r)]

def run(q,r,l):
    V=mp.matrix([[mp.chebyt(k,j+2) for k in range(r)] for j in range(r)])
    nodes=[-q/2+mp.j*mp.acosh(j+2)/(2*mp.pi) for j in range(r)]
    vals=mp.matrix([sample_fixed(q,r,l,t) for t in nodes]);coef=mp.lu_solve(V,vals)
    v=-mp.gamma(2*q)**r/(mp.pi*mp.sin(mp.pi*q))**r*sum(coef[k]*residue_weights(q,r)[k] for k in range(r))
    a=(l+q)/2;b=a+q
    integ=mp.quad(lambda nu:(mp.gamma(2*q)*abs(mp.gamma(a+mp.j*nu)/mp.gamma(b+mp.j*nu))**2)**r/mp.pi,[0,.2,1,5,mp.inf])
    t=mp.mpc('0.071','0.139')
    vtest=sample_fixed(q,r,l,t);pred=sum(coef[k]*mp.cos(2*mp.pi*k*(t+q/2)) for k in range(r))
    return {'q':str(q),'r':r,'l':l,'period_value':str(v),'Barnes_integral':str(integ),'difference':str(v-integ),'off_grid_difference':str(vtest-pred),'coefficients':[str(c) for c in coef]}

if __name__=='__main__':
    rows=[]
    for q,r,l in [(mp.mpf('0.6'),3,0),(mp.mpf('0.7'),3,2),(mp.mpf('0.6'),4,1),(mp.mpf('0.25'),4,0)]:
        start=time.time();row=run(q,r,l);row['seconds']=time.time()-start;rows.append(row);print(row,flush=True)
        Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/wheel_periodization.json').write_text(json.dumps({'working_digits':mp.mp.dps,'checks':rows},indent=2))
