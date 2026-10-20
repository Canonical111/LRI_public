"""Enclose the complete UPLOADED analytic C6 representation.

No numerical value of C6, period, or gamma constant is an input to this run.
All arithmetic that constructs the result uses integer/rational intervals.
The identification of the uploaded expression with the physical graph/RG
coefficient remains an inherited assumption; this program does not prove it.
"""
from __future__ import annotations
from fractions import Fraction as F
from pathlib import Path
from hashlib import sha256
import sys,json,time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'wheel'))
if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
import dyadic
from dyadic import I,evaluate
from elementary import Constants
from rational_tails import enclosure
from primitive import compute as primitive_value,exact_seed_checks
from other_series import alternating_periods,half_argument,lambda_value
from certify import approximant as wheel_approximant,tail_bound as wheel_tail_bound,exact_checks as wheel_exact_checks

CONFIGS={
 'smoke':dict(bits=640,ordinary_N=128,ordinary_M=40,primitive_N=140,Euler_N=400,Lambda_N=700,half_N=400,gamma_shift=128,gamma_M=70),
 'release':dict(bits=1024,ordinary_N=256,ordinary_M=80,primitive_N=240,Euler_N=900,Lambda_N=1600,half_N=700,gamma_shift=256,gamma_M=100),
 'refined':dict(bits=1280,ordinary_N=320,ordinary_M=96,primitive_N=280,Euler_N=1100,Lambda_N=1900,half_N=900,gamma_shift=320,gamma_M=120)
}

def packrat(q):
    q=F(q);return {'numerator':str(q.numerator),'denominator':str(q.denominator)}

def width_text(v):
    # Informational only. No float is used in any interval construction.
    return f'{float(v.width()):.5e}'

def main(name='release'):
    cfg=CONFIGS[name];dyadic.set_precision(cfg['bits']);st=time.time()
    expr=json.loads((ROOT/'inputs/expression.json').read_text());env={};records={};values={}
    cs=Constants(cfg['Euler_N'],cfg['gamma_shift'],cfg['gamma_M']);env.update(cs.environment())
    print('elementary constants ready',round(time.time()-st,2),flush=True)
    for k in ['pi','ell','Q','G','z3','z5']:values[k]=env[k]
    def hyper(label,up,down):
        pair,record=enclosure(tuple(up),tuple(down),cfg['ordinary_N'],cfg['ordinary_M'])
        v=I.bounds(*pair);values[label]=v
        records[label]={k:(packrat(q) if isinstance(q,F) else q) for k,q in record.items()}
        records[label]['numerator_shifts']=list(map(str,up));records[label]['denominator_shifts']=list(map(str,down))
        print(label,v,'width',width_text(v),'seconds',round(time.time()-st,2),flush=True)
        return v
    q=F(1,4);h=F(1,2)
    BM=hyper('Bminus_hyper',[q,q,h,h],[3*q,3*q,1,1])
    BP=hyper('Bplus_hyper',[3*q,3*q,h,h],[5*q,5*q,1,1])
    env['U']=hyper('U',[q,h,h,h,h],[5*q,1,1,1,1])
    env['V']=hyper('V_ordinary',[1,1,5*q,5*q,5*q,5*q],[2,7*q,7*q,7*q,7*q,1])
    Hm=hyper('Hminus',[q]*6,[3*q]*6)
    H0=hyper('H0',[h]*6,[1]*6)
    Hp=hyper('Hplus',[3*q]*6,[5*q]*6)
    pi=env['pi'];Q=env['Q'];A=env['A'];rt2=I(2).sqrt()
    Bminus=pi*Q*BM;Bplus=64*pi**3/Q*BP
    env['Poct']=13*Bminus-3*Bplus
    env['Ell']=-(13*A-3*pi)*Bminus/2+(3*A-pi)*Bplus/2
    env['PB6']=6*Q**3/pi*(2*Hm-1)-104*pi**5*H0+2**18*pi**5/Q**3*Hp
    Y={}
    for r in [1,2,7]:
        t=F(r,8);a=t+q;b=t+3*q
        Y[r]=t*(cs.gamma(a)/cs.gamma(b))**8*hyper('Y'+str(r)+'_normalized',[t+1]+[a]*8,[t]+[b]*8)
        values['Y'+str(r)]=Y[r]
    HH=(17+12*rt2)*Y[1]-(17-12*rt2)*Y[7]
    env['PZ6']=pi**2*((816-828*rt2)*Y[2]+23*HH)
    env['PK6']=pi**2*(432*(1-rt2)*Y[2]+12*HH)
    l7obj=next(t for t in expr['single_index_harmonic_series_terms'] if t['id']=='L7')
    Z,L7,altinfo=alternating_periods(cs,env,l7obj,cfg['Euler_N']);env['L7']=L7
    for r,v in Z.items():env['Z'+str(r)]=v
    Xp=env['c7']*Z[3]-env['s7']*Z[5];Xm=env['c7']*Z[1]+env['s7']*Z[7]
    env['PZ5']=16*pi**F(3,2)*(-35*Z[2]+(22*rt2-13)*Xp+(22*rt2+13)*Xm)
    print('alternating periods ready; L7',L7,'seconds',round(time.time()-st,2),flush=True)
    env['H3real'],env['H5real']=half_argument(cfg['half_N'])
    env['Lambda'],laminfo=lambda_value(cs,cfg['Lambda_N'])
    pobj=expr['single_index_recurrence_series_terms'][0]
    pchecks=exact_seed_checks(pobj)
    env['Pa'],pinfo=primitive_value(pobj,env,cfg['primitive_N'])
    print('Pa',env['Pa'],'width',width_text(env['Pa']),'seconds',round(time.time()-st,2),flush=True)
    wchecks=wheel_exact_checks();wc=wheel_approximant(256,40);wv=I(0)
    for a in wc:wv=wv*pi+a
    werror=wheel_tail_bound(40,256);env['Wcentral']=wv.inflate(werror)
    old=json.loads((ROOT/'inputs/wheel_intervals.json').read_text())['enclosures'][-1]['Wcentral']
    oldlo=F(int(old['lower']['numerator']),int(old['lower']['denominator']))
    oldhi=F(int(old['upper']['numerator']),int(old['upper']['denominator']))
    assert env['Wcentral'].lower()<=oldhi and oldlo<=env['Wcentral'].upper()
    known=evaluate(expr['known_polynomial'],env)
    contribution_expressions={
        'known_polynomial':expr['known_polynomial'],
        'Lambda':'835584*Lambda','H5':'391680*H5real',
        'H3':'13056*sqrt(2)*(32*G+3*pi**2)*H3real',
        'wheel':'-393*pi**3*Wcentral','primitive':'96*Pa','logarithmic':'-784*pi**(3/2)*L7'
    }
    parts={k:evaluate(ex,env) for k,ex in contribution_expressions.items()}
    total=sum(parts.values(),I(0))/2187
    # Re-evaluate a separately parsed full right hand side.
    rhs='('+expr['formula'].split(' = ',1)[1].replace('known_polynomial','('+expr['known_polynomial']+')')+')/2187'
    assembled_again=evaluate(rhs,env)
    assert total.lower()<=assembled_again.upper() and assembled_again.lower()<=total.upper()
    values.update(env);values['Bminus']=Bminus;values['Bplus']=Bplus;values['C6_representation']=total
    out={
       'scope':'Rigorous interval arithmetic enclosure of the complete uploaded corrected analytic representation. Physical graph/RG identification is inherited, not newly proved.',
       'normalization':expr['normalization'],'configuration':name,'parameters':cfg,
       'input_sha256':sha256((ROOT/'inputs/expression.json').read_bytes()).hexdigest(),
       'arithmetic':'Integers and exact Fractions only, with outward dyadic rounding at every arithmetic operation. Floats only in informational timing/printing.',
       'C6_representation':total.package(155),
       'values':{k:v.package(155) for k,v in values.items()},
       'weighted_parts_in_C6_units':{k:(v/2187).package(155) for k,v in parts.items()},
       'hypergeometric_certificates':records,'primitive_certificate':pinfo,
       'alternating_certificate':altinfo,'Lambda_certificate':laminfo,
       'wheel_certificate':{'N':256,'M4':40,'M6':41,'tail_bound':packrat(werror),'recomputed':True,'overlaps_supplied_interval':True},
       'exact_seed_checks':pchecks,'wheel_exact_checks':wchecks,
       'unchanged_source_correction':expr['source_correction'],
       'active_auxiliary_series':expr['active_auxiliary_series'],
       'finite_special_value_reduction_claimed':False,
       'seconds':time.time()-st
    }
    path=ROOT/'results'/('complete_'+name+'.json');path.write_text(json.dumps(out,indent=2)+'\n')
    print('C6:',total.package(155)['decimal_lower'],total.package(155)['decimal_upper'],sep='\n',flush=True)
    print('width:',width_text(total),'seconds',time.time()-st,flush=True)
    return out
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else 'release')
