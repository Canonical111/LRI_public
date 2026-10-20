#!/usr/bin/env python3
"""Plot freshly generated CSV data; no source images or hidden data input."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
 rows=list(csv.DictReader((ROOT/'outputs/tables/wheel_convergence.csv').open()))
 N=[int(r['N']) for r in rows]
 error=[float(r['observed_remaining_tail']) for r in rows]
 bound=[float(r['proved_direct_tail_bound']) for r in rows]
 out=ROOT/'outputs/figures';out.mkdir(parents=True,exist_ok=True)
 fig,ax=plt.subplots(figsize=(7.0,4.3))
 ax.loglog(N,error,'o-',label='Observed remaining tail')
 ax.loglog(N,bound,'s--',label='Proved direct-tail bound')
 ax.set_xlabel('Cutoff N (terms 1 <= n < N)');ax.set_ylabel('Absolute remainder')
 ax.set_title('Wheel: literal partial sums and the analytic bound')
 ax.legend();ax.grid(True,which='both',alpha=0.25);fig.tight_layout()
 for ext in ['pdf','png']:fig.savefig(out/f'wheel_convergence.{ext}',dpi=180)
 plt.close(fig)
 print('Wrote outputs/figures/wheel_convergence.pdf and .png')
if __name__=='__main__':main()
