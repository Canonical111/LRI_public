import sys, time, mpmath as mp
from two_bubble import J2, J2_BA
mp.mp.dps = int(sys.argv[3]) if len(sys.argv) > 3 else 25
level = int(sys.argv[1]); K = mp.mpc(complex(sys.argv[2]))
t0 = time.time()
J = J2(K, level=level)
print(f'level {level}  K={mp.nstr(K, 6)}  time {time.time()-t0:.1f}s')
print('  J2^(0) engine :', mp.nstr(J[0], 20))
print('  J2^(0) BA     :', mp.nstr(J2_BA(K), 20))
print('  rel diff      :', mp.nstr(abs(J[0]/J2_BA(K) - 1), 3))
for k in (1, 2, 3): print(f'  J2^({k}) engine :', mp.nstr(J[k], 15))
