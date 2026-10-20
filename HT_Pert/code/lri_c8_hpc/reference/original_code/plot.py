#!/usr/bin/env python3
from pathlib import Path
import json
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    data=sorted([json.loads(p.read_text()) for p in (ROOT/'results/raw').glob('*_d8.json')],key=lambda r:r['cutoff'])
    fig,ax=plt.subplots(figsize=(8.3,4.8))
    ax.plot([r['cutoff'] for r in data],[r['C'][8]/1e6 for r in data],'o-',label='Direct raw Hamiltonian coefficients')
    ax.set_xlabel(r'Frozen free-energy cutoff $\Lambda$')
    ax.set_ylabel(r'$C_8(\Lambda)$, in millions')
    ax.set_title(r'Direct eighth-order $\varphi^4$ Hamiltonian truncation')
    ax.grid(alpha=.25);ax.legend()
    fig.text(.5,.01,'Finite-cutoff values; no physical continuum uncertainty band.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.03,1,1]);fig.savefig(out/'C8_raw_sequence.png',dpi=180);plt.close(fig)
    rows=json.loads((ROOT/'results/extrapolation_models.json').read_text())
    fig,ax=plt.subplots(figsize=(8.3,4.8))
    for model in ('A','B','C'):
        rr=sorted([r for r in rows if r['model']==model and r['hi']==50 and r['shift']==0],key=lambda r:r['lo'])
        ax.plot([r['lo'] for r in rr],[r['limits'][8]/1e6 for r in rr],'o-',label='Linked-tail basis '+model)
    ax.set_xlabel('Lower edge of fit window (upper edge fixed at 50)')
    ax.set_ylabel(r'Fitted $C_8$ intercept, in millions')
    ax.set_title('Conditional extrapolation: not a physical determination')
    ax.grid(alpha=.25);ax.legend()
    fig.text(.5,.01,'Uses C2/C3 controls and a single leading channel; standalone fits are much less stable.',ha='center',fontsize=8.5)
    fig.tight_layout(rect=[0,.03,1,1]);fig.savefig(out/'C8_conditional_extrapolation.png',dpi=180);plt.close(fig)
if __name__=='__main__':main()
