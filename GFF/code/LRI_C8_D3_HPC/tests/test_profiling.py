#!/usr/bin/env python3
"""Stage-4a profiling tools (PLAN "Performance plan", P1-P4, A-PERF-1; tools/benchkit.py, prepare_benchmarks.py --order
8, perf_profile.py, benchmark.py --lane-shapes / --interleave-probe, the prof jobs of slurm/native_job.sh): Mac-runnable
tests of the pure logic. No native build and no measurement: the worker is tests/fake_worker.py, perf is
tests/fake_perf.py, the diagnostic builds are wrappers that add fake tier timers or ratio histograms, the CPU topology
is --fake-topology with --no-pin. Port of C62d's tests/test_profiling.py (LRI_C8_D2_HPC@651c56f) to the d=3 tools.

  shapes        lane shapes -> disjoint NUMA-aligned CPU sets on the Expanse (2 x 4 x 16) and symmetry (2 x 4 x 8)
                topologies, the exact sets, and the refusals (does not fit, misaligned, unequal nodes, no NUMA data,
                malformed or repeated shapes)
  lpt_blocks    deterministic LPT shares, blocks of T tasks, production's two-maxima blocks (production.cut_blocks)
  perf_report   perf report --stdio parsing (symbol, dso,symbol, dso; -n; perf 4.18's IPC columns) and the plan's shares,
                with the d=3 categories (sqrtq, sqrtl)
  perf_stat     perf stat -x, CSV (IPC, unsupported and uncounted events) and perf record's summary line
  parsers       perf annotate, addr2line -a -i -f, ltrace -c, numa_maps, node numastat, the d=3 kernel.hpp regions
  ratio         P3 summaries on the d=3 histogram keys (-1..-401, zero_or_below), checks, fractions, margins
  tiers         the per-graph tier table and the population re-weighting of a stratified block (perf_profile.tier_split)
  fixtures      the committed benchmarks/fixtures8: every pin, block sizes, strata and weights, seeds, nets, chunking,
                P4 sizing and production's chunk rule; tampering refused; the cost model is the Stage-3 Expanse model
                (sha256 fc78fc8f...) read from J-SWEEP-1's evidence copy, never the live cost_models/ site model that
                Stage 5's refresh replaces, and the manifest is the Stage-4a one (sha256 becacd70...) but for that path
  determinism   rebuilding the fixtures gives the same bytes (nets compared when the scipy version is the manifest's)
  refusals      staging with a wrong member hash or no pack, interrupted builds, unfit shapes, wrong executables
  scripts       slurm/native_job.sh's prof jobs: names, baseline check before any profile, the clean merge first in prof1
  order7        prepare_benchmarks.py --order 7 verifies C7(3)'s committed fixtures and never rebuilds them
  inputs_verified  prepare_benchmarks.build_fixtures8 verifies its inputs against their manifest first (S4-005): the
                fixture pins are the verified hashes; a changed gamma or inventory is refused (65), no folder left
  e2e_lanes     benchmark.py --lane-shapes on a mini fixture (inputs_mini) with the fake worker: identical rows across
                shapes, --fraction, production blocks, a failing worker recorded
  e2e_probe     benchmark.py --interleave-probe driver with a fake probe executable
  e2e_perf      perf_profile.py p1 (perf, the reparse and the refusal fallback), p2, p3 and mpcheck with fake perf and
                fake diagnostics
  e2e_fe        perf_profile.py fe with fake C7 and C8 workers on C7(3)'s fixtures and symmetry's records
--only NAME,... runs the named tests (unknown names or an empty list exit 2 before any setup).
Usage: python3 -B tests/test_profiling.py [--output FILE] [--only NAME,...]"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,math,os,shutil,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import benchkit as bk  # noqa: E402
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,flush=True)

def refused(code,fn,*a,**k)->str:
    try:fn(*a,**k)
    except bk.BenchError as e:
        assert e.code==code,(code,e.code,str(e));return str(e)
    raise AssertionError(f'{getattr(fn,"__name__",fn)} did not refuse (expected {code})')

def fake_text(*args)->str:
    cp=subprocess.run([PY,str(ROOT/'tests/fake_perf.py'),*args],capture_output=True,text=True);assert cp.returncode==0,cp.stderr;return cp.stdout

# ---------------------------------------------------------------- shapes
def check_sets(cores,n,t):
    sets=bk.partition(cores,n,t);where={c:(s,nd)for s,nd,c in cores};c=sum(1 for x in cores if x[1]==cores[0][1])
    assert len(sets)==n and all(len(x)==t for x in sets),(n,t)
    flat=[x for s in sets for x in s];assert len(flat)==len(set(flat)),'not disjoint'
    for s in sets:
        nodes={where[x][1]for x in s};socks={where[x][0]for x in s}
        if t<=c:assert len(nodes)==1
        else:assert all(sum(1 for y in cores if y[1]==nd)==sum(1 for x in s if where[x][1]==nd)for nd in nodes),'partial NUMA node'
        if t<=4*c:assert len(socks)==1,'lane crosses sockets'
    return sets

def test_shapes():
    ex=bk.fake_cores('2x4x16');sy=bk.fake_cores('2x4x8')
    assert len(ex)==128 and ex[16]==(0,1,16)and ex[64]==(1,4,64)
    want={(1,128):[list(range(128))],(2,64):[list(range(64)),list(range(64,128))],(4,32):[list(range(32*i,32*i+32))for i in range(4)],
          (8,16):[list(range(16*i,16*i+16))for i in range(8)],(16,8):[list(range(8*i,8*i+8))for i in range(16)],(1,64):[list(range(64))]}
    for (n,t),sets in want.items():assert check_sets(ex,n,t)==sets,(n,t)
    for n,t in ((1,64),(2,32),(4,16),(8,8),(16,4),(3,16)):check_sets(sy,n,t)
    msgs=[refused(64,bk.partition,ex,1,256),refused(64,bk.partition,ex,3,24),refused(64,bk.partition,ex,5,32),refused(64,bk.partition,ex,1,96),
          refused(64,bk.partition,ex,2,12),refused(64,bk.partition,sy,16,8),refused(64,bk.partition,sy,3,32),refused(64,bk.partition,ex,0,8)]
    assert 'needs 256 cores'in msgs[0]and 'whole NUMA nodes'in msgs[1]and 'needs 160 cores'in msgs[2]and 'whole sockets'in msgs[3]and 'does not divide'in msgs[4]
    uneq=[(0,0,c)for c in range(16)]+[(0,1,c)for c in range(16,24)];refused(64,bk.partition,uneq,1,8)
    refused(64,bk.partition,[(0,-1,c)for c in range(8)],1,4)
    refused(64,bk.partition,[(0,0,0),(1,0,1)],1,1)  # a node across sockets
    assert bk.parse_shapes('1x128,2x64, 8x16')==[(1,128),(2,64),(8,16)]
    for bad in ('','1x','x2','0x8','2x0','1x4,1x4','2*64','1x4,'):refused(64,bk.parse_shapes,bad)
    refused(64,bk.fake_cores,'2x4');refused(64,bk.fake_cores,'0x4x4')
    ok('lane_shapes_numa_aligned_partition_and_refusals',expanse_shapes=len(want),refusals=len(msgs)+3)

def test_lpt_blocks():
    import production as prod
    costs=[5,3,3,2,2,2,1,1,1,1,9,4]
    items=[(float(c),(f'p{i%2}',i),[i])for i,c in enumerate(costs)]
    a=bk.lpt_shares(items,3);b=bk.lpt_shares(list(reversed(items)),3)
    assert a==b,'LPT depends on the input order'
    loads=[sum(x[0]for x in s)for s in a];assert sorted(x[1]for s in a for x in s)==sorted(x[1]for x in items)
    assert max(loads)-min(loads)<=max(costs),loads
    blocks=bk.lane_blocks(a[0],2,['p0','p1']);assert all(len(r)<=2 for _,r in blocks)
    seen=[p for p,_ in blocks];assert seen==sorted(seen),seen
    for p in ('p0','p1'):
        flat=[x for q,r in blocks if q==p for x in r];assert [x[0]for x in flat]==sorted((x[0]for x in flat),reverse=True)
    assert len(bk.lane_blocks(a[0],None,['p0','p1']))==len({x[1][0]for x in a[0]})
    assert [bk.block_tasks(t)for t in (1,8,16,32,64,128)]==[256,256,256,512,1024,2048]and bk.block_tasks(8,'all')is None and bk.block_tasks(8,'100')==100
    refused(64,bk.block_tasks,8,'x');refused(64,bk.block_tasks,8,'0')
    # production's two maxima: <= T tasks and <= S seconds at width w, the same bounds as production.cut_blocks
    many=[(float(10+(i%5)),('p0',i),[i])for i in range(40)];S,w=60.,2
    pb=bk.lane_blocks(many,16,['p0'],S,w);rows=sorted(many,key=lambda x:(-x[0],x[1]))
    cut=prod.cut_blocks([x[0]for x in rows],16,S,w)['bounds']
    assert [len(r)for _,r in pb]==[cut[k+1]-cut[k]for k in range(len(cut)-1)]and all(len(r)<=16 and sum(x[0]for x in r)/w<=S+1e-9 for _,r in pb)
    assert [x for _,r in pb for x in r]==rows and len(pb)>3
    ok('lpt_shares_and_production_blocks',loads=loads,production_blocks=len(pb))

# ---------------------------------------------------------------- perf parsing
EXPECT={'binary128_arith':52.0,'binary128_other':0.5,'expq':8.0,'sqrtq':0.0,'expl':4.0,'logl':0.5,'sqrtl':0.0,'gmpf':5.0,'gmpn':6.5,'gmp_other':0.0,'malloc_free':3.5,
        'mp_to_ld_lower':4.5,'mp_to_ld_likely':5.0,'calculate_reference_ld':3.0,'libgomp':1.5,'kernel':1.0,'worker_other':10.0,'unknown':0.0,'other':0.0,'gmp_total':16.0}
CAPTURED_IPC="""# Total Lost Samples: 0
#
# Samples: 3M of event 'cycles'
# Event count (approx.): 10952386853576
#
# Overhead       Samples  Shared Object         Symbol                                                                                    IPC   [IPC Coverage]
# ........  ............  ....................  ........................................................................................  ....................
#
    41.86%       1493097  libgcc_s.so.1         [.] __addtf3                                                                              -      -
     5.82%        207511  c8d3_gmp              [.] main._omp_fn.0                                                                        -      -
     5.16%        183950  libgcc_s.so.1         [.] __multf3                                                                              -      -
     2.64%         94037  c8d3_gmp              [.] calculate_shared<boost::multiprecision::number<boost::multiprecision::backends::gmp_float<350u>, (boost::multiprecision::expression_template_option)1>, false>     -      -
     1.90%         67702  libquadmath.so.0.0.0  [.] sqrtq                                                                                 -      -
     1.10%         39229  libgcc_s.so.1         [.] __divtf3                                                                              -      -
     0.61%         21754  c8d3_gmp              [.] __addtf3@plt                                                                          -      -
     0.35%         12306  libgcc_s.so.1         [.] __lttf2@@GCC_4.3.0                                                                    -      -
     0.24%          8600  libc-2.28.so          [.] malloc                                                                                -      -
     0.19%          6636  libm-2.28.so          [.] fesetenv                                                                              -      -
     0.12%          4340  libm-2.28.so          [.] __expl_finite                                                                         -      -
     0.09%          3073  [unknown]             [k] 0xffffffff824770f5                                                                    -      -
     0.07%          2538  libquadmath.so.0.0.0  [.] expq                                                                                  -      -
     0.05%          1700  libgmp.so.10.4.1      [.] __gmpf_sqrt                                                                           -      -
     0.04%          1312  libc-2.28.so          [.] __GI_____strtold_l_internal                                                           -      -
"""
def with_ipc(text:str,tail:str='  -      -')->str:
    """perf 4.18's layout: 'IPC   [IPC Coverage]' after the Symbol header and an IPC tail on every row."""
    out=[]
    for line in text.splitlines():
        if line.startswith('# Overhead')and 'Symbol'in line:line=line+'  IPC   [IPC Coverage]'
        elif bk._PCT.match(line):line=line+'   '+tail
        out.append(line)
    return '\n'.join(out)+'\n'

def test_perf_report():
    ds=bk.parse_perf_report(fake_text('report','--no-children','--stdio','-n','--sort','dso,symbol'))
    sy=bk.parse_perf_report(fake_text('report','--no-children','--stdio','-n','--sort','symbol'))
    dd=bk.parse_perf_report(fake_text('report','--no-children','--stdio','-n','--sort','dso'))
    assert ds['header']=={'lost':0,'samples_text':'1M','event':'cycles','event_count':987654321000},ds['header']
    assert len(ds['rows'])==19 and ds['rows'][0]=={'overhead':30.0,'samples':300000,'dso':'libgcc_s.so.1','level':'.','symbol':'__multf3'},ds['rows'][0]
    sh=bk.perf_shares(ds['rows'],'c8d3_gmp')
    for k,v in EXPECT.items():assert abs(sh['categories'][k]-v)<1e-9,(k,sh['categories'][k],v)
    assert sh['binary128_ops']=={'__addtf3':20.0,'__subtf3':1.0,'__multf3':30.0,'__divtf3':1.0}and abs(sh['total_listed']-100)<1e-9
    s2=bk.perf_shares(sy['rows'],None)
    assert all(abs(s2['categories'][k]-v)<1e-9 for k,v in EXPECT.items()if k not in('worker_other','other'))and s2['categories']['other']==10.0
    dt={x['dso']:x for x in bk.dso_table(dd['rows'])};assert abs(dt['libgcc_s.so.1']['overhead']-52.5)<1e-9 and dt['libgcc_s.so.1']['samples']==525000
    for text,ref in ((fake_text('report','--no-children','--stdio','-n','--sort','dso,symbol'),ds),(fake_text('report','--no-children','--stdio','-n','--sort','symbol'),sy)):
        assert bk.parse_perf_report(with_ipc(text))['rows']==ref['rows']
    cap=bk.parse_perf_report(CAPTURED_IPC);c=bk.perf_shares(cap['rows'],'c8d3_gmp');cc=c['categories']
    assert [r['symbol']for r in cap['rows']][:3]==['__addtf3','main._omp_fn.0','__multf3']and cap['rows'][3]['symbol'].endswith(', false>')
    assert abs(c['binary128_ops']['__addtf3']-(41.86+0.61))<1e-9 and abs(cc['sqrtq']-1.90)<1e-9 and abs(c['named']['sqrtq']-1.90)<1e-9 and abs(c['named']['__gmpf_sqrt']-0.05)<1e-9
    assert abs(cc['gmpf']-0.05)<1e-9 and abs(cc['fenv']-0.19)<1e-9 and abs(cc['expl']-0.12)<1e-9 and abs(cc['expq']-0.07)<1e-9 and abs(cc['kernel']-0.09)<1e-9
    assert abs(cc['worker_other']-(5.82+2.64))<1e-9 and abs(c['plt_stubs']-0.61)<1e-9 and abs(cc['mp_to_ld_lower']-0.04)<1e-9
    assert bk.SQRTL.match('__ieee754_sqrtl')and bk.SQRTL.match('sqrtl')and not bk.SQRTQ.match('sqrtl')
    ok('perf_report_parsing_and_plan_shares',categories=len(EXPECT))

def test_perf_stat():
    st=bk.parse_perf_stat_csv(subprocess.run([PY,str(ROOT/'tests/fake_perf.py'),'stat','-x,','--','true'],capture_output=True,text=True).stderr)
    assert abs(st['derived']['ipc']-98765432/123456789)<1e-12 and abs(st['derived']['branch_miss_rate']-0.01)<1e-12
    assert st['events']['L1-dcache-loads']=={'value':None,'unit':None,'running_percent':100.0,'status':'not supported'}
    assert st['events']['L1-dcache-load-misses']['status']=='not counted'and st['derived']['l1d_miss_rate']is None and st['multiplexed']
    one=bk.parse_perf_stat_csv('# started on x\n\n5,,cycles:u,1,50.00,,\n10,,instructions:u,1,50.00,2.0,insn per cycle\n')
    assert one['derived']['ipc']==2.0 and one['multiplexed']
    rec=bk.parse_perf_record_stderr('[ perf record: Woken up 3 times to write data ]\n[ perf record: Captured and wrote 312.456 MB /x/perf.data (5750000 samples) ]\n'
                                    'Processed 99 events and lost 7 chunks!\n\nCheck IO/CPU overload!\n')
    assert rec['mb']==312.456 and rec['samples']==5750000 and rec['lost_chunks']==7 and rec['warnings']==['Check IO/CPU overload!'],rec
    ok('perf_stat_csv_ipc_and_record_summary',ipc=round(st['derived']['ipc'],4))

def test_parsers():
    import perf_profile as pp
    an=bk.parse_annotate(fake_text('annotate','--stdio'))
    assert len(an)==1 and an[0]['dso']=='c8d3_gmp'and an[0]['samples']==100000 and an[0]['instructions']=={0x403f62:60.0,0x403f66:40.0},an
    a2l=bk.parse_addr2line('0x0000000000403f62\nevaluate(Graph const&, long double const*, long double, Scratch&)\n/x/src/kernel.hpp:193\nsample(Graph const&)\n'
                           '/x/src/kernel.hpp:230 (discriminator 2)\n0x0000000000403f66\n??\n??:0\n')
    assert a2l[0x403f62][1]==('sample(Graph const&)','/x/src/kernel.hpp',230)and a2l[0x403f66]==[('??','??',0)]
    lt=bk.parse_ltrace_c('% time     seconds  usecs/call     calls      function\n------ ----------- ----------- --------- --------------------\n'
                         ' 60.00    0.600000          2    300000 __gmpf_mul\n 40.00    0.400000          1    400000 __gmpf_add\n'
                         '------ ----------- ----------- --------- --------------------\n100.00    1.000000                700000 total\n')
    assert [r['function']for r in lt['rows']]==['__gmpf_mul','__gmpf_add']and lt['total']['calls']==700000
    assert bk.parse_numa_maps('7f00 default anon=10 N0=6 N1=4 kernelpagesize_kB=4\n7f10 default N2=2 kernelpagesize_kB=2048\n')=={0:24,1:16,2:4096}
    with tempfile.TemporaryDirectory()as td:
        for n,(h,m)in enumerate(((10,1),(20,2))):
            d=Path(td)/f'devices/system/node/node{n}';d.mkdir(parents=True);(d/'numastat').write_text(f'numa_hit {h}\nnuma_miss {m}\nlocal_node {h}\n')
        b=bk.node_numastat(td);(Path(td)/'devices/system/node/node1/numastat').write_text('numa_hit 25\nnuma_miss 2\nlocal_node 24\n')
        assert bk.numastat_delta(b,bk.node_numastat(td))[1]=={'numa_hit':5,'numa_miss':0,'local_node':4}
    text=(ROOT/'src/kernel.hpp').read_text();lines=text.splitlines();reg=pp.kernel_regions(text)
    assert set(reg)=={'shift_loop','calculate_reference','calculate_products','calculate_shared','mp_check_record','evaluate','sample'},reg
    lo,hi=reg['shift_loop'];assert lo==hi and 'for(auto mask:g.masks)'in lines[lo-1]
    for k in ('calculate_reference','calculate_products','calculate_shared','mp_check_record','evaluate','sample'):
        lo,hi=reg[k];assert lo<hi and k in lines[lo-1]and lines[hi-1]=='}',(k,lo,hi)
    assert reg['evaluate'][0]<reg['shift_loop'][0]<reg['evaluate'][1]
    assert any('sqrtl(U)'in l for l in lines[reg['calculate_products'][0]-1:reg['calculate_products'][1]])
    ok('annotate_addr2line_ltrace_numa_and_kernel_regions',regions={k:list(v)for k,v in reg.items()})

def test_ratio():
    rows=[{'begin':0,'end':100,'quad':30,'mp':5},{'begin':0,'end':50,'quad':10,'mp':0}]
    rh={'ld_fail':{'-10':25,'-15':15},'quad':{'-1':3,'-12':17,'-22':10,'-23':5,'-30':4,'zero_or_below':1},'mp':{'-40':3,'-100':2}}
    s=bk.ratio_summary({'rows':rows,'ratio_histogram':rh})
    assert s['ok']and s['points']==150 and s['quad']==40 and s['mp']==5,s['checks']
    assert s['cdf']['quad']['1e-20']==20/40 and s['cdf']['quad']['1e-23']==5/40 and s['cdf']['quad']['1e-9']==37/40 and s['cdf']['ld_fail']['1e-12']==15/40
    assert s['cdf']['mp']['1e-50']==2/5 and s['quad_accepted_margin_digits']=={'22':3,'11':17,'1':10,'0':5}
    assert s['histograms']['quad']=={'-402':1,'-30':4,'-23':5,'-22':10,'-12':17,'-1':3}
    bad=bk.ratio_summary({'rows':[{**rows[0],'mp':6},rows[1]],'ratio_histogram':rh})
    assert not bad['ok']and not bad['checks']['mp_equals_mp_calls']and not bad['checks']['quad_below_1e-23_equals_mp_calls']
    assert bk.below({-1:3,-10:2,-402:1},9)==3 and bk.below({-1:3},1)==0 and bk.RATIO_ZERO==-402
    # the native key scheme (src/diagnostics.hpp): bin b holds [10^-(b+1), 10^-b) under key -(b+1); 401 keys, then zero_or_below
    dh=(ROOT/'src/diagnostics.hpp').read_text();assert 'constexpr int RATIO_BINS=402;'in dh and 'zero_or_below'in dh and 'std::to_string(-(b+1))'in dh
    ok('ratio_histogram_summaries_and_checks')

def test_tiers():
    import perf_profile as pp
    n={'integration_seconds':2.0,'threads':2,'rows':[{'graph':1,'begin':0,'end':100,'seconds':1.0,'quad':10,'mp':1},{'graph':2,'begin':0,'end':100,'seconds':3.0,'quad':50,'mp':10},
                                                     {'graph':1,'begin':100,'end':200,'seconds':1.0,'quad':10,'mp':1}],
       'tier_timers':{'clock':'steady_clock','first_pass_seconds':2.0,'first_pass_calls':300,'quad_seconds':1.5,'quad_calls':70,'mp_seconds':0.9,'mp_calls':12,
                      'per_graph':{'1':[1.2,0.4,0.2,200,20,2],'2':[0.8,1.1,0.7,100,50,10]}}}
    t=pp.tier_split(n,{'1':{'weight':3.0},'2':{'weight':1.0}})
    assert t['task_seconds']==5.0 and abs(t['share_of_task_time']['quad']-0.3)<1e-12 and abs(t['microseconds_per_call']['mp']-1e6*0.9/12)<1e-6
    g=t['per_graph'];assert g['1']['points']==200 and g['1']['task_seconds']==2.0 and g['2']['seconds']['mp']==0.7 and g['2']['calls']['quad']==50
    p=t['population'];W=4.0
    task=(3*2.0/200+1*3.0/100)/W;quad=(3*0.4/200+1.1/100)/W
    assert abs(p['task_seconds_per_point']-task)<1e-15 and abs(p['tier_seconds_per_point']['quad']-quad)<1e-15 and abs(p['share_of_task_time']['quad']-quad/task)<1e-12
    assert abs(sum(p['share_of_task_time'].values())-1)<1e-12 and pp.tier_split(n,None)['population']is None and pp.tier_split(n,{'1':{'weight':None},'2':{'weight':1}})['population']is None
    ok('per_graph_tiers_and_population_reweighting')

# ---------------------------------------------------------------- fixtures
NAMES={'strat_free_L7':1024,'strat_power_L7':1024,'nopromo_free_L7':1024}
STAGE3_MODEL_SHA256='fc78fc8fe60f45f08040f9f17036b7b4a4474ab7abfe655b61773a27aa016353'   # J-SWEEP-1 (54676977), executable 24adff54...
STAGE4A_MANIFEST_SHA256='becacd705fa4b4396d75950a68374b4232ec0eb9b5e49b999ee1ece127c977b4'  # cited by the Stage-4a profiling records
LIVE_MODEL='cost_models/gmp_expanse_epyc7742_c8.json'   # the live Expanse site model (Stage 5's J-SWEEP-2 replaces it)
def test_fixtures():
    import prepare_benchmarks as pb,production as prod
    m=bk.load_fixtures();blocks=m['blocks']
    assert set(blocks)=={s['name']for s in pb.BLOCKS8}|{'p4_free_L8','p4_power_L8'},sorted(blocks)
    # the fixtures' own copy of the Stage-3 model (J-SWEEP-1's evidence file, FIX8), never the live cost_models/ path
    cmrel=m['cost_model']['path'];assert cmrel==pb.FIX8['cost_model']and not cmrel.startswith('cost_models/')and m['cost_model']['sha256']==STAGE3_MODEL_SHA256,m['cost_model']
    cm=json.loads((ROOT/cmrel).read_text());assert bk.digest(ROOT/cmrel)==m['cost_model']['sha256']
    # every other manifest byte is the Stage-4a manifest's: naming the live path again gives its sha256
    raw=(Path(m['_folder'])/'manifest.json').read_bytes();was=b'"path": "'+cmrel.encode()+b'"'
    assert raw.count(was)==1 and hashlib.sha256(raw.replace(was,b'"path": "'+LIVE_MODEL.encode()+b'"')).hexdigest()==STAGE4A_MANIFEST_SHA256
    assert m['cost_model']['executable_sha256'].startswith('24adff54')and m['native']=={'layout':0,'rate':'.8','sum_mode':'compensated','bits':52,'grid':'-','order':8,'mp_check':'on'}
    assert bk.digest(ROOT/m['promotions']['path'])==m['promotions']['sha256'];prom=pb.read_promotions(ROOT/m['promotions']['path'])
    inv=json.loads((ROOT/'inputs/inventory.json').read_text())
    for n,b in blocks.items():
        if n in NAMES:assert b['tasks']==NAMES[n],(n,b['tasks'])
        o,L,rows=bk.read_tasks(Path(m['_folder'])/b['files']['tasks']);assert o==8 and L==b['L']and len(rows)==b['tasks']
        assert all(r[3]<r[4]<=r[5]and r[5]==b['total']and r[5]&(r[5]-1)==0 and r[1]<b['replicates']and r[2]in set(b['graphs'])for r in rows)and len({r[0]for r in rows})==len(rows)
        per={};[per.setdefault((r[1],r[2]),[]).append((r[3],r[4]))for r in rows]
        assert all(sorted(v)==[(i*b['total']//len(v),(i+1)*b['total']//len(v))for i in range(len(v))]and len(v)==b['chunks'][str(k[1])]for k,v in per.items()),n
        assert len(per)==b['replicates']*len(b['graphs'])
        assert b['native_seed']==bk.bench_seed(m['seed'],n,'native')and b['net']['seed']==bk.bench_seed(m['seed'],n,'net')
        raw=(Path(m['_folder'])/b['files']['net']).read_bytes();B,dim,bits=__import__('struct').unpack('<III',raw[:12])
        assert (B,dim,bits)==(b['replicates'],4*L-1,52)and len(raw)==12+B*dim*bits*8 and b['net']['sha256']==hashlib.sha256(raw).hexdigest()
        assert abs(b['predicted']['cost_model_seconds']-math.fsum(float(cm['seconds_per_point'][f'a:{b["sector"]}:{L}:{r[2]}'])*(r[4]-r[3])for r in rows))<1e-6
        spp={g['id']:float(cm['seconds_per_point'][f'a:{b["sector"]}:{L}:{g["id"]}'])for g in inv[b['sector']][str(L)]}
        if n.startswith('nopromo'):assert all(prom[(c,b['sector'],L,g)][1]==0 and prom[(c,b['sector'],L,g)][2]==0 for g in b['graphs']for c in 'ab')
        if n.startswith('heavy'):assert sorted(sorted(spp,key=lambda g:(-spp[g],g))[:len(b['graphs'])])==b['graphs']
        if n.startswith('strat'):
            st=b['strata'];top=sorted(spp,key=lambda g:(-spp[g],g))[:8]
            assert sorted(g for g in b['graphs']if st[str(g)]['stratum']=='heaviest')==sorted(top)
            bins={};[bins.setdefault(v['stratum'],[]).append(v['weight'])for v in st.values()]
            assert len(bins)==9 and all(len(v)==15 for k,v in bins.items()if k!='heaviest')
            assert abs(sum(v['weight']for v in st.values())-len(spp))<1e-6,(n,sum(v['weight']for v in st.values()),len(spp))
            assert b['predicted']['mp_calls']>=1000,(n,b['predicted']['mp_calls'])
        if n.startswith('p4'):
            for g in b['graphs']:
                ch=b['total']//b['chunks'][str(g)];want=min(b['total'],max(prod.MIN_CHUNK,1<<max(0,math.floor(math.log2(prod.TASK_SECONDS/spp[g])))))
                assert ch==want,(n,g,ch,want)
            assert b['predicted']['max_task_seconds']<=prod.TASK_SECONDS+1e-9
        elif 'wall_seconds'in b['predicted']:
            assert 0.5*b['predicted']['target_seconds']<=b['predicted']['wall_seconds']<=2*b['predicted']['target_seconds'],(n,b['predicted'])
            assert b['predicted']['max_task_seconds']<=b['predicted']['target_seconds']/4+1e-9 or all(v==b['total']//64 for v in [b['total']//b['chunks'][str(g)]for g in b['graphs']if spp[g]*b['total']/b['chunks'][str(g)]>b['predicted']['target_seconds']/4])
    wl=m['workloads']['p4_L8'];assert 300<=wl['predicted_ideal_wall_seconds']<=360 and wl['blocks']==['p4_free_L8','p4_power_L8'],wl
    nf,np_=len(blocks['p4_free_L8']['graphs']),len(blocks['p4_power_L8']['graphs']);assert abs(np_-nf*4336/16064)<=1,(nf,np_)
    size=sum(f.stat().st_size for f in Path(m['_folder']).iterdir());assert size<2*2**20,size
    with tempfile.TemporaryDirectory()as td:
        c=Path(td)/'fx';shutil.copytree(m['_folder'],c);f=c/'heavy_free_L8.tasks';f.write_text(f.read_text()+'\n')
        assert 'changed'in refused(65,bk.load_fixtures,c);shutil.copy2(Path(m['_folder'])/'heavy_free_L8.tasks',f);bk.load_fixtures(c)
        (c/'random_free_L7.net').unlink();assert 'missing'in refused(65,bk.load_fixtures,c)
        d=Path(td)/'fy';shutil.copytree(m['_folder'],d);j=json.loads((d/'manifest.json').read_text());j['inventory_sha256']='0'*64;(d/'manifest.json').write_text(json.dumps(j))
        assert 'inventory.json'in refused(65,bk.load_fixtures,d)
        j['schema']='x';(d/'manifest.json').write_text(json.dumps(j));refused(65,bk.load_fixtures,d);refused(69,bk.load_fixtures,Path(td)/'none')
    ok('committed_fixtures8_pins_strata_sizes_seeds_nets',manifest_sha256=m['_manifest_sha256'],bytes=size,p4_ideal_seconds=round(wl['predicted_ideal_wall_seconds'],1))

def test_determinism():
    import prepare_benchmarks as pb
    r=pb.check_fixtures8(bk.FIXTURES8);assert r['identical'],r
    with tempfile.TemporaryDirectory()as td:
        refused_build=False
        try:pb.build_fixtures8(bk.FIXTURES8)
        except FileExistsError:refused_build=True
        assert refused_build,'an existing folder was overwritten'
    ok('fixtures_rebuild_byte_identical',nets_compared=r['nets_compared'],scipy=r['scipy_here'])

# ---------------------------------------------------------------- refusals
def write_exe(path:Path,body:str)->Path:
    path.write_text(f'#!{PY} -S\n'+body);path.chmod(0o755);return path

def test_refusals():
    import perf_profile as pp,prepare_benchmarks as pb
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);pack=ROOT/'inputs/packs/free_L5.pack';inv=json.loads((ROOT/'inputs/inventory.json').read_text())['free']['5'][:3]
        mem={r['id']:r for r in inv};st=bk.stage_members(pack,mem,5,list(mem),td/'g')
        assert st['graphs']==3 and all((td/'g/L5'/f'G{g}.txt').read_bytes()==pack.read_bytes()[r['offset']:r['offset']+r['length']]for g,r in mem.items())
        g0=inv[0]['id'];bad={**mem,g0:{**mem[g0],'sha256':'0'*64}};assert 'does not match'in refused(65,bk.stage_members,pack,bad,5,[g0],td/'h')
        assert 'missing'in refused(69,bk.stage_members,td/'none.pack',mem,5,[g0],td/'i');refused(65,bk.stage_members,pack,mem,5,[10**9],td/'j')
        (td/'fx').mkdir();(td/'fx/stray.tasks').write_text('x');assert pb.main(['--order','8','--folder',str(td/'fx')])==65
        try:pb.main(['--order','7','--check']);raise AssertionError('order 7 accepted --check')
        except SystemExit as e:assert e.code==2
        for extra,code in ((['--lane-shapes','1x3','--fake-topology','1x2x2','--no-pin'],64),(['--lane-shapes','1x4','--fake-topology','1x2x2'],64)):
            out=td/f'p4_{code}_{len(extra)}';cp=subprocess.run([PY,'-B',str(ROOT/'tools/benchmark.py'),*extra,'--output',str(out)],capture_output=True,text=True)
            assert cp.returncode==code and not out.exists(),(extra,cp.returncode,cp.stderr[-300:])
        cp=subprocess.run([PY,'-B',str(ROOT/'tools/benchmark.py'),'--lane-shapes','1x4','--interleave-probe','--output',str(td/'z')],capture_output=True,text=True);assert cp.returncode==2
        cp=subprocess.run([PY,'-B',str(ROOT/'tools/perf_profile.py'),'p1','--fake-topology','1x2x2','--output',str(td/'pp')],capture_output=True,text=True)
        assert cp.returncode==64 and '--no-pin'in cp.stderr,cp.stderr[-300:]
        rel=write_exe(td/'c8d3_gmp',(ROOT/'tests/fake_worker.py').read_text())
        diag=write_exe(td/'diag_gmp','import json,sys\nprint(json.dumps({"diagnostic":True,"diagnostic_kind":"tier_timers"}))\n')
        pp.check_exe(rel,None);assert 'diagnostic build'in refused(65,pp.check_exe,diag,None);pp.check_exe(diag,'tier_timers')
        refused(65,pp.check_exe,rel,'ratio_histogram');refused(69,pp.check_exe,td/'nothing',None);assert 'expected'in refused(65,pp.check_exe,rel,None,'deadbeef')
        assert bk.native_cmd('x','g','gm','n','t','o',1,0,'.8',4)[-2:]==['--mp-check','on']and '--mp-check'not in bk.native_cmd('x','g','gm','n','t','o',1,0,'.8',4,mp_check=None)
        refused(64,bk.native_cmd,'x','g','gm','n','t','o',1,0,'.8',4,'compensated','sometimes')
    ok('refusals_staging_builds_shapes_executables')

# ---------------------------------------------------------------- scripts
def test_scripts():
    t=(ROOT/'slurm/native_job.sh').read_text()
    for j in ('profbuild','prof1','prof2','prof3'):assert f'|{j}' in t.split('case "$C8_JOB" in val1|',1)[1].split(')',1)[0]+'|',j
    body=t[t.index('profbuild|prof1|prof2|prof3)\n'):t.index('val3a)\n')]
    # B0 is this site's c8-stage3 baseline (tools/baseline.py sha before the case; Expanse's record pins 24adff54...)
    pre=t[:t.index('case "$C8_JOB" in\nval1)')];assert 'tools/baseline.py sha c8d3_gmp'in pre and 'B8="${BASE_SHA:0:8}"'in pre and '24adff54'not in body
    base=json.loads((ROOT/'reference/baseline_c8_stage3.json').read_text());assert base['files']['c8d3_gmp'].startswith('24adff54')and 'baseline_record'in body
    i_merge=body.index('merge_scale_clean');i_make=body.index('step make_native');i_base=body.index('step baseline_identity');i_fe=body.index('step fe ')
    assert i_merge<i_make<i_base<i_fe,'prof1: the clean merge first, then the build and the baseline check, then the profiles'
    assert "grep -q '\"FAIL\"'"in body[i_base:i_fe]and '--skip-many-shards --skip-memory-scaling'in body and '--rows 1000000 --jobs 16 --run-jobs 16'in body
    for want in ('perf_profile.py p1','perf_profile.py mpcheck','perf_profile.py fe','perf_profile.py p2','perf_profile.py p3','benchmark.py --lane-shapes','benchmark.py --interleave-probe',
                 '8x16,4x32,2x64,1x128,16x8','--expect-sha256 "$B8"'):
        assert want in body,want
    smoke=body[body.index('profbuild)\n'):body.index('prof1)\n',body.index('profbuild)\n'))]
    assert smoke.count('--no-pin')>=4 and '--stage-check'in smoke and smoke.count('"${SM[@]}"')==4
    if shutil.which('bash'):cp=subprocess.run(['bash','-n',str(ROOT/'slurm/native_job.sh')],capture_output=True,text=True);assert cp.returncode==0,cp.stderr
    ok('native_job_prof_steps')

def test_order7():
    import prepare_benchmarks as pb
    r=pb.prepare_benchmarks();assert r['schema']=='c7-d3-hpc-benchmark-fixtures-1'and set(r['records'])=={'free_L6','free_L7','power_L6','power_L7'}
    with tempfile.TemporaryDirectory()as td:
        c=Path(td)/'f';shutil.copytree(ROOT/'benchmarks/fixtures',c);(c/'free_L7.tasks').write_text('x\n')
        try:pb.verify_fixtures7(c);raise AssertionError('a changed C7(3) fixture was accepted')
        except ValueError:pass
        try:pb.verify_fixtures7(Path(td)/'none');raise AssertionError('a missing manifest was accepted')
        except FileNotFoundError:pass
    ok('order7_fixtures_verified_never_rebuilt')

# ---------------------------------------------------------------- end to end with fakes
def mini_inputs(td:Path)->Path:
    """tests/fixtures/inputs_mini (8 L8 graphs per sector, their mini packs) materialized as a C8_INPUTS directory
    (prepare_inputs.materialize_mini: the package files it pins, gamma_d3_8.txt among them, hard-linked), which
    prepare_inputs.verify accepts (build_fixtures8 verifies its inputs first, S4-005)."""
    import prepare_inputs as pi
    return pi.materialize_mini(td/'inputs_mini')

def mini_fixture(td:Path,I:Path|None=None,out:str='fx')->Path:
    """A fixture folder td/out on inputs_mini (I, default: materialized here) and a synthetic cost model and promotion
    tarball in which every third free graph is promotion-free."""
    import prepare_benchmarks as pb
    I=I or mini_inputs(td);inv=json.loads((I/'inventory.json').read_text());spp={}
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz')as tf:
        for c in 'ab':
            for s in ('free','power'):
                for L in ('7','8'):
                    costs=io.StringIO();pro=io.StringIO();cw=csv.writer(costs);pw=csv.writer(pro)
                    cw.writerow(['graph','points','row_seconds','tasks']);pw.writerow(['replicate','graph','quad','mp'])
                    for r in inv[s][L]:
                        z=r['id']%3==0 and s=='free';spp[f'{c}:{s}:{L}:{r["id"]}']=1e-6*(1+r['id']%7)
                        cw.writerow([r['id'],1024,0.001,2]);pw.writerow([0,r['id'],0 if z else 300,0 if z else 30]);pw.writerow([1,r['id'],0 if z else 200,0 if z else 20])
                    for name,sio in (('graph_costs.csv',costs),('graph_promotions.csv',pro)):
                        data=sio.getvalue().encode();ti=tarfile.TarInfo(f'groups/{c}_{s}_L{L}/{name}');ti.size=len(data);tf.addfile(ti,io.BytesIO(data))
    (td/'promo.tgz').write_bytes(buf.getvalue())
    for s in ('free','power'):
        for L,rows in inv[s].items():
            for r in rows:
                for c in 'ab':spp.setdefault(f'{c}:{s}:{L}:{r["id"]}',1e-6*(1+r['id']%7))
    (td/'cm.json').write_text(json.dumps({'executable_sha256':'fake','cpu_model':'fake','lane_shape':{'threads':[4]},'job_ids':['0'],'mp_check':'on','seconds_per_point':spp}))
    blocks=(dict(name='strat_free_L8',purpose='P1',sector='free',L=8,select='tbins',graphs=6,bins=2,heaviest=2,replicates=2,chunks=2,target_seconds=.01,target_threads=4),
            dict(name='heavy_power_L8',purpose='P1',sector='power',L=8,select='heaviest',graphs=4,replicates=2,chunks=1,target_seconds=.01,target_threads=4),
            dict(name='nopromo_free_L8',purpose='P2',sector='free',L=8,select='nopromo',graphs=3,replicates=2,chunks=1,target_seconds=.01,target_threads=4),
            dict(name='random_power_L8',purpose='P3',sector='power',L=8,select='random',graphs=5,replicates=2,chunks=1,target_seconds=.01,target_threads=4))
    wls=(dict(name='p4_L8',purpose='P4',L=8,sectors=('free','power'),replicates=2,points=64,target_seconds=.004,target_threads=4),)
    pb.build_fixtures8(td/out,inputs_rel=str(I),cost_model=td/'cm.json',promotions=td/'promo.tgz',seed=7,blocks=blocks,workloads=wls);return td/out

def test_inputs_verified():
    """S4-005: build_fixtures8 verifies its inputs against their manifest (prepare_inputs.verify) before any selection;
    the fixture pins are the verified hashes; a gamma or inventory changed to other valid-looking bytes is refused (65)
    and leaves no fixture folder (the changed file replaces the hard link, never writes through)."""
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);I=td/'inputs_mini';m=bk.load_fixtures(fx)
        assert (m['inputs_manifest_sha256'],m['inventory_sha256'],m['gamma_sha256'])==(bk.digest(I/'manifest.json'),bk.digest(I/'inventory.json'),bk.digest(I/'gamma_d3_8.txt'))
        def bump(b:bytes)->bytes:   # one digit after the first decimal point +1 (mod 10): another finite value
            i=b.index(b'.')+1;return b[:i]+str((int(chr(b[i]))+1)%10).encode()+b[i+1:]
        for rel,edit in (('gamma_d3_8.txt',bump),('inventory.json',lambda b:b.replace(b'"wa": ',b'"wa":  ',1))):
            p=I/rel;orig=p.read_bytes();new=edit(orig);assert new!=orig,rel
            p.unlink();p.write_bytes(new)
            try:why=refused(65,mini_fixture,td,I,f'fx_{rel}')
            finally:p.unlink();p.write_bytes(orig)
            assert 'Checksum mismatch'in why and rel in why and not (td/f'fx_{rel}').exists(),(rel,why)
        assert bk.digest(ROOT/'inputs/gamma_d3_8.txt')==json.loads((ROOT/'inputs/manifest.json').read_text())['sha256']['gamma_d3_8.txt']
    ok('fixtures8_build_verifies_inputs',refused=['gamma_d3_8.txt','inventory.json'])

FAKE_DIAG='''import json,subprocess,sys
FW={fw!r};KIND={kind!r}
if sys.argv[1:]==['--describe']:
    d=json.loads(subprocess.run([sys.executable,'-S',FW,'--describe'],capture_output=True,text=True).stdout);d['diagnostic']=True;d['diagnostic_kind']=KIND
    print(json.dumps(d));sys.exit(0)
rc=subprocess.run([sys.executable,'-S',FW,*sys.argv[1:]]).returncode
if rc:sys.exit(rc)
out=sys.argv[5];n=json.load(open(out));Q=M=P=0;pg={{}}
mode=sys.argv[13]if len(sys.argv)>13 else'off'
for r in n['rows']:
    p=r['end']-r['begin'];P+=p;g=pg.setdefault(str(r['graph']),[0.,0.,0.,0,0,0])
    g[0]+=1e-3*p;g[1]+=2e-3*r['quad'];g[2]+=(5e-3 if mode=='on'else 4e-3 if mode=='off'else 4.1e-3)*r['mp'];g[3]+=p;g[4]+=r['quad'];g[5]+=r['mp']
    if KIND=='ratio_histogram':r['quad']=p//2;r['mp']=p//8;Q+=p//2;M+=p//8
if KIND=='tier_timers':
    s=[sum(v[i]for v in pg.values())for i in range(6)]
    n['tier_timers']={{'clock':'steady_clock','first_pass_seconds':s[0],'first_pass_calls':s[3],'quad_seconds':s[1],'quad_calls':s[4],'mp_seconds':s[2],'mp_calls':s[5],'per_graph':pg}}
else:n['ratio_histogram']={{'bins':'fake','ld_fail':{{'-12':Q}},'quad':{{'-15':Q-M,'-30':M}},'mp':{{'-100':M}}}}
json.dump(n,open(out,'w'))
'''
def fakes(td:Path)->dict:
    fw=str(ROOT/'tests/fake_worker.py')
    return {'gmp':write_exe(td/'c8d3_gmp',(ROOT/'tests/fake_worker.py').read_text()),'prof':write_exe(td/'c8d3_gmp_prof',FAKE_DIAG.format(fw=fw,kind='tier_timers')),
            'ratio':write_exe(td/'c8d3_gmp_ratiohist',FAKE_DIAG.format(fw=fw,kind='ratio_histogram')),
            'c7':write_exe(td/'c7d3_gmp',(ROOT/'tests/fake_worker.py').read_text()),'perf':write_exe(td/'perf',(ROOT/'tests/fake_perf.py').read_text())}

def tool(script,*args,env=None)->subprocess.CompletedProcess:
    return subprocess.run([PY,'-B',str(ROOT/'tools'/script),*map(str,args)],capture_output=True,text=True,env={**os.environ,**(env or{})},timeout=900)

def test_e2e_lanes():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td);common=['--fake-topology','1x2x2','--no-pin','--exe',f['gmp'],'--fixtures',fx,'--scratch',td,'--numa-sample-seconds','0.05']
        cp=tool('benchmark.py','--lane-shapes','1x4,2x2,4x1,2x1',*common,'--output',td/'p4');assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        r=json.loads((td/'p4/p4.json').read_text());m=bk.load_fixtures(fx);nt=sum(m['blocks'][b]['tasks']for b in m['workloads']['p4_L8']['blocks'])
        assert r['schema']=='c8-d3-prof-p4-1'and r['all_shapes_identical_rows']and [t['shape']for t in r['table']]==['1x4','2x2','4x1','2x1']and r['workload']['tasks']==nt
        assert r['settings']['mp_check']=='on'and r['settings']['block_seconds']==900.
        for s in r['shapes']:
            assert s['tasks']==nt and s['rows']==nt and len(s['lanes_detail'])==int(s['shape'].split('x')[0])and s['throughput_cost_model_s_per_node_s']>0 and not s['errors']
        cp=tool('benchmark.py','--lane-shapes','2x2',*common,'--output',td/'fail',env={'C8_FAKE_FAIL':'1'});assert cp.returncode==1
        x=json.loads((td/'fail/p4.json').read_text());assert x['table'][0]['errors']and x['best_shape']is None
    ok('e2e_lane_shapes_fake_worker',shapes=4)

def test_e2e_probe():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td)
        probe=write_exe(td/'probe','import json,sys\ng=int(sys.argv[1].split("/G")[-1].split(".")[0])\n'
                        'print(json.dumps({"graph":g,"speedup":{"2":1.1+0.1*(g%2),"4":1.3},"identical":{"2":True,"4":True},"seconds_per_point":{"1":1e-6,"2":9e-7,"4":8e-7}}))\n')
        cp=tool('benchmark.py','--interleave-probe','--probe-exe',probe,'--probe-graphs','nopromo_free_L8:2,strat_free_L8:2','--fake-topology','1x2x4','--no-pin','--fixtures',fx,'--scratch',td,'--output',td/'ip')
        assert cp.returncode==0,cp.stderr[-800:]+cp.stdout[-800:]
        r=json.loads((td/'ip/interleave.json').read_text());assert len(r['results'])==4 and r['all_identical']and r['speedup']['all']['4']['median']==1.3 and r['speedup']['heavy']['4']['median']==1.3
        bad=write_exe(td/'bad','import sys\nsys.exit(3)\n')
        cp=tool('benchmark.py','--interleave-probe','--probe-exe',bad,'--probe-graphs','nopromo_free_L8:1','--fake-topology','1x2x4','--no-pin','--fixtures',fx,'--scratch',td,'--output',td/'ip2')
        assert cp.returncode==1
        cp=tool('benchmark.py','--interleave-probe','--probe-exe',td/'none','--fixtures',fx,'--output',td/'ip3');assert cp.returncode==69
    ok('e2e_interleave_probe_driver')

def test_e2e_perf():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td);base=['--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--scratch',td,'--perf',f['perf']]
        cp=tool('perf_profile.py','p1',*base,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','strat_free_L8,heavy_power_L8','--no-srcline','--output',td/'p1')
        assert cp.returncode==0,cp.stdout[-2000:]+cp.stderr[-1500:]
        r=json.loads((td/'p1/p1.json').read_text());assert r['stage']=='final'and r['perf']['ok']and r['settings']['concurrent']and r['settings']['perf_cpus']==[0,1,2,3]
        assert r['settings']['wait_policy']=='passive'and r['settings']['mp_check']=='on'
        for b in ('strat_free_L8','heavy_power_L8'):
            x=r['blocks'][b];assert abs(x['perf']['shares']['categories']['binary128_arith']-52.0)<1e-9 and x['perf']['total_samples']==1000000
            assert x['rows_identical_worker_vs_prof']and x['perf_run']['record']['samples']==1234
            ts=x['tier_run']['tier_split'];assert set(ts['per_graph'])=={str(g)for g in bk.load_fixtures(fx)['blocks'][b]['graphs']}
            assert ts['population']is not None and abs(sum(ts['population']['share_of_task_time'].values())-1)<1e-12
        cp=tool('perf_profile.py','p1-reparse','--input',td/'p1');assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        rr=json.loads((td/'p1/p1_reparsed.json').read_text());assert rr['blocks']['strat_free_L8']['perf']['shares']==r['blocks']['strat_free_L8']['perf']['shares']
        cp=tool('perf_profile.py','p1',*base,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_power_L8','--output',td/'p1r',env={'FAKE_PERF_REFUSE':'1'})
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p1r/p1.json').read_text());assert not r['perf']['ok']and 'perf_event_paranoid'in r['fallback']['reason']and 'tier_run'in r['blocks']['heavy_power_L8']
        cp=tool('perf_profile.py','p2',*base,'--threads',4,'--exe',f['gmp'],'--blocks','nopromo_free_L8','--serial-seconds','1e-9','--output',td/'p2')
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p2/p2.json').read_text());x=r['blocks']['nopromo_free_L8'];assert abs(r['ipc']['nopromo_free_L8']['parallel']-0.8)<1e-6 and x['serial']['threads']==1
        cp=tool('perf_profile.py','p3',*base,'--threads',8,'--exe',f['ratio'],'--blocks','random_power_L8','--rates','.8,.7','--output',td/'p3')
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p3/p3.json').read_text());assert r['all_checks_ok']and set(r['results'])=={'random_power_L8@.8','random_power_L8@.7'}
        cp=tool('perf_profile.py','mpcheck',*base,'--threads',4,'--exe',f['prof'],'--blocks','strat_free_L8,heavy_power_L8','--output',td/'mc')
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'mc/mpcheck.json').read_text());s=r['summary']['heavy_power_L8']
        assert set(r['summary'])=={'strat_free_L8','heavy_power_L8'}and s['values_identical_across_modes']and s['on']['mp_tier_overhead']>0 and abs(s['on']['mp_tier_ratio']-1.25)<1e-9
        assert abs(s['stride16']['mp_tier_ratio']-4.1/4)<1e-9 and 'population_mp_tier_overhead'in r['summary']['strat_free_L8']['on']
        assert {r['blocks']['heavy_power_L8'][m]['cpus']for m in ('on','off','stride16')}=={'4-7'}and {r['blocks']['strat_free_L8'][m]['cpus']for m in ('on','off','stride16')}=={'0-3'}
        # --smoke-tasks cuts every block (a function test on a small allocation)
        cp=tool('perf_profile.py','p3',*base,'--threads',4,'--exe',f['ratio'],'--blocks','random_power_L8','--rates','.8','--smoke-tasks',3,'--smoke-points',8,'--output',td/'p3s')
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p3s/p3.json').read_text());assert r['results']['random_power_L8@.8']['native']['tasks']==3 and r['results']['random_power_L8@.8']['native']['points']<=24
    ok('e2e_perf_profile_p1_fallback_p2_p3_mpcheck_fake_perf')

def test_e2e_fe():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);f=fakes(td)
        cp=tool('perf_profile.py','fe','--c7-exe',f['c7'],'--c8-exe',f['gmp'],'--repeats',1,'--loaded-threads',4,'--fake-topology','1x2x2','--no-pin','--scratch',td,'--output',td/'fe',
                env={'C8_FAKE_SPP':'1e-7'})
        assert cp.returncode==0,cp.stdout[-2000:]+cp.stderr[-1500:]
        r=json.loads((td/'fe/fe.json').read_text());t={(x['sector'],x['L'],x['threads']):x for x in r['table']}
        assert set(t)=={('free',6,1),('free',7,1),('free',7,2),('free',7,4),('power',6,1),('power',7,1),('power',7,2),('power',7,4)}
        x=t[('power',7,1)];assert x['symmetry_production_s']==6.677626302000135 and x['expanse_loaded_n']==4 and x['rows_identical_all_runs']
        assert abs(x['f_E_isolated_vs_production']-x['expanse_isolated_median_s']/6.677626302000135)<1e-12 and 'f_E_loaded_vs_reference'in x
        assert t[('free',6,1)].get('symmetry_production_s')is None and t[('free',6,1)]['symmetry_reference_s']==3.563843318261206
        assert r['executables']['c7ref']==bk.digest(f['c7'])and r['settings']['loaded_cpus']=='0-3'and not r['errors']
    ok('e2e_fe_fake_workers')

TESTS=(('shapes',test_shapes),('lpt_blocks',test_lpt_blocks),('perf_report',test_perf_report),('perf_stat',test_perf_stat),('parsers',test_parsers),
       ('ratio',test_ratio),('tiers',test_tiers),('fixtures',test_fixtures),('determinism',test_determinism),('refusals',test_refusals),('scripts',test_scripts),
       ('order7',test_order7),('inputs_verified',test_inputs_verified),('e2e_lanes',test_e2e_lanes),('e2e_probe',test_e2e_probe),('e2e_perf',test_e2e_perf),('e2e_fe',test_e2e_fe))
NAMES_T=[n for n,_ in TESTS]

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--only',help='NAME,... of: '+', '.join(NAMES_T))
    a=ap.parse_args()
    sel=NAMES_T
    if a.only is not None:
        sel=[s.strip()for s in a.only.split(',')if s.strip()]
        bad=[s for s in sel if s not in NAMES_T]
        if not sel or bad:ap.error(f'--only: unknown test(s) {bad}'if bad else'--only: no test named')
    os.environ.pop('C8_FAKE_FAIL',None);os.environ.pop('FAKE_PERF_REFUSE',None);failed=[]
    for name,fn in TESTS:
        if name not in sel:continue
        try:fn()
        except Exception as e:  # report every failure, then fail
            import traceback;traceback.print_exc();failed.append(name);RESULTS.append({'test':name,'status':'failed','error':f'{type(e).__name__}: {e}'[:2000]});print('FAIL',name,flush=True)
    rec={'schema':'c8-d3-test-profiling-1','requested':sel,'executed':[r['test']for r in RESULTS],'results':RESULTS,'passed':not failed and bool(RESULTS),'failed':failed}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({'passed':rec['passed'],'tests':len(RESULTS),'failed':failed}));return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
