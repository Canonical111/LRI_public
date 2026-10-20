#!/usr/bin/env python3
"""Fresh binary128 quadrature replay using the archived independent implementation.
The references read the native extended-precision .bin weights; the optimized binary reads cw_*.txt when the
inputs directory has one, else the same .bin. --reference-ld also runs the original long-double program, so
original LD, optimized LD and binary128 are compared on one fixture (e.g. tests/make_validation_inputs.py output).
"""
from pathlib import Path
import argparse, decimal, hashlib, json, os, subprocess, sys
ROOT=Path(__file__).resolve().parents[1];D=decimal.Decimal
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(ref,other,keys,jac):
    """Differences of other minus binary128 ref: normalized raw (scale max(1,|quad|)), per-slot absolute, projected C7."""
    mx=D(0);slot=[D(0)]*14;project=D(0)
    for k in keys:
        rv=ref[k];delta=[D(x)-D(y) for x,y in zip(other[k],rv)]
        mx=max(mx,max(abs(dx)/max(D(1),abs(D(y))) for dx,y in zip(delta,rv)));slot=[max(s,abs(dx)) for s,dx in zip(slot,delta)];project=max(project,abs(sum(dx*j for dx,j in zip(delta,jac))))
    return mx,slot,project

def accuracy(Q,O,R,keys,criterion='strict'):
    """Per-element (replicate, graph, slot) accuracy of optimized O and original R against binary128 Q.
    strict = plan A5 literally: optimized error <= original error for every element.
    rounding_floor = proposed amendment: a genuine element may also be within 64*2^-64 of its own |binary128|;
    a structurally zero element (|binary128| < 1e-12 of its row's largest slot) must stay below 1e-15 of it."""
    ulp=D(64)/D(2)**64;tol=lambda er:er*(1+D('1e-12'))+D('1e-30');n=0;sf=[];ff=[]
    for k in keys:
        q=[D(x) for x in Q[k]];o=[D(x) for x in O[k]];r=[D(x) for x in R[k]];G=max(abs(x) for x in q)
        for s in range(14):
            eo=abs(o[s]-q[s]);er=abs(r[s]-q[s]);n+=1;structural=abs(q[s])<G*D('1e-12')
            rec={'replicate':k[0],'graph':k[1],'slot':s,'structural_zero':structural,'binary128':str(q[s]),'optimized_error':str(eo),'original_error':str(er),
                 'optimized_error_in_2^-64_units':str(eo/abs(q[s])*D(2)**64) if q[s] else None}
            if eo>tol(er):sf.append(rec)
            if not (eo<=G*D('1e-15') if structural else eo<=max(tol(er),ulp*abs(q[s]))):ff.append(rec)
    out={'elements':n,'gate':criterion,'strict':{'rule':'every element: optimized error <= original error (plan A5)','failures':len(sf),'failed_elements':sf[:100],'passed':not sf},
         'rounding_floor':{'rule':'genuine element: optimized error <= max(original error, 64*2^-64*|binary128|); structurally zero element (|binary128| < 1e-12 of the row maximum): optimized error <= 1e-15 of the row maximum',
                           'failures':len(ff),'failed_elements':ff[:100],'passed':not ff}}
    out['passed']=out[criterion.replace('-','_')]['passed'];return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--L',type=int,default=7,choices=[5,6,7]);p.add_argument('--degree',type=int,default=3)
    p.add_argument('--inputs',type=Path,default=ROOT/'reference/inputs');p.add_argument('--counts',type=Path,help='default: INPUTS/quad_replay_L{L}_N{degree}.txt');p.add_argument('--reference-ld',action='store_true',help='also run the original long-double bin/reference_power');p.add_argument('--criterion',choices=['strict','rounding-floor'],default='strict',help='gate: strict = plan A5 (default); rounding-floor = proposed amendment');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if any(a.out.iterdir()):raise FileExistsError('Use an empty output directory')
    if not (ROOT/'bin/reference_power_quad').exists():subprocess.run([sys.executable,ROOT/'tools/build_reference.py','--quad'],check=True)
    if a.reference_ld and not (ROOT/'bin/reference_power').exists():subprocess.run([sys.executable,ROOT/'tools/build_reference.py'],check=True)
    inputs=a.inputs.resolve();cf=(a.counts or inputs/f'quad_replay_L{a.L}_N{a.degree}.txt').resolve();tokens=list(map(int,cf.read_text().split()));ng=tokens[0];counts=dict(zip(tokens[1::2],tokens[2::2]));rows=[]
    for rep in range(2):
        for gi,count in counts.items():
            if count:rows.append((len(rows),rep,gi,0,count,count))
    task=a.out/'tasks.txt';task.write_text(f'C7TASKS1 {ng} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n' for r in rows));seed=649410
    commands=[([ROOT/'bin/reference_power_quad',inputs,a.L,a.degree,0,2,seed,a.out/'quad.json','power','.8',cf],'quad'),
       ([ROOT/'bin/c7_integrate','--mode','power','--inputs',inputs,'--L',a.L,'--degree',a.degree,'--tasks',task,'--seed',seed,'--rate','.8','--threads',1,'--output',a.out/'optimized.json'],'optimized')]
    if a.reference_ld:commands.append(([ROOT/'bin/reference_power',inputs,a.L,a.degree,0,2,seed,a.out/'original.json','power','.8',cf],'original'))
    for cmd,tag in commands:
        with (a.out/f'{tag}.log').open('w') as f:subprocess.run(list(map(str,cmd)),check=True,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_NUM_THREADS='1'))
    rd=lambda t:json.loads((a.out/f'{t}.json').read_text(),parse_float=D)
    ref=rd('quad');new=rd('optimized');mapping=json.loads((ROOT/'reference/verification/full_affine_assembly.json').read_text(),parse_float=D)
    jac=list(map(D,mapping['loops'][str(a.L)]['adjusted'][7]));keys=[(r['replicate'],r['graph']) for r in new['rows']]
    grid=lambda d:{k:d['graph_batches'][k[0]][k[1]] for k in keys};Q=grid(ref);O={(r['replicate'],r['graph']):r['value'] for r in new['rows']}
    base=inputs/f'cw_L{a.L}_N{a.degree}';weights={s:(sha(base.with_suffix(s)) if base.with_suffix(s).exists() else None) for s in ('.bin','.txt')}
    result={'fresh_binary128_reference':True,'native_extended_precision_weights':True,'L':a.L,'degree':a.degree,'rows':len(rows),'inputs':str(inputs),'counts_file':str(cf),'counts_sha256':sha(cf),
            'weights_sha256':weights,'optimized_reads':'txt' if weights['.txt'] else 'bin','executables':{tag:{'path':str(cmd[0]),'sha256':sha(cmd[0])} for cmd,tag in commands}}
    with decimal.localcontext() as ctx:
        ctx.prec=50;mx,slot,project=stats(Q,O,keys,jac)
        result.update(max_normalized_raw_difference=str(mx),max_absolute_projected_C7_difference=str(project),optimized_vs_quad={'max_normalized_raw_difference':str(mx),'per_slot_max_absolute_difference':list(map(str,slot)),'max_absolute_projected_C7_difference':str(project)})
        if a.reference_ld:
            R=grid(rd('original'));rmx,rslot,rproject=stats(Q,R,keys,jac);dmx,_,dproject=stats(R,O,keys,jac)
            result['original_vs_quad']={'max_normalized_raw_difference':str(rmx),'per_slot_max_absolute_difference':list(map(str,rslot)),'max_absolute_projected_C7_difference':str(rproject)}
            result['optimized_vs_original']={'max_normalized_raw_difference':str(dmx),'max_absolute_projected_C7_difference':str(dproject),'note':'scale max(1,|original|)'}
            result['optimized_no_less_accurate_all_slots']=all(o<=r*(1+D('1e-12'))+D('1e-30') for o,r in zip(slot,rslot))
            result['accuracy_criterion']=accuracy(Q,O,R,keys,a.criterion)
    result['scope']='selected graph/tree replays, not interval certification or full C7 integration'
    (a.out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert mx<D('1e-9')
    if a.reference_ld and not result['accuracy_criterion']['passed']:sys.exit(f'accuracy criterion "{a.criterion}" failed (see accuracy_criterion)')
if __name__=='__main__':main()
