import sys, time
import numpy as np
sys.path.insert(0, '..')
import c4lib as lib
import engine as eg
import chains as ch
N = 12
ser = lib.Series(N)
modes = eg.Modes(N, 3)
P = (0, 1, 2, 3)
def cmp(name, a, b):
    err = max(np.abs(a[p] - b[p]).max() for p in P); scale = max(np.abs(b[p]).max() for p in P)
    print(f"{name:28s} max|diff| = {err:.2e}  (scale {scale:.2e})")
t = time.time()
# 2-vertex
for kinds, d, op in ((["V","V"],[0,0],(1,0)), (["V","V"],[0,0],(2,1)), (["M","V"],[0,0],(1,0)), (["V","V"],[1,0],(1,0)),
                     (["V","V"],[2,0],(1,0)), (["V","V"],[1,1],(1,0)), (["M","V"],[1,0],(1,0)), (["M","V"],[0,1],(1,0))):
    a = lib.chain2(kinds, d, op, N, ser, P)
    b = ch.eval_group(kinds, d, [((op,), None)], N, modes, P)[0]
    cmp(f"{''.join(kinds)} d={d} op={op}", b, a)
# 3-vertex
for kinds, ops, dv in ((["V","V","V"],[(1,0),(1,0)],None), (["V","V","V"],[(2,1),(1,0)],None), (["M","V","V"],[(1,0),(1,0)],None),
                       (["V","M","V"],[(1,0),(1,0)],None), (["V","V","V"],[(1,0),(1,0)],0), (["V","V","V"],[(1,0),(1,0)],1)):
    a = lib.chain(kinds, ops, N, ser, P, deriv_vertex=dv)
    d = [0,0,0] if dv is None else [1 if i == dv else 0 for i in range(3)]
    b = ch.eval_group(kinds, d, [(tuple(ops), None)], N, modes, P)[0]
    cmp(f"{''.join(kinds)} ops={ops} dv={dv}", b, a)
# 4-vertex (pruned <=5 lines as c4)
a = lib.chain(["V"]*4, [(1,0)]*3, N, ser, P, max_lines=5)
b = ch.eval_group(["V"]*4, [0]*4, [(((1,0),)*3, None)], N, modes, P, max_lines=5)[0]
cmp("VVVV <=5 lines", b, a)
a = lib.chain(["V"]*4, [(1,0)]*3, N, ser, P)
b = ch.eval_group(["V"]*4, [0]*4, [(((1,0),)*3, None)], N, modes, P)[0]
cmp("VVVV all patterns", b, a)
print("time", time.time() - t)
