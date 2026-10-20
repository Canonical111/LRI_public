# Factorization of the d=2 summand of gs:Kseries: g(m,n)=2 E_m E_n - (1/4) C_m C_n R(m,n), with C_k=c_k^2, E_k=e_k^2,
# c_k=(1/2)_k/k!, e_k=k!/(3/2)_k. All of R is built from additive single-index pieces, so g = sum_i alpha_i A_i(m) B_i(n).
import sympy as sp, json
names=['x1','x2','x3','x4','w0','w1','w2','w3']   # x_j(k)=psi_{j-1}(k+1/2)-psi_{j-1}(k+1); w_j(k)=psi_j(k+1)
M=sp.symbols(' '.join(n+'m' for n in names)); N=sp.symbols(' '.join(n+'n' for n in names))
k2,k4,p1,p3,cs=sp.symbols('kappa2 kappa4 psi1one psi3one cstar')  # kappa_j=2(psi_{j-1}(1)-psi_{j-1}(1/2)), psi_j(1), c*=2psi0(1)
x=lambda j:M[j-1]+N[j-1]; w=lambda j:M[4+j]+N[4+j]
l1,l2,l3,l4=x(1),x(2)+k2,x(3),x(4)+k4
psione={0:0,1:p1,2:0,3:p3}       # only odd j enter via (1-(-1)^j)psi_j(1)
lam={1:l1,2:l2,3:l3,4:l4}
r={j:lam[j+1]/2+w(j)-(1-(-1)**j)*psione[j] for j in range(4)}
R=((r[0]-cs)/2*(l1**3+3*l1*l2+l3)+sp.Rational(3,4)*r[1]*(l1**2+l2)-(l1*r[2]+r[3])/4
   -l1**4/12+l1**2*l2/8+sp.Rational(7,24)*l1*l3+l2**2/8+l4/12)
P=sp.expand(-R/4)     # times C_m C_n ; plus the separate 2 E_m E_n term
terms={}
for mono,coef in sp.Poly(P,*M,*N).terms():
    key=('C',tuple(mono[:8]),'C',tuple(mono[8:]))
    terms[key]=sp.expand(terms.get(key,0)+coef)
terms[('E',(0,)*8,'E',(0,)*8)]=sp.Integer(2)
out=[{'mw':a,'m':list(b),'nw':c,'n':list(d),'coef':str(v)} for (a,b,c,d),v in terms.items() if v!=0]
json.dump({'names':names,'terms':out},open('K2_factorized.json','w'),indent=1)
singles={(t['mw'],tuple(t['m'])) for t in out}|{(t['nw'],tuple(t['n'])) for t in out}
print(len(out),'product terms;',len(singles),'distinct single sequences')
