"""Compare cluster_engine cx-mode outputs with exact references.
usage: python cluster_check.py n out1 [out2 ...]
n = 2: J2^{(0)} vs the Bethe ansatz (two_bubble.J2_BA); n = 3: J3^{(0)} vs J3_BA below."""
import sys
import mpmath as mp
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from cluster_assemble import read_out, assemble_cx
mp.mp.dps = 40


def J3_BA(K):
    """exact delta = 0 three-bubble cluster (DERIVATION.md / m3_step0.J3_BA_fun)."""
    a10 = 2 * (2 * K - 1) * mp.gamma(1 - 2 * K)
    b = lambda n: -(-1) ** (n + 1) * mp.gamma(mp.mpf(1) / 2 + n * (1 - K)) / (mp.sqrt(mp.pi) * mp.factorial(n) * mp.gamma(1 - n * K))
    a3 = a10 ** 3 * b(3) / b(1) ** 3
    return a3 / (2 * (1 + 6 * (K - 1)))


def J4_BA(K):
    """exact delta = 0 four-bubble cluster a1^4 b4 / b1^4 / (2 (1 + 8 (K - 1))) (m4_step0.J4_BA_fun)."""
    a10 = 2 * (2 * K - 1) * mp.gamma(1 - 2 * K)
    b = lambda n: -(-1) ** (n + 1) * mp.gamma(mp.mpf(1) / 2 + n * (1 - K)) / (mp.sqrt(mp.pi) * mp.factorial(n) * mp.gamma(1 - n * K))
    return a10 ** 4 * b(4) / b(1) ** 4 / (2 * (1 + 8 * (K - 1)))


def J2_BA(K):
    a10 = 2 * (2 * K - 1) * mp.gamma(1 - 2 * K)
    R = mp.sqrt(mp.pi) * mp.gamma(mp.mpf(5) / 2 - 2 * K) * mp.gamma(1 - K) ** 2 / (
        2 * mp.gamma(1 - 2 * K) * mp.gamma(mp.mpf(3) / 2 - K) ** 2)
    return a10 ** 2 * R / (2 * (4 * K - 3))


def Kof(hdr):
    return mp.mpc(mp.mpf(hdr['K']), mp.mpf(hdr['K_im'])) if 'K_im' in hdr else None


if __name__ == '__main__':
    n = int(sys.argv[1])
    for path in sys.argv[2:]:
        hdr, secs = read_out(path)
        # header: '# n 3 mode cx kmax 0 tau .. nseg .. m .. nplain .. K re im LS .. VMIN ..'
        line = open(path).readline().split()
        i = line.index('K'); K = mp.mpc(mp.mpf(line[i + 1]), mp.mpf(line[i + 2]))
        if 'Kdd' in line:
            j = line.index('Kdd'); K = mp.mpc(mp.mpf(float.fromhex(line[j + 1])) + mp.mpf(float.fromhex(line[j + 2])),
                                             mp.mpf(float.fromhex(line[j + 3])) + mp.mpf(float.fromhex(line[j + 4])))
        J, A = assemble_cx(n, secs, K, int(hdr['kmax']))
        ref = J3_BA(K) if n == 3 else J2_BA(K)
        tt = sum(s['time'] for s in secs.values())
        print(f'{path.split("/")[-1]:40s} K={mp.nstr(K, 12):>26}  J0={mp.nstr(J[0], 26):>58}  exact={mp.nstr(ref, 26)}'
              f'  rel.diff={mp.nstr(abs(J[0] / ref - 1), 3)}  wall={tt:.0f}s')
        for k in range(1, len(J)):
            print(f'{"":40s} J{k}={mp.nstr(J[k], 26)}')
