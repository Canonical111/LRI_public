import json
from fractions import Fraction as F
from itertools import combinations
import mpmath as mp
from jet_engine import X,D,HALF
from polar_reconstruction import PolarEngine,edge,kernel_small
from five_vertex import evaluate,remove_two_vertex

def input_periods(d):
    # Shared external period INPUTS; the amplitude is reconstructed separately.
    from calculate_a5 import fixed_periods
    T,P4,_ = fixed_periods(mp.mpf(d))
    return T,P4

def outer(E,a,b):
    return E.gr([HALF,HALF-b,2*a+b-D,a+b-HALF,a+b-HALF],[a,a,2*a+2*b-D])

def four_sum(E):
    rows=json.load(open('graphs_n4.json'));u=X(1,F(-1,4));pairs=list(combinations(range(4),2));S={};details=[]
    for row in rows:
        g={p:m*u for p,m in zip(pairs,row['edges']) if m}
        val=kernel_small(E,g,(0,1,2,3),(0,1))
        w=E.m(F(row['weight']));S=E.add(S,E.scale(val,w));details.append({k:val.get(k,0) for k in (-2,-1,0,1)})
    return S,details

def compute(d,seed=0,star_choice=0):
    T,P4=input_periods(d);E=PolarEngine(d,T,N=6);q=E.q;A,R,U,V=E.A,E.R,E.U,E.V
    M=mp.gamma(-q)*mp.gamma(2*q)**2/mp.gamma(3*q)
    N=mp.digamma(-q)+mp.digamma(3*q)-mp.digamma(1)-mp.digamma(2*q)
    b3=T+mp.mpf(87)/4*A*A-mp.mpf(9)/4*R+M
    b4=-mp.mpf(393)/4*A**3-mp.mpf(11)/2*A*M-9*A*T+mp.mpf(117)/4*A*R-mp.mpf(3)/2*M*N-6*P4-mp.mpf(165)/8*U+mp.mpf(9)/4*V
    S4,details4=four_sum(E)
    rows=json.load(open('graphs_n5.json'));S5={};details5=[]
    for row in rows:
        val,meta=evaluate(E,row,seed=seed,star_choice=star_choice)
        S5=E.add(S5,E.scale(val,F(row['weight'])));details5.append((val,meta))
    u=X(1,F(-1,4));Jn={n:outer(E,u,(2*n-1)*u-(n-2)*HALF) for n in (2,3,4,5)}
    h=E.conv(2*u,2*u)
    f2=E.scale(Jn[2],F(1,6))
    f3=E.add(E.shift(Jn[2],-1),E.scale(E.mul(h,Jn[3]),F(-1,4)))
    f4=E.add(E.mul({-2:mp.mpf(9)/2,-1:-A},Jn[2]), E.scale(E.shift(E.mul(h,Jn[3]),-1),F(-9,4)), E.mul(S4,Jn[4]))
    f5=E.add(E.mul({-3:mp.mpf(18),-2:-10*A,-1:b3/9},Jn[2]),E.mul({-2:mp.mpf(-27)/2,-1:9*A/4},h,Jn[3]),E.scale(E.shift(E.mul(S4,Jn[4]),-1),12),E.scale(E.mul(S5,Jn[5]),-1))
    gs={1:mp.mpf(1)/3,2:2*A/9,3:8*A*A/27-b3/81,4:40*A**3/81-(10*A*b3+b4)/243}
    fs={2:f2,3:f3,4:f4,5:f5}
    answer={}
    for n in (2,3,4,5):
        term=E.mul(*([gs]*n),{k:v for k,v in fs[n].items() if 0<=k<=5-n})
        answer=E.add(answer,term)
    K=mp.gamma(1-q)*mp.gamma(2*q)**3/(54*mp.gamma(1+q)*mp.gamma(4*q))
    B=mp.digamma(-q)-mp.digamma(q);S=mp.polygamma(1,-q)-mp.polygamma(1,q)
    previous={2:-K,3:-K*(4*A/3-B/4),4:-K*(mp.mpf(25)/36*A*A-A*B/3+(B*B+S)/32+R/6-2*T/27)}
    out=dict(d=str(d),periods=dict(T=T,P4=P4),S4={k:S4.get(k,0) for k in (-2,-1,0,1)},S5=S5,
        fs={n:{k:fs[n].get(k,0) for k in range(-3,6-n)} for n in fs},
        coefficients={n:answer[n] for n in (2,3,4,5)},previous_checks={n:answer[n]-previous[n] for n in previous},graphs5=details5)
    return out

def stringify(x):
    if isinstance(x,mp.mpf):return mp.nstr(x,45)
    if isinstance(x,dict):return {k:stringify(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [stringify(v) for v in x]
    return x
if __name__=='__main__':
    mp.mp.dps=65
    for d in (1,2,3):
        result=compute(d)
        print('d',d,'a coefficients',stringify(result['coefficients']),flush=True)
        print('S4',stringify(result['S4']),'S5',stringify(result['S5']),flush=True)
        print('previous checks',stringify(result['previous_checks']),flush=True)
        print('f5 poles',stringify({k:result['fs'][5][k] for k in (-3,-2,-1)}),flush=True)
        json.dump(stringify(result),open(f'assembled_d{d}.json','w'),indent=2)
