import numpy as np, json
import engine as eg, windows5 as w5, partners as pt, assemble as asm
N = 9
modes = eg.Modes(N, 3)
dE, T = pt.dE3(modes, N)
def efun(k, z):
    return {(): dE[z]} if (k == 3 and z in dE) else {(): np.zeros(N + 1)}
res = w5.eval_window_group(["V", "V"], [0, 0], [(((2, 0),), 0, 3)], N, modes, efun)
# word: g1^2 <V R D3 R V>  -> slice op R^2 after merging (R before + R after)
val = res[0][()]
d = (1 / 9.0) * asm.Pi(val)
# observed: zeromode_exact - mine (validate_win log)
obs = {2: -3.112183200038032e-05, 4: 1.724307199957309e-05, 6: 1.483905499988225e-05, 8: 1.0774860001561137e-05,
       10: 7.8591399983452e-06, 12: 5.886911999652966e-06, 14: 4.5328950015743885e-06, 16: 3.5773059998689405e-06,
       18: 2.8837219971933337e-06}
for L in range(2, 19, 2):
    print(L, "predicted shift %+.6e   observed (exact - mine) %+.6e   diff %.1e" % (d[L // 2], obs[L], d[L // 2] - obs[L]))
