"""Measured performance figures; each chart is a separate figure."""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];out=R/'results/figures';out.mkdir(parents=True,exist_ok=True)
def read(name):
 with (R/'results/tables'/name).open() as f:return list(csv.DictReader(f))
def finish(fig,name):
 fig.savefig(out/(name+'.png'),dpi=180);fig.savefig(out/(name+'.svg'));plt.close(fig)
def main():
 d=read('full_solve_timings.csv');d=sorted(d,key=lambda r:(int(r['L']),-float(r['x'])))
 positions=np.arange(len(d));width=.35
 fig,ax=plt.subplots(figsize=(10.2,5.9))
 for impl,off,label in [('baseline',-width/2,'Supplied 3D package'),('optimized',width/2,'Optimized 3D package')]:
  y=np.array([float(r[impl+'_seconds_median']) for r in d]);lo=np.array([float(r[impl+'_seconds_min']) for r in d]);hi=np.array([float(r[impl+'_seconds_max']) for r in d])
  bars=ax.bar(positions+off,y,width,label=label,yerr=np.array([y-lo,hi-y]),capsize=3)
  ax.bar_label(bars,labels=[f'{a:.2f} s' for a in y],padding=5,fontsize=9)
 ax.set_xticks(positions,[f"L={r['L']}, x={float(r['x']):g}" for r in d]);ax.set_ylabel('Elapsed seconds: median and full range')
 ax.set_title('3D consistent vacuum window: setup + retuning + final scalar validation')
 ax.legend();ax.grid(axis='y',alpha=.2);ax.set_ylim(0,1.25*max(float(r['baseline_seconds_max']) for r in d))
 fig.text(.5,.025,'Three serial independent processes per method; one thread; identical tolerances.\nExcludes imports/JIT, local-basis training and angular diagnostics. Static disk cache disabled.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.085,1,1));finish(fig,'full_solve_speed')
 d=read('setup_scaling.csv');Ls=sorted(set(int(r['L']) for r in d))
 fig,ax=plt.subplots(figsize=(8.8,5.6))
 for impl,label in [('baseline','Supplied setup'),('optimized','Optimized setup')]:
  g=sorted([r for r in d if r['implementation']==impl],key=lambda r:int(r['L']))
  ax.plot([int(r['L']) for r in g],[float(r['setup_seconds_median']) for r in g],marker='o',label=label)
 ax.set_xticks(Ls);ax.set_yscale('log');ax.set_ylabel('Median setup time (seconds, logarithmic scale)');ax.set_xlabel('Total bath cutoff L')
 ax.set_title('True scalar SO(3) projector and four bath vertices');ax.legend();ax.grid(alpha=.2)
 fig.text(.5,.025,'Three independent warmed-JIT runs. No eigensolves; no persistent disk cache.\nThe L=14 construction is not an L=14 nonperturbative curve calculation.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.085,1,1));finish(fig,'setup_scaling')
 print('Generated two figures in PNG/SVG.')
if __name__=='__main__':main()
