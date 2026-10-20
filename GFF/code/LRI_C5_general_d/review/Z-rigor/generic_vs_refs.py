"""Reviewed code (two-node formula) vs C63d spectral references (independent session) at generic d."""
import sys, json, time
import mpmath as mp
sys.path.insert(0, '<PROJECT>/LRI_C5_general_d/Z')
import Z_general as Zg
ref = json.load(open('<PROJECT>/LRI_C5_general_d/references/reference_values.json'))['values']
mp.mp.dps = 25
for d in ['1.25', '2.5']:
    r = ref['d=' + d]
    for od in r['offdiag']:
        st = time.time()
        W = Zg.W3_two_node(d, od['b'], 25)
        print('d=%s b=%s  two-node W3 = %s  ref = %s  rel %s (%.1fs)' % (d, od['b'], mp.nstr(mp.re(W), 22), od['W3'][:24], mp.nstr(abs(mp.re(W)/mp.mpf(od['W3'])-1), 3), time.time()-st))
    st = time.time()
    out = Zg.Z(d, 25, full=True)
    print('d=%s  Z = %s  ref %s  rel %s ; 3Q rel %s ; dW %s ; Z_zero_mode rel %s (%.1fs)' % (d, mp.nstr(out['Z'], 22), r['Z']['value'][:24],
          mp.nstr(abs(out['Z']/mp.mpf(r['Z']['value'])-1), 3), mp.nstr(abs(3*out['Q']/mp.mpf(r['threeQ']['value'])-1), 3),
          mp.nstr(out['dW'], 3), mp.nstr(abs(out['Z_zero_mode']/out['Z']-1), 3), time.time()-st))
