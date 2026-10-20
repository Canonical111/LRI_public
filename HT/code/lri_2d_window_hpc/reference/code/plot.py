#!/usr/bin/env python3
"""Plot direct finite-cutoff data. No fitted continuum curves or error bands."""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def table(name):
    with (ROOT/'results/tables'/name).open() as f:return list(csv.DictReader(f))
def finish(fig,name):
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    fig.savefig(out/(name+'.png'),dpi=180);fig.savefig(out/(name+'.svg'));plt.close(fig)
def main():
    rows=table('curve.csv')
    fig,ax=plt.subplots(figsize=(9,5.7))
    for key,label,style in [('raw_L10','Raw, L=10','s--'),('window_L6','Window, L=6','o-'),('window_L8','Window, L=8','o-'),('window_L10','Window, L=10','o-'),('window_L12','Window, L=12 (selected points)','x')]:
        rr=[r for r in rows if r.get(key)]
        ax.plot([float(r['x']) for r in rr],[float(r[key]) for r in rr],style,label=label,markersize=4)
    ax.plot([.125,.5],[1,1],'D',linestyle='none',label='Endpoint benchmarks (not fitted)',markersize=6)
    ax.set(xlabel=r'$\Delta_\sigma$',ylabel=r'$\Delta_{\mathcal{E}}^{\mathrm{HT}}$',title='2D direct Hamiltonian truncation: full-vacuum window')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.text(.5,.01,'Finite-cutoff spectra, not a controlled continuum curve. Optimized local bases trained at L=6.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,1));finish(fig,'curve')
    rows=table('first_descendant_comparison.csv')
    fig,ax=plt.subplots(figsize=(9,5.7))
    for fam in ['sigma','thermal','chi']:
        rr=[r for r in rows if r['family']==fam and r.get('raw_spacing_error') and r.get('window_spacing_error')]
        for name,style in [('raw','o--'),('window','s-')]:
            ax.semilogy([float(r['x']) for r in rr],[abs(float(r[name+'_spacing_error'])) for r in rr],style,label=f'{fam}, {name}',markersize=4)
    ax.set(xlabel=r'$\Delta_\sigma$',ylabel=r'$|\Delta_{A O}-\Delta_O-1|$',title='First-angular candidate spacings at L=10')
    ax.legend(fontsize=8,ncol=2);ax.grid(alpha=.2)
    fig.text(.5,.01,'Free-generator ancestry only; several strong-coupling assignments have low overlap. See CSV flags.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,1));finish(fig,'first_angular_errors')
    rows=table('local_convergence.csv')
    fig,ax=plt.subplots(figsize=(9,5.4))
    for comp in ['nested density 12 versus 16','transferred density16 versus independent moving32/256']:
        rr=[r for r in rows if r['comparison']==comp]
        ax.semilogy([float(r['x']) for r in rr],[max(abs(float(r['thermal_difference'])),1e-16) for r in rr],'o-',label=comp)
    ax.set(xlabel=r'$\Delta_\sigma$',ylabel='Absolute thermal-gap difference',title='Local-basis checks at L=10; thermal states excluded from training')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.text(.5,.01,'Differences between finite numerical representations, not physical error estimates.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,1));finish(fig,'local_basis')
    print('Generated 3 figures (PNG and SVG).')
if __name__=='__main__':main()
