"""Optional exact GMP scalar backend; no numerical approximation or new identities."""
def install_domain():
 import numbers
 from fast_fraction import Q
 numbers.Rational.register(Q)
 import sympy.polys.domains.rationalfield as rf
 from sympy.polys.domains import QQ
 rf.MPQ=Q
 cls=type(QQ)
 cls.dtype=Q;cls.tp=Q;cls.zero=Q(0);cls.one=Q(1)
 return Q

def install_endpoint():
 from fast_fraction import Q
 import scaled_b as sb
 sb.F=Q;sb.tb.F=Q;sb.mt.F=Q;sb.tp.F=Q;sb.nm.Q=Q
 return Q
