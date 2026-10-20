#!/usr/bin/env python3
"""R3a development evidence summary (standard library): every number of the R3a write-up, recomputed from the job
records under benchmarks/expanse_2026-10-c8/stage4b/dev_r3a/ (round1_908bd9d/ = the first version, round2_add273b/ =
the final one; dev/ = the development jobs: try1 the first fast path (13 work bits everywhere), try2 v1 with wrapper
overloads, try3 v1 with if constexpr (and the IPA probe), try4 the word-based addition through memcpy'd words, try5 the
same through unsigned __int128, try6 the final version, try7 the final version with a bit-pattern accumulator
(rejected), ipa_add273b the IPA probe on the final source). Writes r3a_summary.json next to this script's parent and prints it.

  python3 summarize_r3a.py
"""
import glob,json,os,statistics
from pathlib import Path
D=Path(__file__).resolve().parents[1]

def one(pattern):
    m=sorted(glob.glob(str(D/pattern)))
    return Path(m[0])if m else None

def round_summary(rd:Path)->dict:
    out={}
    b=one(f'{rd.name}/r3abuild.*/binaries_vs_stage3.json')
    if b:
        rec=json.loads(b.read_text());out['binaries']={k:v for k,v in rec['sha256'].items()}
        for be in('decimal','gmp'):
            a=json.loads((b.parent/f'asm_compare_{be}.json').read_text())
            out[f'asm_compare_{be}']={'functions':[a['functions_baseline'],a['functions_candidate']],'identical':a['identical'],
                                      'different':sorted(v['demangled']for v in a['different'].values()),'only_baseline':a['only_baseline'],'only_candidate':a['only_candidate']}
    q=one(f'{rd.name}/r3aval.*/quad_differential.json')
    if q:
        r=json.loads(q.read_text());R=r['differential']['result']
        out['differential']={'status':r['status'],'gates':r['gates'],'seed':R['seed'],'threads':R['threads'],'seconds':r['differential']['seconds'],
            'kernel_add_window_biased':R['kernel_add_window'],'kernel_mul_window_biased':R['kernel_mul_window'],
            'observed_add_sub_unbiased':r['ranges']['add_sub_window'].get('observed_unbiased'),'observed_mul_unbiased':r['ranges']['mul_window'].get('observed_unbiased'),
            'per_op':{op:{'random_pairs':R['random'][op]['pairs'],'random_fast':R['random'][op]['fast'],'random_mismatches':R['random'][op]['mismatches'],
                          'streams':{k:v['pairs']for k,v in R['random'][op]['streams'].items()},
                          'edge_pairs':R['edges'][op]['pairs'],'edge_fast':R['edges'][op]['fast'],'edge_mismatches':R['edges'][op]['mismatches'],
                          'edge_categories':{k:v['pairs']for k,v in R['edges'][op]['categories'].items()}}for op in('add','sub','mul')},
            'inject_mismatches':r['inject']['mismatches'],'sanitizer':{op:{'random':v['pairs'],'mismatches':v['mismatches']}for op,v in r['sanitizer']['random'].items()},
            'sanitizer_edge_mismatches':{op:v['mismatches']for op,v in r['sanitizer']['edges'].items()},'bench_ns':R.get('bench')}
        rs=r['ranges']['summary']or{}
        out['kernel_ranges']={blk:{'points':v['points'],'quad_points':v['quad_points'],
            **{op:{k:v[op][k]for k in v[op]if k in('n','fast_fraction','zero_operand','subnormal_operand','inf_nan_operand','operand_exponent','result_exponent','effective_sub_fraction','d_le_3','d_le_127','d_max_bin','cancellation_shift_max')}for op in('add','sub','mul')}}
            for blk,v in rs.items()}
    l=one(f'{rd.name}/r3aval.*/l8self.json')
    if l:
        r=json.loads(l.read_text());out['l8self']={'status':r['status'],'tests':[{k:t[k]for k in('sector','backend','graphs','rows','quad_points','mp_points','rule')}for t in r['tests']],
                                                  'baseline':r['tests'][0]['baseline'],'candidate':r['tests'][0]['candidate']}
    p=one(f'{rd.name}/r3aval.*/replay.json')
    if p:
        r=json.loads(p.read_text());out['replay_subset']={'status':r['status'],'executed':r['executed'],'items':len(r['tests'])}
    s=one(f'{rd.name}/r3aspeed.*/r3a_speed.json')
    if s:
        r=json.loads(s.read_text());ph=r['phase1']
        out['speed']={'host':r['host'],'threads':r['threads'],'repeats':r['repeats'],'baseline_sha256':r['baseline']['sha256'],'candidate_sha256':r['candidate']['sha256'],
            'blocks':{k:{'runs_integration_seconds':[(x['variant'],round(x['integration_seconds'],2))for x in v['runs']],'median_integration_seconds':v['median_integration_seconds'],
                         'speedup_integration':round(v['speedup_integration'],4),'speedup_wall':round(v['speedup_wall'],4),'rows_identical':v['rows_identical'],
                         'quad':v['runs'][0]['quad'],'mp':v['runs'][0]['mp']}for k,v in ph.items()},
            'ipc':{k:{'ipc':round(r['phase2'][k]['ipc'],4),'integration_seconds':round(r['phase2'][k]['integration_seconds'],2),'multiplexed':r['phase2'][k]['perf_stat']['multiplexed']}for k in('candidate','baseline')}}
        if r['phase3'].get('runs'):
            out['speed']['tier_timers']={x['tag']:{'quad_us_per_call':round(x['tier_timers']['quad_seconds']/x['tier_timers']['quad_calls']*1e6,1),
                'mp_us_per_call':round(x['tier_timers']['mp_seconds']/x['tier_timers']['mp_calls']*1e6,1),
                'first_pass_us_per_call':round(x['tier_timers']['first_pass_seconds']/x['tier_timers']['first_pass_calls']*1e6,2),
                'shares_of_thread_time':{t:round(x['tier_timers'][f'{t}_seconds']/(x['integration_seconds']*r['threads']),4)for t in('first_pass','quad','mp')}}for x in r['phase3']['runs']}
    return out

def dev_summary()->dict:
    out={}
    for t in sorted(glob.glob(str(D/'dev'/'*'))):
        name=Path(t).name;rec={}
        q=Path(t)/'out'/'qd.json'
        if q.exists():
            r=json.loads(q.read_text());rec['differential']={op:[v['pairs'],v['mismatches']]for op,v in r['random'].items()};rec['edges']={op:[v['pairs'],v['mismatches']]for op,v in r['edges'].items()};rec['bench_ns']=r.get('bench')
        p=Path(t)/'out'/'prof'/'r3a_prof.json'
        if p.exists():
            r=json.loads(p.read_text());rec['slice']={k:{'integration_seconds':round(v['integration_seconds'],2),'digest':v['rows_digest'][:16]}for k,v in r['runs'].items()};rec['slice_rows_identical']=r.get('rows_identical')
        ipa=sorted(glob.glob(str(Path(t)/'out'/'ipa'/'asm_*.json'))+glob.glob(str(Path(t)/'ipa'/'asm_*.json')))
        if ipa:
            rec['ipa_probe']={}
            for f in ipa:
                a=json.loads(Path(f).read_text());rec['ipa_probe'][Path(f).stem]={'identical':a['identical'],'different':sorted(v['demangled'][:90]for v in a['different'].values())}
        out[name]=rec
    return out

def main():
    s={'schema':'c8-d2-r3a-summary-1','round1_908bd9d':round_summary(D/'round1_908bd9d')if (D/'round1_908bd9d').exists()else None,
       'round2_add273b':round_summary(D/'round2_add273b')if (D/'round2_add273b').exists()else None,'dev':dev_summary()}
    (D/'r3a_summary.json').write_text(json.dumps(s,indent=1)+'\n');print(json.dumps(s,indent=1))

if __name__=='__main__':main()
