"""Render calculated susceptibilities and analytic subtractions, without fits."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def save(fig,name):
    p=ROOT/'figures';p.mkdir(exist_ok=True)
    for ext in ['png','svg']:fig.savefig(p/f'{name}.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)

def main():
    with (ROOT/'results/phase_overlap_convergence.csv').open() as f:r=list(csv.DictReader(f))
    x=np.array([float(a['mu']) for a in r]);y=np.array([float(a['complete_response4']) for a in r]);z=np.array([float(a['renormalized_finite_part']) for a in r]);C=float(r[0]['finite_part_comparison'])
    fig,ax=plt.subplots(figsize=(9,5.4))
    ax.semilogx(x,y,'o-',label='Complete low-bath phase response')
    ax.semilogx(x,z,'s-',label='After three derived overlap subtractions')
    ax.axhline(C,ls='--',label='Finite part from convergent sums/integrals')
    ax.set(xlabel=r'Auxiliary low-space cutoff $\mu$',ylabel=r'$\mathcal{R}_{\pi,4}(\mu)$',title='The boundary response is not a constant tail amplitude')
    ax.grid(alpha=.25);ax.legend(fontsize=9)
    fig.text(.5,.015,'This is one complete source response, not the physical fourth-order thermal coefficient. No cutoff fit.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));save(fig,'overlap_mixing')
    a=json.loads((ROOT/'results/general_bath_annulus.json').read_text());rr=[v for v in a if v['alpha']==.5 and v['reflection']==0]
    fig,ax=plt.subplots(figsize=(9,5.4))
    for key,label,marker in [('phase_only_error','Prior particle-phase term only','o'),('error','Including the low-bath level operator','s')]:ax.loglog([v['L'] for v in rr],[v[key] for v in rr],marker+'-',label=label)
    ax.set(xlabel=r'Annulus lower cutoff $\Lambda$',ylabel='Maximum matrix-entry discrepancy',title='General low-bath leading kernel: independent annulus test')
    ax.grid(alpha=.25);ax.legend()
    fig.text(.5,.015,'Both calculations include the same high-shell sums. The new term changes the observed error power.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));save(fig,'general_bath_kernel')
    print('Saved two PNG/SVG diagnostic figures')
if __name__=='__main__':main()
