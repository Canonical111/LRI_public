"""Which flow coefficients enter C8 in the magnetization scheme, and with what (symbolic) coefficient."""
import time, sympy as sp, pickle
from mscheme_invariants import C_list
t0 = time.time()
Cs = C_list(4)
C8 = Cs[7]
print('built C1..C8 in %.1fs' % (time.time() - t0))
syms = sorted(C8.free_symbols, key=lambda s: str(s))
print('C8 depends on', len(syms), 'coefficients:')
lin = {s: sp.diff(C8, s) for s in syms}
for s in syms:
    m, n, k = map(int, str(s).split('_')[1:])
    print(f'  {s}  (u^{m} X^{n} delta^{k})  linear coefficient: {sp.simplify(lin[s]) if len(str(lin[s])) < 80 else "<expr>"}')
pickle.dump(Cs, open('../results/C_list4.pkl', 'wb'))
