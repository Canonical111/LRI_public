"""Reproduce conditional tail scenarios; these are NOT certified intervals."""
import json
from pathlib import Path
from tail_integral_probe import prep_even,oddbound,integrate_tails
ROOT=Path(__file__).resolve().parent

def evaluate(gp,gm,multiplier):
    fs=prep_even('sigma',nsig=multiplier,gap=gp)
    fe=prep_even('epsilon',nsig=multiplier,gap=gp)
    anchors=[oddbound(x,fs,fe,nsig=multiplier) for x in [2/3,.68,.7,.75,.8]]
    b,ae,ao=integrate_tails(fs,fe,anchors,gm)
    return dict(input_box_multiplier=multiplier,even_gap=gp,odd_gap=gm,
                b_tail_estimate=b,a_even_tail_estimate=ae,a_odd_tail_estimate=ao,
                C1_tail_estimate=(ae+ao+.273152423826*b)/12.254914105481)

if __name__=='__main__':
    out=[]
    for multiplier in [0,1,2]:
        r=evaluate(8,8,multiplier);out.append(r);print(r,flush=True)
    (ROOT/'tail_gap8_results.json').write_text(json.dumps(out,indent=2))
    out=[]
    for gap in [2,4,6,7,8]:
        r=evaluate(5,gap,2);out.append(r);print(r,flush=True)
    (ROOT/'tail_estimates.json').write_text(json.dumps(dict(cases=out,
        status='Exploratory conditional estimates, NOT rigorous bounds'),indent=2))
