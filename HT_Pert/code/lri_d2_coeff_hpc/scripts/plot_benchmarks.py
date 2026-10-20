"""Plot measured complete runs, not projection of untested cluster performance."""
from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def main():
    with (ROOT/'results/benchmark_summary.csv').open() as f:
        rows=[r for r in csv.DictReader(f) if int(r['L'])==20]
    labels=['Original\n1 thread','Optimized\n1 thread','Optimized\n4 threads']
    x=np.arange(3)
    t=np.array([float(r['median_seconds']) for r in rows])
    low=t-np.array([float(r['min_seconds']) for r in rows])
    high=np.array([float(r['max_seconds']) for r in rows])-t
    fig,ax=plt.subplots(figsize=(8.4,5.2))
    ax.bar(x,t,yerr=np.array([low,high]),capsize=6)
    ax.set_xticks(x,labels);ax.set_ylabel('Complete coefficient calculation, seconds')
    ax.set_title('2D C0–C8 at L=20: measured full-run performance')
    for i,v in enumerate(t):ax.text(i,v+high[i]+4,f'{v:.2f} s',ha='center',va='bottom')
    ax.set_ylim(0,185);ax.grid(axis='y',alpha=.2)
    fig.text(.5,.017,'Median of three separate processes; whiskers show observed min/max.\nBasis construction and all consistent-window solves included; import/JIT warmup excluded.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.09,1,1))
    dest=ROOT/'figures';dest.mkdir(exist_ok=True)
    for ext in ('png','svg'):fig.savefig(dest/f'L20_runtime.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    mem=[float(r['median_peak_rss_GiB']) for r in rows]
    fig,ax=plt.subplots(figsize=(8.4,5.2))
    ax.bar(x,mem);ax.set_xticks(x,labels);ax.set_ylim(0,3.15)
    for i,v in enumerate(mem):ax.text(i,v+.06,f'{v:.3f} GiB',ha='center',va='bottom')
    ax.set(ylabel='Median peak process memory, GiB',title='2D C0–C8 at L=20: 56% less peak memory')
    ax.grid(axis='y',alpha=.2)
    fig.text(.5,.017,'Same physical cutoff, coefficient degree, and float64 vector precision.\nLocal process RSS measurements, not a target-cluster memory guarantee.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.09,1,1))
    for ext in ('png','svg'):fig.savefig(dest/f'L20_memory.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    print('Saved runtime and memory figures from the completed benchmark records.')
if __name__=='__main__':main()
