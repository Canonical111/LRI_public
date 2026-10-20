from pathlib import Path
import sympy as s,json
P=Path(__file__).parent
A,R,U,V,X,M,N,Q,K,Z,P4,P5,L=s.symbols('A R U V X M N Q K Z P4 P5 L')
loc={str(x):x for x in [A,R,U,V,X,M,N,Q,K,Z,P4,P5,L]}
j1,v1=s.symbols('j1 v1')
rows=json.loads((P/'rows_3_0_8.json').read_text())
b3=sum(s.sympify(r['wb'])*s.sympify(r['r'],locals=loc) for r in rows).subs(v1,j1+R).expand()
c3=sum(s.sympify(r['wc'])*s.sympify(r['r'],locals=loc) for r in rows).subs(v1,j1+R).expand()
assert s.expand(b3-(6*Q+s.Rational(87,4)*A*A-s.Rational(9,4)*R+M))==0
assert s.expand(c3-(s.Rational(7,2)*A*A-R/2+M/3))==0
four=json.loads((P/'sum4.json').read_text());five=json.loads((P/'sum5.json').read_text())
b4=s.sympify(four['b4'],locals=loc);c4=s.sympify(four['c4'],locals=loc);D4=3*c4-b4
D5=s.sympify(five['D5rem'],locals=loc)-54*A*P4-9*L-63*Q**2-24*P5
C4=(16*P4-A**3-8*A*Q-3*A*R+s.Rational(53,2)*U-3*V)/648
C5=(-1536*(P5+K)+384*A*P4-576*L-1728*Q**2+720*A*A*Q+1008*Q*R+7152*Z-15*A**4-90*A*A*R+414*A*U-108*A*V-117*R**2-75*X)/46656
asm4=(60*A**3-8*A*b3+18*A*c3+D4)/243
asm5=(336*A**4-60*A*A*b3+108*A*A*c3+b3*b3-3*b3*c3-10*A*b4+24*A*c4+D5)/729
assert s.expand(C4-asm4)==0
assert s.expand(C5-asm5)==0
pi,zet,H=s.symbols('pi zeta3 H')
d1={R:pi*pi/3,U:-2*pi**3-56*zet,V:-16*zet,X:s.Rational(14,15)*pi**4,Z:Q*H}
old4=(16*P4-A**3-A*pi*pi-8*A*Q-53*pi**3-1436*zet)/648
old5=(-1536*(P5+K)+384*A*P4-576*L-1728*Q**2+48*Q*(15*A*A+149*H+7*pi*pi)-15*A**4-30*A*A*pi*pi-828*A*pi**3-21456*A*zet-83*pi**4)/46656
assert s.expand(C4.subs(d1)-old4)==0
assert s.expand(C5.subs(d1)-old5)==0
# Centered balanced-wheel path: 18 t^2; central-only path: 6 t^2.
import analytic_core as ac
t=s.symbols('t');qc=s.Rational(1,2)
lt=ac.complete([qc-t,qc+t,qc-t,qc+t,qc+t])
assert s.expand(sum((v-qc)**2 for v in lt))==18*t*t
lc=ac.complete([qc,qc,qc,qc,qc+t])
assert s.expand(sum((v-qc)**2 for v in lc))==6*t*t
# Gamma subtraction in the common-kernel K proof.
# z=2*tau: coefficient of z^2 in the explicit Gamma product.
gamma2=A**4/6-A*A*R/2+R*R/8+A*(2*V-U)/12-X/48
sub2=A**4/6-A*A*R/2+R*R/8+A*(V+U)/6-X/48
assert s.expand(gamma2-sub2+A*U/4)==0
# New residue polynomial derived both directly and after integration by parts.
a,b,c,dd=s.symbols('l1 l2 l3 l4');p0,p1,p2,p3,c0=s.symbols('p0 p1 p2 p3 c0')
lser=-1/t+a+b*t+c*t*t/2+dd*t**3/6
pser=1/(2*t)+p0+p1*t+p2*t*t/2+p3*t**3/6
E=1+2*a*t+(2*a*a+b)*t*t+(s.Rational(4,3)*a**3+2*a*b+c/3)*t**3+(s.Rational(2,3)*a**4+2*a*a*b+b*b/2+2*a*c/3+dd/12)*t**4
F=(c0-pser)*(lser*lser/8-s.Rational(5,16)*s.diff(lser,t))+lser*s.diff(pser,t)/4-s.Rational(5,32)*s.diff(pser,t,2)
rr=s.expand(E*F).coeff(t,1)
answer=(p0-c0)/2*(a**3+3*a*b+c)+s.Rational(3,4)*p1*(a*a+b)-(a*p2+p3)/4-a**4/12+a*a*b/8+7*a*c/24+b*b/8+dd/12
assert s.expand(rr-answer)==0
out=dict(b3=str(b3),c3=str(c3),b4=str(b4),c4=str(c4),D4=str(s.expand(D4)),D5=str(s.expand(D5)),
         C4=str(s.expand(C4)),C5=str(s.expand(C5)),checks={'three_loop_benchmarks':True,'fourth_order_fixed_point':True,'fifth_order_fixed_point':True,'all_mass_Gamma_terms_cancel':not bool(C5.has(M,N)),'d1_C4':True,'d1_C5':True,'tetrahedron_quadratic_normalization':True,'K_Gamma_subtraction':True,'K_residue_polynomial':True},
         graph_rows={'three':8,'four_nonprimitive':26,'five_regular_nonzero':92,'five_wheel':6,'five_primitive':3,'five_zero_combined':28})
(P/'exact_checks.json').write_text(json.dumps(out,indent=2))
print('All exact checks passed')
