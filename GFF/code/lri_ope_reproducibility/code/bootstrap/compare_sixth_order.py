#!/usr/bin/env python3
"""Compare the supplied sixth-order LRI series with published bootstrap figures.

pip install mpmath numpy matplotlib
python compare_sixth_order.py --output-dir .

Inputs are read from inputs.json alongside this script. This does not perform
new diagram integration or a numerical bootstrap run. All static bootstrap
curves/points are approximate visual readings, explicitly identified as such.
The HTML overlay uses the ORIGINAL arXiv PNGs when internet is available.
"""
from __future__ import annotations
import argparse
import base64
import csv
import io
import json
from pathlib import Path
from typing import Sequence

import mpmath as mp
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
INPUT = json.loads((HERE / 'inputs.json').read_text())


def num(value):
    value=str(value)
    if '/' in value:
        n,d=value.split('/')
        return mp.mpf(n)/mp.mpf(d)
    return mp.mpf(value)


class PadeBorel:
    """Ordinary Borel--Leroy rational approximation, with pole checking."""
    def __init__(self, coeffs: Sequence, L: int, M: int, leroy=0):
        if len(coeffs) < L+M+1 or L<0 or M<0:
            raise ValueError('Insufficient coefficients or negative degree.')
        self.L,self.M,self.b=L,M,num(leroy)
        if self.b <= -1:
            raise ValueError('The Borel--Leroy parameter must exceed -1.')
        c=[num(x)/mp.gamma(k+self.b+1) for k,x in enumerate(coeffs[:L+M+1])]
        self.p,self.q=mp.pade(c,L,M)
        self.roots=mp.polyroots(self.q[::-1],maxsteps=1000) if M else []
        self.positive_poles=[r for r in self.roots if abs(mp.im(r))<mp.mpf('1e-30') and mp.re(r)>0]
        self.match_residual=max(abs(sum(self.q[j]*c[k-j] for j in range(min(k,M)+1))
              -(self.p[k] if k<=L else 0)) for k in range(L+M+1))
        if self.match_residual > mp.mpf('1e-35'):
            raise ArithmeticError('Taylor matching failed.')

    def evaluate(self,e):
        if self.positive_poles:
            raise ValueError('Rejected: pole on the positive real Borel axis.')
        e=num(e)
        if e<0:
            raise ValueError('Only nonnegative epsilon is used here.')
        return mp.quad(lambda t: mp.exp(-t)*t**self.b*
                       mp.polyval(self.p[::-1],e*t)/mp.polyval(self.q[::-1],e*t),
                       [0,1,5,20,mp.inf])

    def metadata(self):
        return dict(degrees=[self.L,self.M],leroy=str(self.b),
                    numerator=list(map(str,self.p)),denominator=list(map(str,self.q)),
                    poles=list(map(str,self.roots)),
                    positive_real_poles=list(map(str,self.positive_poles)),
                    Taylor_matching_residual=str(self.match_residual))


def pixel_to_data(key,coords):
    meta=INPUT['figures'][key]
    pts=np.asarray(coords,dtype=float)
    l,t,r,b=meta['box']; x0,x1=meta['xlim']; y0,y1=meta['ylim']
    return (x0+(pts[:,0]-l)/(r-l)*(x1-x0),
            y1-(pts[:,1]-t)/(b-t)*(y1-y0))


def calculate():
    result=dict(method='Borel-Pade [3/1] and [1/3] on a(epsilon)/epsilon^2; thermal [4/2]. All use Borel-Leroy b=0. No bootstrap/endpoint fitting.',
                caveat='Series coefficients inherited from the earlier calculation, not independently derived here. Neither prescription spread nor successive-order shifts are certified errors.',
                source=INPUT['source'],bootstrap_status=INPUT['digitization_status'],
                models={},rows=[])
    with mp.workdps(60):
        for d in (3,2):
            ac=[num(INPUT['a_coefficients'][str(d)][str(k)]) for k in range(2,7)]
            tc=[num(s) for s in INPUT['thermal_coefficients'][str(d)]]
            models={'a_BP31':PadeBorel(ac,3,1),'a_BP13':PadeBorel(ac,1,3),
                    'a_BP22_rejected':PadeBorel(ac,2,2),
                    'thermal_BP42':PadeBorel(tc,4,2),
                    'thermal_BP32':PadeBorel(tc,3,2)}
            result['models'][str(d)]={k:v.metadata() for k,v in models.items()}
            for label,ds in zip('ABCD',INPUT['Delta_phi'][str(d)]):
                e=mp.mpf(d)-4*num(ds)
                r=dict(d=d,label=label,Delta_phi=float(num(ds)),epsilon=float(e))
                for n in (2,3,4,5,6):
                    r[f'a_raw{n}']=float(mp.fsum(ac[k-2]*e**k for k in range(2,n+1)))
                    r[f'a_term{n}']=float(ac[n-2]*e**n)
                for key in ('a_BP31','a_BP13'):
                    r[key]=float(e**2*models[key].evaluate(e))
                for key in ('thermal_BP42','thermal_BP32'):
                    r[key]=float(models[key].evaluate(e))
                if d==3:
                    idx='ABCD'.index(label)
                    bx,by=pixel_to_data('fig11',[INPUT['fig11_kink_pixels'][idx]])
                else:
                    idx=INPUT['fig7_blue_Delta_phi'].index(ds.rstrip('0').rstrip('.') if ds not in INPUT['fig7_blue_Delta_phi'] else ds)
                    bx,by=pixel_to_data('fig7',[INPUT['fig7_blue_pixels'][idx]])
                r['kink_a_approx']=float(bx[0]); r['kink_Delta_E_approx']=float(by[0])
                result['rows'].append(r)
    return result


def source_boundaries(ax,key,labels=True):
    if key not in INPUT['trace_pixels']:
        return
    for idx,pix in enumerate(INPUT['trace_pixels'][key]):
        x,y=pixel_to_data(key,pix)
        ax.plot(x,y,lw=1.5,alpha=.55,
                label=(f'Boundary {"ABCD"[idx]} (visual trace)' if labels else None),zorder=1)


def predictions(ax,rows,labels=True):
    x1=[r['a_BP31'] for r in rows]; x2=[r['a_BP13'] for r in rows]
    ys=[r['thermal_BP42'] for r in rows]
    ax.plot(x1,ys,linestyle='none',marker='D',ms=8,
            label=r'$a/\epsilon^2$: Borel–Padé [3/1]',zorder=9)
    ax.plot(x2,ys,linestyle='none',marker='o',ms=9,fillstyle='none',mew=1.8,
            label=r'$a/\epsilon^2$: Borel–Padé [1/3]',zorder=10)
    xx=[];yy=[]
    for a,b,y in zip(x1,x2,ys): xx.extend([a,b,np.nan]);yy.extend([y,y,np.nan])
    ax.plot(xx,yy,'--',lw=1.2,alpha=.75,
            label='Prescription shift (not an error bar)',zorder=7)
    if labels:
        for r in rows:
            mid=(r['a_BP31']+r['a_BP13'])/2
            off=(-15,11) if r['label']=='A' else (-3,11)
            if r['d']==2 and r['label']=='B': off=(-3,-20)
            ax.annotate(r['label'],(mid,r['thermal_BP42']),xytext=off,
                        textcoords='offset points',fontsize=12,fontweight='bold',zorder=15)


def mapping_text(rows):
    return '   ·   '.join(f'{r["label"]}: Δφ = {r["Delta_phi"]:g}' for r in rows)


def main_plot(result,out,d):
    rr=[r for r in result['rows'] if r['d']==d]
    fig=plt.figure(figsize=(11.1,8.2))
    ax=fig.add_axes([.10,.30,.87,.57])
    if d==3:
        source_boundaries(ax,'fig11')
        ax.set_xlim(-.08,.001);ax.set_ylim(1.400,1.501)
        sub='Published boundaries from Figure 11: approximate visual traces'
    else:
        ax.set_xlim(-.44,.010);ax.set_ylim(.953,1.001)
        sub='12,000-sample bootstrap kinks from Figure 7: approximate visual readings'
    ax.plot([r['kink_a_approx'] for r in rr],[r['kink_Delta_E_approx'] for r in rr],
            ls='none',marker='x',ms=8,mew=1.8,label='Bootstrap kink (approximate)',zorder=12)
    for r in rr:
        off=(-22,-14) if r['label'] in ('A','B') else (-8,-15)
        if d==2 and r['label']=='B':off=(-14,8)
        ax.annotate(r['label'],(r['kink_a_approx'],r['kink_Delta_E_approx']),xytext=off,
                    textcoords='offset points',fontsize=10,alpha=.85)
    predictions(ax,rr)
    ax.set_xlabel(r'$a_{\phi^2}$',fontsize=14)
    ax.set_ylabel(r'$\Delta_{\mathcal{E}}$',fontsize=14)
    ax.tick_params(labelsize=11)
    ax.grid(alpha=.15)
    fig.suptitle(f'{d}D long-range Ising: sixth-order series vs. bootstrap',fontsize=18,y=.975)
    fig.text(.5,.917,sub,ha='center',fontsize=11)
    fig.text(.5,.889,r'Both coordinates use coefficients through $\epsilon^6$; thermal coordinate: Borel–Padé [4/2].',ha='center',fontsize=10)
    fig.text(.5,.202,mapping_text(rr),ha='center',fontsize=10)
    handles,names=ax.get_legend_handles_labels()
    fig.legend(handles,names,loc='lower center',bbox_to_anchor=(.53,.060),
               ncol=2 if d==3 else 2,fontsize=9.5,frameon=False)
    fig.text(.5,.025,'arXiv:2311.02742v6. No bootstrap or endpoint data fitted. No certified resummation error.\n'
             'The static bootstrap marks are digitized approximations, not raw numerical-bootstrap output.',
             ha='center',fontsize=9)
    p=out/f'{d}d_sixth_order_comparison.png'
    fig.savefig(p,dpi=180);plt.close(fig)
    return p


def weak_plot(result,out,d):
    r=next(r for r in result['rows'] if r['d']==d and r['label']=='A')
    fig=plt.figure(figsize=(10.5,7.3));ax=fig.add_axes([.12,.30,.84,.56])
    y=r['thermal_BP42']
    if d==3:
        source_boundaries(ax,'fig11',labels=False)
        ax.set_xlim(-.0055,-.00065);ax.set_ylim(1.4645,1.481)
        title='Weakest-coupling 3D point: changing the horizontal prescription'
        subtitle=r'$\Delta_\phi=0.70363,\quad \epsilon=0.18548$'
        caption='Boundary A is visually traced from Fig. 11; compare only with this external dimension.'
    else:
        ax.set_xlim(-.0088,-.002);ax.set_ylim(.957,.971)
        title='Weakest-coupling 2D point: changing the horizontal prescription'
        subtitle=r'$\Delta_\phi=0.425,\quad \epsilon=0.30$'
        caption='The kink is the approximate 12,000-sample reading from Fig. 7, not a full bound.'
    ax.plot([r['kink_a_approx']],[r['kink_Delta_E_approx']],marker='x',ls='none',ms=10,mew=2,
            label='Bootstrap kink (approximate)')
    shapes={3:'v',4:'^',5:'s',6:'P'}
    for n in (3,4,5,6):
        ax.plot([r[f'a_raw{n}']],[y],marker=shapes[n],ls='none',fillstyle='none',ms=10,mew=1.5,
                label=rf'Raw $a$: through $\epsilon^{n}$')
    ax.plot([r['a_BP31']],[y],marker='D',ls='none',ms=8,label=r'Resummed $a/\epsilon^2$: [3/1]')
    ax.plot([r['a_BP13']],[y],marker='o',ls='none',fillstyle='none',ms=11,mew=1.8,
            label=r'Resummed $a/\epsilon^2$: [1/3]')
    ax.set_xlabel(r'$a_{\phi^2}$',fontsize=14);ax.set_ylabel(r'$\Delta_{\mathcal{E}}$',fontsize=14)
    ax.tick_params(labelsize=11);ax.grid(alpha=.15)
    fig.suptitle(title,fontsize=16,y=.965);fig.text(.5,.90,subtitle,ha='center',fontsize=13)
    fig.text(.5,.19,rf'All perturbative markers have $\Delta_{{\mathcal{{E}}}}={y:.8f}$ (thermal BP [4/2]).',ha='center',fontsize=11)
    fig.legend(*ax.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.53,.06),
               ncol=3,fontsize=9,frameon=False)
    fig.text(.5,.018,caption+'\nThese are different truncations/prescriptions, not confidence limits.',ha='center',fontsize=9)
    p=out/f'{d}d_weak_point_orders.png';fig.savefig(p,dpi=180);plt.close(fig)
    return p


def svg_string(fig):
    stream=io.StringIO();fig.savefig(stream,format='svg',transparent=True)
    s=stream.getvalue();return s[s.index('<svg'):]


def svg_uri(s):
    return 'data:image/svg+xml;base64,'+base64.b64encode(s.encode()).decode()


def axes_for_source(key):
    meta=INPUT['figures'][key];w,h=meta['width'],meta['height'];l,t,r,b=meta['box']
    fig=plt.figure(figsize=(w/100,h/100),dpi=100)
    ax=fig.add_axes([l/w,(h-b)/h,(r-l)/w,(b-t)/h])
    ax.set_xlim(meta['xlim']);ax.set_ylim(meta['ylim'])
    return fig,ax


def html_overlay(result,out):
    cards=[]
    for key in ('fig11','fig7','fig4'):
        meta=INPUT['figures'][key]
        rr=[r for r in result['rows'] if r['d']==meta['d'] and (key!='fig4' or r['label']!='D')]
        layers={}
        for name in ('resummed','raw5','raw6','fallback'):
            fig,ax=axes_for_source(key)
            if name=='resummed':predictions(ax,rr)
            elif name.startswith('raw'):
                ax.plot([r['a_'+name] for r in rr],[r['thermal_BP42'] for r in rr],
                        ls='none',marker='s' if name=='raw5' else 'P',ms=8,fillstyle='none',mew=1.5)
            else:
                source_boundaries(ax,key,labels=False)
                if key=='fig7':
                    xx,yy=pixel_to_data(key,INPUT['fig7_blue_pixels'])
                    ax.plot(xx,yy,ls='none',marker='x',ms=8)
                ax.set_xlabel(r'$a_{\phi^2}$',fontsize=20)
                ax.set_ylabel(r'$\Delta_{\mathcal{E}}$',fontsize=20)
                ax.tick_params(labelsize=15)
            if name!='fallback':ax.set_axis_off()
            layers[name]=svg_uri(svg_string(fig));plt.close(fig)
        table=''.join(f'<tr><td>{r["label"]}</td><td>{r["Delta_phi"]:.5f}</td><td>{r["epsilon"]:.5f}</td>'
                f'<td>{r["a_BP31"]:.8f}</td><td>{r["a_BP13"]:.8f}</td><td>{r["a_raw6"]:.8f}</td>'
                f'<td>{r["thermal_BP42"]:.8f}</td></tr>' for r in rr)
        cards.append(f'''<section><h2>{meta['d']}D: Figure {meta['number']}</h2><p>{meta['detail']}</p>
<p id="status-{key}"><strong>Approximate traced background until the original arXiv image loads.</strong></p>
<div class="controls"><label><input type="checkbox" checked onchange="toggle('{key}','resummed',this.checked)">Resummed sixth-order estimates</label>
<label><input type="checkbox" onchange="toggle('{key}','raw5',this.checked)">Raw a through ε⁵</label>
<label><input type="checkbox" onchange="toggle('{key}','raw6',this.checked)">Raw a through ε⁶</label>
<label>Zoom <input type="range" min="100" max="400" step="25" value="100" oninput="document.getElementById('frame-{key}').style.width=this.value+'%'"></label></div>
<div class="viewport"><div class="frame" id="frame-{key}" style="aspect-ratio:{meta['width']}/{meta['height']}">
<img src="{layers['fallback']}" alt="Approximate traced fallback, not raw bootstrap data">
<img src="{meta['url']}" class="original" alt="Original arXiv Figure {meta['number']}"
 onload="this.style.visibility='visible';document.getElementById('status-{key}').textContent='Original published arXiv figure loaded; predictions overlaid at calibrated coordinates.'"
 onerror="document.getElementById('status-{key}').textContent='Original image unavailable: displaying a labelled approximate trace. This is not a bootstrap exclusion certificate.'">
<img id="{key}-resummed" src="{layers['resummed']}" alt="Two pole-free Borel-Pade predictions">
<img id="{key}-raw5" src="{layers['raw5']}" style="display:none" alt="Raw fifth-order horizontal prediction">
<img id="{key}-raw6" src="{layers['raw6']}" style="display:none" alt="Raw sixth-order horizontal prediction">
</div></div><p>Diamond: Borel–Padé [3/1] of a/ε². Open circle: [1/3]. Both use a₂,…,a₆.
Dashed segment: prescription dependence, NOT an error bar. The vertical coordinate is thermal BP [4/2] through C₆.
Raw predictions outside the original plot axes are clipped, not silently replaced.</p>
<div class="tablewrap"><table><thead><tr><th>ID</th><th>Δφ</th><th>ε</th><th>a: BP[3/1]</th><th>a: BP[1/3]</th><th>a: raw ε⁶</th><th>ΔE: BP[4/2]</th></tr></thead><tbody>{table}</tbody></table></div></section>''')
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sixth-order LRI / bootstrap overlay</title><style>
body{font:16px/1.5 system-ui,sans-serif;margin:24px auto;max-width:1150px;padding:0 20px}h1{line-height:1.15}section{margin:34px 0;padding:18px;border:1px solid;border-radius:8px}.viewport{overflow:auto}.frame{position:relative;width:100%}.frame img{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}.original{visibility:hidden}.controls{display:flex;flex-wrap:wrap;gap:16px;margin:14px 0;font-size:14px}.tablewrap{overflow:auto}table{border-collapse:collapse;font-size:14px;width:100%;font-variant-numeric:tabular-nums}th,td{padding:8px;text-align:right;border-bottom:1px solid}p{max-width:1050px}.notice{border:1px solid;padding:14px}
</style></head><body><h1>Sixth-order long-range Ising predictions vs. bootstrap</h1>
<p>Behan, Lauria, Nocchi and van Vliet, arXiv:2311.02742v6. Interactive overlays on the original figure images when online; explicitly labelled approximate tracings when offline.</p>
<div class="notice">No bootstrap or short-range endpoint data were fitted. The ordinary Borel [2/2] approximation of a/ε² has a positive-real-axis pole in both 2D and 3D and was rejected. The two plotted pole-free alternatives are illustrative, not controlled confidence bounds. All loop coefficients are inherited from the preceding calculation, not independently rederived for this plot. Comparing a resummation to a plotted bound does not by itself rule out the perturbative coefficients.</div>'''+''.join(cards)+'''<script>function toggle(k,n,b){document.getElementById(k+'-'+n).style.display=b?'block':'none';}</script></body></html>'''
    p=out/'original_figure_overlay.html';p.write_text(page);return p


def write_results(result,out):
    out.mkdir(parents=True,exist_ok=True)
    (out/'comparison_results.json').write_text(json.dumps(result,indent=2))
    with (out/'prediction_coordinates.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(result['rows'][0]));w.writeheader();w.writerows(result['rows'])


def plot_all(result,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    paths=[main_plot(result,out,d) for d in (3,2)]
    paths.extend(weak_plot(result,out,d) for d in (3,2))
    paths.append(html_overlay(result,out))
    return paths


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=HERE)
    parser.add_argument('--calculate-only',action='store_true')
    args=parser.parse_args();res=calculate();write_results(res,args.output_dir)
    if not args.calculate_only:plot_all(res,args.output_dir)
    for row in res['rows']:
        print(row['d'],row['label'],f"epsilon={row['epsilon']:.5f}",f"a_BP31={row['a_BP31']:.9f}",
              f"a_BP13={row['a_BP13']:.9f}",f"Delta_E={row['thermal_BP42']:.9f}")
