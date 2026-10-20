#!/usr/bin/env python3
"""Fresh real-axis Gamma-kernel comparisons, independent of Horn evaluation.
The wheel tail uses analytically integrated centered-Stirling coefficients.
The zig-zag spin tail uses a finite Euler acceleration. No interval enclosure.
"""
from pathlib import Path
import json,time
import mpmath as mp
OUT=Path(__file__).resolve().parents[2]/'verification/general_d3'
OUT.mkdir(parents=True,exist_ok=True)

def wheel_tail(r,L,H):
    a=mp.mpf(1)/8
    logs=[mp.mpf(0)]+[-r*mp.bernpoly(2*j+1,a)/(j*(2*j+1)) for j in range(1,H+1)]
    e=[mp.mpf(1)]
    for j in range(1,H+1):e.append(sum(k*logs[k]*e[j-k] for k in range(1,j+1))/j)
    alpha=mp.mpf(3)*r/4
    out=mp.mpf(0)
    for h in range(H+1):
        c=2*mp.gamma(mp.mpf('1.5'))**r*mp.gamma(2*alpha+2*h-1)*sum(e[j]*e[h-j]/(mp.gamma(alpha+2*j)*mp.gamma(alpha+2*h-2*j)) for j in range(h+1))
        out+=c*mp.zeta(2*alpha-2+2*h,mp.mpf(L)+mp.mpf('.5'))
    return out

def wheel(L,H,breaks):
    g=mp.gamma(mp.mpf('1.5'));total=mp.mpc(0)
    for l in range(L):
        n=mp.mpf(l)+mp.mpf('.5')
        a=n/2+mp.mpf(1)/8;b=n/2+mp.mpf(7)/8
        def f(y):
            rat=abs(mp.gamma(a+mp.j*n*y/2)/mp.gamma(b+mp.j*n*y/2))**2
            return n*n/mp.pi*((g*rat)**3+mp.j*(g*rat)**4)
        total+=mp.quad(f,breaks)
        if l%20==0:print('wheel',mp.mp.dps,l,flush=True)
    return (total.real+wheel_tail(3,L,H))/3,total.imag+wheel_tail(4,L,H)

def zigzag(spins,depth,breaks):
    vals=[];g=mp.gamma(mp.mpf('1.5'))**5/(2*mp.pi)
    for l in range(spins):
        n=mp.mpf(l)+mp.mpf('.5');a=n/2+mp.mpf(1)/8;b=n/2+mp.mpf(7)/8
        def f(y):
            v=n*y/2
            rat=abs(mp.gamma(a+mp.j*v)/mp.gamma(b+mp.j*v))**2
            return (n*n+4*v*v)*(2*v*mp.tanh(2*mp.pi*v))*rat**7*n/2
        vals.append(g*(2*l+1)*mp.quad(f,breaks))
        if l%30==0:print('zigzag',mp.mp.dps,l,flush=True)
    start=12
    row=vals[start:start+depth];fac=mp.mpf('.5');tail=mp.mpf(0)
    while row:
        tail+=fac*row[0];row=[row[j]-row[j+1] for j in range(len(row)-1)];fac/=2
    return mp.fsum([(-1)**l*v for l,v in enumerate(vals[:start])])+(-1)**start*tail

rows=[]
for dps,L,H,spins,depth,breaks in [(45,48,22,184,168,[0,mp.mpf('.2'),1,4,mp.inf]),(60,72,32,232,216,[0,mp.mpf('.3'),mp.mpf('1.5'),6,mp.inf])]:
    mp.mp.dps=dps;st=time.time()
    Q,P4=wheel(L,H,breaks);P5=zigzag(spins,depth,breaks)
    row=dict(dps=dps,wheel_spins=L,wheel_tail_order=H,zigzag_spins=spins,euler_start=12,euler_depth=depth,breaks=[str(x) for x in breaks],Q3=str(Q),P4_3=str(P4),P5_3=str(P5),seconds=time.time()-st)
    rows.append(row)
    (OUT/'fresh_spectral.json').write_text(json.dumps(dict(scope='fresh Gamma-kernel integrals with changed quadrature breakpoints and tail settings; not interval bounds; no saved period input',rows=rows),indent=2)+'\n')
    print('COMPLETE',row,flush=True)
