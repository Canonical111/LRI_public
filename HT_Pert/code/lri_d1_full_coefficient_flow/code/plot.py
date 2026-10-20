"""Plot full-model finite coefficients and prediction diagnostics, not CFT limits."""
from pathlib import Path
import csv, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def rows(name):
 with (ROOT/'results'/name).open() as f:return list(csv.DictReader(f))
def save(fig,name):
 (ROOT/'figures').mkdir(exist_ok=True)
 fig.savefig(ROOT/'figures'/f'{name}.png',dpi=170,bbox_inches='tight');fig.savefig(ROOT/'figures'/f'{name}.svg',bbox_inches='tight');plt.close(fig)
def main():
 data=rows('forecast_validation.csv');fig,ax=plt.subplots(figsize=(9,5.3))
 for model,label in [('homogeneous','Homogeneous'),('source5','Source at fifth order'),('sources567','Sources at orders 5–7'),('free_omega','Free leading exponent')]:
  r=[a for a in data if a['lo']=='8' and a['base']=='A' and a['model']==model and a['coefficient']=='8'];r.sort(key=lambda a:int(a['cutoff']))
  ax.semilogy([int(a['cutoff']) for a in r],[abs(float(a['error'])) for a in r],'o-',label=label)
 ax.set(xlabel=r'New cutoff $\Lambda$',ylabel=r'Absolute error predicting $C_8^{D_{\rm conn}}(\Lambda)$',title='Frozen forecasts tested on new whole-coefficient calculations')
 ax.grid(alpha=.2);ax.legend(fontsize=9)
 fig.text(.5,.02,'Prior high-order training: C6,C7 to 28 and C8 to 24; lower orders to 118.\nNo high-order continuum target is used. Forecast error is not a physical continuum uncertainty.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.09,1,1));save(fig,'new_C8_forecasts')
 r=[a for a in rows('whole_model_coefficients.csv') if a['scheme']=='dconn'];fig,ax=plt.subplots(figsize=(9,5.3))
 ax.plot([int(a['Lambda']) for a in r],[float(a['C8']) for a in r],'o-')
 ax.axvline(24,ls='--',label='Previous complete degree-eight reach')
 ax.set(xlabel=r'Frozen energy cutoff $\Lambda$',ylabel=r'$C_8^{D_{\rm conn}}(\Lambda)$',title='The full corrected coefficient, not a tagged response class');ax.legend();ax.grid(alpha=.2)
 fig.text(.5,.02,'These are finite-cutoff Taylor coefficients. No continuum estimate is displayed.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.07,1,1));save(fig,'complete_C8_sequence')
 r=rows('leading_polynomial_probes.csv');fig,ax=plt.subplots(figsize=(9,5.3))
 for extra,label,marker in [('0','All seven leading logs','o'),('1','Plus one subleading power','s'),('2','Plus two subleading powers','^')]:
  q=[a for a in r if a['order']=='8' and a['status']=='completed' and a['extra_powers']==extra]
  ax.plot([int(a['lo']) for a in q],[float(a['intercept'])/1e6 for a in q],marker+'-',label=label)
 ax.set(xlabel='Lower edge of increment-fit window',ylabel='Fitted intercept / million',title='Unconstrained whole-leading-polynomial extraction is unstable')
 ax.legend(fontsize=9);ax.grid(alpha=.2)
 fig.text(.5,.02,'All fits use complete data through 36 and predict 38–44.\nThese intercepts are failed inference diagnostics, not a physical C8 range.',ha='center',fontsize=9)
 fig.tight_layout(rect=(0,.09,1,1));save(fig,'unstable_full_polynomial')
if __name__=='__main__':main()
