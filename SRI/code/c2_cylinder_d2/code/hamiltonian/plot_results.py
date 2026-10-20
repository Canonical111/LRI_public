"""Plot completed direct g^4 data; default matplotlib colours, no reference target."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from regulator_extrapolation import basis
ROOT=Path(__file__).parent
x=json.loads((ROOT/'FINAL_NUMERICAL_RESULTS.json').read_text())
fig,ax=plt.subplots(figsize=(8,5.3))
for model in x['representative_regulator_fits']:
    k=model['order'];r=[p for p in x['data_points'] if p['order']==k]
    lam=np.array([p['lam'] for p in r]);val=np.array([p['h_estimate'] for p in r]);err=np.array([p['spectral_model_half_spread'] for p in r])
    pts=ax.errorbar(lam,val,yerr=err,fmt='o',capsize=3,label=f'Regulator order {k}: spectral limits')
    xx=np.linspace(1e-5,max(lam),250);a=np.array([np.ones_like(xx)]+[basis(xx,t) for t in model['terms']]).T
    # No explicit colours: each plotted object uses the default cycle.
    ax.plot(xx,a@model['coefficients'],linestyle='--',label=f'Order {k}: regulator extrapolation')
ax.set_xlabel(r'Artificial regulator $\lambda$ (not physical $\delta$)')
ax.set_ylabel(r'Direct fourth-order coefficient $h(\lambda)$')
ax.set_title('Hamiltonian perturbation theory: three regulator families')
ax.grid(alpha=.25);ax.legend(fontsize=8,loc='lower left');ax.set_xlim(0,.53)
fig.text(.5,.015,'Error bars show spectral-model spread only; dashed curves are not confidence bands.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,.035,1,1));fig.savefig(ROOT/'regulator_convergence.png',dpi=170);plt.close(fig)
