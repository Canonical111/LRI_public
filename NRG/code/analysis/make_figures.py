"""Stage E: figures of the note (PDF) from the summaries and results.

Reads   results/ds13_final.json, results/lambda_study.json, data/summaries/*_summary.json, *_details.json
Writes  note/figures/fig_error_budget.pdf, fig_keep_nb.pdf, fig_lambda.pdf, fig_plateau.pdf, fig_alpha_c.pdf
Open symbols / hatched bars: Delta_sigma = 0.249, 0.24, 0.225, not converged in chain depth (not used in any comparison).
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from estimator import estimate,value

ROOT=Path(__file__).resolve().parents[2]
SUM=ROOT/'data'/'summaries';FIG=ROOT/'note'/'figures';FIG.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':9,'axes.labelsize':10,'legend.fontsize':8,'figure.dpi':150,'savefig.bbox':'tight','pdf.fonttype':42})
META={'CreationDate':None,'ModDate':None}
F=json.loads((ROOT/'results'/'ds13_final.json').read_text())
LS=json.loads((ROOT/'results'/'lambda_study.json').read_text())
ROWS=[r for c in ('ds13','lambda_pilot','lambda_followup') for r in json.loads((SUM/f'{c}_summary.json').read_text())]
DET={d['id']:d for c in ('ds13','lambda_pilot','lambda_followup') for d in json.loads((SUM/f'{c}_details.json').read_text())}
DS=[x['ds'] for x in F];FD={x['ds']:x for x in F}
NC=[x['ds'] for x in F if x['status']=='not converged']
CMAP=plt.get_cmap('viridis')
def color(ds):return CMAP(1-ds/0.25)


def get(ds,L,K,B):
    m=[r for r in ROWS if r['ds']==ds and r['Lambda']==L and r['keep']==K and r['nb']==B]
    return m[0] if m else None


def val(r):
    ds=r['ds'];return value(estimate(DET[r['id']],r['Lambda']),FD[ds]['estimator']=='extrapolated')


def fig_error_budget():
    fig,ax=plt.subplots(figsize=(6.0,3.1));x=np.arange(len(F));w=0.27
    comps=[('chain depth $\\delta_{\\rm depth}$','depth'),('$K$, $n_b$: $\\delta_K$','keep_nb'),('discretization $\\delta_\\Lambda$','Lambda')]
    for k,(lab,key) in enumerate(comps):
        ys=[max(f[key],1e-7) if f[key] is not None else 0 for f in F]
        bars=ax.bar(x+(k-1)*w,ys,w,label=lab,color=f'C{k}')
        for b,f in zip(bars,F):
            if f['status']=='not converged':b.set_hatch('////');b.set_alpha(0.45)
    tot=[(i,f['total']) for i,f in enumerate(F) if f['total'] is not None]
    ax.plot([i for i,_ in tot],[t for _,t in tot],'k_',ms=14,mew=1.5,label='total (linear sum)')
    for i,f in enumerate(F):
        if f['status']=='not converged':ax.text(i-w,2e-6,'n.c.',ha='center',fontsize=6.5,rotation=90)
    ax.set_yscale('log');ax.set_ylim(1e-6,3e-3);ax.set_xticks(x);ax.set_xticklabels([f"{f['ds']:g}" for f in F],rotation=45)
    ax.set_xlabel('$\\Delta_\\sigma$');ax.set_ylabel('error component of $\\Delta_E$')
    ax.legend(ncol=2,frameon=False,loc='upper right',fontsize=7)
    fig.savefig(FIG/'fig_error_budget.pdf',metadata=META);plt.close(fig)


def fig_keep_nb():
    fig,axs=plt.subplots(1,2,figsize=(6.8,3.0),sharey=True)
    for ds in DS:
        cen=FD[ds]['Delta_E'];ls='--' if ds in NC else '-';mfc='white' if ds in NC else None
        ks=[(k,get(ds,3,k,10)) for k in (48,64,96,128,160,192)];ks=[(k,r) for k,r in ks if r]
        axs[0].plot([k for k,_ in ks],[max(abs(val(r)-cen),1e-7) for _,r in ks],'o'+ls,ms=3,lw=.9,color=color(ds),mfc=mfc,label=f'{ds:g}')
        bs=[(b,get(ds,3,64,b)) for b in (8,10,12,16,20,24)];bs=[(b,r) for b,r in bs if r]
        axs[1].plot([b for b,_ in bs],[max(abs(val(r)-cen),1e-7) for _,r in bs],'o'+ls,ms=3,lw=.9,color=color(ds),mfc=mfc)
    axs[0].set_yscale('log');axs[0].set_xlabel('kept states $K$ ($n_b=10$, $\\Lambda=3$)');axs[1].set_xlabel('oscillator levels $n_b$ ($K=64$, $\\Lambda=3$)')
    axs[0].set_ylabel('$|\\Delta_E-\\Delta_E^{\\rm central}|$ (floored at $10^{-7}$)')
    axs[0].legend(title='$\\Delta_\\sigma$ (dashed: n.c.)',ncol=2,fontsize=6,title_fontsize=7,frameon=False,loc='upper right')
    for a in axs:a.grid(alpha=.3)
    fig.savefig(FIG/'fig_keep_nb.pdf',metadata=META);plt.close(fig)


def fig_lambda():
    fig,axs=plt.subplots(1,2,figsize=(7.4,3.2),constrained_layout=True)
    mk={64:'o',128:'s',192:'^',256:'D'}
    for i,ds in enumerate((0.2,0.1,0.05)):
        pts=[x for x in LS if x['ds']==ds and x['nb']==10]
        for K in (64,128,192,256):
            q=[x for x in pts if x['keep']==K]
            if q:axs[0].plot([x['Lambda'] for x in q],[x['value'] for x in q],mk[K],color=f'C{i}',mfc='none',ms=4.5)
        ref=[x for x in pts if x['Lambda']==3 and x['keep']==128][0]
        conv=[]
        for L,K in ((2,256),(2.5,128),(3,128),(4,64)):
            x=[p for p in pts if p['Lambda']==L and p['keep']==K]
            if x:conv.append((L,x[0]['value']-ref['value'],x[0]['plateau_drift'] if ds!=0.2 else 0,x[0]['mid']-ref['mid']))
        axs[1].errorbar([c[0]+0.03*(i-1) for c in conv],[1e4*c[1] for c in conv],yerr=[1e4*c[2] for c in conv],fmt='o-',ms=4,capsize=2,
                        color=f'C{i}',label=f'$\\Delta_\\sigma={ds:g}$'+(' (extrapolated)' if ds==0.2 else ''))
        axs[1].plot([c[0]+0.03*(i-1) for c in conv],[1e4*c[3] for c in conv],'x:',ms=4,lw=.7,color=f'C{i}',alpha=.6)
    for i,ds in enumerate((0.2,0.1,0.05)):axs[0].plot([],[],'-',color=f'C{i}',label=f'$\\Delta_\\sigma={ds:g}$')
    for K in (64,128,192,256):axs[0].plot([],[],mk[K],color='0.3',mfc='none',ms=4.5,label=f'$K={K}$')
    axs[0].set_xlabel('$\\Lambda$');axs[0].set_ylabel('$\\Delta_E$ ($n_b=10$)')
    axs[0].legend(frameon=False,fontsize=6.5,ncol=2,loc='upper right');axs[0].grid(alpha=.3,which='both')
    axs[1].plot([],[],'x:',color='0.4',label='superseded midpoint');axs[1].axhline(0,color='k',lw=.6);axs[1].set_xlabel('$\\Lambda$')
    axs[1].set_ylabel('$10^4\\,[\\Delta_E(\\Lambda)-\\Delta_E(\\Lambda{=}3)]$');axs[1].set_title('largest $K$ run: 256, 128, 128, 64 at $\\Lambda$=2, 2.5, 3, 4 ($\\Lambda$=4: $K$ convergence not tested)',fontsize=7)
    axs[1].legend(frameon=False,fontsize=6.5);axs[1].grid(alpha=.3)
    fig.savefig(FIG/'fig_lambda.pdf',metadata=META);plt.close(fig)


def fig_plateau():
    fig,axs=plt.subplots(1,3,figsize=(7.4,2.8),constrained_layout=True)
    for ax,ds in zip(axs,(0.2,0.05,0.001)):
        r=get(ds,3,128,16);d=DET[r['id']];e=estimate(d,3.0);f=FD[ds]
        w=d['windows'];st=[x['start'] for x in w];y=[x['Delta_E'] for x in w]
        q=[(x['gap_relative_variation']<.005 and x['log_response_residual']<.003) for x in w]
        ax.axhspan(r['q_lo'],r['q_hi'],color='0.85',lw=0,label='old: quality range')
        ax.axhline(r['q_mid'],color='0.5',lw=.8,ls=':',label='old: midpoint')
        ax.plot(st,y,'.',color='0.55',ms=3,label='all windows')
        ax.plot([a for a,b in zip(st,q) if b],[a for a,b in zip(y,q) if b],'o',color='C0',ms=3,mfc='none',label='quality windows')
        ax.axvspan(e['settled_start']-e['h'],e['settled_start']+e['h'],color='C1',alpha=.15,lw=0)
        ax.plot([e['settled_start']],[e['settled']],'*',color='C1',ms=9,label='settled window $\\pm h$')
        if f['estimator']=='extrapolated':ax.axhline(f['Delta_E'],color='C3',lw=1,ls='--',label='extrapolated')
        ax.set_ylim(r['q_mid']-0.004,r['q_mid']+0.004);ax.set_title(f"$\\Delta_\\sigma={ds:g}$ ($N={r['nsites']}$, $w={w[0]['stop']-w[0]['start']}$)",fontsize=8)
        ax.set_xlabel('first site of the window');ax.grid(alpha=.3);ax.locator_params(axis='x',nbins=5)
    axs[0].set_ylabel('$\\Delta_E$ of the window');axs[0].legend(frameon=False,fontsize=5.5,loc='upper right')
    fig.savefig(FIG/'fig_plateau.pdf',metadata=META);plt.close(fig)


def fig_alpha_c():
    fig,ax=plt.subplots(figsize=(4.6,3.0))
    for L,K,B,m in ((2,64,10,'v'),(2.5,128,10,'^'),(3,128,16,'o'),(4,64,10,'s')):
        pts=[(ds,get(ds,L,K,B)) for ds in DS];pts=[(ds,r) for ds,r in pts if r]
        ax.plot([ds for ds,_ in pts],[r['alpha_c'] for _,r in pts],m+'-',ms=3,lw=.8,label=f'$\\Lambda={L:g}$, $K={K}$, $n_b={B}$')
    ax.set_xlabel('$\\Delta_\\sigma$');ax.set_ylabel('$\\alpha_c$ (non-universal)');ax.legend(frameon=False);ax.grid(alpha=.3)
    fig.savefig(FIG/'fig_alpha_c.pdf',metadata=META);plt.close(fig)


if __name__=='__main__':
    for f in (fig_error_budget,fig_keep_nb,fig_lambda,fig_plateau,fig_alpha_c):f();print('wrote',f.__name__)
