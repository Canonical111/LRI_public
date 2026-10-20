import json, os, sys
import mpmath as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2e import GDK_TABLE, GDK_SPECIAL_R3, gdk_s, basis
mp.mp.dps = 110
mb = json.load(open('../../../K_general/position_space/K_d_values_mb_D100.json'))['values']
def ulp_check(printed, exact):
    s = printed.replace('...', '')
    dec = len(s.split('.')[1])
    err = abs(mp.mpf(s) - exact) / mp.mpf(10) ** (-dec)
    return float(err)  # in units of the last printed digit; correct rounding iff <= 0.5
for dk, (Ks, rs) in GDK_TABLE.items():
    K = mp.mpf(mb[dk]['K']); q = mp.mpf(dk) / 4
    A, R, U, V, X = basis(q)
    r3 = 4 * (K - U / 8 * (mp.psi(0, 1) + mp.psi(0, 2 * q) + 4 * mp.psi(0, q))) + gdk_s(q)[3]
    line = [dk, 'K ulp', round(ulp_check(Ks, K), 3), 'r3 ulp', round(ulp_check(rs, r3), 3)]
    if dk in GDK_SPECIAL_R3:
        line += ['special r3 ulp', round(ulp_check(GDK_SPECIAL_R3[dk], r3), 3)]
    print(*line)
# d=3 printed K3 in gdk:special: 1.14859464952717933655664631081067318763...
K3 = mp.mpf(json.load(open('<PROJECT>/LRI_C5_d3/wf_K3/K3_value.json'))['K3'] if 'K3' in json.load(open('<PROJECT>/LRI_C5_d3/wf_K3/K3_value.json')) else 0)
print('K3 json keys', list(json.load(open('<PROJECT>/LRI_C5_d3/wf_K3/K3_value.json')).keys())[:10])
