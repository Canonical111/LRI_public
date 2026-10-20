#!/usr/bin/env python3
"""Stage 4a write-up: recompute the headline numbers of docs/PERFORMANCE.md ("Stage 4a: profiles on the Stage-3
baseline") from the raw evidence, independently of the runners' summaries and of tools/benchkit.py's classifier.

Standard library only; reads committed files only; writes stage4a_derived.json beside this script (or --output).
Sources (paths relative to benchmarks/):
  P1  expanse_2026-10-c8/stage4a/prof1.54661716.0/p1/: the perf report texts (--sort dso,symbol and --sort dso) parsed
      here with this script's own parser and categories, and the tier-timer rows and source-line regions the job wrote
      into p1.json (runs and source lines are byte-equal in p1.json and p1_reparsed.json);
  P2  prof2.54661717.0/p2/*.perfstat.csv (perf stat -x,) and interleave/interleave.json (per-graph repeat timings);
  P3  prof3.54661718.0/p3/p3.json (histogram counts per block and rate);
  P4  prof4.54661719.0/p4/<shape>.json (Expanse full node), prof4.54661771.0/p4/<shape>.json (Expanse half node) and
      ../symmetry_2026-10-c8/stage4a/prof4.569788.0/p4/<shape>.json (symmetry);
  P5  stage3b/sweep1.54641706.0/cost_model.json (J-SWEEP-1);
  cost  stage4a/admission/sacct_stage4a.txt and ../symmetry_2026-10-c8/stage4a/admission/sacct_569788.txt,
      ../symmetry_2026-10-c8/jgen3/verdict.json.
Usage: python3 -B derive_stage4a.py [--output FILE] [--quiet]"""
from __future__ import annotations
import argparse,json,math,re,statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
S4=HERE.parent                      # benchmarks/expanse_2026-10-c8/stage4a
EXP=S4.parent                       # benchmarks/expanse_2026-10-c8
BENCH=EXP.parent                    # benchmarks
SYM=BENCH/'symmetry_2026-10-c8'
P1DIR=S4/'prof1.54661716.0'/'p1'
BLOCKS=('heavy_free_L7','heavy_power_L7','heavy_free_L8','heavy_power_L8')
QOPS=('__addtf3','__subtf3','__multf3','__divtf3')

def r(x,n=4):return None if x is None else round(x,n)

# ------------------------------------------------------------------ P1: perf report texts
ROW=re.compile(r'^\s*([\d.]+)%\s+(\d+)\s+(\S+)\s+\[(.)\]\s+(.*)$')
def parse_dso_symbol(path:Path)->dict:
    """perf report --sort dso,symbol --stdio -n: rows (percent, samples, dso, level, symbol). perf 4.18 appends the
    IPC and [IPC Coverage] columns ('-  -' without LBR); they are separated from the padded symbol by 2+ spaces."""
    rows=[];head={}
    for line in path.read_text().splitlines():
        if line.startswith('#'):
            m=re.match(r'# Total Lost Samples: (\d+)',line)
            if m:head['lost']=int(m[1])
            m=re.match(r"# Samples: (\S+) of event '(\S+)'",line)
            if m:head['samples_text'],head['event']=m[1],m[2]
            continue
        m=ROW.match(line)
        if not m:continue
        parts=re.split(r'\s{2,}',m[5].strip())
        sym=parts[0];tail=parts[1:]
        if any(not re.fullmatch(r'-|[\d.]+%?|\[[\d. %]*\]',t)for t in tail):raise ValueError(f'unexpected columns in {path.name}: {line!r}')
        rows.append({'pct':float(m[1]),'samples':int(m[2]),'dso':m[3],'level':m[4],'sym':sym})
    return {'head':head,'rows':rows}
def parse_dso(path:Path)->dict:
    out={}
    for line in path.read_text().splitlines():
        if line.startswith('#'):continue
        m=re.match(r'^\s*([\d.]+)%\s+(\d+)\s+(\S+)\s*$',line)
        if m:out[m[3]]=float(m[1])
    return out

def base(sym:str)->str:
    s=re.sub(r'@.*$','',sym)
    return s[5:]if s.startswith('__GI_')else s

def p1_block(name:str)->dict:
    rep=parse_dso_symbol(P1DIR/f'{name}.perf_report_dso_symbol.txt');rows=rep['rows'];dso=parse_dso(P1DIR/f'{name}.perf_report_dso.txt')
    def S(pred):return sum(x['pct']for x in rows if pred(x))
    W='c8d2_gmp';LG='libgcc_s.so.1';QM='libquadmath.so.0.0.0';GMP='libgmp.so.10.4.1';LIBC='libc-2.28.so';LIBM='libm-2.28.so'
    ops={o:{'libgcc':S(lambda x,o=o:x['dso']==LG and x['sym']==o),
            'plt':S(lambda x,o=o:x['dso']==W and x['sym']==o+'@plt'),
            'libquadmath':S(lambda x,o=o:x['dso']==QM and x['sym']==o)}for o in QOPS}
    kernel_q={o:ops[o]['libgcc']+ops[o]['plt']for o in QOPS}   # what calculate_shared<Q> calls (libquadmath's copies serve expq)
    libgcc_support=S(lambda x:x['dso']==LG and x['sym']not in QOPS)
    sfp=S(lambda x:x['dso']==LG and x['sym']=='__sfp_handle_exceptions')
    fenv=S(lambda x:x['dso']==LIBM and re.fullmatch(r'fe(setenv|holdexcept|setround|getround|updateenv|getenv)',base(x['sym']))is not None)
    expq=S(lambda x:x['sym']=='expq')
    gmp_plt_w=S(lambda x:x['dso']==W and x['sym'].startswith('__gmp')and x['sym'].endswith('@plt'))
    g=lambda *names:S(lambda x:x['dso']==GMP and base(x['sym'])in names)
    mp_exp_syms=S(lambda x:x['dso']==W and re.search(r'hyp0F0|eval_exp|pow_imp',x['sym'])is not None)
    lifetime_gmp=g('__gmpf_init2','__gmpf_clear','__gmp_default_allocate','__gmp_default_free','__gmpf_set','__gmpf_set_si')
    opassign=S(lambda x:x['dso']==W and 'gmp_float_imp<350u>::operator='in x['sym'])
    malloc=S(lambda x:x['dso']==LIBC and re.fullmatch(r'(_int_)?(malloc|free)|cfree|malloc_consolidate|tcache.*',base(x['sym']))is not None)
    get_str=S(lambda x:x['dso']==GMP and re.search(r'get_str',x['sym'])is not None)
    strtold=S(lambda x:'strtold'in x['sym'])
    extract_float=S(lambda x:'_M_extract_float'in x['sym'])
    calc_ref=S(lambda x:'calculate_reference'in x['sym'])
    res={
     'total_samples_text':rep['head'].get('samples_text'),'lost':rep['head'].get('lost'),'listed_pct':sum(x['pct']for x in rows),
     'dso':dso,
     'binary128':{
        'ops_by_place':ops,
        'all_arith':sum(sum(v.values())for v in ops.values()),
        'kernel_ops':kernel_q,'kernel_addsubmul':kernel_q['__addtf3']+kernel_q['__subtf3']+kernel_q['__multf3'],
        'kernel_div':kernel_q['__divtf3'],
        'libgcc_support_other':libgcc_support,'sfp_handle_exceptions':sfp,
        'plt_stubs_quad':sum(ops[o]['plt']for o in QOPS)},
     'expq':{'expq_self':expq,'libquadmath_dso':dso.get(QM,0.),'fenv_libm':fenv,'family_upper':dso.get(QM,0.)+fenv},
     'gmp':{'dso':dso.get(GMP,0.),'plt_in_worker':gmp_plt_w,
            'mul_basecase':g('__gmpn_mul_basecase'),'add_n':g('__gmpn_add_n'),'gmpf_add':g('__gmpf_add'),'copyi':g('__gmpn_copyi'),
            'divrem_1':g('__gmpn_divrem_1'),'sqr_basecase':g('__gmpn_sqr_basecase'),'gmpf_mul':g('__gmpf_mul'),'gmpf_div_ui':g('__gmpf_div_ui'),
            'division':g('__gmpn_sbpi1_div_q','__gmpn_invert_limb','__gmpn_div_q','__gmpn_sbpi1_div_qr','__gmpn_tdiv_qr','__gmpf_div','__gmpn_submul_1'),
            'lifetime':lifetime_gmp,'get_str':get_str},
     'worker':{'dso':dso.get(W,0.),'main_omp_fn':S(lambda x:x['dso']==W and x['sym']=='main._omp_fn.0'),
               'calculate_shared_mp':S(lambda x:x['dso']==W and x['sym'].startswith('calculate_shared<boost')),
               'calculate_shared_q':S(lambda x:x['dso']==W and x['sym'].startswith('calculate_shared<__float128')),
               'mp_exp_symbols':mp_exp_syms,'mp_operator_assign':opassign},
     'malloc_free':malloc,'mp_to_ld':{'get_str':get_str,'strtold':strtold,'upper':get_str+strtold},'graph_parse_extract_float':extract_float,
     'calculate_reference_symbol':calc_ref,
     'kernel_space':S(lambda x:x['level']=='k'),'libgomp':dso.get('libgomp.so.1.0.0',0.),
    }
    res['mp_exp_lower']=mp_exp_syms+res['gmp']['gmpf_div_ui']+res['gmp']['divrem_1']+res['gmp']['sqr_basecase']
    res['r4a']={'allocation_lifetime':malloc+lifetime_gmp+opassign+S(lambda x:x['dso']==W and x['sym']=='__gmpf_init2@plt'),
                'with_copyi':malloc+lifetime_gmp+opassign+S(lambda x:x['dso']==W and x['sym']=='__gmpf_init2@plt')+res['gmp']['copyi']+g('__gmpn_copyi@plt')}
    return res

def p1()->dict:
    j=json.loads((P1DIR/'p1.json').read_text());jr=json.loads((P1DIR/'p1_reparsed.json').read_text())
    out={'settings':{k:j['settings'][k]for k in('threads','freq','call_graph','concurrent','pinned')},'perf_version':j['perf']['version'].strip(),
         'paranoid':j['perf']['paranoid'],'worker_sha256':j['identity']['executables']['worker']['sha256'],'blocks':{}}
    for b in BLOCKS:
        assert j['blocks'][b]['tier_run']==jr['blocks'][b]['tier_run']and j['blocks'][b]['perf_run']==jr['blocks'][b]['perf_run']
        t=j['blocks'][b]['tier_run'];n=t['native'];sec=t['tier_split']['seconds'];calls=t['tier_split']['calls']
        thread=n['threads']*n['integration_seconds'];tiers=sum(sec.values())
        pr=j['blocks'][b]['perf_run']
        out['blocks'][b]={
          'points':n['points'],'quad_calls':n['quad'],'mp_calls':n['mp'],'quad_fraction':n['quad']/n['points'],'mp_fraction':n['mp']/n['points'],
          'mp_per_quad':n['mp']/n['quad'],'thread_seconds':thread,'task_seconds':n['task_seconds'],'openmp_efficiency':n['openmp_efficiency'],
          'share_of_thread_time':{k:sec[k]/thread for k in sec},'share_of_tiers':{k:sec[k]/tiers for k in sec},'tiers_over_thread_time':tiers/thread,
          'us_per_call':{k:1e6*sec[k]/calls[k]for k in sec},'rows_identical_worker_vs_prof':j['blocks'][b]['rows_identical_worker_vs_prof'],
          'perf_record':{'samples':pr['record']['samples'],'lost':pr['record']['lost_samples'],'wall':pr['wall_seconds'],'tier_wall':t['wall_seconds']},
          'srcline':{k:j['blocks'][b]['perf']['srcline']['kernel_regions_percent'][k]for k in('shift_loop','calculate_reference','calculate_products','calculate_shared','evaluate','sample')},
          'srcline_regions_lines':j['blocks'][b]['perf']['srcline']['kernel_regions_lines'],
          'srcline_top':j['blocks'][b]['perf']['srcline']['top_lines'][:3],'srcline_status':j['blocks'][b]['perf']['srcline']['status'],
          'perf':p1_block(b)}
    # Affine per-call model from the L7 and L8 heavy blocks of each sector: c(tier) = a + k * c(first pass).
    fits={}
    for s in('free','power'):
        u7=out['blocks'][f'heavy_{s}_L7']['us_per_call'];u8=out['blocks'][f'heavy_{s}_L8']['us_per_call']
        f={}
        for t in('quad','mp'):
            k=(u8[t]-u7[t])/(u8['first_pass']-u7['first_pass']);f[t]={'k':k,'a_us':u7[t]-k*u7['first_pass']}
        fits[s]=f
    out['per_call_fit']=fits
    return out

# ------------------------------------------------------------------ P2
def perfstat(path:Path)->dict:
    ev={}
    for line in path.read_text().splitlines():
        if not line.strip()or line.startswith('#'):continue
        f=line.split(',');ev[f[2]]={'value':float(f[0]),'running_pct':float(f[4])}
    c=ev['cycles']['value'];i=ev['instructions']['value']
    return {'ipc':i/c,'l1d_miss_rate':ev['L1-dcache-load-misses']['value']/ev['L1-dcache-loads']['value'],
            'branch_miss_rate':ev['branch-misses']['value']/ev['branches']['value'],'ghz':c/(ev['task-clock']['value']*1e6),
            'min_running_pct':min(v['running_pct']for k,v in ev.items()if k!='task-clock'),'task_clock_s':ev['task-clock']['value']/1e3}
def p2()->dict:
    d=S4/'prof2.54661717.0';out={'perfstat':{},'probe':{}}
    for b in('nopromo_free_L7','nopromo_free_L8','heavy_free_L8'):
        out['perfstat'][b]={m:perfstat(d/'p2'/f'{b}.{m}.perfstat.csv')for m in('parallel','serial')}
    pj=json.loads((d/'p2'/'p2.json').read_text())
    out['p2_native']={b:{m:{k:pj['blocks'][b][m]['native'].get(k)for k in('quad','mp','points','threads')}for m in('parallel','serial')}
                      for b in pj.get('blocks',{})}if 'blocks'in pj else None
    ij=json.loads((d/'interleave'/'interleave.json').read_text());per=[]
    for x in ij['results']:
        res=x['result'];med={k:statistics.median(v)for k,v in res['all_seconds'].items()}
        per.append({'block':x['block'],'graph':x['graph'],'terms':res['terms'],'addends':res['addends'],'us_per_point_1':1e6*med['1'],
                    'speedup2':med['1']/med['2'],'speedup4':med['1']/med['4'],'identical':all(res['identical'].values())})
    gm=lambda xs:math.exp(sum(math.log(v)for v in xs)/len(xs))
    out['probe']={'per_graph':per,'settings':ij['settings'],
                  'geomean2_all':gm([p['speedup2']for p in per]),'geomean4_all':gm([p['speedup4']for p in per]),
                  'geomean2_nopromo':gm([p['speedup2']for p in per if p['block'].startswith('nopromo')]),
                  'geomean2_heavy':gm([p['speedup2']for p in per if p['block'].startswith('heavy')]),
                  'max2':max(p['speedup2']for p in per),'all_identical':all(p['identical']for p in per)}
    return out

# ------------------------------------------------------------------ P3
def frac(h:dict,pred)->int:return sum(v for k,v in h.items()if pred(int(k)))
def p3()->dict:
    j=json.loads((S4/'prof3.54661718.0'/'p3'/'p3.json').read_text());out={}
    for key,x in j['results'].items():
        h=x['ratio']['histograms'];n=x['native'];ld=h['ld_fail'];q=h['quad'];mp=h['mp']
        nld=sum(ld.values());nq=sum(q.values());nmp=sum(mp.values())
        fail23=frac(q,lambda k:k<=-24)            # ratio < 1e-23 (bin k: [10^k, 10^(k+1)); -401: zero or < 1e-400)
        o={'block':x['block'],'sector':x['sector'],'L':x['L'],'rate':x['rate'],'points':n['points'],'quad':n['quad'],'mp':n['mp'],
           'us_per_point_thread':n['microseconds_per_point_thread'],
           'checks':{'ld_total_eq_quad':nld==n['quad'],'quad_total_eq_quad':nq==n['quad'],'mp_total_eq_mp':nmp==n['mp'],'quad_fail_eq_mp':fail23==n['mp'],
                     'ld_all_below_1e-9':frac(ld,lambda k:k>=-9)==0,'job_ok':x['ratio']['ok']},
           'quad_fraction':n['quad']/n['points'],'mp_fraction':n['mp']/n['points'],'mp_per_quad':n['mp']/n['quad'],
           'ld_top_decade':frac(ld,lambda k:k==-10)/nld,'ld_below_1e-12':frac(ld,lambda k:k<=-13)/nld,
           'quad_pass_within_1':frac(q,lambda k:k==-23)/nq,'quad_pass_within_2':frac(q,lambda k:-23<=k<=-22)/nq,'quad_pass_within_3':frac(q,lambda k:-23<=k<=-21)/nq,
           'mp_increase_dd_1e-21':frac(q,lambda k:-23<=k<=-22)/n['mp'],'mp_increase_dd_1e-20':frac(q,lambda k:-23<=k<=-21)/n['mp'],
           'mp_below_1e-50':frac(mp,lambda k:k<=-51)/nmp,'mp_below_1e-60':frac(mp,lambda k:k<=-61)/nmp,
           'mp_below_1e-63':frac(mp,lambda k:k<=-64)/nmp,'mp_below_1e-66':frac(mp,lambda k:k<=-67)/nmp,'mp_below_1e-77':frac(mp,lambda k:k<=-78)/nmp,
           'mp_count_below_1e-63':frac(mp,lambda k:k<=-64),'mp_deepest_bin':min(int(k)for k in mp),'mp_zero_bin':mp.get('-401',0)}
        out[key]=o
    return out

# ------------------------------------------------------------------ P4
def p4_run(d:Path,shapes:list[str])->dict:
    out={}
    for s in shapes:
        x=json.loads((d/f'{s}.json').read_text());L=x['lanes'];W=x['wall_seconds']
        lanes=x['lanes_detail'];ns=x['numastat_delta']
        hit=sum(v['numa_hit']for v in ns.values());other=sum(v['other_node']for v in ns.values());miss=sum(v['numa_miss']for v in ns.values())
        out[s]={'lanes':L,'threads':x['threads'],'cores':x['cores'],'wall':W,'throughput':x['cost_model_seconds']/W,
                'busy':sum(l['task_seconds']for l in lanes)/(x['cores']*W),'openmp_efficiency':x['openmp_efficiency'],
                'load_share':sum(l['load_seconds']for l in lanes)/(L*W),'stage_share':sum(l['stage_seconds']for l in lanes)/(L*W),
                'native_overhead_share':x['native_overhead_seconds']/(L*W),
                'load_staging_share':(sum(l['load_seconds']+l['stage_seconds']for l in lanes))/(L*W),
                'max_rss_gib_per_lane':max(l['max_rss_kb']for l in lanes)/2**20,'sum_rss_gib':sum(l['max_rss_kb']for l in lanes)/2**20,
                'min_lane_numa_local':min(l['numa_local_fraction']for l in lanes),'numastat_other_node_fraction':other/hit if hit else None,'numa_miss':miss,
                'lane_end_spread':x['lane_end_spread_seconds'],'blocks':x['blocks'],'tasks':x['tasks'],
                'task_seconds_per_task':sum(l['task_seconds']for l in lanes)/x['tasks'],'rows_digest':x['rows_digest'],'quad':x['quad'],'mp':x['mp'],
                'errors':x['errors']}
    best=max(out,key=lambda s:out[s]['throughput'])
    for s in out:out[s]['relative_to_best']=out[s]['throughput']/out[best]['throughput']
    return {'shapes':out,'best':best,'rows_identical':len({v['rows_digest']for v in out.values()})==1}
def p4()->dict:
    full=p4_run(S4/'prof4.54661719.0'/'p4',['1x128','2x64','4x32','8x16','16x8'])
    half=p4_run(S4/'prof4.54661771.0'/'p4',['1x64','2x32','4x16','8x8'])
    sym=p4_run(SYM/'stage4a'/'prof4.569788.0'/'p4',['1x64','2x32','4x16','8x8'])
    for s in sym['shapes']:sym['shapes'][s]['symmetry_over_expanse_half']=sym['shapes'][s]['throughput']/half['shapes'][s]['throughput']
    return {'expanse_full':full,'expanse_half':half,'symmetry':sym,
            'rows_symmetry_eq_expanse_half':sym['shapes']['8x8']['rows_digest']==half['shapes']['8x8']['rows_digest']}

# ------------------------------------------------------------------ P5
def quant(xs:list[float],q:float)->float:
    xs=sorted(xs);i=q*(len(xs)-1);lo=math.floor(i);hi=math.ceil(i);return xs[lo]+(xs[hi]-xs[lo])*(i-lo)
def p5(fits:dict)->dict:
    cm=json.loads((EXP/'stage3b'/'sweep1.54641706.0'/'cost_model.json').read_text())
    spp=cm['seconds_per_point'];qf=cm['quad_fraction'];mf=cm['mp_fraction'];out={};tiers={}
    for camp in('a','b'):
        for sector in('free','power'):
            for L in(7,8):
                keys=[k for k in spp if k.startswith(f'{camp}:{sector}:{L}:')]
                us=[1e6*spp[k]for k in keys];tot=sum(us)
                top=sorted(us,reverse=True);n10=max(1,round(len(us)/10))
                # Model tier split (per-call fits of P1): t = F (1 + kq q + km m) + aq q + am m, F = first pass + sampling.
                f=fits[sector];fp=qt=mt=mfix=0.;neg=0
                for k in keys:
                    t=1e6*spp[k];q=qf[k];m=mf[k]
                    F=(t-f['quad']['a_us']*q-f['mp']['a_us']*m)/(1+f['quad']['k']*q+f['mp']['k']*m)
                    if F<=0:neg+=1;F=0.
                    fp+=F;qt+=q*(f['quad']['a_us']+f['quad']['k']*F);mt+=m*(f['mp']['a_us']+f['mp']['k']*F);mfix+=m*f['mp']['a_us']
                s=fp+qt+mt;tiers[(camp,L)]=[x+y for x,y in zip(tiers.get((camp,L),[0.,0.,0.]),(fp,qt,mt))]
                out[f'{camp}:{sector}:L{L}']={'graphs':len(us),'sum_s_per_point':tot/1e6,'mean_us':tot/len(us),'p10':quant(us,.1),'p50':quant(us,.5),
                    'p90':quant(us,.9),'p99':quant(us,.99),'max':max(us),'top10pct_cost_share':sum(top[:n10])/tot,
                    'quad_fraction_point_mean':statistics.fmean(qf[k]for k in keys),'mp_fraction_point_mean':statistics.fmean(mf[k]for k in keys),
                    'quad_fraction_cost_weighted':sum(qf[k]*spp[k]for k in keys)/sum(spp[k]for k in keys),
                    'mp_fraction_cost_weighted':sum(mf[k]*spp[k]for k in keys)/sum(spp[k]for k in keys),
                    'promotion_free_graphs':sum(1 for k in keys if qf[k]==0 and mf[k]==0),
                    'model_tier_split':{'first_pass_and_sampling':fp/s,'quad':qt/s,'mp':mt/s,'mp_fixed_per_call_part':mfix/s,'graphs_clamped':neg,'model_over_measured':s/tot}}
    for (camp,L),(fp,qt,mt) in sorted(tiers.items()):
        s=fp+qt+mt;out[f'{camp}:both:L{L}']={'model_tier_split':{'first_pass_and_sampling':fp/s,'quad':qt/s,'mp':mt/s}}
    allsum=sum(spp.values());l8=sum(v for k,v in spp.items()if k.split(':')[2]=='8')
    out['all']={'core_seconds_per_point_all_graphs':allsum,'l8_share':l8/allsum,'keys':len(spp),'executable_sha256':cm['executable_sha256']}
    return out

# ------------------------------------------------------------------ cost
def cost()->dict:
    jobs=[]
    for line in (S4/'admission'/'sacct_stage4a.txt').read_text().splitlines():
        f=line.split('|')
        if len(f)<9 or not f[0].isdigit():continue
        jid,name,part,cpus,mem,el,state,code,node=f[:9];cpus=int(cpus);el=int(el)
        mem_g=float(mem.rstrip('G'))
        charged=max(cpus,mem_g/1.95)if part=='shared'else cpus  # Expanse: shared charges max(cores, mem/1.95 GB) (README rule); compute the node
        jobs.append({'job':jid,'name':name,'partition':part,'cpus':cpus,'elapsed_s':el,'state':state,'exit':code,'node':node,'su':charged*el/3600})
    sym=[]
    for line in (SYM/'stage4a'/'admission'/'sacct_569788.txt').read_text().splitlines():
        f=line.split('|')
        if f[0]=='569788':sym.append({'job':'569788','name':f[1],'partition':f[2],'state':f[3],'elapsed':f[7],'exit':f[8],'node':f[9],'cpus':int(f[10]),'core_hours':int(f[11])/3600})
    v=json.loads((SYM/'jgen3'/'verdict.json').read_text())['job']
    return {'expanse':jobs,'expanse_su':sum(j['su']for j in jobs),'symmetry_prof4':sym,'symmetry_jgen3':v}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=HERE/'stage4a_derived.json');ap.add_argument('--quiet',action='store_true')
    a=ap.parse_args()
    P1=p1();res={'schema':'c8-d2-stage4a-derived-1','P1':P1,'P2':p2(),'P3':p3(),'P4':p4(),'P5':p5(P1['per_call_fit']),'cost':cost()}
    def rnd(o):
        if isinstance(o,float):return float(f'{o:.6g}')
        if isinstance(o,dict):return {k:rnd(v)for k,v in o.items()}
        if isinstance(o,list):return [rnd(v)for v in o]
        return o
    a.output.write_text(json.dumps(rnd(res),indent=1,sort_keys=True)+'\n')
    if not a.quiet:print(f'wrote {a.output}')
    return 0

if __name__=='__main__':raise SystemExit(main())
