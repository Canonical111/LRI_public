#!/usr/bin/env python3
"""Reassemble recorded raw data and compare to a separately evaluated reference.

No reference coefficient is used to adjust a raw amplitude. The reference is
only used after the forward Laurent/MS/fixed-point calculation is complete.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import mpmath as mp
import laurent_assembly as alg
ROOT=Path(__file__).resolve().parent
REC=ROOT/'records';mp.mp.dps=80

def load(path):return json.loads(path.read_text(),parse_float=str)
def number(v):return mp.mpf(str(v))
def lower_case(cutoff):
    data=load(REC/f'lower_{cutoff}_32.json');data['5']=[{},{}]
    baseline=alg.assemble(data)
    prediction={}
    for pole in range(2,6):
        gr=mp.fsum(baseline['beta'][L-1]*(6-L)*baseline['G'][6-L].get(1-pole,0)for L in range(1,5))/5
        zr=mp.fsum(((5-L)*baseline['beta'][L-1]+baseline['gamma'][L-1])*baseline['Z'][5-L].get(1-pole,0)for L in range(1,5))/5
        zero=3*baseline['Z'][5].get(-pole,0)-baseline['G'][6].get(-pole,0)
        prediction[-pole]=3*zr-gr-zero
    return data,baseline,prediction

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--refresh-reference',action='store_true')
    args=ap.parse_args();REC.mkdir(exist_ok=True)
    rp=REC/'reference.json'
    refreshed=args.refresh_reference or not rp.exists()
    if refreshed:rp.write_text(json.dumps(alg.serial(alg.reference()),indent=2))
    ref={k:number(v)for k,v in load(rp).items()}
    history=load(ROOT/'inputs/historical_five_loop_results.json')
    results=[]
    for old in history:
        v=alg.assemble(old['amplitudes'])
        results.append({'method':'historical','degree':old['N'],'cutoff':old['cutoff'],
             'lower_degree':old['lower_N'],'C5':v['C'][-1],
             'printed_C5':number(old['dimension_coefficients'][-1]),
             'C5_minus_closed':v['C'][-1]-ref['C5'],
             'D5':v['D5'],'reassembly_minus_printed':v['C'][-1]-number(old['dimension_coefficients'][-1])})
    budgets=[]
    for cutoff in ['span','maxgap']:
        data,baseline,higher=lower_case(cutoff)
        old=next(v for v in history if v['N']==22 and v['cutoff']==cutoff)
        h_old={int(k):3*number(old['amplitudes']['5'][1][k])-number(old['amplitudes']['5'][0][k])for k in old['amplitudes']['5'][0]}
        old_assembled=alg.assemble(old['amplitudes'])['C'][-1]
        old_newlower=baseline['C'][-1]+5*h_old[-1]/729
        budgets.append({'cutoff':cutoff,'old_printed':number(old['dimension_coefficients'][-1]),
             'old_decimal_reassembled':old_assembled,'old5_with_fresh_lower':old_newlower,
             'rounding_printed_minus_reassembled':number(old['dimension_coefficients'][-1])-old_assembled,
             'lower_old_minus_fresh':old_assembled-old_newlower,
             'reference':ref['C5'],'historical_H_simple':h_old[-1]})
        for method,pattern in [('scalar_extended',f'amplitude5_{cutoff}_*.json'),('combined_simd',f'combined5_{cutoff}_*.json')]:
            for path in sorted(REC.glob(pattern)):
                raw=load(path);N=int(path.stem.split('_')[-1])
                h=({int(k):3*number(raw['B'][k])-number(raw['A'][k])for k in raw['A']}if method=='scalar_extended'else{int(k):number(v)for k,v in raw['H'].items()})
                C5=baseline['C'][-1]+5*h[-1]/729
                row={'method':method,'degree':N,'cutoff':cutoff,'lower_degree':32,
                     'C5':C5,'C5_minus_closed':C5-ref['C5'],'D5':baseline['D5']+5*h[-1],
                     'H_simple':h[-1],'H_higher_pole_residuals':{k:h[k]-v for k,v in higher.items()},
                     'max_H_higher_pole_residual':max(abs(h[k]-v)for k,v in higher.items()),
                     'kernel_shift_vs_old_degree22':C5-old_newlower,
                     'raw_file':path.name}
                matched=next((old for old in history if old['cutoff']==cutoff and old['N']==N),None)
                if matched:
                    same_h=3*number(matched['amplitudes']['5'][1]['-1'])-number(matched['amplitudes']['5'][0]['-1'])
                    row['same_degree_same_lower_precision_shift']=5*(h[-1]-same_h)/729
                if method=='scalar_extended':
                    full=dict(data);full['5']=[raw['A'],raw['B']];v=alg.assemble(full)
                    row['full_assembly_minus_combined_assembly']=v['C'][-1]-C5
                    row['beta']=v['beta'];row['gamma']=v['gamma'];row['pole_residuals']=v['pole_residuals']
                else:
                    row['regular_simple']=number(raw['regular_simple']);row['endpoint_simple']=number(raw['endpoint_simple'])
                results.append(row)
    for row in results:
        if row['method']=='combined_simd':
            control=next((r for r in results if r['method']=='scalar_extended'and r['degree']==row['degree']and r['cutoff']==row['cutoff']),None)
            if control:row['C5_minus_scalar_control']=row['C5']-control['C5']
    new=[r for r in results if r['method']=='combined_simd']
    if new:
        best=max(r['degree']for r in new)
        for budget in budgets:
            row=next(r for r in new if r['cutoff']==budget['cutoff']and r['degree']==best)
            budget['corrected_degree']=best;budget['corrected_C5']=row['C5']
            budget['five_loop_old_minus_corrected']=budget['old5_with_fresh_lower']-row['C5']
            budget['remaining_residual']=row['C5']-ref['C5']
            budget['sum_of_budget_terms']=sum(budget[k]for k in ['rounding_printed_minus_reassembled','lower_old_minus_fresh','five_loop_old_minus_corrected','remaining_residual'])
            budget['budget_identity_residual']=budget['sum_of_budget_terms']-(budget['old_printed']-ref['C5'])
    out={'working_decimal_digits':80,'reference_recomputed_during_this_audit':refreshed,'saved_reference_is_output_of_period_evaluator':True,
         'raw_integrator_uses_analytic_periods':False,'rigorous_interval_error_bound':False,
         'cases':results,'error_budgets':budgets}
    (REC/'resolution_audit.json').write_text(json.dumps(alg.serial(out),indent=2))
    for r in results:print(r['method'],r['degree'],r['cutoff'],mp.nstr(r['C5'],32),'error',mp.nstr(r['C5_minus_closed'],12))
if __name__=='__main__':main()
