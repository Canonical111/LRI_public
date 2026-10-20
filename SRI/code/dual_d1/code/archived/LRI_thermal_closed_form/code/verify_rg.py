"""Independent symbolic RG checks and numerical invariant assembly.
The numerical T2 is assembled from computed residues P,R,S, NOT from
the zeta-value identity proved in the accompanying note.
"""
from pathlib import Path
import json
import math
import sympy as s

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
u,z,d=s.symbols('u z d')
a,b,c,f,p=s.symbols('a b c f p')
u2,z2=s.symbols('u2 z2')
Bu=2*u*(z+u+a*z*u+p*d*u+b*u*u)
Bz=(1+z)*(-d+4*u+c*u*u+f*z*u*u)
ustar=d/4+u2*d*d
zstar=-d/4+z2*d*d
sol=s.solve([s.expand(Bu.subs({u:ustar,z:zstar})).coeff(d,3),
             s.expand(Bz.subs({u:ustar,z:zstar})).coeff(d,2)],(u2,z2),dict=True)[0]
M=s.Matrix([Bu,Bz]).jacobian([u,z]).subs({u:ustar,z:zstar}).subs(sol)
T=s.series(s.trace(M),d,0,3).removeO().expand()
D=s.series(M.det(),d,0,3).removeO().expand()
D2=s.simplify(D.coeff(d,2));T2=s.simplify(T.coeff(d,2))
assert s.simplify(D2-(s.Rational(1,2)-a/2-c/8))==0
assert s.simplify(T2-(-a/8+b/4-c/32+f/16+p/2))==0
print('Fixed-point coefficients:',sol)
print('D2 =',D2)
print('T2 =',T2)
print()

# Reassemble fifth-order response counterterms from raw integrated moments.
l,g,h=s.symbols('l g h')
P,R,S=s.symbols('P R S'); Z2=s.zeta(2);Z3=s.zeta(3);rt=s.sqrt(2)
C3=2*l*l+5*l+3-2*Z2
C5=s.Rational(10,3)*l**4+s.Rational(62,3)*l**3+(s.Rational(95,2)-24*Z2)*l*l+(96-40*Z2-S)*l
GH2=4*l*l+10*l+12-2*Z2
F40=-62+36*Z2+30*Z3+16*s.log(2)
G3H=rt*(-s.Rational(20,3)*l**3-28*l*l+(-48+24*Z2)*l+F40)
H2ct=rt*l;G3ct=2*l*l-l
H4ct=rt*(s.Rational(4,3)*l**3-2*l*l-4*l)
G5ct=-s.expand(C5-2*rt*(l+1)*(H4ct+G3ct*H2ct)+3*C3*G3ct+GH2*H2ct**2+G3H*H2ct)
bexpr=-21+38*Z2+60*Z3+32*s.log(2)-S
assert s.simplify(-G5ct.coeff(l,1)-bexpr)==0
assert s.simplify(G5ct-(s.Rational(10,3)*l**4-s.Rational(22,3)*l**3-(8*s.pi**2+39)*l*l/6-bexpr*l))==0
print('Fifth-order raw-moment counterterm: PASS')

# High logarithms from a separate Lie-series calculation.
bg=-2*rt*g*h+g**3+2*g*h*h+8*rt*Z2*g**3*h
bh=-rt*g*g+2*h*g*g+4*rt*g**4
V=lambda F:s.diff(F,g)*bg+s.diff(F,h)*bh
flow=g;F=g
for n in range(1,5):
    F=s.expand(V(F));flow+=(-l)**n/s.factorial(n)*F
pred=s.expand(flow).coeff(g,5).subs(h,0)
for k in [2,3,4]:
    assert s.simplify(G5ct.coeff(l,k)-pred.coeff(l,k))==0
print('Fifth-order higher-logarithm consistency: PASS')

# Charge derivative of the fourth-insertion logarithms.
q=s.symbols('q')
AQ=8/q**2-6/q-6-4*Z2+P*q
AQv=32/q**3-4/q**2+(4+16*Z2)/q+R
MQv=s.series(AQv/(q*q*(q+1))+4*AQ*(2*q+1)/(q**3*(q+1)**2),q,0,0).removeO().expand()
Q4vdiv=sum(MQv.coeff(q,-k)*(-l)**(k-1)/s.factorial(k-1) for k in range(2,6))
K4vdiv=s.expand(Q4vdiv-2*l**3+8*l)
H2v=-s.Rational(8,3)*l**3+2*l*l+24*l+44-12*Z2-8*Z3
H2=4*l*l+10*l+10-4*Z2
Q=-l-1;Qv=l*l-2;C3ctv=-s.Rational(4,3)*l**3+3*l*l+4*Z2*l
C4ctv=s.expand(-K4vdiv-2*Qv*G3ct-2*Q*C3ctv-H2v*l+H2*l*l)
fexpr=16*P+4*R-32+16*Z2+32*Z3
assert s.simplify(4*C4ctv.coeff(l,1)-fexpr)==0
print('Fourth-order charge derivative: PASS')

B=s.symbols('B')
bg=(B*B-1)*g+(1-4*Z2*(B*B-1))*g**3
bB=B*(2*g*g-8*g**4+f*(B*B-1)*g**4/2)
V=lambda F:s.diff(F,g)*bg+s.diff(F,B)*bB
flow=B;F=B
for n in range(1,7):
    F=s.expand(V(F))
    F=s.Add(*[t for t in s.Add.make_args(F) if t.as_powers_dict().get(g,0)<=4])
    flow+=(-l)**n/s.factorial(n)*F
pred=s.expand(s.expand(flow).coeff(g,4)/B).subs(B**2,1+z).expand().coeff(z,1)
assert s.simplify(pred.subs(f,fexpr)+2*C4ctv)==0
print('Fourth-order charge-flow higher logarithms: PASS')

# Finite-delta matching of the essential fugacity.
bg=(B*B-1)*g+(1-4*Z2*(B*B-1)+p*d)*g**3
bB=-d*B/2+2*B*g*g
V=lambda F:s.diff(F,g)*bg+s.diff(F,B)*bB
flow=g;F=g
for n in range(1,6):
    F=s.expand(V(F))
    F=s.Add(*[t for t in s.Add.make_args(F)
               if t.as_powers_dict().get(g,0)<=3 and t.as_powers_dict().get(d,0)<=1])
    flow+=(-l)**n/s.factorial(n)*F
pred=s.expand(flow.subs(B,1)).coeff(g,3).coeff(d,1)
matched=-s.Rational(4,3)*l**4+s.Rational(13,6)*l**3+2*Z2*l*l-p*l
assert s.simplify(pred-matched)==0
print('Finite-delta essential-fugacity matching: PASS')
print()

# Assemble numerical T2 from raw residues before comparison with the proved identity.
zeta2=float(s.N(Z2,18));zeta3=float(s.N(Z3,18));ln2=math.log(2)
pvalue=8-2*zeta2-7*zeta3-8*ln2
rows=[]
for N in [48,96,128]:
    suffix='_r0.13_m64' if N==128 else '_r0.19_m48'
    qfile=DATA/f'Q4_jet_N{N}{suffix}.json'
    gfile=DATA/f'G5_jet_N{N}{suffix}.json'
    if not qfile.exists():
        qfile=DATA/f'Q4_jet_N{N}.json'
    if not gfile.exists():
        gfile=DATA/f'G5_jet_N{N}.json'
    if not qfile.exists() or not gfile.exists():
        continue
    Qdata=json.loads(qfile.read_text());Gdata=json.loads(gfile.read_text())
    Pv=Qdata['coeff']['1'][0];Rv=Qdata['vcoeff']['0'][0];Sv=Gdata['coeff']['0'][0]
    av=-4*zeta2;cv=-16.0
    bv=-21+38*zeta2+60*zeta3+32*ln2-Sv
    fv=16*Pv+4*Rv-32+16*zeta2+32*zeta3
    determinant=0.5-av/2-cv/8
    trace=-av/8+bv/4-cv/32+fv/16+pvalue/2
    row=dict(N=N,P=Pv,R=Rv,S=Sv,a1=av,b1=bv,c1=cv,f1=fv,p=pvalue,
             D2=determinant,T2=trace,A=determinant-1/16,B=2*trace,
             reconstructed_T2=2-2*zeta2-4*zeta3,
             reconstruction_difference=trace-(2-2*zeta2-4*zeta3),
             period_identity_residual=Sv-4*Pv-5-28*zeta2-40*zeta3)
    rows.append(row)
    print(json.dumps(row,indent=2))
if not rows:
    raise RuntimeError('No complete quadrature pair found; run Q4 and G5 first.')
(DATA/'results.json').write_text(json.dumps(rows,indent=2))
print('\nAll symbolic consistency checks passed.')
print('Numerical convergence is not a rigorous interval error bound.')
print('The closed form is proved separately in the accompanying note and verify_closed_forms.py.')
