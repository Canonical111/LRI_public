"""Plot accepted finite-cutoff coefficients; no fitted continuum C8 curve."""
from pathlib import Path
import csv,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def read(name):
    with (ROOT/'results'/name).open() as f:return list(csv.DictReader(f))

def save(fig,name):
    (ROOT/'figures').mkdir(exist_ok=True)
    for ext in ['png','svg']:fig.savefig(ROOT/'figures'/f'{name}.{ext}',dpi=175,bbox_inches='tight')
    plt.close(fig)

def main():
    rows=read('coefficients_C0_C8.csv')
    fig,ax=plt.subplots(figsize=(9,5.4))
    for scheme,style in [('raw','s--'),('consistent','o-')]:
        data=sorted([r for r in rows if r['scheme']==scheme and int(r['L'])>=2],key=lambda r:int(r['L']))
        ax.plot([int(r['L']) for r in data],[float(r['C8']) for r in data],style,label=scheme)
    ax.set(xlabel='Total bath-mode cutoff L',ylabel=r'$C_8(L)$',title='Direct 2D thermal coefficient through eighth order')
    ax.grid(alpha=.2);ax.legend()
    fig.text(.5,.012,'Raw and consistent-window curves nearly overlap on this scale. These are finite-regulator values, not continuum estimates.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1));save(fig,'C8_cutoff')
    data=read('window_shifts.csv');fig,ax=plt.subplots(figsize=(9,5.4))
    ax.plot([int(r['L']) for r in data],[float(r['delta_C8']) for r in data],'o-')
    ax.set(xlabel='Total bath-mode cutoff L',ylabel=r'$C_8^{\rm consistent}-C_8^{\rm raw}$',title='The directly calculated eighth-order vacuum-window change')
    ax.grid(alpha=.2)
    fig.text(.5,.012,'No thermal value is a calibration target. A complete model correction is not a proof of complete physical high-state matching.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1));save(fig,'window_changes')
    data=sorted([r for r in rows if r['scheme']=='consistent'],key=lambda r:int(r['L']))
    fig,ax=plt.subplots(figsize=(9,5.4))
    ax.plot([int(r['L']) for r in data],[float(r['C2']) for r in data],'o-',label='Direct coefficient; exact finite sum agrees')
    ax.axhline(4*math.log(2)/9,linestyle='--',label=r'Exact $4\log 2/9$ limit')
    ax.set(xlabel='Total bath-mode cutoff L',ylabel=r'$C_2(L)$',title='Independent lowest-order control and the remaining UV tail')
    ax.legend();ax.grid(alpha=.2)
    fig.text(.5,.012,'The exact limit is checked after calculation; it is not used to tune the Hamiltonian.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.05,1,1));save(fig,'C2_control')
    print('Saved three PNG/SVG figures from accepted coefficient data.')
if __name__=='__main__':main()
