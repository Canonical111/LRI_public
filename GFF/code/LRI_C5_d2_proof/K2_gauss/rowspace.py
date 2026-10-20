# Re-derive the q=1/2 residue polynomial R(m,n) of gs:Kpoly, write it in shifted variables P_j=psi_{j-1}(k+1/2)-psi_{j-1}(1/2),
# Q_j=psi_{j-1}(k+1)-psi_{j-1}(1) for k=m (suffix m) and k=n (suffix n), and check whether the row space of the bilinear
# coefficient matrix lies in the Gauss span {Y_a(P)Y_b(P)Y_c(-Q)}.
import sympy as sp, itertools
Pm=sp.symbols('Pm1:5'); Qm=sp.symbols('Qm1:5'); Pn=sp.symbols('Pn1:5'); Qn=sp.symbols('Qn1:5')
# fixed constants: psi_{j-1}(1/2), psi_{j-1}(1) symbolic
p_h=sp.symbols('h0 h1 h2 h3')  # psi_j(1/2), j=0..3
p_1=sp.symbols('o0 o1 o2 o3')  # psi_j(1)
def psi_half(j,P): return P[j]+p_h[j]      # psi_j(k+1/2), j=0..3
def psi_one(j,Q): return Q[j]+p_1[j]       # psi_j(k+1)
# q = 1/2 specialisation, directly from gs:seriesBase, gs:lambda, gs:rj:
# a = m+1/2, b = m+1 (m = l+n);  chi_j(n;q) = (-1)^j psi_j(n+1/2) + psi_j(1/2) - (-1)^j psi_j(1/2)
def lam(j):  # j=1..4
    jj=j-1
    chi=(-1)**jj*psi_half(jj,Pn)+p_h[jj]-(-1)**jj*p_h[jj]
    return psi_half(jj,Pm)-psi_one(jj,Qm)-(-1)**j*chi+(1+(-1)**j)*p_1[jj]-psi_one(jj,Qn)
def r(j):  # j=0..3
    return lam(j+1)/2+psi_one(j,Qm)+psi_one(j,Qn)-(1-(-1)**j)*p_1[j]
cs=p_1[0]+p_1[0]  # c_* = psi0(1)+psi0(2q), 2q=1
l1,l2,l3,l4=[lam(j) for j in (1,2,3,4)]
r0,r1,r2,r3=[r(j) for j in range(4)]
R=((r0-cs)/2*(l1**3+3*l1*l2+l3)+sp.Rational(3,4)*r1*(l1**2+l2)-(l1*r2+r3)/4
   -l1**4/12+l1**2*l2/8+sp.Rational(7,24)*l1*l3+l2**2/8+l4/12)
R=sp.expand(R)
# numeric constant values for later
import mpmath as mp
vals={}
for j in range(4):
    vals[p_h[j]]=sp.polygamma(j,sp.Rational(1,2)); vals[p_1[j]]=sp.polygamma(j,1)
print('R has',len(R.as_ordered_terms()),'terms')
# bilinear structure: monomials in m-vars x monomials in n-vars
mvars=list(Pm)+list(Qm); nvars=list(Pn)+list(Qn)
poly=sp.Poly(R,*mvars,*nvars)
mmon=set();nmon=set();coef={}
for mono,c in poly.terms():
    a=mono[:8];b=mono[8:]
    mmon.add(a);nmon.add(b);coef[(a,b)]=sp.simplify(c)
mmon=sorted(mmon);nmon=sorted(nmon)
print(len(mmon),'m-monomials',len(nmon),'n-monomials')
# Gauss span in m-variables: Y_a(P)Y_b(P)Y_c(-Q), a+b+c<=4, as polynomials in P,Q
def bell(n,xs):
    # complete Bell polynomial Y_n(x1..xn)
    if n==0: return sp.Integer(1)
    return sp.expand(sum(sp.binomial(n-1,i)*bell(n-1-i,xs)*xs[i] for i in range(n)))
Pv=list(Pm);Qv=[-q for q in Qm]
span=[]
for a in range(5):
    for b in range(a,5):
        for c in range(5):
            if a+b+c<=4:
                span.append(sp.expand(bell(a,Pv)*bell(b,Pv)*bell(c,Qv)))
# vector space: represent polys in m-vars as coefficient vectors over all monomials of weight<=4
allm=set()
for f in span:
    for mono,_ in sp.Poly(f,*mvars).terms(): allm.add(mono)
for a in mmon: allm.add(a)
allm=sorted(allm)
idx={m:i for i,m in enumerate(allm)}
def vec(f):
    v=[0]*len(allm)
    if f==0: return v
    for mono,c in sp.Poly(f,*mvars).terms(): v[idx[mono]]=c
    return v
Smat=sp.Matrix([vec(f) for f in span])
print('Gauss span rank',Smat.rank(),'of',len(span),'generators; ambient dim',len(allm))
# row space: for each n-monomial b, the m-polynomial sum_a coef[(a,b)] m^a
rows=[]
for b in nmon:
    f=sum(coef.get((a,b),0)*sp.prod([v**e for v,e in zip(mvars,a)]) for a in mmon)
    rows.append((b,sp.expand(f)))
# membership test, treat constants p_h,p_1 as generic symbols: coefficients are polynomials in constants -> test over field of rational functions
bad=[]
for b,f in rows:
    M2=Smat.col_join(sp.Matrix([vec(f)]))
    if M2.rank()>Smat.rank(): bad.append(b)
print('n-monomials whose m-row is NOT in the Gauss span:',len(bad))
for b in bad: print(b)

# quotient analysis: dimension of (G + Row)/G, with constants substituted numerically-exact (sympy polygamma values)
subsd={**vals}
def vecs(f): return [sp.nsimplify(sp.simplify(c.subs(subsd))) if c!=0 else 0 for c in vec(f)]
Gm=sp.Matrix([vec(f) for f in span])
Rm=sp.Matrix([vec(f) for _,f in rows]).subs(subsd)
Rm=Rm.applyfunc(lambda c: sp.simplify(c))
big=Gm.col_join(Rm)
print('rank G',Gm.rank(),' rank Row',Rm.rank(),' rank G+Row',big.rank())
# which pure monomials are missing: test each monomial for membership in G
names_m=[str(v) for v in mvars]
def monostr(a): return '*'.join(f'{n}^{e}' if e>1 else n for n,e in zip(names_m,a) if e) or '1'
missing=[]
for a in allm:
    f=sp.prod([v**e for v,e in zip(mvars,a)])
    if Gm.col_join(sp.Matrix([vec(f)])).rank()>Gm.rank(): missing.append(monostr(a))
print('monomials not in G:',missing)

# explicit quotient directions: reduce each row modulo G (row-echelon over G's pivots) and list a basis of the residue space
import itertools
Gech=Gm.rref()[0]
piv=Gm.rref()[1]
def reduce_mod_G(v):
    v=sp.Matrix([v])
    for i,p in enumerate(piv):
        if v[p]!=0:
            v=v-v[p]*Gech.row(i)
    return v.applyfunc(sp.simplify)
res=[]
for b,f in rows:
    v=reduce_mod_G([sp.simplify(sp.sympify(c).subs(subsd)) for c in vec(f)])
    if any(c!=0 for c in v):
        res.append((b,v))
print('rows with nonzero residue mod G:',len(res))
Mres=sp.Matrix([list(v) for _,v in res])
print('rank of residues',Mres.rank())
for b,v in res:
    terms=[f'({sp.nsimplify(c)})*{monostr(allm[i])}' for i,c in enumerate(v) if c!=0]
    print('n-mono',monostr(b).replace('m','n'),':',' + '.join(terms))
