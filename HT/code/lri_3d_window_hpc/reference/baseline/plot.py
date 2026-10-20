"""Plot measured finite-cutoff spectra only; no fitted/interpolated continuum band."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent

def table(name):
 with (R/'results/tables'/name).open() as f:return list(csv.DictReader(f))
def finish(fig,name):
 out=R/'figures';out.mkdir(exist_ok=True)
 fig.savefig(out/(name+'.png'),dpi=190);fig.savefig(out/(name+'.svg'));plt.close(fig)
def main():
 rows=table('comparison.csv');x=np.array([float(d['x']) for d in rows]);b=json.loads((R/'inputs/benchmarks.json').read_text())['short_range_reference']
 fig,ax=plt.subplots(figsize=(11.8,6.6))
 ax.plot(x,[float(d['raw_L10']) for d in rows],'s--',markersize=4,label='Raw, L=10 (fresh replay)')
 for L in [6,8,10]:ax.plot(x,[float(d[f'window_L{L}']) for d in rows],'o-',markersize=4,label=f'Window, L={L}')
 sel=[d for d in rows if d.get('window_L12')]
 ax.plot([float(d['x']) for d in sel],[float(d['window_L12']) for d in sel],'x',linestyle='none',markersize=7,label='Window, L=12 (selected points)')
 ax.plot([b['Delta_sigma'],.75],[b['Delta_thermal'],1.5],'D',linestyle='none',markersize=7,label='Endpoint benchmarks (not fitted)')
 ax.set(xlabel=r'$\Delta_\sigma$',ylabel=r'$\Delta_\varepsilon^{\rm HT}$',title='3D dressed Hamiltonian truncation: self-consistent full-vacuum window')
 top=ax.secondary_xaxis('top',functions=(lambda t:3-2*t,lambda s:(3-s)/2));top.set_xlabel(r'$s=3-2\Delta_\sigma$')
 ax.legend(fontsize=9,loc='upper left');ax.grid(alpha=.2)
 fig.text(.5,.014,'Direct finite-cutoff spectra, not a controlled continuum curve. Local bases trained at L=6; thermal state held out.',ha='center',fontsize=10)
 fig.tight_layout(rect=(0,.045,1,1));finish(fig,'curve')
 fig,ax=plt.subplots(figsize=(9,5.8));row=next(d for d in rows if float(d['x'])==.5182)
 ls=[6,8,10,12]
 raw=[]
 for L in ls:
  p=next((R/f'reference/d3original/results/L{L}').glob('*_x0.51820000.json'));raw.append(json.loads(p.read_text())['Delta_thermal'])
 ax.plot(ls,raw,'s--',label='Original raw parent (20 local states/parity)')
 ax.plot(ls,[float(row[f'window_L{L}']) for L in ls],'o-',label='New consistent window')
 ax.axhline(b['Delta_thermal'],linestyle=':',label='Short-range endpoint benchmark (different x)')
 ax.set(xlabel='Total bath-level cutoff L',ylabel=r'$\Delta_\varepsilon^{\rm HT}$',title=r'Near the short-range end: $\Delta_\sigma=0.5182$')
 ax.set_xticks(ls);ax.legend(fontsize=9);ax.grid(alpha=.2)
 fig.text(.5,.015,'The window sequence crosses the endpoint benchmark and continues rising; proximity alone is not convergence.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.045,1,1));finish(fig,'endpoint_cutoff')
 data=table('first_descendant_comparison.csv');fig,ax=plt.subplots(figsize=(11,6))
 for fam in ['sigma','thermal','chi']:
  rr=[d for d in data if d['family']==fam]
  for mode,style in [('raw','--'),('window','-')]:
   ax.plot([float(d['x']) for d in rr],[float(d[mode+'_error']) for d in rr],style,marker='o',markersize=3,label=f'{fam}: {mode}')
 ax.axhline(0,linewidth=.6);ax.set(xlabel=r'$\Delta_\sigma$',ylabel=r'$E_{\partial O}-E_O-1$',title='First spin-one descendant candidates at the same L=10')
 ax.legend(ncol=2,fontsize=9);ax.grid(alpha=.2)
 fig.text(.5,.01,'Free-generator ancestry, not exact interacting charges. Low-overlap assignments are flagged in the accompanying CSV.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.05,1,1));finish(fig,'descendant_candidates')
 print('Generated three figures in PNG and SVG.')
if __name__=='__main__':main()
