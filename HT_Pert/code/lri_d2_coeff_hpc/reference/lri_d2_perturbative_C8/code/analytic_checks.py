"""Independent finite sums for C2, the Gaussian vacuum, and first window effect.
These are checks/reporting functions; circle_jets does not import this module.
"""
from fractions import Fraction as F
import math,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def c2(L:int)->F:
    if L<0 or L%2:raise ValueError('even L required')
    z=F(17,81);c=F(1)
    for n in range(1,L//2+1):
        c*=F(2*n-1,2*n)
        z+=c*c*(F(2,81*(2*n-1))+F(1,9*n)+F(2,9*(2*n+1))+F(1,81*(n+1)))
    return z

def vacuum2(L:int)->F:
    K=L//2
    return -F((K+1)*(K+2),216)

def window4(L:int)->F:
    K=L//2;c=F(1);z=F()
    for n in range(1,K+1):
        c*=F(2*n-1,2*n)
        b=F(1,9*(2*n-1)**2)+F(1,4*n*n)+F(1,(2*n+1)**2)+F(1,36*(n+1)**2)
        z+=F(n*(2*K+3-n),972)*c*c*b
    return z

def main():
    import mpmath as mp
    mp.mp.dps=50
    Sodd2=mp.hyper([mp.mpf('.5')]*4,[mp.mpf(1),mp.mpf('1.5'),mp.mpf('1.5')],1)
    s1=mp.log(2)+mp.mpf(1)/9-2/(9*mp.pi)-Sodd2/2
    out=dict(C2_infinite=str(4*mp.log(2)/9),window4_linear_coefficient=str(s1/972),window4_log_coefficient=str(-5/(8748*mp.pi)),window4_asymptotic='deltaC4 = A*L - 5*log(L)/(8748*pi) + O(1); not an asymptotic claim for raw or full corrected C4 separately',finite=[dict(L=L,C2=str(c2(L)),vacuum2=str(vacuum2(L)),window4=str(window4(L))) for L in range(0,22,2)],scope='Independent exact finite sums, not thermal tuning targets.')
    (ROOT/'results/analytic_checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
