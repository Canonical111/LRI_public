#!/usr/bin/env python3
"""Stage-4a profiling tools (PLAN "Performance plan", P1-P4; tools/benchkit.py, prepare_benchmarks.py --order 8,
perf_profile.py, benchmark.py --lane-shapes / --interleave-probe, the stage4a job and submit scripts): Mac-runnable
tests of the pure logic. No native build and no measurement: the worker is tests/fake_worker.py, perf is
tests/fake_perf.py, the CPU topology is --fake-topology with --no-pin.

  shapes        lane shapes -> disjoint NUMA-aligned CPU sets on the Expanse (2 x 4 x 16) and symmetry (2 x 4 x 8)
                topologies, the exact sets, and the refusals (does not fit, misaligned, unequal nodes, no NUMA data,
                malformed or repeated shapes)
  lpt_blocks    deterministic LPT shares, production-style blocks, block sizes
  perf_report   perf report --stdio parsing (symbol, dso,symbol, dso; -n) of perf's text and the plan's shares
  perf_stat     perf stat -x, CSV (IPC, unsupported and uncounted events) and perf record's summary line
  parsers       perf annotate, addr2line -a -i -f, ltrace -c, numa_maps, node numastat, kernel.hpp regions
  ratio         P3 summaries: histograms, consistency checks, fractions below 10^-k, margins
  fixtures      the committed benchmarks/fixtures8: every pin, block sizes, seeds, nets, P4 sizing; tampering refused
  determinism   rebuilding the fixtures gives the same bytes (nets compared when the scipy version is the manifest's)
  refusals      staging with a wrong member hash or no pack, interrupted builds, unfit shapes, wrong executables
  admission     h7_admit.py (H7E-R on Expanse, H7 on symmetry) on squeue snapshots; constants = slurm_submit's
  scripts       the Slurm and submit scripts: directives, names, logs, evidence, budget, admission before sbatch
  order7        prepare_benchmarks.py imports, and its order-7 function is C7(2)'s apart from the moved import
  e2e_lanes     benchmark.py --lane-shapes on a mini fixture (inputs_mini) with the fake worker: identical rows
                across shapes, --fraction, a failing worker recorded
  e2e_probe     benchmark.py --interleave-probe driver with a fake probe executable
  e2e_perf      perf_profile.py p1 (perf and the refusal fallback, with a fake ltrace too), p2 and p3 with fake perf and
                fake diagnostics
  perf_team     perf_profile.py run(): the controlled OpenMP environment; a direct run's team watched (verified, smaller
                stopped and refused, unverified refused), a wrapped run and a stand-in worker not watched (Y2's class)
  perf_binding  P1 fails (exit 1, the block and uids named) when the release and tier-timer workers' rows differ (Z20),
                also without perf, where the release worker now runs every requested block directly (W19)
  perf_expect   --expect-sha256 binds P1, P2, P3 (Z21), --lane-shapes and --interleave-probe before any output, scratch or
                worker run; empty or malformed values refused; legacy mode refuses it
  perf_keep     P1 --keep-perf-data keeps perf.data in <output>/perf_data with or without --keep-scratch (Z22); P1 only
  p3_binding    P3 fails (exit 1, the block, rate and uids named) when the release worker's rows differ from the
                ratio-histogram build's on any (block, rate); a diagnostic or missing --worker-exe is refused before
                any output (W19's class)
  tool_cleanup  a tool that times out is killed with every process it started (its process group; W15's class)
--only NAME,... runs the named tests (unknown names or an empty list exit 2 before any setup).
Usage: python3 -B tests/test_profiling.py [--output FILE] [--only NAME,...]"""
from __future__ import annotations
import argparse,ast,hashlib,importlib.util,json,math,os,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import benchkit as bk  # noqa: E402
RESULTS=[]
SCRIPTS=ROOT/'benchmarks/expanse_2026-10-c8/stage4a/scripts';SYM=ROOT/'benchmarks/symmetry_2026-10-c8/stage4a/scripts'
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
    assert bk.partition(sy,8,8)==[list(range(8*i,8*i+8))for i in range(8)]and bk.partition(sy,2,32)==[list(range(32)),list(range(32,64))]
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
    ok('lpt_shares_and_production_blocks',loads=loads)

# ---------------------------------------------------------------- perf parsing
EXPECT={'binary128_arith':52.0,'binary128_other':0.5,'expq':8.0,'expl':4.0,'logl':0.5,'gmpf':5.0,'gmpn':6.5,'gmp_other':0.0,'malloc_free':3.5,
        'mp_to_ld_lower':4.5,'mp_to_ld_likely':5.0,'calculate_reference_ld':3.0,'libgomp':1.5,'kernel':1.0,'worker_other':10.0,'unknown':0.0,'other':0.0,'gmp_total':16.0}
def test_perf_report():
    ds=bk.parse_perf_report(fake_text('report','--no-children','--stdio','-n','--sort','dso,symbol'))
    sy=bk.parse_perf_report(fake_text('report','--no-children','--stdio','-n','--sort','symbol'))
    dd=bk.parse_perf_report(fake_text('report','--no-children','--stdio','-n','--sort','dso'))
    assert ds['header']=={'lost':0,'samples_text':'1M','event':'cycles','event_count':987654321000},ds['header']
    assert len(ds['rows'])==19 and ds['rows'][0]=={'overhead':30.0,'samples':300000,'dso':'libgcc_s.so.1','level':'.','symbol':'__multf3'},ds['rows'][0]
    cr=[r for r in ds['rows']if 'calculate_reference'in r['symbol']][0]
    assert cr['symbol']=='std::pair<long double, long double> calculate_reference<long double>(Graph const&, long double const*, long double)'and cr['dso']=='c8d2_gmp'
    assert all(r['dso']is None and r['samples']is not None for r in sy['rows'])and len(sy['rows'])==19
    sh=bk.perf_shares(ds['rows'],'c8d2_gmp')
    for k,v in EXPECT.items():assert abs(sh['categories'][k]-v)<1e-9,(k,sh['categories'][k],v)
    assert sh['binary128_ops']=={'__addtf3':20.0,'__subtf3':1.0,'__multf3':30.0,'__divtf3':1.0}and abs(sh['total_listed']-100)<1e-9
    assert sh['named']['__gmpf_get_str']==2.5 and sh['named']['expq']==8.0 and sh['named']['free']==1.5 and sh['named']['____strtold_l_internal']==2.0
    s2=bk.perf_shares(sy['rows'],None)
    assert all(abs(s2['categories'][k]-v)<1e-9 for k,v in EXPECT.items()if k not in('worker_other','other'))and s2['categories']['other']==10.0
    st=bk.symbol_table(ds['rows']);assert [(x['symbol'],x['overhead'])for x in st]==[(r['symbol'],r['overhead'])for r in sorted(sy['rows'],key=lambda r:(-r['overhead'],r['symbol']))]
    dt={x['dso']:x for x in bk.dso_table(dd['rows'])};assert abs(dt['libgcc_s.so.1']['overhead']-52.5)<1e-9 and dt['libgcc_s.so.1']['samples']==525000 and len(dd['rows'])==len(dt)
    assert all(r['symbol']is None for r in dd['rows'])
    # perf 4.18 (RHEL 8, Expanse) appends "IPC [IPC Coverage]" columns to symbol sorts: the rows must parse identically.
    for text,ref in ((fake_text('report','--no-children','--stdio','-n','--sort','dso,symbol'),ds),(fake_text('report','--no-children','--stdio','-n','--sort','symbol'),sy)):
        assert bk.parse_perf_report(with_ipc(text))['rows']==ref['rows']
    assert bk.parse_perf_report(with_ipc(fake_text('report','--no-children','--stdio','-n','--sort','dso,symbol'),'  1.23  [ 45.6%]'))['rows']==ds['rows']
    # A captured excerpt of that perf's output (job 54661716, heavy_free_L7): versioned, PLT and __GI_ names classified.
    cap=bk.parse_perf_report(CAPTURED_IPC);c=bk.perf_shares(cap['rows'],'c8d2_gmp')
    assert [r['symbol']for r in cap['rows']][:3]==['__addtf3','main._omp_fn.0','__multf3']and cap['rows'][3]['symbol'].startswith('calculate_shared<boost::multiprecision::number<')and cap['rows'][3]['symbol'].endswith(', false>')
    cc=c['categories'];ops=c['binary128_ops']
    assert abs(ops['__addtf3']-(41.86+0.61+0.54))<1e-9 and abs(ops['__multf3']-(5.16+0.75))<1e-9 and abs(ops['__subtf3']-0.39)<1e-9 and abs(ops['__divtf3']-1.10)<1e-9,ops
    assert abs(cc['binary128_other']-(0.70+0.42+0.35))<1e-9 and abs(cc['malloc_free']-(0.24+0.23+0.11))<1e-9 and abs(cc['fenv']-(0.19+0.13))<1e-9,cc
    assert abs(cc['expl']-0.12)<1e-9 and abs(cc['expq']-0.07)<1e-9 and abs(cc['mp_to_ld_lower']-0.04)<1e-9 and abs(cc['kernel']-0.09)<1e-9 and abs(cc['unknown']-0.06)<1e-9,cc
    assert abs(cc['worker_other']-(5.82+2.64+0.58))<1e-9 and abs(cc['other']-0.07)<1e-9 and abs(c['plt_stubs']-0.61)<1e-9 and abs(c['named']['____strtold_l_internal']-0.04)<1e-9,(cc,c['plt_stubs'])
    assert set(c['binary128_ops_by_dso'])=={'libgcc_s.so.1','libquadmath.so.0.0.0','c8d2_gmp'}and abs(c['binary128_ops_by_dso']['c8d2_gmp']['__addtf3']-0.61)<1e-9
    assert bk.base_symbol('__lttf2@@GCC_4.3.0')=='__lttf2'and bk.base_symbol('cfree@GLIBC_2.2.5')=='cfree'and bk.base_symbol('__GI_____strtold_l_internal')=='____strtold_l_internal'
    ok('perf_report_parsing_and_plan_shares',categories=len(EXPECT))

def with_ipc(text:str,tail:str='  -      -')->str:
    """perf 4.18's layout: 'IPC   [IPC Coverage]' after the Symbol header and an IPC tail on every row."""
    out=[]
    for line in text.splitlines():
        if line.startswith('# Overhead')and 'Symbol'in line:line=line+'  IPC   [IPC Coverage]'
        elif bk._PCT.match(line):line=line+'   '+tail
        out.append(line)
    return '\n'.join(out)+'\n'

CAPTURED_IPC="""# Total Lost Samples: 0
#
# Samples: 3M of event 'cycles'
# Event count (approx.): 10952386853576
#
# Overhead       Samples  Shared Object         Symbol                                                                                                                                                                 IPC   [IPC Coverage]
# ........  ............  ....................  .....................................................................................................................................................................  ....................
#
    41.86%       1493097  libgcc_s.so.1         [.] __addtf3                                                                                                                                                           -      -
     5.82%        207511  c8d2_gmp              [.] main._omp_fn.0                                                                                                                                                     -      -
     5.16%        183950  libgcc_s.so.1         [.] __multf3                                                                                                                                                           -      -
     2.64%         94037  c8d2_gmp              [.] calculate_shared<boost::multiprecision::number<boost::multiprecision::backends::gmp_float<350u>, (boost::multiprecision::expression_template_option)1>, false>     -      -
     1.10%         39229  libgcc_s.so.1         [.] __divtf3                                                                                                                                                           -      -
     0.75%         26832  libquadmath.so.0.0.0  [.] __multf3                                                                                                                                                           -      -
     0.70%         25145  libgcc_s.so.1         [.] __sfp_handle_exceptions                                                                                                                                            -      -
     0.61%         21754  c8d2_gmp              [.] __addtf3@plt                                                                                                                                                       -      -
     0.58%         20525  c8d2_gmp              [.] calculate_shared<__float128, true>                                                                                                                                 -      -
     0.54%         19197  libquadmath.so.0.0.0  [.] __addtf3                                                                                                                                                           -      -
     0.42%         15155  libgcc_s.so.1         [.] __floatsitf                                                                                                                                                        -      -
     0.39%         13849  libquadmath.so.0.0.0  [.] __subtf3                                                                                                                                                           -      -
     0.35%         12306  libgcc_s.so.1         [.] __lttf2@@GCC_4.3.0                                                                                                                                                 -      -
     0.24%          8600  libc-2.28.so          [.] malloc                                                                                                                                                             -      -
     0.23%          8249  libc-2.28.so          [.] _int_free                                                                                                                                                          -      -
     0.19%          6636  libm-2.28.so          [.] fesetenv                                                                                                                                                           -      -
     0.13%          4720  libm-2.28.so          [.] feholdexcept                                                                                                                                                       -      -
     0.12%          4340  libm-2.28.so          [.] __expl_finite                                                                                                                                                      -      -
     0.11%          4095  libc-2.28.so          [.] cfree@GLIBC_2.2.5                                                                                                                                                  -      -
     0.09%          3073  [unknown]             [k] 0xffffffff824770f5                                                                                                                                                 -      -
     0.07%          2538  libquadmath.so.0.0.0  [.] expq                                                                                                                                                               -      -
     0.07%          2398  libstdc++.so.6.0.32   [.] std::num_get<char, std::istreambuf_iterator<char, std::char_traits<char> > >::_M_extract_float                                                                 -      -
     0.06%          2272  libm-2.28.so          [.] 0x000000000001667f                                                                                                                                                 -      -
     0.04%          1312  libc-2.28.so          [.] __GI_____strtold_l_internal                                                                                                                                        -      -
"""

def test_perf_stat():
    st=bk.parse_perf_stat_csv(fake_text('stat','-x,','--','true')or subprocess.run([PY,str(ROOT/'tests/fake_perf.py'),'stat','-x,','--','true'],capture_output=True,text=True).stderr)
    assert abs(st['derived']['ipc']-98765432/123456789)<1e-12 and abs(st['derived']['branch_miss_rate']-0.01)<1e-12
    assert st['events']['L1-dcache-loads']=={'value':None,'unit':None,'running_percent':100.0,'status':'not supported'}
    assert st['events']['L1-dcache-load-misses']['status']=='not counted'and st['derived']['l1d_miss_rate']is None and st['multiplexed']
    assert st['events']['task-clock']['unit']=='msec'and st['events']['task-clock']['value']==1234.56
    one=bk.parse_perf_stat_csv('# started on x\n\n5,,cycles:u,1,50.00,,\n10,,instructions:u,1,50.00,2.0,insn per cycle\n')
    assert one['derived']['ipc']==2.0 and one['multiplexed']
    rec=bk.parse_perf_record_stderr('[ perf record: Woken up 3 times to write data ]\n[ perf record: Captured and wrote 312.456 MB /x/perf.data (5750000 samples) ]\n'
                                    'Processed 99 events and lost 7 chunks!\n\nCheck IO/CPU overload!\n')
    assert rec['mb']==312.456 and rec['samples']==5750000 and rec['lost_chunks']==7 and rec['warnings']==['Check IO/CPU overload!'],rec
    ok('perf_stat_csv_ipc_and_record_summary',ipc=round(st['derived']['ipc'],4))

def test_parsers():
    import perf_profile as pp
    an=bk.parse_annotate(fake_text('annotate','--stdio'))
    assert len(an)==1 and an[0]['dso']=='c8d2_gmp'and an[0]['samples']==100000 and an[0]['symbol']=='main._omp_fn.0'and an[0]['instructions']=={0x403f62:60.0,0x403f66:40.0},an
    a2l=bk.parse_addr2line('0x0000000000403f62\nevaluate(Graph const&, long double const*, long double, Scratch&)\n/x/src/kernel.hpp:193\nsample(Graph const&)\n'
                           '/x/src/kernel.hpp:230 (discriminator 2)\nmain._omp_fn.0\n/x/src/c8d2_integrate.cpp:150\n0x0000000000403f66\n??\n??:0\n0x10\n??\n??:?\n')
    assert a2l[0x403f62]==[('evaluate(Graph const&, long double const*, long double, Scratch&)','/x/src/kernel.hpp',193),('sample(Graph const&)','/x/src/kernel.hpp',230),
                           ('main._omp_fn.0','/x/src/c8d2_integrate.cpp',150)]and a2l[0x403f66]==[('??','??',0)]and a2l[0x10]==[('??','??',None)],a2l
    lt=bk.parse_ltrace_c('% time     seconds  usecs/call     calls      function\n------ ----------- ----------- --------- --------------------\n'
                         ' 60.00    0.600000          2    300000 __gmpf_mul\n 40.00    0.400000          1    400000 __gmpf_add\n'
                         '------ ----------- ----------- --------- --------------------\n100.00    1.000000                700000 total\n')
    assert [r['function']for r in lt['rows']]==['__gmpf_mul','__gmpf_add']and lt['total']['calls']==700000 and lt['total']['usecs_per_call']is None
    assert bk.parse_numa_maps('7f00 default anon=10 dirty=10 N0=6 N1=4 kernelpagesize_kB=4\n7f10 default file=/x N2=2 kernelpagesize_kB=2048\n7f20 default N3=1\n')=={0:24,1:16,2:4096,3:4}
    with tempfile.TemporaryDirectory()as td:
        for n,(h,m)in enumerate(((10,1),(20,2))):
            d=Path(td)/f'devices/system/node/node{n}';d.mkdir(parents=True);(d/'numastat').write_text(f'numa_hit {h}\nnuma_miss {m}\nlocal_node {h}\n')
        b=bk.node_numastat(td);(Path(td)/'devices/system/node/node1/numastat').write_text('numa_hit 25\nnuma_miss 2\nlocal_node 24\n')
        assert bk.numastat_delta(b,bk.node_numastat(td))=={0:{'numa_hit':0,'numa_miss':0,'local_node':0},1:{'numa_hit':5,'numa_miss':0,'local_node':4}}
    text=(ROOT/'src/kernel.hpp').read_text();lines=text.splitlines();reg=pp.kernel_regions(text)
    assert set(reg)=={'shift_loop','calculate_reference','calculate_products','calculate_shared','evaluate','sample'},reg
    lo,hi=reg['shift_loop'];assert lo==hi and 'for(auto mask:g.masks)'in lines[lo-1]
    for k in ('calculate_reference','calculate_products','calculate_shared','evaluate','sample'):
        lo,hi=reg[k];assert lo<hi and k in lines[lo-1]and lines[hi-1]=='}',(k,lo,hi)
    assert reg['evaluate'][0]<reg['shift_loop'][0]<reg['evaluate'][1]
    ok('annotate_addr2line_ltrace_numa_and_kernel_regions',regions={k:list(v)for k,v in reg.items()})

def test_ratio():
    rows=[{'begin':0,'end':100,'quad':30,'mp':5},{'begin':0,'end':50,'quad':10,'mp':0}]
    rh={'ld_fail':{'-10':25,'-15':15},'quad':{'-12':20,'-22':10,'-23':5,'-30':4,'zero_or_below':1},'mp':{'-40':3,'-100':2}}
    s=bk.ratio_summary({'rows':rows,'ratio_histogram':rh})
    assert s['ok']and s['points']==150 and s['quad']==40 and s['mp']==5,s['checks']
    assert s['cdf']['quad']['1e-20']==20/40 and s['cdf']['quad']['1e-23']==5/40 and s['cdf']['quad']['1e-9']==1.0 and s['cdf']['ld_fail']['1e-12']==15/40
    assert s['cdf']['mp']['1e-50']==2/5 and s['cdf']['mp']['1e-23']==1.0 and s['quad_accepted_margin_digits']=={'11':20,'1':10,'0':5}
    assert s['histograms']['quad']=={'-401':1,'-30':4,'-23':5,'-22':10,'-12':20}
    bad=bk.ratio_summary({'rows':[{**rows[0],'mp':6},rows[1]],'ratio_histogram':rh})
    assert not bad['ok']and not bad['checks']['mp_equals_mp_calls']and not bad['checks']['quad_below_1e-23_equals_mp_calls']
    assert bk.below({0:3,-10:2,-401:1},9)==3 and bk.below({0:3},0)==0
    ok('ratio_histogram_summaries_and_checks')

# ---------------------------------------------------------------- fixtures
NAMES={'heavy_free_L7':1024,'heavy_power_L7':1024,'heavy_free_L8':256,'heavy_power_L8':256,'nopromo_free_L7':1024,'nopromo_free_L8':256,
       'random_free_L7':512,'random_power_L7':512,'random_free_L8':512,'random_power_L8':512}
def test_fixtures():
    m=bk.load_fixtures();blocks=m['blocks']
    assert set(NAMES)<=set(blocks)and set(blocks)-set(NAMES)=={'p4_free_L8','p4_power_L8'},sorted(blocks)
    cm=json.loads((ROOT/m['cost_model']['path']).read_text());assert bk.digest(ROOT/m['cost_model']['path'])==m['cost_model']['sha256']
    assert m['cost_model']['executable_sha256'].startswith('5c5328af')and m['native']=={'layout':0,'rate':'.8','sum_mode':'compensated','bits':52,'grid':'-','order':8}
    for n,b in blocks.items():
        if n in NAMES:assert b['tasks']==NAMES[n],(n,b['tasks'])
        o,L,rows=bk.read_tasks(Path(m['_folder'])/b['files']['tasks']);assert o==8 and L==b['L']and len(rows)==b['tasks']
        assert all(r[3]<r[4]<=r[5]and r[5]&(r[5]-1)==0 and r[1]<b['replicates']and r[2]in set(b['graphs'])for r in rows)and len({r[0]for r in rows})==len(rows)
        assert b['native_seed']==bk.bench_seed(m['seed'],n,'native')and b['net']['seed']==bk.bench_seed(m['seed'],n,'net')
        raw=(Path(m['_folder'])/b['files']['net']).read_bytes();B,dim,bits=__import__('struct').unpack('<III',raw[:12])
        assert (B,dim,bits)==(b['replicates'],4*L-1,52)and len(raw)==12+B*dim*bits*8 and b['net']['sha256']==hashlib.sha256(raw).hexdigest()
        assert abs(b['predicted']['cost_model_seconds']-math.fsum(float(cm['seconds_per_point'][f'a:{b["sector"]}:{L}:{r[2]}'])*(r[4]-r[3])for r in rows))<1e-6
        if n.startswith('nopromo'):assert all(float(cm[f][f'{c}:{b["sector"]}:{L}:{g}'])==0 for g in b['graphs']for c in 'ab'for f in('quad_fraction','mp_fraction'))
        if n.startswith('heavy'):
            spp={g:float(cm['seconds_per_point'][f'a:{b["sector"]}:{L}:{g}'])for g in (r['id']for r in json.loads((ROOT/'inputs/inventory.json').read_text())[b['sector']][str(L)])}
            top=sorted(spp,key=lambda g:(-spp[g],g))[:len(b['graphs'])];assert sorted(top)==b['graphs']
        if 'wall_seconds'in b['predicted']:assert 0.5*b['predicted']['target_seconds']<=b['predicted']['wall_seconds']<=2*b['predicted']['target_seconds'],(n,b['predicted'])
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
    ok('committed_fixtures8_pins_sizes_seeds_nets',manifest_sha256=m['_manifest_sha256'],bytes=size,p4_ideal_seconds=round(wl['predicted_ideal_wall_seconds'],1))

def test_determinism():
    import prepare_benchmarks as pb
    r=pb.check_fixtures8(bk.FIXTURES8);assert r['identical'],r
    with tempfile.TemporaryDirectory()as td:
        spec=dict(blocks=pb.BLOCKS8[:2]+pb.BLOCKS8[4:6],workloads=pb.WORKLOADS8)
        a=pb.build_fixtures8(Path(td)/'a',**spec);b=pb.build_fixtures8(Path(td)/'b',**spec)
        fa=sorted(p.name for p in (Path(td)/'a').iterdir());assert fa==sorted(p.name for p in (Path(td)/'b').iterdir())
        assert all((Path(td)/'a'/n).read_bytes()==(Path(td)/'b'/n).read_bytes()for n in fa)and a['sha256']==b['sha256']
        refused_build=False
        try:pb.build_fixtures8(Path(td)/'a',**spec)
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
        # unfit or misused shapes are refused before any output exists
        for extra,code in ((['--lane-shapes','1x3','--fake-topology','1x2x2','--no-pin'],64),(['--lane-shapes','1x4','--fake-topology','1x2x2'],64)):
            out=td/f'p4_{code}_{len(extra)}';cp=tool('benchmark.py',*extra,'--output',out)
            assert cp.returncode==code and not out.exists(),(extra,cp.returncode,cp.stderr[-300:])
        cp=tool('benchmark.py','--lane-shapes','1x4','--interleave-probe','--output',td/'z');assert cp.returncode==2
        cp=tool('perf_profile.py','p1','--fake-topology','1x2x2','--output',td/'pp')
        assert cp.returncode==64 and '--no-pin'in cp.stderr,cp.stderr[-300:]
        fw=(ROOT/'tests/fake_worker.py').read_text();rel=write_exe(td/'c8d2_gmp',fw)
        diag=write_exe(td/'diag_gmp','import json,sys\nprint(json.dumps({"diagnostic":True,"diagnostic_kind":"tier_timers"}))\n')
        pp.check_exe(rel,None);assert 'diagnostic build'in refused(65,pp.check_exe,diag,None);pp.check_exe(diag,'tier_timers')
        refused(65,pp.check_exe,rel,'ratio_histogram');refused(69,pp.check_exe,td/'nothing',None);assert 'expected'in refused(65,pp.check_exe,rel,None,'deadbeef')
    ok('refusals_staging_builds_shapes_executables')

# ---------------------------------------------------------------- admission and scripts
def h7():
    spec=importlib.util.spec_from_file_location('h7_admit',SCRIPTS/'h7_admit.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def test_admission():
    h=h7();import slurm_submit as ss,production as prod
    assert h.H7E_R==ss.H7E_R and h.RUNNING_LIKE==ss.RUNNING_LIKE and h.AMD_PARTITIONS==ss.AMD_PARTITIONS and h.EXPANSE_NODE_PARTITIONS==ss.EXPANSE_NODE_PARTITIONS and h.LIVE_STATES==prod.LIVE_STATES
    me='zzheng8';L=lambda i,st,p,name,user=me,q='normal',n=1:f'{i}|{st}|{p}|{q}|{n}|{user}|{name}'
    def adm(lines,part='compute',site='expanse',who=me,job='c8d2-prof1'):return h.admit('\n'.join(lines)+'\n',site,who,job,part)
    assert adm([])['admitted']and adm([],'shared')['admitted']
    three=[L(i,'RUNNING','compute',f'c8d2-prof{i}')for i in range(3)];assert adm(three)['checks']['c8d2 compute nodes']=={'with_new':4,'cap':4}
    for lines,part,why in ((three+[L(9,'PENDING','compute','c8d2-prof9')],'compute','compute nodes'),
                           ([L(i,'RUNNING','compute','other',user='someone')for i in range(32)],'compute','yun124 running'),
                           ([L(i,'PENDING','shared',f'c8d2-s{i}',q='shared-normal')for i in range(32)],'shared','shared-partition'),
                           ([L(i,'PENDING','compute',f'c8d2-x{i}',n=0)for i in range(27)],'compute','submitted normal')):
        try:adm(lines,part);raise AssertionError(why)
        except h.Refused as e:assert e.code==65 and why in str(e),(why,str(e))
    assert adm([L(i,'RUNNING','compute',f'c8d3-y{i}')for i in range(6)]+[L(7,'COMPLETED','compute','c8d2-old')])['my_compute_nodes_live']==0
    for bad in (['1|RUNNING||normal|1|zzheng8|c8d2-x'],['garbage']):
        try:adm(bad);raise AssertionError('unparsable accepted')
        except h.Refused as e:assert e.code==69
    sym=lambda lines:h.admit('\n'.join(lines),'symmetry','zzheng1','c8d2-prof4','amddebugq')
    S=lambda i,p,name,st='RUNNING',user='zzheng1':f'{i}|{st}|{p}|normal|1|{user}|{name}'
    r=sym([S(1,'amdq','c8d2-a'),S(2,'amddebugq','c8d2-b'),S(3,'amdpreq','c8d2-c'),S(4,'amdq','lri-prod1'),S(5,'defq','c8d2-d'),S(6,'amdq','c8d2-e',user='x')])
    assert r['admitted']and r['amd_live']==3
    try:sym([S(i,'amdq',f'c8d2-{i}','PENDING')for i in range(4)]);raise AssertionError('H7 cap')
    except h.Refused as e:assert e.code==65
    for args in (('expanse','me','job','compute'),('expanse','me','c8d2-x','gpu'),('symmetry','me','c8d2-x','defq'),('nowhere','me','c8d2-x','x')):
        try:h.admit('',*args);raise AssertionError(args)
        except h.Refused as e:assert e.code==64
    cp=subprocess.run([PY,str(SCRIPTS/'h7_admit.py'),'--site','expanse','--me',me,'--job','c8d2-prof1','--partition','compute'],input='\n'.join(three+three)+'\n',capture_output=True,text=True)
    assert cp.returncode==65 and 'admission refused'in cp.stderr
    ok('h7_admission_expanse_and_symmetry')

def directives(text:str)->str:return ' '.join(l[len('#SBATCH'):].strip()for l in text.splitlines()if l.startswith('#SBATCH'))

def minutes(t:str)->int:
    h,m,s=map(int,t.split(':'));return 60*h+m+(s>0)

def test_scripts():
    import re
    su=0.;names=set()
    for k in (1,2,3,4):
        t=(SCRIPTS/f'expanse_prof{k}.slurm').read_text();d=directives(t)
        assert '-A yun124 -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G'in d and f'-J c8d2-prof{k}'in d,d
        assert '-o /expanse/lustre/scratch/zzheng8/temp_project/c8d2/logs/%x_%j.out'in d and 'E=$C8_DATA/evidence/$TAG/$RUN'in t and '--no-requeue'in d
        mm=minutes(re.search(r'-t (\d\d:\d\d:\d\d)',d)[1]);assert mm<=60;su+=128*mm/60;names.add(f'c8d2-prof{k}')
        assert '/scratch/$USER/job_$SLURM_JOB_ID'in t and 'source "$HOME/c8d2/env_expanse.sh"'in t
    b=directives((SCRIPTS/'expanse_prof_build.slurm').read_text());assert '-A yun124 -p shared'in b and '--mem=32G'in b and '-J c8d2-prof-build'in b and '-t 00:30:00'in b
    su+=16*30/60;assert su<=300,su
    for k,want in ((1,'perf_profile.py p1'),(2,'perf_profile.py p2'),(3,'perf_profile.py p3'),(4,'benchmark.py --lane-shapes')):assert want in (SCRIPTS/f'expanse_prof{k}.slurm').read_text()
    assert '--interleave-probe'in (SCRIPTS/'expanse_prof2.slurm').read_text()
    s=(SYM/'symmetry_prof4.slurm').read_text();d=directives(s)
    assert '-p amddebugq --exclude=cn112 -N 1 -n 1 --exclusive --mem=245G -t 01:00:00'in d and '-J c8d2-prof4'in d and '-o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out'in d
    assert '1x64,2x32,4x16,8x8'in s and '--fraction'in s and 'E=$D/evidence/$TAG/$RUN'in s and 'longq'not in s
    for f,site in ((SCRIPTS/'submit_prof_expanse.sh','expanse'),(SYM/'submit_prof4_symmetry.sh','symmetry')):
        t=f.read_text();body=[l for l in t.splitlines()if not l.lstrip().startswith('#')]
        assert 'git archive'in t and 'rsync'not in '\n'.join(body)and 'export_check.py'in t and 'h7_admit.py'in t
        sb=[i for i,l in enumerate(body)if 'sbatch'in l];adm=[i for i,l in enumerate(body)if 'admit'in l]
        assert sb and all(any(a<i for a in adm)for i in sb),(f.name,sb,adm)
    t=(SCRIPTS/'submit_prof_expanse.sh').read_text();body='\n'.join(l for l in t.splitlines()if not l.lstrip().startswith('#'))
    assert body.index('ssh -O check expanse')<body.index('git archive')and 'Master running'in body
    loop=body[body.index('for j in $JOBS'):];assert loop.count('admit ')>=2 and loop.count('sbatch')==2
    if shutil.which('bash'):
        for f in [*SCRIPTS.glob('*.sh'),*SCRIPTS.glob('*.slurm'),*SYM.glob('*')]:
            cp=subprocess.run(['bash','-n',str(f)],capture_output=True,text=True);assert cp.returncode==0,(f.name,cp.stderr)
    ok('job_and_submit_scripts',worst_case_su=round(su,1),jobs=sorted(names))

def test_order7():
    import prepare_benchmarks as pb,inspect
    new=inspect.getsource(pb.prepare_benchmarks).splitlines()
    assert new[1].lstrip().startswith('# C7(2)')and any('from prepare_inputs import prepare'in l for l in new[:6])
    if (ROOT/'.git').exists()and shutil.which('git'):
        old=subprocess.run(['git','-C',str(ROOT),'show','c8-stage3:tools/prepare_benchmarks.py'],capture_output=True,text=True)
        if old.returncode==0:
            tree=ast.parse(old.stdout);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='prepare_benchmarks')
            body_old=old.stdout.splitlines()[fn.lineno-1:fn.end_lineno];body_new=[l for l in new if not l.lstrip().startswith('#')and 'from prepare_inputs import prepare'not in l]
            assert body_old==body_new,'the order-7 function changed beyond the moved import'
            assert 'from prepare_inputs import prepare'in old.stdout
            ok('order7_builder_unchanged_apart_from_the_moved_import',compared_with='c8-stage3');return
    ok('order7_builder_unchanged_apart_from_the_moved_import',compared_with='none (no git checkout)')

# ---------------------------------------------------------------- end to end with fakes
def mini_fixture(td:Path)->Path:
    """A fixture folder on tests/fixtures/inputs_mini (8 L8 graphs per sector; the package's L7 packs) and a synthetic
    cost model in which every third free graph is promotion-free."""
    import prepare_benchmarks as pb
    inv=json.loads((ROOT/'tests/fixtures/inputs_mini/inventory.json').read_text());spp,qf,mf={},{},{}
    for c in 'ab':
        for s in ('free','power'):
            for L,rows in inv[s].items():
                for r in rows:k=f'{c}:{s}:{L}:{r["id"]}';spp[k]=1e-6*(1+r['id']%7);z=r['id']%3==0 and s=='free';qf[k]=0. if z else .5;mf[k]=0. if z else .1
    (td/'cm.json').write_text(json.dumps({'executable_sha256':'fake','cpu_models':['fake'],'lane_width':4,'job_ids':['0'],'seconds_per_point':spp,'quad_fraction':qf,'mp_fraction':mf}))
    blocks=(dict(name='heavy_free_L8',purpose='P1',sector='free',L=8,select='heaviest',graphs=4,replicates=2,chunks=2,target_seconds=.01,target_threads=4),
            dict(name='heavy_power_L8',purpose='P1',sector='power',L=8,select='heaviest',graphs=4,replicates=2,chunks=1,target_seconds=.01,target_threads=4),
            dict(name='heavy_free_L7',purpose='P1',sector='free',L=7,select='heaviest',graphs=3,replicates=2,chunks=2,target_seconds=.01,target_threads=4),
            dict(name='nopromo_free_L8',purpose='P2',sector='free',L=8,select='nopromo',graphs=3,replicates=2,chunks=1,target_seconds=.01,target_threads=4),
            dict(name='random_power_L8',purpose='P3',sector='power',L=8,select='random',graphs=5,replicates=2,chunks=1,target_seconds=.01,target_threads=4))
    wls=(dict(name='p4_L8',purpose='P4',L=8,sectors=('free','power'),replicates=2,points=64,target_seconds=.004,target_threads=4),)
    pb.build_fixtures8(td/'fx',inputs_rel='tests/fixtures/inputs_mini',cost_model=td/'cm.json',seed=7,blocks=blocks,workloads=wls);return td/'fx'

FAKE_DIAG='''import json,subprocess,sys
FW={fw!r};KIND={kind!r}  # None: a release stand-in whose rows carry the ratio-histogram stand-in's promotion counters (P3's binding)
if sys.argv[1:]==['--describe']:
    d=json.loads(subprocess.run([sys.executable,'-S',FW,'--describe'],capture_output=True,text=True).stdout)
    if KIND:d['diagnostic']=True;d['diagnostic_kind']=KIND
    print(json.dumps(d));sys.exit(0)
rc=subprocess.run([sys.executable,'-S',FW,*sys.argv[1:]]).returncode
if rc:sys.exit(rc)
out=sys.argv[5];n=json.load(open(out));Q=M=P=0
for r in n['rows']:
    p=r['end']-r['begin'];P+=p
    if KIND in('ratio_histogram',None):r['quad']=p//2;r['mp']=p//8;Q+=p//2;M+=p//8
SKEW=__import__('os').environ.get('C8_FAKE_DIAG_SKEW')  # a stale diagnostic build: one scientific value of the run on that block differs
if KIND and SKEW and SKEW in sys.argv[1]and n['rows']:
    r=min(n['rows'],key=lambda r:r['uid']);v=float(r['values'][0]);r['values'][0]=repr(v*(1+2**-40)if v else 1e-300)
if KIND=='tier_timers':n['tier_timers']={{'clock':'steady_clock','first_pass_seconds':.5,'first_pass_calls':P,'quad_seconds':.3,'quad_calls':0,'mp_seconds':.2,'mp_calls':0}}
elif KIND=='ratio_histogram':n['ratio_histogram']={{'bins':'fake','ld_fail':{{'-12':Q}},'quad':{{'-15':Q-M,'-30':M}},'mp':{{'-100':M}}}}
json.dump(n,open(out,'w'))
'''
# A fake ltrace (P1's fallback, W19): runs the traced command and writes a `ltrace -c` table; FAKE_LTRACE_SKEW=1 changes
# one value of the traced run's rows (a traced run that is not the plain run's computation).
FAKE_LTRACE='''import json,os,subprocess,sys
a=sys.argv[1:];lo=a[a.index('-o')+1];cmd=a[a.index('--')+1:]
rc=subprocess.run(cmd).returncode
open(lo,'w').write('% time     seconds  usecs/call     calls      function\\n------ ----------- ----------- --------- --------------------\\n'
                   ' 60.00    0.600000          2    300000 __gmpf_mul\\n 40.00    0.400000          1    400000 __gmpf_add\\n'
                   '------ ----------- ----------- --------- --------------------\\n100.00    1.000000                700000 total\\n')
if os.environ.get('FAKE_LTRACE_SKEW')and rc==0:
    n=json.load(open(cmd[5]));r=min(n['rows'],key=lambda r:r['uid']);r['values'][0]=repr(float(r['values'][0])*(1+2**-40));json.dump(n,open(cmd[5],'w'))
sys.exit(rc)
'''
def fakes(td:Path)->dict:
    fw=str(ROOT/'tests/fake_worker.py')
    return {'gmp':write_exe(td/'c8d2_gmp',(ROOT/'tests/fake_worker.py').read_text()),'prof':write_exe(td/'c8d2_gmp_prof',FAKE_DIAG.format(fw=fw,kind='tier_timers')),
            'ratio':write_exe(td/'c8d2_gmp_ratiohist',FAKE_DIAG.format(fw=fw,kind='ratio_histogram')),
            'rel':write_exe(td/'c8d2_gmp_release',FAKE_DIAG.format(fw=fw,kind=None)),  # P3's release worker (rows = the ratio stand-in's)
            'perf':write_exe(td/'perf',(ROOT/'tests/fake_perf.py').read_text())}

def tool(script,*args,env=None,timeout:float=600.)->subprocess.CompletedProcess:
    """Run tools/<script> (stdout and stderr captured). W15's class (Stage-6 fix round 4): the tool runs in a session of
    its own, and when it does not finish (the timeout, an interrupt) its whole process group, the tool and every worker,
    fake perf or ltrace it started, is killed and reaped before the exception propagates (subprocess.run's timeout
    killed the tool alone and left its children running). On the normal path the group is not signalled: the tool has
    then been reaped, and its group's id could already belong to someone else."""
    cmd=[PY,'-B',str(ROOT/'tools'/script),*map(str,args)]
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,**(env or{})},start_new_session=True)
    try:out,err=p.communicate(timeout=timeout)
    except BaseException:
        try:os.killpg(p.pid,signal.SIGKILL)  # the tool is not reaped yet, so its group's id is still its own
        except OSError:p.kill()  # macOS refuses killpg once only the exited, unreaped leader is left
        p.communicate();raise
    return subprocess.CompletedProcess(cmd,p.returncode,out,err)

def test_e2e_lanes():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td);common=['--fake-topology','1x2x2','--no-pin','--exe',f['gmp'],'--fixtures',fx,'--scratch',td,'--numa-sample-seconds','0.05']
        cp=tool('benchmark.py','--lane-shapes','1x4,2x2,4x1,2x1',*common,'--output',td/'p4');assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        r=json.loads((td/'p4/p4.json').read_text())
        assert r['schema']=='c8-d2-prof-p4-1'and r['all_shapes_identical_rows']and [t['shape']for t in r['table']]==['1x4','2x2','4x1','2x1']and r['workload']['tasks']==32
        assert r['settings']['fake_topology']=='1x2x2'and r['settings']['pinned']is False and r['identity']['executables']['worker']['sha256']==bk.digest(f['gmp'])
        for s in r['shapes']:
            assert s['tasks']==32 and s['rows']==32 and len(s['lanes_detail'])==int(s['shape'].split('x')[0])and s['throughput_cost_model_s_per_node_s']>0
            assert 0<=s['load_staging_share_of_node_time']<=1 and s['stage_seconds']>0 and not s['errors']
        lanes2=[x['cpus']for x in r['shapes'][1]['lanes_detail']];assert lanes2==['0-1','2-3'],lanes2
        cp=tool('benchmark.py','--lane-shapes','2x2',*common,'--fraction','0.5','--output',td/'half');assert cp.returncode==0,cp.stderr[-800:]
        h=json.loads((td/'half/p4.json').read_text());assert h['workload']['tasks']==16 and h['workload']['parts']['p4_free_L8']['graphs']==4
        cp=tool('benchmark.py','--lane-shapes','2x2',*common,'--output',td/'fail',env={'C8_FAKE_FAIL':'1'});assert cp.returncode==1
        x=json.loads((td/'fail/p4.json').read_text());assert x['table'][0]['errors']and 'forced native failure'in x['table'][0]['errors'][0]and x['best_shape']is None
    ok('e2e_lane_shapes_fake_worker',shapes=4)

def test_e2e_probe():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td)
        probe=write_exe(td/'probe','import json,sys\ng=int(sys.argv[1].split("/G")[-1].split(".")[0])\n'
                        'print(json.dumps({"graph":g,"speedup":{"2":1.1+0.1*(g%2),"4":1.3},"identical":{"2":True,"4":True},"seconds_per_point":{"1":1e-6,"2":9e-7,"4":8e-7}}))\n')
        cp=tool('benchmark.py','--interleave-probe','--probe-exe',probe,'--probe-graphs','nopromo_free_L8:2,heavy_free_L8:2','--fake-topology','1x2x4','--no-pin','--fixtures',fx,'--scratch',td,'--output',td/'ip')
        assert cp.returncode==0,cp.stderr[-800:]+cp.stdout[-800:]
        r=json.loads((td/'ip/interleave.json').read_text());assert len(r['results'])==4 and r['all_identical']and r['speedup']['all']['4']['median']==1.3
        assert {x['cpu']for x in r['results']}=={0,1,2,3}and r['probe_speedup_2']is not None and 1.1<=r['probe_speedup_2']<=1.2
        bad=write_exe(td/'bad','import sys\nsys.exit(3)\n')
        cp=tool('benchmark.py','--interleave-probe','--probe-exe',bad,'--probe-graphs','nopromo_free_L8:1','--fake-topology','1x2x4','--no-pin','--fixtures',fx,'--scratch',td,'--output',td/'ip2')
        assert cp.returncode==1
    ok('e2e_interleave_probe_driver')

def test_e2e_perf():
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td);base=['--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--scratch',td,'--perf',f['perf']]
        cp=tool('perf_profile.py','p1',*base,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_free_L8,heavy_power_L8','--no-srcline','--output',td/'p1')
        assert cp.returncode==0,cp.stdout[-2000:]+cp.stderr[-1500:]
        r=json.loads((td/'p1/p1.json').read_text());assert r['stage']=='final'and r['perf']['ok']and r['settings']['concurrent']and r['settings']['perf_cpus']==[0,1,2,3]and r['settings']['tier_cpus']==[4,5,6,7]
        for b in ('heavy_free_L8','heavy_power_L8'):
            x=r['blocks'][b];assert abs(x['perf']['shares']['categories']['binary128_arith']-52.0)<1e-9 and x['perf']['total_samples']==1000000
            assert x['rows_identical_worker_vs_prof']and abs(sum(x['tier_run']['tier_split']['share_of_tiers'].values())-1)<1e-12 and x['perf_run']['record']['samples']==1234
            assert x['perf']['srcline']['status'].startswith('skipped')and len(x['perf']['top40'])==19 and (td/'p1'/f'{b}.perf_report_symbol.txt').is_file()
        assert not r['errors']and r['fallback']is None
        # p1-reparse: the same summaries from the saved texts, also after perf 4.18's IPC columns are added to them;
        # never over the original record.
        cp=tool('perf_profile.py','p1-reparse','--input',td/'p1');assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        rr=json.loads((td/'p1/p1_reparsed.json').read_text());assert rr['reparsed']['blocks']==['heavy_free_L8','heavy_power_L8']
        for b in ('heavy_free_L8','heavy_power_L8'):
            assert rr['blocks'][b]['perf']['shares']==r['blocks'][b]['perf']['shares']and rr['blocks'][b]['perf']['srcline']==r['blocks'][b]['perf']['srcline']
            assert rr['blocks'][b]['tier_run']==r['blocks'][b]['tier_run']
        for k in ('symbol','dso_symbol'):
            p=td/'p1'/f'heavy_free_L8.perf_report_{k}.txt';p.write_text(with_ipc(p.read_text()))
        cp=tool('perf_profile.py','p1-reparse','--input',td/'p1','--output',td/'re2.json');assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r2=json.loads((td/'re2.json').read_text());assert r2['blocks']['heavy_free_L8']['perf']['shares']==r['blocks']['heavy_free_L8']['perf']['shares']
        assert tool('perf_profile.py','p1-reparse','--input',td/'p1').returncode==64  # p1_reparsed.json exists: refused
        cp=tool('perf_profile.py','p1',*base,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_free_L8','--output',td/'p1r',env={'FAKE_PERF_REFUSE':'1'})
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p1r/p1.json').read_text());assert not r['perf']['ok']and 'perf_event_paranoid'in r['fallback']['reason']and 'tier_run'in r['blocks']['heavy_free_L8']
        assert 'perf'not in r['blocks']['heavy_free_L8']and r['settings']['concurrent']and r['fallback']['ltrace']is not None and not r['errors']
        # W19: without perf the release worker runs the requested block itself (directly, at --threads, on the first
        # set of cores, concurrently with the tier timers on the second) and the two are bound on that block
        x=r['blocks']['heavy_free_L8'];rr=x['release_run']
        assert x['rows_identical_worker_vs_prof']is True and rr['threads']==4 and rr['cpus']==[0,1,2,3]and rr['native']['tasks']==x['tier_run']['native']['tasks']and rr['team']['wrapped']is False,x
        assert rr['cmd'][0]==str(f['gmp'].resolve())and r['settings']['tier_cpus']==[4,5,6,7]and (td/'p1r/heavy_free_L8.release.log').is_file()
        bd=r['fallback']['binding'];assert bd['blocks']=={'heavy_free_L8':True}and bd['threads']==4,bd  # W19 (the Z20 binding on every block)
        # the ltrace part (a fake ltrace first on PATH): the GMP call table of a mini block, its rows equal to a plain run
        # of that mini block; a traced run whose rows differ is an error of P1
        lb=td/'ltbin';lb.mkdir();write_exe(lb/'ltrace',FAKE_LTRACE);pth={'PATH':f'{lb}{os.pathsep}{os.environ["PATH"]}','FAKE_PERF_REFUSE':'1'}
        lt_args=['p1',*base,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_free_L8']
        cp=tool('perf_profile.py',*lt_args,'--output',td/'p1lt',env=pth);assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p1lt/p1.json').read_text());lt=r['fallback']['ltrace']
        assert isinstance(lt,dict)and lt['block']=='heavy_power_L8'and lt['returncode']==0 and lt['rows_identical_plain_vs_ltrace']is True and lt['table']['total']['calls']==700000,lt
        assert lt['tasks']==8 and (td/'p1lt/mini_ltrace_c.txt').is_file()and (td/'p1lt/mini_plain.log').is_file()and not r['errors']
        cp=tool('perf_profile.py',*lt_args,'--output',td/'p1lt2',env={**pth,'FAKE_LTRACE_SKEW':'1'});assert cp.returncode==1,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p1lt2/p1.json').read_text());assert r['fallback']['ltrace']['rows_identical_plain_vs_ltrace']is False and len(r['errors'])==1
        assert r['errors'][0].startswith('heavy_power_L8 (mini block, ltrace)')and r['blocks']['heavy_free_L8']['rows_identical_worker_vs_prof']is True,r['errors']
        cp=tool('perf_profile.py','p2',*base,'--threads',4,'--exe',f['gmp'],'--blocks','nopromo_free_L8','--serial-seconds','1e-9','--output',td/'p2')
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p2/p2.json').read_text());x=r['blocks']['nopromo_free_L8']
        assert abs(r['ipc']['nopromo_free_L8']['parallel']-0.8)<1e-6 and x['serial']['threads']==1 and x['parallel']['promotion_free']and x['serial']['native']['tasks']==1
        cp=tool('perf_profile.py','p3',*base,'--threads',8,'--exe',f['ratio'],'--worker-exe',f['rel'],'--blocks','random_power_L8','--rates','.8,.9','--output',td/'p3')
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-800:]
        r=json.loads((td/'p3/p3.json').read_text());assert r['all_checks_ok']and set(r['results'])=={'random_power_L8@.8','random_power_L8@.9'}
        assert r['results']['random_power_L8@.9']['ratio']['cdf']['quad']['1e-23']==0.25
        for k,x in r['results'].items():  # W19's class: every (block, rate) also run by the release worker, rows bound
            assert x['rows_identical_worker_vs_ratiohist']is True and x['release_run']['native']['tasks']==x['native']['tasks']and 'rows_mismatch'not in x,(k,x)
        assert r['identity']['worker_check']==bk.digest(f['rel'])and r['settings']['worker_exe']==str(f['rel'].resolve())
    ok('e2e_perf_profile_p1_fallback_p2_p3_fake_perf')

def test_perf_team():
    """Stage-6 fix round 2 (Y2's defect class in tools/perf_profile.py, P1-P3; the P4 side is benchkit.run_watched):
    run() starts the worker in the controlled OpenMP environment (no inherited OMP_*, GOMP_*, KMP_*) and watches the
    team of a direct run of the native exe (common.TeamWatch; /proc stubbed here, as on Linux): a worker that shows
    its team is 'verified' and passes native_result's team gate; one that does not while it computes is stopped long
    before its end and refused; one that never shows it (a wait, not a computation) is refused as 'unverified'; a run
    wrapped by perf or ltrace is not watched (team.wrapped); a stand-in worker that is not ELF is not watched."""
    import common as C,perf_profile as pp
    from unittest import mock
    me=os.getpid();team={'n':4};cpu={'s':100.}
    dirty={'OMP_THREAD_LIMIT':'1','OMP_DYNAMIC':'true','OMP_NUM_THREADS':'64','GOMP_SPINCOUNT':'0','KMP_AFFINITY':'none'}
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);sl=td/'sleeper';wrap=td/'wrap'
        sl.write_text(f'#!{PY}\nimport json,os,sys,time\nopen(sys.argv[1],"w").write(json.dumps({{k:v for k,v in os.environ.items()if k.startswith(("OMP_","GOMP_","KMP_"))}}))\ntime.sleep(float(sys.argv[2]))\n')
        wrap.write_text(f'#!{PY}\nimport subprocess,sys\nsys.exit(subprocess.call(sys.argv[1:]))\n');sl.chmod(0o755);wrap.chmod(0o755)
        def go(tag,secs,wrapped=False):
            cmd=[str(sl),str(td/f'{tag}.env'),str(secs)];cmd=[str(wrap),*cmd]if wrapped else cmd
            t0=time.time();r=pp.run(cmd,[0],4,td/f'{tag}.log',False,exe=sl);r['elapsed']=time.time()-t0;r['env']=json.loads((td/f'{tag}.env').read_text())
            return r
        def gate(r)->str:
            try:pp.native_result(td/'missing.json',4,r)
            except RuntimeError as e:return str(e)
            raise AssertionError('native_result accepted a run without its output')
        want={'OMP_NUM_THREADS':'4','OMP_DYNAMIC':'FALSE','OMP_PROC_BIND':'close','OMP_PLACES':'cores'}
        with mock.patch.dict(os.environ,dirty),mock.patch.object(C,'proc_task_count',lambda pid:1 if pid==me else team['n']),\
             mock.patch.object(C,'proc_cpu_seconds',lambda pid:cpu['s']),mock.patch.object(C,'TEAM_DEADLINE_SECONDS',0.4),mock.patch.object(bk,'team_check',lambda e:True):
            r=go('verified',0.3);assert r['team']['verdict']=='verified'and r['team']['watched']and r['returncode']==0 and r['env']==want,r
            assert 'OpenMP team'not in gate(r)  # past the team gate (then refused for the missing output only)
            team['n']=1;r=go('smaller',30);assert r['team']['verdict']=='smaller'and r['returncode']!=0 and r['elapsed']<15,(r['team'],r['elapsed'])
            assert 'asked for an OpenMP team of 4 threads but showed at most 1'in gate(r),gate(r)
            cpu['s']=0.;r=go('unverified',1.2);assert r['team']['verdict']=='unverified'and r['returncode']==0,r['team']
            assert 'did not show its OpenMP team of 4 threads (verdict unverified'in gate(r),gate(r)
            cpu['s']=100.;r=go('wrapped',0.3,wrapped=True);assert r['team']['watched']is False and r['team']['wrapped']and r['returncode']==0 and r['env']==want,r
            assert 'OpenMP team'not in gate(r)
        with mock.patch.dict(os.environ,dirty):
            r=go('standin',0.1);assert r['team']['verdict']=='unavailable'and r['team']['watched']is False and r['env']==want,r  # not ELF: not watched
    ok('perf_profile_controlled_env_direct_runs_team_watched_wrapped_not')

def test_perf_binding():
    """Z20 (Stage-6 fix round 3, S6H3-02): P1 combines the release worker's perf run with the tier-timer worker's run of
    each block, so any difference of their scientific rows fails P1 (exit 1), naming the block and the differing uids;
    the other blocks stay accepted. W19 (Stage-6 fix round 4, S6H4-02): without perf the release worker runs every
    requested block directly and the same per-block binding applies; before, the fallback compared the two workers on a
    mini block of heavy_power_L8 only, so the finding's counterexample (no perf, the stale build differing on
    heavy_free_L8, --blocks heavy_free_L8) exited 0. A difference on a block P1 does not measure no longer matters. The
    stale build is the fake diagnostic worker with C8_FAKE_DIAG_SKEW=<block>: one value of one row of its run on that
    block differs."""
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td);base=['--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--scratch',td,'--perf',f['perf'],'--threads',4,
                                                       '--exe',f['gmp'],'--prof-exe',f['prof']]
        cp=tool('perf_profile.py','p1',*base,'--blocks','heavy_free_L8,heavy_power_L8','--no-srcline','--output',td/'skew',env={'C8_FAKE_DIAG_SKEW':'heavy_power_L8'})
        assert cp.returncode==1,(cp.returncode,cp.stdout[-1500:]+cp.stderr[-800:])
        r=json.loads((td/'skew/p1.json').read_text());assert r['stage']=='final',r['stage']
        good,bad=r['blocks']['heavy_free_L8'],r['blocks']['heavy_power_L8']
        assert good['rows_identical_worker_vs_prof']is True and 'rows_mismatch'not in good and bad['rows_identical_worker_vs_prof']is False,(good,bad)
        mm=bad['rows_mismatch'];assert mm['rows_differing']==1 and len(mm['uids'])==1 and mm['rows_in_one_run_only']==0,mm
        assert len(r['errors'])==1 and r['errors'][0].startswith('heavy_power_L8')and 'tier-timer worker'in r['errors'][0]and str(mm['uids'][0])in r['errors'][0],r['errors']
        assert 'perf'in bad and 'tier_run'in bad  # the measurements stay recorded; the record is not accepted
        # W19: the finding's counterexample (no perf; the stale build differs on the requested block, outside the old mini
        # block): exit 1, the block named; its runs stay recorded
        cp=tool('perf_profile.py','p1',*base,'--blocks','heavy_free_L8','--output',td/'skewfb',env={'C8_FAKE_DIAG_SKEW':'heavy_free_L8','FAKE_PERF_REFUSE':'1'})
        assert cp.returncode==1,(cp.returncode,cp.stdout[-1500:]+cp.stderr[-800:])
        r=json.loads((td/'skewfb/p1.json').read_text());x=r['blocks']['heavy_free_L8'];bd=r['fallback']['binding']
        assert not r['perf']['ok']and x['rows_identical_worker_vs_prof']is False and x['rows_mismatch']['rows_differing']==1 and bd['blocks']=={'heavy_free_L8':False},(x,bd)
        assert len(r['errors'])==1 and r['errors'][0].startswith('heavy_free_L8:')and 'tier-timer worker'in r['errors'][0]and str(x['rows_mismatch']['uids'][0])in r['errors'][0],r['errors']
        assert 'release_run'in x and 'tier_run'in x and 'perf'not in x
        # two blocks without perf: the mismatch on heavy_free_L8 (outside the old mini block) fails P1, heavy_power_L8 stays accepted
        cp=tool('perf_profile.py','p1',*base,'--blocks','heavy_free_L8,heavy_power_L8','--output',td/'skewfb2',env={'C8_FAKE_DIAG_SKEW':'heavy_free_L8','FAKE_PERF_REFUSE':'1'})
        assert cp.returncode==1,(cp.returncode,cp.stdout[-1500:]+cp.stderr[-800:])
        r=json.loads((td/'skewfb2/p1.json').read_text())
        assert r['fallback']['binding']['blocks']=={'heavy_free_L8':False,'heavy_power_L8':True}and len(r['errors'])==1 and r['errors'][0].startswith('heavy_free_L8:'),(r['fallback'],r['errors'])
        # a difference on a block P1 does not measure is no error (the tier timers of the requested block are bound)
        cp=tool('perf_profile.py','p1',*base,'--blocks','heavy_free_L8','--output',td/'skewfb3',env={'C8_FAKE_DIAG_SKEW':'heavy_power_L8','FAKE_PERF_REFUSE':'1'})
        assert cp.returncode==0,(cp.returncode,cp.stdout[-1500:]+cp.stderr[-800:])
        r=json.loads((td/'skewfb3/p1.json').read_text());assert r['fallback']['binding']['blocks']=={'heavy_free_L8':True}and not r['errors'],r['errors']
    ok('perf_profile_p1_release_vs_tier_timer_rows_bound_with_and_without_perf')

def test_p3_binding():
    """W19's defect class in P3 (Stage-6 fix round 4): P3 measured the ratio-histogram build alone, never bound to the
    release worker (its Slurm script only asserted "its rows equal the release worker's"). Now the release worker
    (--worker-exe, a release build, checked before any output) runs every (block, rate) too, and any difference of the
    scientific rows is an error naming the block, the rate and the uids (rows_mismatch) and P3 exits 1; the other runs
    stay accepted and recorded. Cases: a stale ratio-histogram build on one block (C8_FAKE_DIAG_SKEW), a release worker
    that computes other promotion counters (the plain fake), a release run that fails (the margins stay recorded,
    unbound, and are an error), and a diagnostic or missing --worker-exe (refused, 65 or 69, no output)."""
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td);flog=td/'invocations.jsonl'
        base=['p3','--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--scratch',td,'--perf',f['perf'],'--threads',8,'--exe',f['ratio'],'--rates','.8,.9']
        cp=tool('perf_profile.py',*base,'--worker-exe',f['rel'],'--blocks','random_power_L8,nopromo_free_L8','--output',td/'skew',env={'C8_FAKE_DIAG_SKEW':'random_power_L8'})
        assert cp.returncode==1,(cp.returncode,cp.stdout[-1500:]+cp.stderr[-800:])
        r=json.loads((td/'skew/p3.json').read_text());assert not r['all_checks_ok']and len(r['results'])==4,r['results'].keys()
        for k,x in r['results'].items():
            bad=k.startswith('random_power_L8@');assert x['rows_identical_worker_vs_ratiohist']is (not bad)and ('rows_mismatch'in x)is bad and x['ratio']['ok'],(k,x)
            if bad:assert x['rows_mismatch']['rows_differing']==1 and x['rows_mismatch']['rows_in_one_run_only']==0,x['rows_mismatch']
        assert sorted(e.split(':')[0]for e in r['errors'])==['random_power_L8@.8','random_power_L8@.9']and all('ratio-histogram build'in e for e in r['errors']),r['errors']
        cp=tool('perf_profile.py',*base,'--worker-exe',f['gmp'],'--blocks','random_power_L8','--output',td/'other')  # rows with other promotion counters
        assert cp.returncode==1,(cp.returncode,cp.stdout[-1500:]+cp.stderr[-800:])
        r=json.loads((td/'other/p3.json').read_text());assert all(x['rows_identical_worker_vs_ratiohist']is False for x in r['results'].values())and len(r['errors'])==2,r['errors']
        # a release run that fails: the ratio-histogram measurement stays recorded, unbound (None), and is an error
        fail=write_exe(td/'c8d2_gmp_failing',f'import subprocess,sys\nif sys.argv[1:]==["--describe"]:print(subprocess.run([sys.executable,"-S",{str(ROOT/"tests/fake_worker.py")!r},"--describe"],'
                       'capture_output=True,text=True).stdout,end="");sys.exit(0)\nsys.exit(3)\n')
        cp=tool('perf_profile.py',*base,'--worker-exe',fail,'--blocks','random_power_L8','--output',td/'relfail');assert cp.returncode==1,(cp.returncode,cp.stderr[-600:])
        r=json.loads((td/'relfail/p3.json').read_text());assert len(r['results'])==2 and len(r['errors'])==2 and all('release run'in e for e in r['errors']),r['errors']
        assert all(x['rows_identical_worker_vs_ratiohist']is None and 'release_run_error'in x and x['ratio']['ok']for x in r['results'].values()),r['results']
        for bad in (f['ratio'],f['prof']):  # a diagnostic build as the release reference: refused before any output or run
            out=td/f'diag_{bad.name}';cp=tool('perf_profile.py',*base,'--worker-exe',bad,'--blocks','random_power_L8','--output',out,env={'C8_FAKE_LOG':str(flog)})
            assert cp.returncode==65 and 'diagnostic build'in cp.stderr and not out.exists()and not flog.exists(),(cp.returncode,cp.stderr[-400:])
        out=td/'missing';cp=tool('perf_profile.py',*base,'--worker-exe',td/'none','--blocks','random_power_L8','--output',out)
        assert cp.returncode==69 and not out.exists(),(cp.returncode,cp.stderr[-400:])
    ok('perf_profile_p3_release_vs_ratio_histogram_rows_bound')

HANG='''import subprocess,sys,time
c=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)','fx4g4-grandchild'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
open(sys.argv[1],'w').write(str(c.pid))
time.sleep(120)
'''
def test_tool_cleanup():
    """W15's class in this suite (Stage-6 fix round 4): a tool that does not finish is stopped with everything it
    started. The control: a stand-in tool starts a 120 s worker (output redirected) and hangs; tool() with a 3 s timeout
    raises TimeoutExpired, and by then the tool and its worker are gone (independently: the worker's pid). Before, the
    timeout of subprocess.run killed the tool alone and left the worker running."""
    def alive(pid):
        try:os.kill(pid,0);return True
        except ProcessLookupError:return False
        except PermissionError:return True
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);hang=td/'hang.py';hang.write_text(HANG);pidf=td/'worker.pid';w=None
        try:
            t0=time.time()
            try:tool(hang,pidf,timeout=3);raise AssertionError('the hanging tool was not stopped by the timeout')
            except subprocess.TimeoutExpired:pass
            assert pidf.exists(),'the stand-in tool never started its worker';w=int(pidf.read_text())
            t1=time.time()
            while alive(w)and time.time()-t1<10:time.sleep(0.05)
            assert not alive(w),('the worker of the timed-out tool survives',w)
            assert time.time()-t0<60
        finally:  # this control's own cleanup if it failed
            if w is not None and alive(w):os.kill(w,signal.SIGKILL)
    ok('tool_timeout_kills_the_tools_process_group')

def test_perf_expect():
    """Z21 (Stage-6 fix round 3, S6H3-03) and its class: --expect-sha256 binds the executable each mode measures (P1 and
    P2 the release worker, P3 the ratio-histogram build, benchmark.py --lane-shapes the worker and --interleave-probe
    the probe). A mismatched prefix is refused (65) before any output directory, scratch directory or worker run
    exists; an empty or malformed value is refused (64), never taken as 'no constraint'; the C7(2) legacy mode, which
    binds no executable, refuses the option (2)."""
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td);flog=td/'invocations.jsonl';env={'C8_FAKE_LOG':str(flog)}
        def base(tag):(td/f's_{tag}').mkdir();return ['--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--scratch',td/f's_{tag}','--perf',f['perf']]
        wrong='0'*16
        runs={'p1':['p1','--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_free_L8','--no-srcline'],
              'p2':['p2','--threads',4,'--exe',f['gmp'],'--blocks','nopromo_free_L8','--serial-seconds','1e-9'],
              'p3':['p3','--threads',8,'--exe',f['ratio'],'--worker-exe',f['rel'],'--blocks','random_power_L8','--rates','.8']}
        for mode,args in runs.items():
            for val,code,why in ((wrong,65,'is not the expected'),('',64,'hexadecimal'),('xyz12345',64,'hexadecimal'),('abc',64,'hexadecimal')):
                tag=f'{mode}_{code}_{len(val)}_{val[:1]}';out=td/f'out_{tag}'
                cp=tool('perf_profile.py',*args[:1],*base(tag),*args[1:],'--expect-sha256',val,'--output',out,env=env)
                assert cp.returncode==code and why in cp.stderr,(mode,val,cp.returncode,cp.stdout[-800:]+cp.stderr[-800:])
                assert not out.exists()and not any((td/f's_{tag}').iterdir())and not flog.exists(),(mode,val,'output, scratch or a worker run before the refusal')
        ok_=tool('perf_profile.py','p3',*base('p3ok'),*runs['p3'][1:],'--expect-sha256',bk.digest(f['ratio'])[:16].upper(),'--output',td/'p3ok')
        assert ok_.returncode==0,ok_.stdout[-1500:]+ok_.stderr[-800:]
        r=json.loads((td/'p3ok/p3.json').read_text());assert r['all_checks_ok']and r['identity']['ratiohist_check']==bk.digest(f['ratio'])and r['settings']['expect_sha256']==bk.digest(f['ratio'])[:16].lower()
        # benchmark.py: --lane-shapes (bound before), --interleave-probe (the probe; was ignored), legacy (refused)
        probe=write_exe(td/'probe','import json,sys\nprint(json.dumps({"graph":1,"speedup":{"2":1.1,"4":1.3},"identical":{"2":True,"4":True},"seconds_per_point":{"1":1e-6}}))\n')
        pb_=['--interleave-probe','--probe-exe',probe,'--probe-graphs','nopromo_free_L8:1','--fake-topology','1x2x4','--no-pin','--fixtures',fx,'--scratch',td]
        for val,code in ((wrong,65),('',64),('g'*8,64)):
            cp=tool('benchmark.py',*pb_,'--expect-sha256',val,'--output',td/'ip_bad');assert cp.returncode==code and not (td/'ip_bad').exists(),(val,cp.returncode,cp.stderr[-600:])
        cp=tool('benchmark.py',*pb_,'--expect-sha256',bk.digest(probe)[:12],'--output',td/'ip_ok');assert cp.returncode==0,cp.stderr[-800:]
        r=json.loads((td/'ip_ok/interleave.json').read_text());assert r['settings']['expect_sha256']==bk.digest(probe)[:12]
        lane=['--lane-shapes','2x2','--fake-topology','1x2x2','--no-pin','--exe',f['gmp'],'--fixtures',fx,'--scratch',td]
        for val,code in ((wrong,65),('',64)):
            cp=tool('benchmark.py',*lane,'--expect-sha256',val,'--output',td/'p4_bad',env=env);assert cp.returncode==code and not (td/'p4_bad').exists()and not flog.exists(),(val,cp.returncode)
        cp=tool('benchmark.py','--output',td/'legacy','--expect-sha256','abcdef12',env={'CXX':'false'})
        assert cp.returncode==2 and '--expect-sha256'in cp.stderr and not (td/'legacy').exists(),(cp.returncode,cp.stderr[-600:])
    ok('expect_sha256_binds_every_mode_before_any_output',modes=['p1','p2','p3','lane-shapes','interleave-probe','legacy'])

def test_perf_keep():
    """Z22 (Stage-6 fix round 3, S6H3-04): P1's --keep-perf-data moves every block's perf.data from the scratch directory
    into <output>/perf_data/ and records its retained path, size and sha256, so the files survive the scratch removal
    with or without --keep-scratch (and a job-local scratch purge); without the option they are deleted as before.
    P2 and P3 write no perf.data: the option is P1's only (2 elsewhere)."""
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=mini_fixture(td);f=fakes(td)
        def p1(tag,*extra):
            s=td/f's_{tag}';s.mkdir()
            cp=tool('perf_profile.py','p1','--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--scratch',s,'--perf',f['perf'],'--threads',4,'--exe',f['gmp'],
                    '--prof-exe',f['prof'],'--blocks','heavy_free_L8,heavy_power_L8','--no-srcline',*extra,'--output',td/tag)
            assert cp.returncode==0,(tag,cp.stdout[-1500:]+cp.stderr[-800:]);return json.loads((td/tag/'p1.json').read_text()),s
        for tag,extra,scratch_kept in (('keep',('--keep-perf-data',),False),('keepboth',('--keep-perf-data','--keep-scratch'),True)):
            r,s=p1(tag,*extra);assert r['settings']['keep_perf_data']is True and r['settings']['keep_scratch']is scratch_kept
            for b in ('heavy_free_L8','heavy_power_L8'):
                kd=r['blocks'][b]['perf_data'];p=td/tag/'perf_data'/f'{b}.perf.data'
                assert kd['retained']and kd['relative_path']==f'perf_data/{b}.perf.data'and Path(kd['path'])==p.resolve()and p.read_text()=='FAKE PERF DATA\n',(tag,kd)
                assert kd['bytes']==p.stat().st_size and kd['sha256']==bk.digest(p)
            left=sorted(x.name for x in s.iterdir());assert (len(left)==1)is scratch_kept,(tag,left)
            if scratch_kept:assert not list((s/left[0]).glob('*.perf.data'))and (s/left[0]/'graphs').is_dir()  # moved, not copied
        r,s=p1('nokeep');assert not (td/'nokeep/perf_data').exists()and all('perf_data'not in r['blocks'][b]for b in r['blocks'])and not any(s.iterdir())
        for mode,extra in (('p2',['--blocks','nopromo_free_L8']),('p3',['--blocks','random_power_L8'])):
            cp=tool('perf_profile.py',mode,'--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--scratch',td,'--perf',f['perf'],*extra,'--keep-perf-data','--output',td/f'{mode}k')
            assert cp.returncode==2 and '--keep-perf-data'in cp.stderr and not (td/f'{mode}k').exists(),(mode,cp.returncode,cp.stderr[-400:])
    # a perf.data that cannot be moved (quota, I/O error) is an error, and the scratch directory holding it is kept
    import perf_profile as pp
    from types import SimpleNamespace
    from unittest import mock
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);ctx=SimpleNamespace(out=td/'o',scratch=td/'s');ctx.out.mkdir();ctx.scratch.mkdir();(ctx.scratch/'b1.perf.data').write_text('x')
        res={'b1':{},'b2':{}};errs=[]
        with mock.patch.object(pp.shutil,'move',side_effect=OSError('Disk quota exceeded')):kept=pp.keep_perf_data(ctx,['b1','b2'],res,errs)
        assert kept is False and errs==['b1 perf.data not retained']and (ctx.scratch/'b1.perf.data').is_file(),(kept,errs)
        assert not res['b1']['perf_data']['retained']and 'quota'in res['b1']['perf_data']['reason']and not res['b2']['perf_data']['retained'],res
        pp.cleanup(ctx,SimpleNamespace(keep_scratch=False),not kept);assert (ctx.scratch/'b1.perf.data').is_file()
        pp.cleanup(ctx,SimpleNamespace(keep_scratch=False));assert not ctx.scratch.exists()
    ok('perf_profile_keep_perf_data_retained_without_keep_scratch')

TESTS=(('shapes',test_shapes),('lpt_blocks',test_lpt_blocks),('perf_report',test_perf_report),('perf_stat',test_perf_stat),('parsers',test_parsers),
       ('ratio',test_ratio),('fixtures',test_fixtures),('determinism',test_determinism),('refusals',test_refusals),('admission',test_admission),
       ('scripts',test_scripts),('order7',test_order7),('e2e_lanes',test_e2e_lanes),('e2e_probe',test_e2e_probe),('e2e_perf',test_e2e_perf),('perf_team',test_perf_team),
       ('perf_binding',test_perf_binding),('perf_expect',test_perf_expect),('perf_keep',test_perf_keep),('p3_binding',test_p3_binding),('tool_cleanup',test_tool_cleanup))
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
    rec={'schema':'c8-d2-test-profiling-1','requested':sel,'executed':[r['test']for r in RESULTS],'results':RESULTS,'passed':not failed and bool(RESULTS),'failed':failed}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({'passed':rec['passed'],'tests':len(RESULTS),'failed':failed}));return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
