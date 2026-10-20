"""Stage G (figures): the approach to the fixed point along the chain, and the final table against the references.

Reads   results/ds13_final.json, data/summaries/*_summary.json, *_details.json, method_comparison/comparison.json
Writes  note/figures/fig_flow.pdf
          local exponent Delta_loc(n) against RG time l = n ln Lambda (estimator.local_exponent):
          (a) Delta_sigma = 0.1, plateau, four values of Lambda; (b) 0.2, no plateau, extrapolated; (c) 0.249, the inverse
          excess over the epsilon series against l with the one-loop slope 3; (d) 0.001, Lambda and K at the 1e-4 level
        note/figures/fig_checks.pdf
          left   Delta_E against Delta_sigma: NRG (open: the three points not converged in chain depth, not used in any
                 comparison; no error bar), 1D cluster Monte Carlo (filled: ACCEPTED; open: CROSS-CHECK FAILED or
                 CONDITIONAL, not infinite-size values; bars sigma_stat + sigma_sys, linear), the epsilon series
                 (Borel-Pade, bars = spread over approximants; optimal truncation at 0.249) and 1 - 2 sqrt(Delta_sigma)
          right  NRG minus reference; bars = NRG delta_tot + reference error, added linearly

Usage   python code/analysis/check_figures.py [--root DIR]
"""
import argparse,json,math,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parent))
from estimator import local_exponent   # noqa: E402

plt.rcParams.update({'font.size':9,'axes.labelsize':10,'legend.fontsize':7.5,'figure.dpi':150,'savefig.bbox':'tight',
                     'pdf.fonttype':42})
META={'CreationDate':None,'ModDate':None}


def fig_flow(root,F,C):
    S=[r for c in ('ds13','lambda_pilot','lambda_followup') for r in json.loads((root/'data'/'summaries'/f'{c}_summary.json').read_text())]
    D={d['id']:d for c in ('ds13','lambda_pilot','lambda_followup') for d in json.loads((root/'data'/'summaries'/f'{c}_details.json').read_text())}
    def get(ds,L,K,B):return [r for r in S if r['ds']==ds and r['Lambda']==L and r['keep']==K and r['nb']==B][0]
    def loc(r):
        n,l,d=local_exponent(D[r['id']],r['Lambda']);return l,d
    fig,axs=plt.subplots(2,2,figsize=(8.0,6.0),constrained_layout=True);axs=axs.ravel()
    panels=[(0.1,'(a) $\\Delta_\\sigma=0.1$: plateau',[(2,256,10),(2.5,128,10),(3,128,10),(4,64,10)],(-3,12)),
            (0.2,'(b) $\\Delta_\\sigma=0.2$: no plateau, extrapolated',[(2.5,128,16),(3,128,16),(3,64,24)],(-5,40)),
            (0.001,'(d) $\\Delta_\\sigma=0.001$: $\\Lambda$ and $K$ at $10^{-4}$',[(2.5,64,10),(2.5,128,10),(3,128,16),(4,64,10)],(-4,16))]
    F={x['ds']:x for x in F}
    for ax,(ds,title,items,yl) in zip((axs[0],axs[1],axs[3]),panels):
        ref=F[ds]['Delta_E']
        for i,(L,K,B) in enumerate(items):
            ls='-' if (L,K,B)==(3,128,16) else '--';lw=1.8 if (L,K,B)==(3,128,16) else 1.3
            l,d=loc(get(ds,L,K,B));ax.plot(l,1e4*(d-ref),ls,lw=lw,color=f'C{i}',label=f'$\\Lambda={L:g}$, $K={K}$, $n_b={B}$'+(' (central)' if (L,K,B)==(3,128,16) else ''))
        c=get(ds,3,128,16);w=F[ds]['settled_window'];lnL=math.log(3)
        ax.axvspan(w[0]*lnL,(w[1]-1)*lnL,color='0.85',lw=0,label='settled window (central item)')
        ax.axhline(0,color='k',lw=.6);ax.set_ylim(*yl);ax.set_xlim(0,None);ax.set_title(title,fontsize=8.5)
        ax.set_xlabel('RG time $l=n\\ln\\Lambda$');ax.set_ylabel('$10^4\\,[\\Delta_{\\rm loc}-\\Delta_E]$');ax.grid(alpha=.3)
        ax.legend(frameon=False,fontsize=6.5,loc='upper right',handlelength=2.5)
    # (c) 0.249: inverse excess over the series against l; one loop: slope (N+8)/(N+2) = 3
    ax=axs[2];ser=C[0.249]['series_opt']
    for i,(L,K,B) in enumerate([(3,128,16),(3,64,16),(3,64,24),(2.5,128,16)]):
        l,d=loc(get(0.249,L,K,B));m=(l>=8)&(l<=55)&(d>ser)
        ax.plot(l[m],1/(d[m]-ser),'-',lw=1,color=f'C{i}',label=f'$\\Lambda={L:g}$, $K={K}$, $n_b={B}$')
    l,d=loc(get(0.249,3,128,16));j=int(np.argmin(abs(l-25)));ll=np.linspace(15,55,10)
    ax.plot(ll,1/(d[j]-ser)+3*(ll-l[j]),'k--',lw=1,label='one loop: slope $(N{+}8)/(N{+}2)=3$')
    ax.set_title('(c) $\\Delta_\\sigma=0.249$ ($\\varepsilon=0.004$): slow approach',fontsize=8.5)
    ax.set_xlabel('RG time $l=n\\ln\\Lambda$');ax.set_ylabel('$1/(\\Delta_{\\rm loc}-\\Delta_E^{\\rm series})$');ax.grid(alpha=.3)
    ax.legend(frameon=False,fontsize=6.5,loc='upper left')
    return fig


def fig_checks(F,C):
    fig,axs=plt.subplots(1,2,figsize=(10,3.9),constrained_layout=True)
    ax=axs[0]
    good=[x for x in F if x['status']=='final'];bad=[x for x in F if x['status']!='final']
    ax.errorbar([x['ds'] for x in good],[x['Delta_E'] for x in good],[x['total'] for x in good],fmt='o',ms=4,
                capsize=2,color='C0',label='NRG ($\\Lambda=3$, $K=128$, $n_b=16$)',zorder=3)
    ax.plot([x['ds'] for x in bad],[x['Delta_E'] for x in bad],'o',ms=4,mfc='white',color='C0',
            label='NRG, not converged in chain depth (not used)',zorder=3)
    mc=[r for r in C.values() if r.get('mc') is not None];acc=lambda r:r['mc_status'].startswith('ACCEPTED')
    bar=lambda r:r['mc_stat']+(0 if math.isnan(r['mc_sys']) else r['mc_sys'])
    for sel,lab,mfc in ((acc,'1D cluster Monte Carlo, ACCEPTED','C2'),
                        (lambda r:not acc(r),'Monte Carlo, CROSS-CHECK FAILED or CONDITIONAL','white')):
        q=[r for r in mc if sel(r)]
        ax.errorbar([r['ds']+0.002 for r in q],[r['mc'] for r in q],[bar(r) for r in q],fmt='s',ms=3.5,mfc=mfc,capsize=2,
                    color='C2',label=lab,zorder=2)
    ser=[r for r in C.values() if r['ds']>=0.2]
    ref=lambda r:r['series_bp'] if r['eps']>0.02 else r['series_opt']
    rer=lambda r:r['series_bp_spread'] if r['eps']>0.02 else r['series_opt_err']
    ax.errorbar([r['ds']-0.002 for r in ser],[ref(r) for r in ser],[rer(r) for r in ser],fmt='D',ms=3.5,capsize=2,color='C3',
                label='$\\varepsilon$ series ($C_0\\ldots C_8$, resummed)',zorder=2)
    d=np.linspace(0.0005,0.06,200);ax.plot(d,1-2*np.sqrt(d),':',color='0.4',lw=1.2,label='$1-2\\sqrt{\\Delta_\\sigma}$ ($s\\to1$)')
    ax.set_xlabel('$\\Delta_\\sigma$');ax.set_ylabel('$\\Delta_\\varepsilon=\\Delta_E$');ax.set_xlim(-0.005,0.255);ax.set_ylim(0.46,1.0)
    ax.legend(loc='upper right',frameon=False,fontsize=7);ax.set_title('(a) thermal dimension',fontsize=9)
    ax=axs[1]
    for r in ser:
        nc=r['nrg_err'] is None
        ax.errorbar(r['ds']-0.001,r['nrg']-ref(r),(0 if nc else r['nrg_err'])+rer(r),fmt='D',ms=4,capsize=2,color='C3',mfc='white' if nc else 'C3')
    for r in mc:
        nc=r['nrg_err'] is None;filled=acc(r) and not nc
        ax.errorbar(r['ds']+0.001,r['nrg']-r['mc'],(0 if nc else r['nrg_err'])+bar(r),fmt='s',ms=3.5,capsize=2,color='C2',
                    mfc='C2' if filled else 'white')
    ax.axhline(0,color='0.5',lw=0.8)
    ax.plot([],[],'D',color='C3',ms=4,label='NRG $-$ $\\varepsilon$ series');ax.plot([],[],'s',color='C2',ms=3.5,label='NRG $-$ Monte Carlo (ACCEPTED)')
    ax.plot([],[],'o',color='0.3',mfc='white',ms=4,label='open: NRG not converged, or MC not ACCEPTED (not used)')
    ax.set_xlabel('$\\Delta_\\sigma$');ax.set_ylabel('NRG $-$ reference');ax.set_xlim(0.01,0.255)
    ax.legend(loc='upper left',frameon=False,fontsize=7);ax.set_title('(b) differences',fontsize=9)
    return fig


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);a=ap.parse_args()
    F=json.loads((a.root/'results'/'ds13_final.json').read_text())
    C={r['ds']:r for r in json.loads((a.root/'method_comparison'/'comparison.json').read_text())}
    out=a.root/'note'/'figures';out.mkdir(parents=True,exist_ok=True)
    for name,fig in (('fig_flow.pdf',fig_flow(a.root,F,C)),('fig_checks.pdf',fig_checks(F,C))):
        fig.savefig(out/name,metadata=META);plt.close(fig);print(f'wrote {out/name}')


if __name__=='__main__':
    main()
