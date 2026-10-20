#!/usr/bin/env python3
"""Fresh convergence of the half-interval elliptic evaluation of the final C2.

This is a deterministic representation/refinement check, not a confidence
interval or a proof of physical renormalization. The final 4F3 expression is
reevaluated, never read from a saved reference output.
"""
from pathlib import Path
import argparse,csv,json,time
import mpmath as mp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from lri_C2_three_4F3 import coefficient,elliptic_moments
ROOT=Path(__file__).resolve().parents[1]


def run(dps,terms):
    mp.mp.dps=dps
    final=coefficient(dps);R=final['R'];rows=[]
    for n in terms:
        started=time.perf_counter()
        um,vm=elliptic_moments('-0.25',n,dps)
        up,vp=elliptic_moments('0.75',n,dps)
        f=mp.mpf('2.5')*um-4*up;g=mp.mpf('2.5')*vm-4*vp
        c=16/R**2-R**2/9-mp.pi*R**4*(f+g)*(f+3*g)/10368
        diff=c-final['C2']
        row={'half_interval_terms':n,'working_dps':dps,
             'C2_elliptic':mp.nstr(c,dps-8),'C2_three_4F3_fresh':mp.nstr(final['C2'],dps-8),
             'difference':mp.nstr(diff,dps-8),'absolute_difference':mp.nstr(abs(diff),dps-8),
             'elapsed_seconds':time.perf_counter()-started}
        rows.append(row);print(json.dumps(row),flush=True)
    return {'scope':__doc__,'working_dps':dps,'rows':rows}


def plot(rows,prefix):
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':180})
    fig,ax=plt.subplots(figsize=(7.5,4.6),layout='constrained')
    x=[r['half_interval_terms'] for r in rows]
    # None of the displayed data are zero in the accepted run. If a later run
    # has exact floating-point cancellation, show its working floor explicitly.
    floor=10.0**(-rows[0]['working_dps'])
    y=[max(float(r['absolute_difference']),floor) for r in rows]
    ax.semilogy(x,y,'o-',color='#155e75',lw=2,ms=5)
    ax.set_xlabel('Terms retained in each half-interval Frobenius series')
    ax.set_ylabel('Absolute difference from fresh three-$ {}_4F_3(1)$ evaluation')
    ax.set_title('Convergence of the independent elliptic representation',loc='left',weight='bold',pad=14)
    ax.grid(True,which='major',axis='y',alpha=.22)
    fig.text(.02,-.015,'Deterministic numerical consistency; not a physical error bound.',fontsize=9,color='#4b5563')
    fig.savefig(str(prefix)+'.png',bbox_inches='tight')
    fig.savefig(str(prefix)+'.pdf',bbox_inches='tight')
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dps',type=int,default=80)
    p.add_argument('--terms',nargs='+',type=int,default=[24,40,64,96,144,224,320,400])
    a=p.parse_args()
    if a.dps<60 or min(a.terms)<20:p.error('Require dps>=60 and all term counts>=20.')
    report=run(a.dps,a.terms)
    (ROOT/'outputs/raw/convergence.json').write_text(json.dumps(report,indent=2)+'\n')
    with (ROOT/'outputs/tables/convergence.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=report['rows'][0]);w.writeheader();w.writerows(report['rows'])
    plot(report['rows'],ROOT/'outputs/figures/elliptic_convergence')
if __name__=='__main__':main()
