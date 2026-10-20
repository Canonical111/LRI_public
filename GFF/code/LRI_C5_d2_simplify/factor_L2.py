# Exact factorization of the d=2 (q=1/2) series gs:Lseries for L_2 into products of single-index sums.
# At q=1/2: T_{ln}=c_m c_n (m=l+n, c_k=(1/2)_k/k!), d_l weights turn the (l,n) half-lattice into the full (m,n) square,
# and every ingredient is m<->n symmetric and additive. So L_2 = -sum_{m,n} c_m^4 c_n^4 P(m,n) = -sum coeff*S[f]*S[g].
import sympy as sp, json
X1m,X2m,X3m,Ym,Z1m,Z2m,Z3m,X1n,X2n,X3n,Yn,Z1n,Z2n,Z3n=sp.symbols('X1m X2m X3m Ym Z1m Z2m Z3m X1n X2n X3n Yn Z1n Z2n Z3n')
k2,p1,p3=sp.symbols('kappa2 psi1h psi3h')   # kappa2=2(psi1(1)-psi1(1/2)), psi1h=psi1(1/2), psi3h=psi3(1/2)
l1=X1m+X1n; l2=X2m+X2n+k2; l3=X3m+X3n
mu1=(Ym+Yn)/2
e1=(Z1m+Z1n)/2-p1; e2=(Z2m+Z2n)/2; e3=(Z3m+Z3n)/2-p3
F4=sp.Rational(32,3)*l1**3+8*l1*l2+sp.Rational(2,3)*l3
F41=32*l1**2*e1+8*e1*l2+8*l1*e2+sp.Rational(2,3)*e3
P=sp.expand(4*mu1*F4+F41)
msyms=[X1m,X2m,X3m,Ym,Z1m,Z2m,Z3m]; nsyms=[X1n,X2n,X3n,Yn,Z1n,Z2n,Z3n]
names=['x1','x2','x3','y','z1','z2','z3']
terms={}
for mono,coef in sp.Poly(P,*msyms,*nsyms).terms():
    key=(tuple(mono[:7]),tuple(mono[7:]))
    terms[key]=sp.expand(terms.get(key,0)+coef)
def label(e):return '*'.join(f'{names[i]}^{p}' if p>1 else names[i] for i,p in enumerate(e) if p) or '1'
out=[{'m':list(em),'n':list(en),'mlabel':label(em),'nlabel':label(en),'coef':str(c)} for (em,en),c in terms.items()]
json.dump({'names':names,'terms':out},open('L2_factorized.json','w'),indent=1)
print(len(out),'product terms; distinct single sums:',len({tuple(t['m']) for t in out}|{tuple(t['n']) for t in out}))
