from pathlib import Path
import json,mpmath as m,sympy as s
ROOT=Path(__file__).parent
m.mp.dps=50
values=json.loads((ROOT/'spectral_master_values.json').read_text())
old=json.loads((ROOT/'reference_d1_coefficients.json').read_text())
print(old.keys())

def coeffs(d,Q,P4,P5,K,L,Z):
    d=m.mpf(d);q=d/4
    A=m.digamma(2*q)+m.digamma(1)-2*m.digamma(q)
    R=m.polygamma(1,2*q)-m.polygamma(1,1)
    U=m.polygamma(2,q);V=m.polygamma(2,1)+m.polygamma(2,2*q)
    X=m.polygamma(3,2*q)-m.polygamma(3,1)
    c4=(16*P4-A**3-8*A*Q-3*A*R+53*U/2-3*V)/648
    c5=(-1536*(P5+K)+384*A*P4-576*L-1728*Q**2+720*A*A*Q+1008*Q*R+7152*Z
          -15*A**4-90*A*A*R+414*A*U-108*A*V-117*R*R-75*X)/46656
    return list(map(lambda x:m.nstr(x,38),[d/2,-m.mpf(1)/6,A/9,(A*A+R-8*Q)/108,c4,c5]))
rows=[]
for row in values['rows']:
    d=row['d']
    if d==4:continue
    W3,P4,L,Z,K=map(lambda x:m.mpf(str(x)),row['values'])
    Q=W3/3
    if d==2:
        Q=(m.gamma(m.mpf(1)/4)/m.gamma(m.mpf(3)/4))**4/6
        Z=4*m.catalan*Q
        P5=m.mpf(str(values['zigzag_d2'][1]['5']))
    else:P5=m.mpf(str(json.loads((ROOT/'primitive_recheck.json').read_text())[-1]['P5']))
    rr={k:row[k]for k in ['d','spins','nodes','orders']}
    rr.update(Q=m.nstr(Q,35),P4=m.nstr(P4,35),P5=str(P5),K=m.nstr(K,35),L=m.nstr(L,35),Z=m.nstr(Z,35),coefficients=coeffs(d,Q,P4,P5,K,L,Z))
    rows.append(rr);print(rr)
q=m.mpf(1)/4;Q=m.gamma(q)**4/m.pi;A=m.pi+4*m.log(2);H=2*m.pi**2/3+8*m.catalan
K=2*m.polygamma(1,q)**2-m.pi**2*m.polygamma(1,q)+A*m.polygamma(2,q)/2
P4=m.mpf(old['P4']);P5=m.mpf(old['P5_fresh_gamma_moment']);L=m.mpf(old['L'])
rows.append(dict(d=1,coefficients=coeffs(1,Q,P4,P5,K,L,Q*H),scope='algebraic substitution using previously validated one-dimensional periods'))
(ROOT/'coefficient_values_new.json').write_text(json.dumps(rows,indent=2))
