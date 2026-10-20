#!/usr/bin/env python3
"""Stage-4b tools (PLAN "Performance plan", default-path optimizations; A-PERF-2, A-RPL-4/6/8): Mac-runnable tests of the
pure logic. No native build and no measurement: the worker is tests/fake_worker.py, the CPU topology --fake-topology
with --no-pin, the inputs tests/fixtures/inputs_mini.

  sample        validate.l8self_sample: 1,600 free + 400 power L8 kernels (the 100 costliest per sector included), sorted,
                deterministic, every kernel in the committed cost model; smaller sizes for smoke runs; --parts none
                without --l8self refused
  inputs_verified  tools/opt_speed.py verifies the inputs against their manifest first (prepare_inputs.verify, S4-005):
                the verified manifest, inventory and gamma hashes recorded; a changed gamma or inventory refused (65)
                before anything is created
  speed         tools/opt_speed.py end to end with fake workers on inputs_mini: two binaries in two lane shapes, the
                interleaved order, medians, steps and the 3% bar, rows identical; a binary whose rows differ fails (exit 1);
                a failing worker is recorded and fails
  lanes_plan    opt_speed.build_lanes: both replicates of a kernel in one block, uids independent of the shape, blocks of
                at most block_tasks tasks, free before power, every task once
  compare       tests/record_compare.py --kind forced_tiers: equal records (timing and builds ignored), a changed
                maximum or count found
  script        slurm/native_job.sh's optsmoke and opt modes: syntax, the exact gates before the speed step, the speed
                only after the gates passed, the stored candidate never overwritten, the refusals of bad C8_OPT_* values
--only NAME,... runs the named tests.
Usage: python3 -B tests/test_opt.py [--output FILE] [--only NAME,...]"""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,flush=True)

def write_exe(path:Path,body:str)->Path:
    path.write_text(f'#!{PY} -S\n'+body);path.chmod(0o755);return path

def test_sample():
    import validate as V
    inv=json.loads((ROOT/'inputs/inventory.json').read_text());s=V.l8self_sample(inv);t=V.l8self_sample(inv)
    assert s==t and {k:len(v)for k,v in s.items()}=={'free':1600,'power':400},{k:len(v)for k,v in s.items()}
    for sec,ids in s.items():
        assert ids==sorted(set(ids)),sec
        heavy=[r['id']for r in sorted(inv[sec]['8'],key=lambda r:-r['cost'])[:100]];assert set(heavy)<=set(ids),sec
    spp=json.loads((ROOT/'cost_models/gmp_expanse_epyc7742_c8.json').read_text())['seconds_per_point']
    assert all(f'a:{sec}:8:{g}'in spp for sec,ids in s.items()for g in ids)
    small=V.l8self_sample(inv,{'heavy':2,'free':6,'power':4});assert {k:len(v)for k,v in small.items()}=={'free':8,'power':6}
    assert V.L8SELF_DRAW==81113 and V.L8SELF_NET_SEED==81121 and V.L8SELF_POINTS==512
    cp=subprocess.run([PY,'-B',str(ROOT/'tests/validate.py'),'--parts','none'],capture_output=True,text=True);assert cp.returncode==2 and 'no part selected'in cp.stderr,cp.stderr
    cp=subprocess.run([PY,'-B',str(ROOT/'tests/validate.py'),'--parts','nonsense'],capture_output=True,text=True);assert cp.returncode==2 and 'unknown parts'in cp.stderr,cp.stderr
    ok('l8self_sample',free=1600,power=400)

def mini(td:Path)->tuple[Path,Path]:
    """inputs_mini (8 L8 graphs per sector) materialized as a C8_INPUTS directory (prepare_inputs.materialize_mini: its
    own files copied, the package files it pins, gamma_d3_8.txt among them, hard-linked; so prepare_inputs.verify
    accepts it, S4-005), and a synthetic cost model over its kernels."""
    import prepare_inputs as pi
    d=pi.materialize_mini(td/'inputs_mini');inv=json.loads((d/'inventory.json').read_text());spp={f'{c}:{s}:{L}:{r["id"]}':1e-6*(1+r['id']%7)for c in 'ab'for s in('free','power')for L,rows in inv[s].items()for r in rows}
    (td/'cm.json').write_text(json.dumps({'executable_sha256':'fake','seconds_per_point':spp}));return d,td/'cm.json'

def speed(td:Path,inputs:Path,cm:Path,exes:dict,out:str,extra=(),env=None)->tuple[subprocess.CompletedProcess,dict|None]:
    cmd=[PY,'-B',str(ROOT/'tools/opt_speed.py'),*[f'--exe={k}={v}'for k,v in exes.items()],'--inputs',str(inputs),'--cost-model',str(cm),
         '--sample-sizes','2,3,3','--fake-topology','1x2x2','--no-pin','--shape','2x2','--output',str(td/out),'--scratch',str(td/'scratch'),*extra]
    cp=subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,**(env or{})},timeout=900)
    f=td/out/'opt_speed.json';return cp,(json.loads(f.read_text())if f.exists()else None)

def test_speed():
    fw=(ROOT/'tests/fake_worker.py').read_text()
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);I,cm=mini(td);a=write_exe(td/'c8d3_gmp_a',fw);b=write_exe(td/'c8d3_gmp_b',fw)
        cp,r=speed(td,I,cm,{'B0':a,'CAND':b},'ok',('--shape-of','B0=1x4','--step','R=B0:CAND','--repeats','2'))
        assert cp.returncode==0,cp.stdout[-1500:]+cp.stderr[-1500:]
        assert r['schema']=='c8-d3-stage4b-opt-speed-1'and r['smoke']and r['status']=='passed'and r['rows_identical']
        assert r['shapes']=={'B0':'1x4','CAND':'2x2'}and set(r['lane_plans'])=={'1x4','2x2'}and r['workload']['graphs']=={'free':5,'power':5}
        assert [(x['binary'],x['repeat'])for x in r['runs']]==[('B0',0),('CAND',0),('CAND',1),('B0',1)],[(x['binary'],x['repeat'])for x in r['runs']]
        assert all(x['rows']==20 for x in r['runs'])and {x['shape']for x in r['runs']if x['binary']=='B0'}=={'1x4'}
        s=r['speedups']['R'];m=r['medians']['lane_thread_seconds'];assert abs(s['lane_thread_seconds']-m['B0']/m['CAND'])<1e-12 and s['meets_3pct_bar']==(s['lane_thread_seconds']>=1.03)
        assert r['cumulative_vs_first']['B0']==1.0 and set(r['speedups']['R'])>={'free_lane_thread_seconds','power_lane_thread_seconds','node_wall_seconds'}
        # a binary with other rows: the digests differ -> exit 1, recorded
        c=write_exe(td/'c8d3_gmp_c','import os,sys\nos.environ["C8_FAKE_INTEGRAND"]="const"\nos.execv(sys.executable,[sys.executable,"-S",%r,*sys.argv[1:]])\n'%str(ROOT/'tests/fake_worker.py'))
        cp,r=speed(td,I,cm,{'B0':a,'CAND':c},'diff',('--step','R=B0:CAND','--repeats','1'))
        assert cp.returncode==1 and r['status']=='failed'and r['rows_identical']is False,cp.stdout[-800:]
        # a failing worker: recorded, exit != 0
        cp,r=speed(td,I,cm,{'B0':a},'fail',('--repeats','1'),env={'C8_FAKE_FAIL':'1'})
        assert cp.returncode!=0 and r['status']=='failed'and 'exit'in r.get('error',''),r and r.get('error')
        # refusals before any run: an unknown step binary, a wrong --expect, a missing executable
        for args,why in ((['--step','R=B0:X'],'FROM:TO'),(['--expect','B0=00ff'],'does not start'),):
            cp,_=speed(td,I,cm,{'B0':a},f'ref{len(why)}',args);assert cp.returncode!=0 and why in cp.stderr,cp.stderr[-500:]
        cp,_=speed(td,I,cm,{'B0':td/'missing'},'missing');assert cp.returncode!=0 and 'missing'in cp.stderr
    ok('opt_speed_fake_workers',runs=4)

def test_inputs_verified():
    """S4-005: opt_speed verifies the inputs against their manifest (prepare_inputs.verify) before any run and records the
    verified hashes; a gamma or inventory changed to other valid-looking bytes is refused (65) before anything is
    created. The changed file replaces the hard link (materialize_mini links the package's gamma), never writes through."""
    from common import digest
    fw=(ROOT/'tests/fake_worker.py').read_text()
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);I,cm=mini(td);a=write_exe(td/'c8d3_gmp_a',fw)
        cp,r=speed(td,I,cm,{'B0':a},'good',('--repeats','1'))
        assert cp.returncode==0 and r['status']=='passed'and r['smoke'],cp.stderr[-800:]
        v=r['inputs_verified'];assert v['manifest_sha256']==digest(I/'manifest.json')and v['inventory_sha256']==digest(I/'inventory.json')and v['gamma_sha256']==digest(I/'gamma_d3_8.txt'),v
        assert v['skipped']==[]and any(x.startswith('test_inputs')for x in v['test_only_reasons']),v
        def bump(b:bytes)->bytes:   # one digit after the first decimal point +1 (mod 10): another finite value
            i=b.index(b'.')+1;return b[:i]+str((int(chr(b[i]))+1)%10).encode()+b[i+1:]
        for rel,edit in (('gamma_d3_8.txt',bump),('inventory.json',lambda b:b.replace(b'"wa": ',b'"wa":  ',1))):
            p=I/rel;orig=p.read_bytes();new=edit(orig);assert new!=orig,rel
            p.unlink();p.write_bytes(new)
            try:cp,r=speed(td,I,cm,{'B0':a},f'bad_{rel}',('--repeats','1'))
            finally:p.unlink();p.write_bytes(orig)
            assert cp.returncode==65 and 'Checksum mismatch'in cp.stderr and rel in cp.stderr and r is None and not (td/f'bad_{rel}').exists(),(rel,cp.returncode,cp.stderr[-600:])
        assert digest(ROOT/'inputs/gamma_d3_8.txt')==json.loads((ROOT/'inputs/manifest.json').read_text())['sha256']['gamma_d3_8.txt']
    ok('opt_speed_inputs_verified',refused=['gamma_d3_8.txt','inventory.json'])

def test_lanes_plan():
    import opt_speed as O
    sample={'free':[1,2,3,4,5,6,7],'power':[10,11,12]};spp={f'a:{s}:8:{g}':float(g)for s,ids in sample.items()for g in ids}
    u=O.uids(sample);assert len(u)==2*10 and len(set(u.values()))==20
    for n,t,bt in ((2,8,None),(4,2,4),(1,16,6)):
        plan,pred=O.build_lanes({'seconds_per_point':spp},sample,n,t,bt);B=bt or max(16*t,256)
        rows=[r for lane in plan for _,blk in lane for r in blk];assert sorted(r[0]for r in rows)==list(range(20)),(n,t)
        for lane in plan:
            secs=[s for s,_ in lane];assert secs==sorted(secs,key=lambda x:x!='free'),secs
            for s,blk in lane:
                assert len(blk)<=B and all(r[3:]==(0,512,512)for r in blk)
                gs={r[2]for r in blk};assert all(sum(1 for r in blk if r[2]==g)==2 for g in gs)
                assert all(u[(s,r[1],r[2])]==r[0]for r in blk)
        assert abs(sum(pred)-sum(spp.values())*1024)<1e-6
    try:O.build_lanes({'seconds_per_point':{}},sample,2,8,None);raise AssertionError('missing cost model keys accepted')
    except SystemExit as e:assert 'no entry'in str(e)
    ok('opt_speed_lane_plan')

def test_compare():
    import record_compare as RC
    rec=json.loads((ROOT/'benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/val3/forced_tiers.json').read_text())
    new=json.loads(json.dumps(rec));new['wall_seconds']=1;new['host']={'node':'x'};new['build']={'command':['other']}
    for r in new['results']:
        for x in r['rounds']:x['seconds']=0.5
    assert RC.compare('forced_tiers',new,rec)==[]
    bad=json.loads(json.dumps(new));bad['results'][2]['quad']['max_scaled_accepted']='1.0e-30';d=RC.compare('forced_tiers',bad,rec)
    assert len(d)==1 and 'max_scaled_accepted'in d[0],d
    bad=json.loads(json.dumps(new));bad['results'][0]['rounds'][0]['points']+=1;assert RC.compare('forced_tiers',bad,rec)
    # S1-03: the per-condition counts and full-precision maxima of a new record are no difference against a Stage-3 record
    # made before them; compared when both hold them; still a difference when only the Stage-3 side holds them
    s13=json.loads(json.dumps(new))
    for r in s13['results']:
        r['breach_counts']=dict.fromkeys(('ld_scaled','quad_scaled','mp_scaled','quad_conversion','mp_conversion'),0)
        for t in('ld','quad','mp'):r[t]['full_precision']={'max_scaled_accepted':'1.0000000000000000e-30'}
    assert RC.compare('forced_tiers',s13,rec)==[]
    other=json.loads(json.dumps(s13));other['results'][1]['breach_counts']['quad_scaled']=1
    d=RC.compare('forced_tiers',other,s13);assert len(d)==1 and 'breach_counts/quad_scaled'in d[0],d
    assert RC.compare('forced_tiers',rec,s13)
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'n.json';p.write_text(json.dumps(new));cp=subprocess.run([PY,'-B',str(ROOT/'tests/record_compare.py'),'--kind','forced_tiers',str(p),
            str(ROOT/'benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/val3/forced_tiers.json')],capture_output=True,text=True);assert cp.returncode==0,cp.stdout[-500:]
    ok('record_compare_forced_tiers',s1_03_added_fields=sorted(RC.ADDED['forced_tiers']))

def test_script():
    s=(ROOT/'slurm/native_job.sh').read_text()
    assert subprocess.run(['bash','-n',str(ROOT/'slurm/native_job.sh')]).returncode==0
    body=s[s.index('optsmoke|opt)'):s.index('val3a)\n  step make_native')]
    for k in ('make baseline','baseline_identity','"$BASE_SHA"','prev_identity','prev_build','baseline_record'):assert k in body,k
    # B0 is this site's c8-stage3 baseline (tools/baseline.py sha; Expanse 24adff54..., symmetry's own record, A1)
    pre=s[:s.index('case "$C8_JOB" in\nval1)')];assert 'tools/baseline.py sha c8d3_gmp'in pre and 'B8="${BASE_SHA:0:8}"'in pre
    g=body.index('exact gates');sp=body.index('tools/opt_speed.py "${SPEED[@]}"');st=body.index('store_candidate')
    assert g<sp<st and body.index('an exact gate failed: no speed measurement')<sp and 'never overwritten'in body
    for gate in ('validate.py --full','--l8self bin/baseline','tests/first_error.py','same_binary','tests/thread_identity.py','tests/inspect_check.py',
                 'tests/quad_differential.py','tests/forced_tiers.py','tests/record_compare.py --kind forced_tiers'):assert gate in body,gate
    assert '--expect B0="$B8"'in body and '24adff54'not in body[body.index('optsmoke|opt)\n'):] and 'tools/baseline.py val3'in body and '--step "$C8_OPT_STEP=PREV:CAND"'in body and '--step cumulative=B0:CAND'in body
    v=body.index('C8_OPT_VARIANT_OPTFLAGS');assert v<body.index('snapshot after_gates')<sp and 'variant_validate_full'in body and 'variant_l8self'in body and '--step "7=CAND:VAR"'in body
    assert 'EV="$C8_ROOT/evidence/$SHA12/opt_$C8_OPT_STEP"'in s
    env={**{k:v for k,v in os.environ.items()if not k.startswith('C8_')},'SLURM_JOB_ID':'1'}
    with tempfile.TemporaryDirectory()as td:
        envf=Path(td)/'env.sh';envf.write_text('export C8_ROOT=%s C8_STORE=%s/store\n'%(td,td))
        def run(**kw):return subprocess.run(['bash',str(ROOT/'slurm/native_job.sh')],capture_output=True,text=True,env={**env,'C8_ENV_SETUP':str(envf),'C8_PACKAGE':f'{td}/pkg/0123456789ab',**kw})
        for kw,why in (({'C8_JOB':'opt'},'C8_OPT_STEP'),({'C8_JOB':'opt','C8_OPT_STEP':'R9'},'C8_OPT_STEP'),
                       ({'C8_JOB':'opt','C8_OPT_STEP':'R5a','C8_OPT_PREV':'xyz'},'C8_OPT_PREV'),
                       ({'C8_JOB':'opt','C8_OPT_STEP':'R5a','C8_OPT_GATES':'validate_full,bogus'},'C8_OPT_GATES'),
                       ({'C8_JOB':'opt','C8_OPT_STEP':'R5b','C8_OPT_GATES':'same_binary'},'needs C8_OPT_PREV'),
                       ({'C8_JOB':'opt','C8_OPT_STEP':'R5b','C8_OPT_SHAPES':'B1=8x16'},'C8_OPT_SHAPES'),
                       ({'C8_JOB':'opt','C8_OPT_STEP':'4','C8_OPT_PREV_PKG':'0123456789ab'},'C8_OPT_PREV_PKG'),
                       ({'C8_JOB':'opt','C8_OPT_STEP':'4','C8_OPT_PREV_PKG':'zz'},'C8_OPT_PREV_PKG'),
                       ({'C8_JOB':'opt','C8_OPT_STEP':'final','C8_OPT_VARIANT_OPTFLAGS':'-O3; rm -rf /'},'C8_OPT_VARIANT_OPTFLAGS')):
            cp=run(**kw);assert cp.returncode==64 and why in cp.stderr,(kw,cp.returncode,cp.stderr[-300:])
    ok('native_job_opt_modes')

TESTS=(('sample',test_sample),('speed',test_speed),('inputs_verified',test_inputs_verified),('lanes_plan',test_lanes_plan),('compare',test_compare),('script',test_script))
NAMES_T=[n for n,_ in TESTS]

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--only',help='NAME,... of: '+', '.join(NAMES_T))
    a=ap.parse_args();sel=NAMES_T
    if a.only is not None:
        sel=[s.strip()for s in a.only.split(',')if s.strip()];bad=[s for s in sel if s not in NAMES_T]
        if not sel or bad:ap.error(f'--only: unknown test(s) {bad}'if bad else'--only: no test named')
    os.environ.pop('C8_FAKE_FAIL',None);failed=[]
    for name,fn in TESTS:
        if name not in sel:continue
        try:fn()
        except Exception as e:  # report every failure, then fail
            import traceback;traceback.print_exc();failed.append(name);RESULTS.append({'test':name,'status':'failed','error':f'{type(e).__name__}: {e}'[:2000]});print('FAIL',name,flush=True)
    rec={'schema':'c8-d3-test-opt-1','requested':sel,'executed':[r['test']for r in RESULTS],'results':RESULTS,'passed':not failed and bool(RESULTS),'failed':failed}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({'passed':rec['passed'],'tests':len(RESULTS),'failed':failed}));return 0 if rec['passed']else 1

if __name__=='__main__':sys.exit(main())
