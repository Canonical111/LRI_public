"""Assemble reported results without promoting conditional estimates to certificates."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(name):return json.loads((ROOT/name).read_text())

def main():
    an=read('analysis_results.json');r=an['central']
    tp=next(p for p in r['parts'] if p['name']=='even_ss1_l2_d5.50915')
    olda=3.289592784045669;oldb=12.25344721781144 # from prior audit, not newly fitted
    box=read('input_box_results.json')['two_error_box']
    tail=read('tail_gap8_results.json')[-1]
    eb=tail['b_tail_estimate'];ea=tail['a_even_tail_estimate']+tail['a_odd_tail_estimate']
    ef=ea+r['C1']*eb;den=r['b']+box['delta_b_min']-eb
    lo=r['C1']+(box['delta_F_min']-ef)/den
    hi=r['C1']+(box['delta_F_max']+ef)/den
    g=read('global_input_results.json')['global_inputs']
    if {p['parameter'] for p in g}!={'S','E','sse','eee','ct'}:
        raise ValueError('Run all global input variations before finalizing.')
    hirows=[p for p in an['input_error_linearization'] if p['Delta']>2 and not(p['Delta']==3 and p['ell']==2)]
    rss=math.sqrt(sum(p['quadrature']**2 for p in hirows)+sum(p['one_error_effect']**2 for p in g))
    l1=sum(abs(p[k]) for p in hirows for k in ['error_effect_f','error_effect_h','error_effect_Delta'])+sum(abs(p['one_error_effect']) for p in g)
    rows=read('expanded_spectrum.json')
    result=dict(central={k:r[k] for k in ['a','b','C1']},old=dict(a=olda,b=oldb,C1=olda/oldb),
      Tprime=tp,old_plus_Tprime_C1=(olda+tp['contribution_a'])/(oldb+tp['contribution_b']),
      number_even=sum(p['sector']=='even' for p in rows),number_odd=sum(p['sector']=='odd' for p in rows),
      input_box=box,conditional_tail=tail,conditional_C1_interval=[lo,hi],
      recommended_provisional_C1=.273,recommended_provisional_error=.007,
      physical_certified_interval=None,
      correlated_low_input_rss_assuming_independent_other_errors=rss,input_one_error_l1_sensitivity=l1,
      assumptions=['No unlisted primary exchanged in the relevant OPEs below dimension 8.',
        'True tabulated CFT inputs lie in twice-quoted-error ranges. EFM errors are not statistical or rigorous.',
        'First-order/sampled parameter envelopes and finite block/quadrature estimates are sufficiently accurate; interval arithmetic was not performed.',
        'The full correlators obey reflection positivity and crossing.'],
      limitations=['Completeness below 8 was not established. Published extremal spectra can omit trajectories.',
        'Global leading-dimension dependences are propagated in retained integrals, but are not separately certified in the tail envelope.',
        'The conditional interval is neither an assumption-independent physical bound nor a confidence interval.'])
    (ROOT/'SUMMARY_RESULTS.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
