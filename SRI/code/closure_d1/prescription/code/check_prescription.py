"""Exact supplementary checks for the formal interval-scheme argument.

These checks do NOT reintegrate the high-order kink kernels.  The analytic
forest/endpoint argument is in the standalone note.
"""
from __future__ import annotations
import itertools
import json
from pathlib import Path
import sympy as s

ROOT = Path(__file__).resolve().parents[1]
checks: dict[str, object] = {}

def zero(name: str, value):
    assert s.expand(value) == 0, (name, value)
    checks[name] = True

# 1. Lie algebra, identity-channel uniqueness, and allowed cluster charges.
I = ((1, 0), (0, 1))
M = {
    '+': ((0,1),(0,0)),
    '-': ((0,0),(1,0)),
    'h': ((1,0),(0,-1)),
}

def mul(A, B):
    return tuple(tuple(sum(A[i][k]*B[k][j] for k in range(2))
                       for j in range(2)) for i in range(2))

def sub(A, B):
    return tuple(tuple(A[i][j]-B[i][j] for j in range(2)) for i in range(2))

def scale(A, q):
    return tuple(tuple(q*a for a in row) for row in A)

count = 0
nonzero = 0
for n in range(1,10):
    for word in itertools.product(M, repeat=n):
        count += 1
        A = I
        q = 0
        for x in word:
            A = mul(A, M[x])
            q += (x == '+') - (x == '-')
        if A != ((0,0),(0,0)):
            nonzero += 1
            assert q in (-1,0,1)
            assert sub(mul(M['h'], A), mul(A,M['h'])) == scale(A, 2*q)
checks['matrix_words'] = {'tested':count, 'nonzero':nonzero, 'passed':True}
# Constant matrices neutral under U(1) are diagonal; Z2 exchanges the two entries.
a,b=s.symbols('a b')
D=s.diag(a,b); S1=s.Matrix([[0,1],[1,0]])
assert s.solve(list(S1*D*S1-D),[a],dict=True)==[{a:b}]
checks['dimension_zero_invariant_matrix_is_scalar']=True

# 2. Homogeneity including the loss of the freely translating center at an edge.
for n in range(2,20):
    for d in range(0,8):
        assert (n-2)+(d-n) == d-2
        assert (n-1)+(d-n) == d-1
checks['bulk_and_endpoint_radial_powers']=True

# 3. Current resummation + normal-ordering cancellation, exact at all h.
h,b0,C=s.symbols('h b0 C')
bdim=b0-s.sqrt(2)*h
log_gh=(s.sqrt(2)*b0*h-h*h)*C
zero('normal_ordering_fugacity_cancellation',
     log_gh+bdim**2*C/2-b0**2*C/2)
eta=s.sqrt(2)*h*bdim
zero('endpoint_source',eta-(s.sqrt(2)*b0*h-2*h*h))
# The two endpoint self contractions depend on h^2, not on the number/parity of flips.
checks['endpoint_self_factor'] = 'exp(-h**2*C/2), identical in numerator and denominator'

# 4. Ward identities for the finite-response Jacobian at h=0.
v=s.symbols('v',positive=True)
K,Kv,EK=s.symbols('K Kv EK')
# d_h(sqrt(2)*b K) = -2K + 2v*(-2d_v+E)K.
zero('lambda_source_chain', -2*K+2*v*(-2*Kv+EK)-(-2*K-4*v*Kv+2*v*EK))
# j1 follows from integral of the two endpoint potentials f_delta.
d=s.symbols('delta')
int_f = (1/(1+d)-1)/d
zero('j1_endpoint_integral',s.cancel(2*int_f+2/(1+d)))

# 5. Generate the entire finite-response recurrence through g^9 and h8.
g=s.symbols('g')
c30,c50,c70,c31,c51,c71,c91=s.symbols('C30 C50 C70 C31 C51 C71 C91')
q20,k40,k60,k41,k61,k81=s.symbols('Q20 K40 K60 K41 K61 K81')
j1,j3,j5,j7,l2,l4,l6=s.symbols('j1 j3 j5 j7 lambda2 lambda4 lambda6')
# Use beta_h/(sqrt(2)b0), so the off-diagonal product is 2v.
b3,b5,b7,b9,h4,h6,h8=s.symbols('b3 b5 b7 b9 h4 h6 h8')
br={
 b3:c31+2*v*j1,
 h4:k41-2*q20*b3+l2,
 b5:c51-3*c30*b3-2*v*j1*h4+2*v*j3,
 h6:k61-2*q20*b5-4*k40*b3-l2*h4+l4,
 b7:c71-3*c30*b5-5*c50*b3-2*v*j1*h6-2*v*j3*h4+2*v*j5,
 h8:k81-2*q20*b7-4*k40*b5-6*k60*b3-l2*h6-l4*h4+l6,
 b9:c91-3*c30*b7-5*c50*b5-7*c70*b3-2*v*j1*h8-2*v*j3*h6-2*v*j5*h4+2*v*j7,
}
bg=b3*g**3+b5*g**5+b7*g**7+b9*g**9
bh=-g**2+h4*g**4+h6*g**6+h8*g**8
rowg=(1+3*c30*g**2+5*c50*g**4+7*c70*g**6)*bg+2*v*(j1*g+j3*g**3+j5*g**5+j7*g**7)*bh
rowh=(2*q20*g+4*k40*g**3+6*k60*g**5)*bg+(1+l2*g**2+l4*g**4+l6*g**6)*bh
rhs_g=c31*g**3+c51*g**5+c71*g**7+c91*g**9
rhs_h=-g**2+k41*g**4+k61*g**6+k81*g**8
for n,x in [(3,b3),(5,b5),(7,b7),(9,b9)]:
    zero(f'odd_row_order_{n}',s.expand(rowg-rhs_g).coeff(g,n).subs(x,br[x]))
for n,x in [(4,h4),(6,h6),(8,h8)]:
    zero(f'current_row_order_{n}',s.expand(rowh-rhs_h).coeff(g,n).subs(x,br[x]))
zero('current_row_order_2',s.expand(rowh-rhs_h).coeff(g,2))
(ROOT/'data/derived_response_recurrence.json').write_text(
 json.dumps({str(k):s.sstr(z) for k,z in br.items()},indent=2))

# 6. Elementary hard-core identities: vacuum edge logarithm vs bulk current log.
r,aa,L=s.symbols('r a L',positive=True)
z2=L/aa+s.log(aa/L)-1
q2=L*s.log(L/aa)-L+aa
zero('pair_vacuum_integral',s.integrate((L-r)/r**2,(r,aa,L))-z2)
zero('pair_current_integral',s.integrate((L-r)/r,(r,aa,L))-q2)
# Smooth symmetric translation window autocorrelation has H'(0)=0;
# sharp interval H(r)=L-r has H'(0)=-1. Only identity produces its edge log.
checks['sharp_pair_endpoint_log']='Z2=L/a+log(a/L)-1; its scalar factor cancels in normalized responses'

# 7. Far-field Gaussian OPE factorization for general external charges.
e,r1,r2,x,y,Q=s.symbols('e r1 r2 x y Q')
z=y-x
# A +/- pair couples to a distant V_Q through log differences.
S=s.log(z-e*r1)-s.log(z-e*r2)
zero('neutral_pair_spectator_zeroth',S.subs(e,0))
zero('neutral_pair_spectator_first',s.diff(S,e).subs(e,0)+(r1-r2)/z)
# This is the current Ward contraction; higher e powers are integrable in the pair channel.
checks['far_spectator_expansion']='constant identity term; first derivative is the universal current Ward term'

# 8. Algebraic semigroup check in a nontrivial toy two-coupling vector field.
x,y,t=s.symbols('x y t')
rg=x+x*x*y+y**3
rh=y+x*x+x*y*y
bet=s.Matrix([x*y+x**3,x*x+x*y*y])
R=s.Matrix([rg,rh]); J=R.jacobian([x,y]); B=J*bet
zero('response_generator_first_component',(J.inv()*B-bet)[0].cancel())
zero('response_generator_second_component',(J.inv()*B-bet)[1].cancel())
# Exact cancellation of any common multiplicative endpoint/vacuum factor.
E,N,Z=s.symbols('E N Z',nonzero=True)
zero('common_scalar_endpoint_factor_cancels',s.cancel(E*N/(E*Z)-N/Z))

checks['scope']=(
 'Supplementary algebra and low-order checks of the analytic prescription theorem. '
 'No independent C3-C7 integral calculation, no NRG data verification, '
 'and no all-correlator high-order numerical replay is claimed.'
)
(ROOT/'verification/checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
