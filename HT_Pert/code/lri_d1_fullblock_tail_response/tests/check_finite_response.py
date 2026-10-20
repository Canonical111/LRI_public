"""Independent finite-epsilon matrix/Hellmann--Feynman source check.
No epsilon sampling is used to produce Taylor coefficients; it validates their
remainder. Vacuum equations are solved by exact finite Schur complements.
"""
from pathlib import Path
import sys,json,math
from collections import Counter
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1]

def run(L=2):
    mp.mp.dps=60;states=[]
    def gen(st,N,start):
        states.append(st)
        for n in range(start,L):
            if 4*(N+n)+len(st)+1>4*L:break
            gen(st+(n,),N+n,n)
    gen((),0,0);ix={s:i for i,s in enumerate(states)};D=len(states)
    P=[len(s) for s in states];N=[sum(s) for s in states];e4=[4*n+p for n,p in zip(N,P)]
    def matrices(ep):
        alpha=(1-ep)/2;x=alpha/2;u=[mp.sqrt(mp.rf(alpha,n)/math.factorial(n)) for n in range(L)]
        B=mp.zeros(D)
        for j,st in enumerate(states):
            for n,m in Counter(st).items():
                z=list(st);z.remove(n);B[ix[tuple(z)],j]=mp.sqrt(m)*u[n]
        C=B.T;bs=[mp.eye(D)];cs=[mp.eye(D)]
        for _ in range(6):bs.append(bs[-1]*B);cs.append(cs[-1]*C)
        def normal(q):return sum((math.comb(q,k)*cs[k]*bs[q-k] for k in range(q+1)),mp.zeros(D))
        M=normal(2);V=normal(4)/12;O6=normal(6)
        delta=lambda p:2-2*((p+7)//8)
        jp=cs[2]*mp.diag([delta(p+4) for p in P])+C*mp.diag([delta(p+3)+delta(p+5) for p in P])*B+mp.diag([delta(p+4) for p in P])*bs[2]
        jn=-(mp.diag(N)*M+M*mp.diag(N))/2
        return mp.diag([n+x*p for n,p in zip(N,P)]),M,V,dict(phi6=O6,full=jp+jn)
    def sub(a,ids):return mp.matrix([[a[i,j] for j in ids] for i in ids])
    out=[]
    for channel in ['phi6','full']:
        row=json.loads((ROOT/f'results/dconn_{channel}_L{L}_d8.json').read_text())
        series=lambda key,e:sum(mp.mpf(str(v))*e**j for j,v in enumerate(row[key]))
        rr=[]
        for eps in map(mp.mpf,['.01','.005','.0025']):
            h0,M,V,O=matrices(eps);r,g,dr,dg=[series(k,eps) for k in ['r','g','dr','dg']]
            H=h0+r*M+g*V;dH=dr*M+dg*V+g*g*O[channel]
            vac=[];dvac=[]
            for q in range(2*L+1):
                ids=[i for i in range(D) if P[i]%2==0 and N[i]%2==0 and e4[i]<=2*q]
                non=[i for i in ids if i!=ix[()]]
                if not non:vac.append(mp.mpf(0));dvac.append(mp.mpf(0));continue
                b=mp.matrix([H[i,ix[()]] for i in non]);db=mp.matrix([dH[i,ix[()]] for i in non])
                A=sub(H,non)-mp.diag([vac[(2*q-e4[i])//2] for i in non]);dA=sub(dH,non)-mp.diag([dvac[(2*q-e4[i])//2] for i in non])
                # Positive high block establishes the vacuum branch used by Schur.
                mp.cholesky(A);y=mp.lu_solve(A,b)
                vac.append(-(b.T*y)[0]);dvac.append(-2*(db.T*y)[0]+(y.T*dA*y)[0])
            ids=[i for i in range(D) if P[i]%2==0 and N[i]%2==0]
            lower=[(4*L-e4[i])//2 for i in ids]
            He=sub(H,ids)+mp.diag([vac[-1]-vac[j] for j in lower]);dHe=sub(dH,ids)+mp.diag([dvac[-1]-dvac[j] for j in lower])
            vals,U=mp.eigsy(He);response=[]
            for j in [0,1]:response.append((U[:,j].T*dHe*U[:,j])[0])
            exact=response[1]-response[0];prediction=series('response',eps);error=exact-prediction
            rr.append(dict(epsilon=str(eps),exact=str(exact),series=str(prediction),error=str(error)))
        ratios=[abs(mp.mpf(rr[k]['error'])/mp.mpf(rr[k+1]['error'])) for k in [0,1]]
        assert all(mp.mpf(300)<r<mp.mpf(700) for r in ratios),(channel,ratios)
        out.append(dict(channel=channel,cutoff=L,records=rr,halving_ratios=list(map(str,ratios))))
    (ROOT/'results/finite_response_validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':run()
