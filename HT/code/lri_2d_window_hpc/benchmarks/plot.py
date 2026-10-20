"""Plot saved benchmark medians; no fitted speedup or physical errors."""
from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
    d=json.loads((ROOT/'results/SUMMARY.json').read_text())
    cases=[(10,.126),(10,.25),(12,.25)]
    original=[];optimized=[]
    for L,x in cases:
        for impl,target in [('original',original),('optimized',optimized)]:
            target.append(next(r['median_seconds'] for r in d['full_solves']
                               if r['L']==L and r['x']==x and r['implementation']==impl))
    p=np.arange(len(cases));width=.34
    fig,ax=plt.subplots(figsize=(9.6,5.2))
    old=ax.bar(p-width/2,original,width,label='Original 2D port')
    new=ax.bar(p+width/2,optimized,width,label='Optimized tensor backend')
    ax.bar_label(old,fmt='%.2f s',padding=3,fontsize=10)
    ax.bar_label(new,fmt='%.2f s',padding=3,fontsize=10)
    ax.set_xticks(p,[f'L={L}, Δσ={x:g}' for L,x in cases])
    ax.set_ylabel('Median elapsed time (seconds)')
    ax.set_title('2D consistent vacuum window + primary retuning')
    ax.set_ylim(0,max(original)*1.20)
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.legend(loc='upper left')
    fig.text(.5,.025,'Three serial independent processes per method; one thread; same numerical tolerances.\n'
             'Includes setup, all vacuum solves, retuning and scalar validation. Excludes JIT, training and angular diagnostics.',
             ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.085,1,1))
    out=ROOT/'results/figures';out.mkdir(exist_ok=True)
    fig.savefig(out/'full_solve_speed.png',dpi=180)
    fig.savefig(out/'full_solve_speed.svg');plt.close(fig)
    print('Wrote benchmark chart (PNG/SVG).')

if __name__=='__main__':main()
