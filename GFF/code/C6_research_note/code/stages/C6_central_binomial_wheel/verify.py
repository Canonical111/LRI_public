"""Exact coefficient, symmetry and weighted-substitution checks.
The external analytic input is Mishev's completed-L transformation. The
second-order eigenpath consequence is rederived here, not numerically fitted.
Two project-specific earlier identities are retained under inputs/.
"""
from pathlib import Path
import json,hashlib,copy
import sympy as s
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'results';OUT.mkdir(exist_ok=True)
checks=[]
def check(label,expr):
    assert s.simplify(expr)==0,(label,s.simplify(expr))
    checks.append(label)
# Work exactly in Q(omega), omega^4+1=0, with omega=e^(pi*i/4).
w=s.Symbol('w'); minpoly=w**4+1
def red(p):return s.rem(s.Poly(s.expand(p),w),s.Poly(minpoly,w)).as_expr()
def fieldcheck(label,p):check(label,red(p))
p0=s.Matrix([s.Rational(1,2)]*4+[1,1,1])
v=s.Matrix([w**2,w,1,1-w+w**2,1+w**2,w**2-w**3,1+w**3])
a,b,c,d,e,f,g=s.symbols('a b c d e f g');vars=s.Matrix([a,b,c,d,e,f,g])
C=s.Matrix([g-c,a,b,g-d,1+a+b-f,g,1+a+b-e]);DC=C.jacobian(vars)
for k in range(7):
    check(f'Fixed point coordinate {k}',C[k].subs(dict(zip(vars,p0)))-p0[k])
    fieldcheck(f'Eigenvector coordinate {k}',(DC*v-w*v)[k])
fieldcheck('Eigenpath balance',v[4]+v[5]+v[6]-sum(v[:4]))
rho=1-w+w**3
fieldcheck('Very-well-poised alpha slope',v[3]+v[6]-v[4]-rho)
upper=[rho,v[6]-v[0],v[6]-v[1],v[6]-v[2],v[3],v[3]-v[4]]
lower=[v[0]+v[3]-v[4],v[1]+v[3]-v[4],v[2]+v[3]-v[4],v[6]-v[4],v[6]]
fieldcheck('Sum of half-parameter upper slopes',sum(upper)-4*rho)
fieldcheck('Sum of unit lower slopes',sum(lower)-2*rho)
fieldcheck('Upper squared slopes',sum(x*x for x in upper)-2*rho**2)
fieldcheck('Lower squared slopes',sum(x*x for x in lower))
fieldcheck('Gamma half-denominator slope',v[5]-v[3]+rho)
# Symbolic half-integer gamma/polygamma increment reduction.
H,H2,Hs,H2s,l,pi,k=s.symbols('H H2 Hs H2s ell pi k',real=True)
AA=4*H2-3*H-2*l+1/k
RR=4*H2s-Hs+2/k**2
L1=4*(2*H2-H)-2*H-2+2/k+(2-4*l)
L2=-2*(4*H2s-Hs)+4-4/k**2-4
check('Normalized logarithmic first derivative /rho',L1-2*AA)
check('Normalized logarithmic second derivative /rho^2',L2+2*RR)
check('Coxeter second coefficient /4rho^2',(L1**2+L2)/4-(AA**2-RR/2))
LL=8*H2-6*H-4*l+2/k
MM=5*pi**2/3-16*H2s+6*Hs-4/k**2
delta=pi**2/3-4*H2s+2*Hs
check('S7 summand reduction',LL**2+MM-(pi**2+2*delta)-4*(AA**2-RR/2))
# Eliminate the inherited cubic moment and S7, using their exact normalizations.
Bs,Bd,V,T4,D6,h,tau=s.symbols('Bs Bd V T4 D6 h tau')
S7=pi**2*V+2*D6
Hcubic=3*Bs/64-pi**2*S7/32
Csum=s.expand((Bs/2-16*Hcubic).subs(Bs,2*pi**4*V))
check('Quartic cubic/harmonic elimination',Csum-pi**2*D6)
check('Pointwise cubic identity',128*h**3+24*h*delta+tau-16*h*(8*h**2+delta)-(8*h*delta+tau))
Wpositive=8*pi*T4+5*Csum
check('Complete positive wheel centralization',Wpositive-pi*(8*T4+5*pi*D6))
# Known-part compensation relative to the actual latest W10 expression.
Q,G,A,Poct,Ell,W10,Wcen=s.symbols('Q G A Poct Ell W10 Wcen',real=True)
Tconst=s.Rational(3753,896)-s.Rational(4554752,13125)/Q**2
K=(5*Bd/(2*pi)-5*Bs/(4*pi)+6*pi**2+s.Rational(14733,4480)
   +81920*G/Q**2-s.Rational(1079926784,13125)/Q**2)
S0=(8+5*pi)*pi**2/3
replacement=K-S0-Wcen
# Independent bookkeeping route, through the saved Wpositive->Wres->Wtel definitions.
z5=s.Symbol('z5')
WTplus=pi*(S0+Wcen)
Wres=WTplus-4*pi**3/3-s.Rational(2480,3)*z5/pi**2
KT=s.Rational(5,2)*Bd-s.Rational(5,4)*Bs+s.Rational(14,3)*pi**3-s.Rational(9,10)*pi+81920*pi*(G-1)/Q**2-s.Rational(8192,625)*pi/Q**2-s.Rational(2480,3)*z5/pi**2
Wtel=(Wres-KT)/pi
check('W10 replacement through complete legacy chain',replacement-(Tconst-Wtel))
wheelmap={Bs:(1-4*A/pi)*Poct-8*Ell/pi,Bd:(5*A/(2*pi)-s.Rational(1,2))*Poct+5*Ell/pi}
shift=s.expand((393*pi**3*(K-S0)).subs(wheelmap))
old_path=ROOT/'inputs/previous_expression.json';inp=json.loads(old_path.read_text())
loc={n:s.Symbol(n,real=True) for n in 'A Q G Poct Ell pi Wcen'.split()}
old=s.sympify(inp['known_polynomial'],locals=loc)
new=s.expand(old+shift)
check('Complete weighted numerator',old+393*pi**3*replacement.subs(wheelmap)-(new-393*pi**3*Wcen))
check('Compact polynomial shift',shift-(s.Rational(17685,4)*A*Poct*pi+s.Rational(17685,2)*Ell*pi-s.Rational(1965,2)*Poct*pi**2+1310*pi**5-655*pi**6+s.Rational(5790069,4480)*pi**3+32194560*G*pi**3/Q**2-s.Rational(141470408704,4375)*pi**3/Q**2))
assert all(term.as_powers_dict().get(Q,0)>=0 for term in s.Add.make_args(new)), 'A reciprocal Q monomial remains'
checks.append('All reciprocal-Q terms removed from known polynomial')
# All other objects preserved literally; replace only active wheel object.
out=copy.deepcopy(inp)
terms=out['single_index_harmonic_series_terms']
old_ids=[t.get('id') for t in terms]
assert 'W10' in old_ids,old_ids
new_terms=[]
for t in terms:
 if t.get('id')=='W10':
  new_terms.append({'id':'Wcentral','name':'Wcentral','coefficient_in_r6':'-393*pi**3',
    'summation_indices':1,'n_starts_at':1,'a_n':'(1/2)_n/n!',
    'delta_n':'pi**2/3-4*H_(2*n)^(2)+2*H_n^(2)',
    'summand':'a_n**4*(8+5*pi*(4*n+1)*a_n**2)*delta_n',
    'sum':'sum(n=1..infinity,summand)',
    'coefficient_update':'a_(n+1)=a_n*(2*n+1)/(2*n+2); delta_(n+1)=delta_n-1/(n+1/2)**2+1/(n+1)**2',
    'initial_values':'a_1=1/2; delta_1=pi**2/3-3',
    'asymptotic':'14/(pi**2*n**4)+O(n**-5)',
    'positive':True,'q_or_Catalan_in_summand':False,
    'direct_tail_bound':'(8+20*pi/3)/(54*(N-3/4)**3), terms 1<=n<N, N>=1',
    'fixed_ordinary_pFq_evaluation_claimed':False,
    'tradeoff':'One central-binomial stream instead of two shifts; direct decay n^-4 rather than n^-10. Prior certified W10 evaluator remains available as a numerical alternative.'})
 else:new_terms.append(t)
out.update({'formula':'2187*C6 = known_polynomial + 835584*Lambda + 391680*H5real + 13056*sqrt(2)*(32*G+3*pi**2)*H3real - 393*pi**3*Wcentral + 96*Pa - 784*pi**(3/2)*L7',
 'known_polynomial':str(new),'known_shift_in_r6':str(shift),
 'scope':'A Coxeter second-order identity and two inherited wheel identities reduce the wheel to one central-binomial stream, linear in second-order harmonic numbers. Three auxiliary series remain. No finite summation, minimality, or upstream graph/RG recertification is claimed. Direct convergence slows from n^-10 to n^-4; the previous certified evaluator remains a valid alternative.',
 'single_index_harmonic_series_terms':new_terms,
 'active_auxiliary_series':['Wcentral','Pa','L7'],
 'latest_identity':'Wpositive=pi*((8+5*pi)*pi**2/3+Wcentral)',
 'provenance_latest':'The Coxeter second-coefficient identity is derived from Mishev invariance and the Bailey-Mishev 7F6 representation; its use here is informed by arXiv:2609.34016v1, Proposition 5.4. The central-wheel application and substitution are regenerated in verify.py.',
 'numeric_accuracy_note':'The central wheel has a separate exact-rational cubic-in-pi enclosure from finite fourth/sixth-power corrections. This certifies the defined central series, not the full upstream graph/RG coefficient.',
 'retained_previous_representation':'inputs/previous_expression.json',
 'central_wheel_identity':{'core':'sum a_n**4*(8*h_n*delta_n+tau_n) = pi**2*sum (4*n+1)*a_n**6*delta_n',
 'positive_wheel':'Wpositive=pi*[(8+5*pi)*pi**2/3+Wcentral]',
 'W10_replacement':str(replacement),
 'external_input':'Mishev completed L invariance and its 7F6 representation. The second-order selection identity is also Proposition 5.4 in arXiv:2609.34016v1.',
 'inherited_inputs':['quartic cubic identity','S7 to quartic-moment identity','Bsum=2*pi**4*V']},
 'previous_faster_evaluator_note':'The W10 hierarchy object is retained as provenance only; its target is W10, not Wcentral. The exact W10 replacement above converts between them.',
 'central_certified_evaluator':{
 'script':'certify.py',
 'initial_transcendental_constants':['pi'],
 'finite_approximant':'sum_(n=1..N-1) a_n**4*(8+5*pi*(4*n+1)*a_n**2)*delta_n + 8*a_N**4*q4_M(N) + 5*pi*a_N**6*q6_(M+1)(N)',
 'arithmetic':'exact rational cubic polynomial in pi, with rational interval enclosure of pi',
 'bound':'[(8/9)*K4+(110/189)*K6]/[(2*M+7)*(N-3/4)**(2*M+7)], N>=2, M>=0',
 'K_definition':'finite rational polynomial construction specified in DERIVATION.md Section 4 and implemented in certify.py',
 'certificate':'results/rational_intervals.json',
 'sample_enclosure':'N=256,M4=40,M6=41; width<2.123e-146',
 'scope':'The new central series only, not the complete physical six-loop coefficient.',
 'not_infinite_asymptotic_sum':True},
 'external_sources_this_reduction':[
 {'author':'Ilia D. Mishev','reference':'arXiv:1008.1011','role':'Completed-L invariance and 7F6 representation'},
 {'author':'Dianbin Bao','reference':'arXiv:2609.34016v1, Proposition 5.4','role':'Explicit second-coefficient selection identity, rederived here'},
 {'reference':'NIST DLMF 5.15; 5.11; 4.36','role':'Polygamma recurrence, gamma asymptotics, cosh product'}]})
# Preserve every top-level field except those explicitly replaced.
modified={'formula','known_polynomial','known_shift_in_r6','scope','single_index_harmonic_series_terms','active_auxiliary_series','latest_identity','provenance_latest','numeric_accuracy_note','retained_previous_representation'}
for key in inp:
 if key not in modified:assert out[key]==inp[key],key
checks.append('Every unaffected inherited top-level field preserved exactly')
(OUT/'updated_expression.json').write_text(json.dumps(out,indent=2)+'\n')
(OUT/'exact_checks.json').write_text(json.dumps({'all_checks_pass':True,'check_count':len(checks),'checks':checks,'shift':str(shift),'known_polynomial':str(new),'input_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),'symmetry_matrix':str(DC),'eigenvector':str(v),'scope':'Finite algebra verifies the specified analytic reduction, conditional on Mishev invariance and the retained project identities. No full C6 numerical value was used.'},indent=2)+'\n')
print('Passed',len(checks),'checks')
print('Shift:',shift)
print('Old terms',len(s.Add.make_args(old)),'new terms',len(s.Add.make_args(new)))
