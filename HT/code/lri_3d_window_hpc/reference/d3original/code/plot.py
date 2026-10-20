from pathlib import Path
import json,csv
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
    rows=list(csv.DictReader((ROOT/'results/curve_points.csv').open()));dest=ROOT/'figures';dest.mkdir(exist_ok=True)
    benchmark=json.loads((ROOT/'inputs/benchmarks.json').read_text());sr=benchmark['short_range_reference']
    fig,ax=plt.subplots(figsize=(9.3,5.7))
    for L in (4,6,8,10,12):
        rr=sorted([r for r in rows if r['group']==f'L{L}'],key=lambda r:float(r['Delta_sigma_input']))
        ax.plot([float(r['Delta_sigma_input']) for r in rr],[float(r['Delta_thermal']) for r in rr],marker='o',markersize=3.5,label=rf'Sphere bath $L={L}$')
    ax.scatter([.75],[1.5],marker='D',s=55,label='Exact Gaussian endpoint')
    ax.errorbar([sr['Delta_sigma']],[sr['Delta_thermal']],xerr=[sr['Delta_sigma_uncertainty']],yerr=[sr['Delta_thermal_uncertainty']],fmt='s',markersize=6,capsize=4,label='Short-range bootstrap benchmark (not fitted)')
    ax.set(xlim=(.516,.752),xlabel=r'Exact long-range input $x=\Delta_\sigma=(3-s)/2$',ylabel=r'Finite-cutoff thermal gap $\Delta_{\mathcal{E}}$',title=r'3D long-range Ising: direct dressed-sphere Hamiltonian truncation')
    ax.grid(alpha=.25);ax.legend(fontsize=9)
    fig.text(.5,.015,'Raw product-regulator spectra. No continuum fit or physical error band; untuned descendants still fail.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.045,1,1]);fig.savefig(dest/'d3_direct_curve.png',dpi=185);fig.savefig(dest/'d3_direct_curve.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5.2))
    for L in (8,10):
        rr=[r for r in json.loads((ROOT/f'results/diagnostics_L{L}.json').read_text()) if r['spin']==1]
        rr=sorted(rr,key=lambda a:a['x'])
        for key,lab,mark in [('spin_descendant_error','Spin descendant','o'),('thermal_descendant_error','Thermal descendant','s')]:
            ax.plot([r['x'] for r in rr],[r[key] for r in rr],marker=mark,label=f'{lab}, L={L}')
    ax.axhline(0,linestyle='--',label='Required conformal value')
    ax.set(xlabel=r'$\Delta_\sigma$',ylabel=r'$E_{\partial O}-E_O-1$',title='Untuned spin-one diagnostics at the scalar-tuned couplings')
    ax.grid(alpha=.25);ax.legend(fontsize=9);fig.tight_layout();fig.savefig(dest/'rotational_diagnostics.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.7,5.1))
    checks=json.loads((ROOT/'results/second_order_checks.json').read_text())
    r=[a for a in checks['cutoffs'] if a['L']>0]
    ax.plot([a['L'] for a in r],[a['C2'] for a in r],marker='o',label='Independent finite-shell coefficient')
    ax.axhline(float(checks['note_expression']),linestyle='--',label=r'Note: $(2-\pi+4\log2)/9$')
    ax.set(xscale='log',xlabel=r'Bath level cutoff $L$',ylabel=r'$C_2(L)$',title='Independent weak-coupling normalization check')
    ax.grid(alpha=.25);ax.legend();fig.tight_layout();fig.savefig(dest/'C2_check.png',dpi=180);plt.close(fig)
if __name__=='__main__':main()
