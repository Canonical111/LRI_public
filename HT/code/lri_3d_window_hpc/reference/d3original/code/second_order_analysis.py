"""Independent finite rational sums and continuum integral at second order."""
from pathlib import Path
import sys,json,math
ROOT=Path(__file__).resolve().parents[1]
from check_second_order import C2
import mpmath as mp

def main():
    mp.mp.dps=65
    def f(u):
        q=u*u;r=mp.sqrt(1-q*q);H=mp.sqrt(2/(1+r));hm1=q*q/((1+r)**2*(H+1))
        return 2*u*hm1*(mp.mpf(2)/81/q**mp.mpf('2.5')+mp.mpf(2)/9*mp.sqrt(q)+mp.mpf(2)/81*q*q+mp.mpf(2)/9/q)
    value=mp.mpf(34)/243+mp.quad(f,[0,.25,.5,.9,1])
    comparison=(2-mp.pi+4*mp.log(2))/9
    ans={'integral':str(value),'note_expression':str(comparison),'difference':str(value-comparison),'scope':'Independent numerical integral of derived shell sum, not a rigorous interval enclosure','cutoffs':[{'L':L,'C2':C2(L)} for L in [0,2,4,6,8,10,12,16,32,64,128,256]],'tail_leading_coefficient':str(-mp.mpf(40)/(243*mp.sqrt(mp.pi)))}
    (ROOT/'results/second_order_checks.json').write_text(json.dumps(ans,indent=2));print(ans)
if __name__=='__main__':main()
