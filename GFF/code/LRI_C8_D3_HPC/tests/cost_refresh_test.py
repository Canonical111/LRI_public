#!/usr/bin/env python3
"""The calibration refresh (PLAN D.14, D.5, HD11, R03; A-ORC-3) with fake binaries X -> Y -> Z and the fake integrator,
in a scratch package (tests/c8pkg.py). Mac; about two minutes.

  * X: tools/sweep.py without --refresh is the first sweep (cost_sweep, bootstrap basis) and gives M_X (executable
    sha256 of X, scheduled_with bootstrap with null shas);
  * --choose-only against M_X: X -> the measured basis (a re-measurement); Y (another sha256) -> the prior-model basis;
    M_X with another CPU model, another mp_check mode without an overhead factor, unreadable or missing keys, or
    --refresh-bootstrap -> the bootstrap basis, naming the reason;
  * the prior-model plan (Y): role cost_refresh, cost_basis prior_model, prior_cost_model.json at its pin, the manifest
    records both executables and F = 2; its refusals: role campaign, a non-test plan, another allocation (--points 4096,
    --replicates 4), --design or --graphs, F < 1, a prior model of this very executable, a prior model whose CPU model
    differs, and the validation role;
  * sweep.py's fit check refuses (65) when the factor-inflated wall exceeds half of the remaining time, naming both
    numbers, before any index ran (no checkpoint);
  * the full refresh Y (C8_FAKE_SPP 3x X's): M_Y has Y's sha256, scheduled_with {prior_model, sha(M_X), sha(X), F 2},
    seconds per point from its own checkpoints (3x M_X's, independent of the scheduling model), refresh_report.json
    with fresh/prev 3 per (campaign, sector, L) and every task counted over its planned seconds (3 > F = 2; reported, not a gate); make_cost_model opens no
    prior_cost_model.json (spy); S3-013 (D.5): on the prior-model sweep, design_fallback.py report (with M_Y supplied
    explicitly) and design_adapter.py view succeed and pilot_report.py subset-check refuses it (64), none opening its
    prior_cost_model.json (spy); S3-R2-006: design_fallback.py report WITHOUT --eta-node (eta_node from
    tools/accounting.py, on a fake Slurm whose sacct shows one lane job of the sweep) opens no prior_cost_model.json
    (spy), and succeeds also on a copy of the sweep whose prior_cost_model.json was removed (before S3-R2-006 the
    accounting's verify_base opened it, and failed without it);
  * HD11 afterwards: a role-campaign plan with M_X under Y refuses naming the executable; with M_Y it is accepted;
    tools/cost_identity.py: check --model M_Y --exe Y passes, --model M_X --exe Y fails printing both sha256s; check RUN
    passes on the M_Y plan and fails on the prior-model plan;
  * Z with --refresh M_Y --refresh-bootstrap: the bootstrap basis (role cost_refresh), its fresh model scheduled_with
    bootstrap and Z's sha256.
  * Stage 5: cost_identity.py check --host-cpu --mp-check on (HD11's three fields, as `plan` checks them on this host)
    passes for M_Y and fails, naming both values, for a copy measured on another CPU or with mp_check off; without the
    flags the record's keys are unchanged; cost_identity.py data-only (J-BLD) accepts cost_models/, benchmarks/ and the
    carry set, where designs/forbidden_seeds.json may only grow (the base's entries an exact prefix; a dropped, changed or
    reordered entry, a removed file, a symlink or a non-log refuses, the same verdict as seeds.py mirror), skips bin/,
    bin.bld_failed_*/, the L8 pack links and caches, and fails naming every other changed, added or removed path (2 on a
    missing base); cost_summary.py labels its busy core-hours with the model's own CPU (EPYC
    7742 as before, EPYC 7543, or the whole name) with every number unchanged.
Usage: python3 -B tests/cost_refresh_test.py [--keep]"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg  # noqa: E402
from c8pkg import manifest  # noqa: E402
from unit_orchestration import must,spy,opened  # noqa: E402
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
def sha(p:Path)->str:return hashlib.sha256(Path(p).read_bytes()).hexdigest()
SEED=881100231

def install(pkg:Path,tag:str)->str:
    c8pkg.install_fake_bin(pkg)
    for exe in ('c8d3_gmp','c8d3_decimal'):
        f=pkg/'bin'/exe;f.write_text(f.read_text()+f'\n# fake binary {tag}\n');f.chmod(0o755)
    return sha(pkg/'bin/c8d3_gmp')

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--keep',action='store_true');a=ap.parse_args()
    td=Path(tempfile.mkdtemp(prefix='c8d3_refresh_'))
    try:
        pkg=c8pkg.make(td);scr=td/'scratch';scr.mkdir();seeds=td/'seeds.json';seeds.write_text(json.dumps({'schema':'c8-d3-seeds-1','seeds':[]}))
        T=lambda script,*args,check=True,**x:c8pkg.tool(pkg,script,*args,check=check,**{'C8_LANES':'2','C8_LANE_SECONDS':'3600',**x})
        sweep=lambda run,*args,check=True,**x:T('sweep.py',run,'--seed',SEED,'--scratch',scr,'--threads',2,*args,check=check,**x)
        # X: the first sweep
        sx=install(pkg,'X');cp=sweep(td/'sweepX','--output',td/'M_X.json',C8_FAKE_SPP='0.001');MX=json.loads((td/'M_X.json').read_text())
        assert MX['executable_sha256']==sx and MX['scheduled_with']=={'basis':'bootstrap','model_sha256':None,'executable_sha256':None}and manifest(td/'sweepX')['plan_role']=='cost_sweep'
        first=json.loads(cp.stdout.splitlines()[0]);assert first['role']=='cost_sweep'and first['basis']=='bootstrap'
        choose=lambda prev,*x:json.loads(T('sweep.py',td/'none','--seed',SEED,'--refresh',prev,'--choose-only',*x).stdout.splitlines()[0])
        c=choose(td/'M_X.json');assert c['basis']=='measured'and c['role']=='cost_refresh',c
        sy=install(pkg,'Y');assert sy!=sx
        c=choose(td/'M_X.json');assert c['basis']=='prior_model'and c['previous_executable_sha256']==sx and c['executable_sha256']==sy,c
        variants={'cpu':lambda m:m.__setitem__('cpu_model','AMD EPYC 9999 elsewhere'),'mp':lambda m:(m.__setitem__('mp_check','off'),m.pop('mp_check_overhead',None)),
                  'keys':lambda m:m.pop('seconds_per_point')}
        for name,f in variants.items():
            m=json.loads((td/'M_X.json').read_text());f(m);p=td/f'M_X_{name}.json';p.write_text(json.dumps(m));c=choose(p)
            assert c['basis']=='bootstrap'and c['role']=='cost_refresh'and 'does not qualify'in c['why'],(name,c)
        c=choose(td/'M_X.json','--refresh-bootstrap');assert c['basis']=='bootstrap'and c['why']=='--refresh-bootstrap'
        ok('D.14 basis choice: the first sweep is cost_sweep on the bootstrap basis (M_X: X\'s sha256, scheduled_with bootstrap); against M_X the same '
           'executable gives the measured basis, Y the prior-model basis, and another CPU model, another mp_check mode, missing keys or '
           '--refresh-bootstrap the bootstrap basis with the reason')
        # the prior-model plan and its refusals
        base=['--pilot','--points',512,'--replicates',2,'--test-graphs','all','--threads',2,'--mp-check','on']
        plan=lambda d,*x,check=True:T('production.py','plan',d,'--seed',SEED,*x,'--scratch',scr,check=check,SLURM_JOB_ID='9999')
        d=td/'prior_plan';plan(d,*base,'--plan-role','cost_refresh','--prior-cost-model',td/'M_X.json')
        m=manifest(d);assert m['plan_role']=='cost_refresh'and m['cost_basis']=='prior_model'and m['prior_factor']==2.0 and m['executable_sha256']==sy
        assert m['prior_model']['executable_sha256']==sx and m['prior_model']['sha256']==sha(td/'M_X.json')==sha(d/'prior_cost_model.json')and not (d/'cost_model.json').exists()
        bad=[('campaign',[*base,'--plan-role','campaign','--prior-cost-model',td/'M_X.json'],'cost_refresh only'),
             ('nontest',['--pilot','--points',4096,'--replicates',2,'--threads',2,'--forbid-seeds-from',seeds,'--plan-role','cost_refresh','--prior-cost-model',td/'M_X.json'],'test-only'),
             ('points',['--pilot','--points',4096,'--replicates',2,'--test-graphs','all','--threads',2,'--plan-role','cost_refresh','--prior-cost-model',td/'M_X.json'],'sweep\'s allocation'),
             ('reps',['--pilot','--points',512,'--replicates',4,'--test-graphs','all','--threads',2,'--plan-role','cost_refresh','--prior-cost-model',td/'M_X.json'],'sweep\'s allocation'),
             ('factor',[*base,'--plan-role','cost_refresh','--prior-cost-model',td/'M_X.json','--prior-factor',0.5],'below 1'),
             ('cpu',[*base,'--plan-role','cost_refresh','--prior-cost-model',td/'M_X_cpu.json'],'does not qualify'),
             ('validation',[*base,'--plan-role','validation','--prior-cost-model',td/'M_X.json'],'refuses --prior-cost-model'),
             ('two',[*base,'--plan-role','cost_refresh','--prior-cost-model',td/'M_X.json','--bootstrap-chunk',512,'--shards',2],'one cost basis')]
        for name,args,why in bad:must(plan(td/f'pb_{name}',*args,check=False),1,why);assert not (td/f'pb_{name}').exists(),name
        sy_m=json.loads((td/'M_X.json').read_text());sy_m['executable_sha256']=sy;(td/'M_same.json').write_text(json.dumps(sy_m))
        must(plan(td/'pb_same',*base,'--plan-role','cost_refresh','--prior-cost-model',td/'M_same.json',check=False),1,'measured on this executable')
        ok('D.5 prior-model plan: role cost_refresh, basis prior_model, F = 2, both executables and prior_cost_model.json at its pin; refused under role '
           'campaign, in a non-test plan, with another allocation (points 4096, replicates 4), F < 1, a prior model of this executable or of another '
           'CPU model, the validation role and two bases at once')
        # the fit check: refuses before any index
        cp=sweep(td/'fit','--refresh',td/'M_X.json','--output',td/'M_fit.json',check=False,C8_LANE_SECONDS='1')
        must(cp,65,'fit check','exceeds half of the job\'s remaining 1 s');assert not list((td/'fit').glob('groups/*/checkpoints/*.json'))and not (td/'M_fit.json').exists()
        # the full refresh with Y at 3x the seconds per point
        cp=sweep(td/'sweepY','--refresh',td/'M_X.json','--output',td/'M_Y.json','--report',td/'R_Y.json',C8_FAKE_SPP='0.003')
        MY=json.loads((td/'M_Y.json').read_text());R=json.loads((td/'R_Y.json').read_text())
        assert MY['executable_sha256']==sy and MY['scheduled_with']=={'basis':'prior_model','model_sha256':sha(td/'M_X.json'),'executable_sha256':sx,'factor':2.0}
        assert all(abs(v/MX['seconds_per_point'][k]-3)<1e-9 for k,v in MY['seconds_per_point'].items()),'the fresh model is not its own measurement'
        assert R['previous_executable_sha256']==sx and R['fresh_executable_sha256']==sy and all(abs(r['fresh_over_prev']-3)<1e-9 for r in R['rows'].values())
        assert all(r['tasks_over_planned_seconds']==r['tasks']>0 for r in R['rows'].values()) and all(r['max_task_seconds']<=r['max_task_limit']for r in R['rows'].values())
        cps,ev=spy(pkg,td,'make_cost_model.py',td/'sweepY',td/'M_Y_spy.json');assert cps.returncode==0,cps.stderr
        assert not [p for p in opened(ev,False)if p.endswith('prior_cost_model.json')or p.endswith('bootstrap_proxy.json')]
        assert json.loads((td/'M_Y_spy.json').read_text())['seconds_per_point']==MY['seconds_per_point']
        # S3-013 (D.5 "Never a cost"): the design tools and pilot_report never open the campaign's prior_cost_model.json
        for script,args,rc in (('design_fallback.py',['report','--pilot',td/'sweepY','--cost-model',td/'M_Y.json','--eta-node',0.9,'--json',td/'df_Y.json'],0),
                               ('design_adapter.py',['view',td/'sweepY','--out',td/'view_Y'],0),('pilot_report.py',['subset-check',td/'sweepY'],64)):
            cps,ev=spy(pkg,td,script,*args);assert cps.returncode==rc,(script,cps.returncode,cps.stderr[-1200:])
            bad=[q for q in opened(ev,False)if q.endswith('prior_cost_model.json')];assert not bad and opened(ev,False),(script,bad)
        assert json.loads((td/'df_Y.json').read_text())['label']=='fallback'and not (td/'view_Y/prior_cost_model.json').exists()
        # S3-R2-006 (D.5): the accounting path (design_fallback report without --eta-node: eta_node -> accounting.account ->
        # verify_base) opens no scheduling copy; a fake Slurm's sacct shows one lane job of each campaign (its name carries the
        # campaign's C), so the accounting gives an eta; a copy without prior_cost_model.json is read as well
        import ledger
        site=c8pkg.SlurmSite(td,'acct');noprior=td/'sweepY_noprior';shutil.copytree(td/'sweepY',noprior);(noprior/'prior_cost_model.json').unlink()
        real=sorted(ledger.host_sites({k:v for k,v in os.environ.items()if k!='SLURM_CLUSTER_NAME'}))   # the fake Slurm needs C8_SITE=fake, refused on a real site
        if real:print(f'NOTE S3-R2-006 accounting-path spy skipped on a real site ({",".join(real)}): C8_SITE=fake is refused there; it runs on the Mac')
        for run in(()if real else(td/'sweepY',noprior)):
            site.fake.add_job(f'c8d3-lane-{ledger.dir_sha12(run)}-{"e"*12}',state='COMPLETED',partition='shared',cpus=4,mem='12G',elapsed=100,start_ago=150,end_ago=50,submit_ago=200)
            out=td/f'df_acct_{run.name}.json'
            cps,ev=spy(pkg,td,'design_fallback.py','report','--pilot',run,'--cost-model',td/'M_Y.json','--json',out,**site.env())
            assert cps.returncode==0,(run.name,cps.returncode,cps.stderr[-1200:])
            bad=[q for q in opened(ev,False)if q.endswith(('prior_cost_model.json','synthetic_cost_model.json','bootstrap_proxy.json'))];assert not bad,(run.name,bad)
            assert json.loads(out.read_text())['eta']['source'].startswith('tools/accounting.py'),json.loads(out.read_text())['eta']
        ok('D.14 refresh X -> Y: M_Y carries Y\'s sha256 and scheduled_with {prior_model, sha(M_X), sha(X), F 2}; its seconds per point are its own '
           'measurement (3x M_X\'s, not the scheduling model\'s), refresh_report.json gives fresh/prev 3 per (campaign, sector, L), the largest task '
           'against the limit and every task over its planned seconds (3x measured > F = 2: reported, not a gate); make_cost_model opens no prior_cost_model.json (spy); '
           'S3-013: design_fallback report (M_Y explicit), design_adapter view and pilot_report subset-check (64) on the prior-model sweep open no prior_cost_model.json (spy); '
           'S3-R2-006: design_fallback report without --eta-node (eta from tools/accounting.py on a fake sacct) opens none either and reads a copy '
           'without prior_cost_model.json; the fit '
           'check refuses with C8_LANE_SECONDS = 1 (65, both numbers) before any checkpoint')
        # HD11 afterwards and cost_identity
        tp=['--pilot','--test-only','--replicates',2,'--threads',2]
        must(plan(td/'hd_old',*tp,'--cost-model',td/'M_X.json',check=False),1,'executable');assert not (td/'hd_old').exists()
        plan(td/'hd_new',*tp,'--cost-model',td/'M_Y.json');assert manifest(td/'hd_new')['cost_basis']=='measured'
        cp=T('cost_identity.py','check','--model',td/'M_Y.json','--exe',pkg/'bin/c8d3_gmp');assert cp.returncode==0 and sy in cp.stdout
        cp=T('cost_identity.py','check','--model',td/'M_X.json','--exe',pkg/'bin/c8d3_gmp',check=False);assert cp.returncode==1 and sx in cp.stdout and sy in cp.stdout
        assert T('cost_identity.py','check',td/'hd_new').returncode==0
        must(T('cost_identity.py','check',d,check=False),1,'prior_model')
        ok('HD11 after the refresh: a role-campaign plan with M_X under Y refuses naming the executable, with M_Y it is accepted; cost_identity.py '
           'check --model M_Y --exe Y passes, M_X against Y fails printing both sha256s; check RUN passes on the M_Y plan and fails on the '
           'prior-model plan')
        # Stage 5: HD11's three fields with --host-cpu --mp-check on; the record keys without them; the negative copies
        ci=lambda model,*x:T('cost_identity.py','check','--model',model,'--exe',pkg/'bin/c8d3_gmp',*x,check=False)
        cp=ci(td/'M_Y.json','--host-cpu','--mp-check','on');r=json.loads(cp.stdout)
        assert cp.returncode==0 and r['ok']and r['cpu_model']==r['host_cpu_model']==MY['cpu_model']and r['mp_check']=='on'and r['model_mp_check']=='on'and r['problems']=={},(cp.stdout,cp.stderr)
        r0=json.loads(ci(td/'M_Y.json').stdout);assert set(r0)=={'model','model_executable_sha256','executable','executable_sha256','ok'}and r0['ok'],r0
        OTHER='AMD EPYC 7532 32-Core Processor'if MY['cpu_model']=='AMD EPYC 7543 32-Core Processor'else'AMD EPYC 7543 32-Core Processor'   # a CPU other than this host's (symmetry's nodes are 7543)
        m=json.loads((td/'M_Y.json').read_text());m['cpu_model']=OTHER;(td/'M_Y_cpu.json').write_text(json.dumps(m))
        cp=ci(td/'M_Y_cpu.json','--host-cpu','--mp-check','on');r=json.loads(cp.stdout)
        assert cp.returncode==1 and not r['ok']and r['cpu_model']==OTHER and r['host_cpu_model']==MY['cpu_model']and 'cpu_model'in r['problems'],cp.stdout
        assert ci(td/'M_Y_cpu.json').returncode==0   # without --host-cpu the CPU is not compared (sweep1 and argmax unchanged)
        m=json.loads((td/'M_Y.json').read_text());m['mp_check']='off';m.pop('mp_check_overhead',None);(td/'M_Y_mp.json').write_text(json.dumps(m))
        cp=ci(td/'M_Y_mp.json','--host-cpu','--mp-check','on');r=json.loads(cp.stdout);assert cp.returncode==1 and r['model_mp_check']=='off'and 'mp_check'in r['problems'],cp.stdout
        m['mp_check_overhead']={'on':1.07};(td/'M_Y_mp2.json').write_text(json.dumps(m))
        assert ci(td/'M_Y_mp2.json','--mp-check','on').returncode==0   # a measured overhead factor qualifies (production.identity_problems)
        assert T('cost_identity.py','check',td/'hd_new','--host-cpu',check=False).returncode==2
        ok('Stage 5 cost_identity.py check --host-cpu --mp-check on: M_Y (made on this host) passes printing both CPUs and modes; a copy measured on '
           'EPYC 7543 or with mp_check off fails (1) naming both values; an overhead factor for the mode qualifies; without the flags the record keys '
           'are unchanged and the CPU is not compared')
        # J-BLD's data-only check on two trees
        def mk(root,files):
            for rel,text in files.items():(root/rel).parent.mkdir(parents=True,exist_ok=True);(root/rel).write_text(text)
            return root
        slog=lambda *es,indent=1:json.dumps({'schema':'c8-d3-seeds-1','seeds':[{'seed':e,'source':f'run {e}','added_utc':'2026-10-05T00:00:00Z','host':'h'}for e in es]},indent=indent)+'\n'
        common={'Makefile':'all:\n','tools/x.py':'x=1\n','src/k.cpp':'int k;\n','inputs/manifest.json':'{}\n','cost_models/m.json':'{}\n','docs/HPC.md':'# hpc\n','README.md':'r\n',
                'designs/forbidden_seeds.json':slog(11,22)}
        base=mk(td/'do_base',common)
        def do(name,change):
            dd=td/f'do_{name}';shutil.copytree(base,dd);change(dd)
            cp=T('cost_identity.py','data-only','--base',base,'--data',dd,'--output',td/f'do_{name}.json',check=False)
            return cp.returncode,(json.loads((td/f'do_{name}.json').read_text())if (td/f'do_{name}.json').exists()else None)
        rc,r=do('same',lambda d:None);assert rc==0 and r['ok']and r['differences']==[],r
        rc,r=do('data',lambda d:mk(d,{'cost_models/gmp_symmetry_epyc7543_c8.json':'{"m":1}\n','cost_models/m.json':'{"x":2}\n','benchmarks/symmetry_2026-10-c8/stage5_x/sweep2_1/a.json':'{}\n'}))
        assert rc==0 and r['ok']and {(x['path'],x['class'])for x in r['differences']}=={('cost_models/gmp_symmetry_epyc7543_c8.json','cost_models'),('cost_models/m.json','cost_models'),
            ('benchmarks/symmetry_2026-10-c8/stage5_x/sweep2_1/a.json','benchmarks')},r
        rc,r=do('carry',lambda d:mk(d,{'docs/HPC.md':'# new\n','docs/new.md':'n\n','README.md':'r2\n','CHANGELOG.md':'c\n','designs/forbidden_seeds.json':slog(11,22,33),
                                       'DELIVERY_MANIFEST.json':'{}\n','SHA256SUMS':'x\n'}))
        assert rc==0 and r['ok']and all(x['class']=='carry'for x in r['differences'])and len(r['differences'])==7 and r['refused']==[],r
        assert [x['seeds_added']for x in r['differences']if x['path']=='designs/forbidden_seeds.json']==[[33]],r
        # the HD6 seed mirror only grows (tools/seeds.py mirror's rule; production.py plan's symmetry floor): the same entries
        # reformatted pass, as mirror accepts them; a dropped, changed or reordered entry, a removed file, a symlink and a
        # file that is not a seed log refuse; seeds.py mirror decides each case the same way
        seed_cases=(('seeds_same',lambda d:mk(d,{'designs/forbidden_seeds.json':slog(11,22,indent=2)}),True),
                    ('seeds_dropped',lambda d:mk(d,{'designs/forbidden_seeds.json':slog(11)}),False),
                    ('seeds_changed',lambda d:mk(d,{'designs/forbidden_seeds.json':slog(11,23,33)}),False),
                    ('seeds_reordered',lambda d:mk(d,{'designs/forbidden_seeds.json':slog(22,11,33)}),False),
                    ('seeds_not_log',lambda d:mk(d,{'designs/forbidden_seeds.json':'{}\n'}),False),
                    ('seeds_removed',lambda d:(d/'designs/forbidden_seeds.json').unlink(),False),
                    ('seeds_symlink',lambda d:((d/'designs/forbidden_seeds.json').unlink(),(d/'designs/forbidden_seeds.json').symlink_to('../cost_models/m.json')),False))
        for name,change,good in seed_cases:
            rc,r=do(name,change);x=[y for y in r['differences']if y['path']=='designs/forbidden_seeds.json']
            if good:assert rc==0 and r['ok']and r['refused']==[]and x[0]['class']=='carry'and x[0]['seeds_added']==[],(name,r)
            else:assert rc==1 and not r['ok']and [y['path']for y in r['refused']]==['designs/forbidden_seeds.json']and x[0]['class']=='refused'and r['outside']==[],(name,r)
            f=td/f'do_{name}'/'designs/forbidden_seeds.json'
            if f.is_file()and not f.is_symlink():   # the same verdict as seeds.py mirror onto a copy of the base's file
                dst=td/f'mirror_{name}.json';shutil.copy2(base/'designs/forbidden_seeds.json',dst)
                cp=T('seeds.py','mirror','--log',f,'--to',dst,check=False);assert (cp.returncode==0)==good and cp.returncode in(0,64),(name,cp.returncode,cp.stderr)
        rc,r=do('skips',lambda d:mk(d,{'bin/c8d3_gmp':'w','bin.bld_failed_9/c8d3_gmp':'w','inputs/packs/free_L8.pack':'p','inputs/packs/power_L8.pack':'p',
                                       'tools/__pycache__/x.cpython-311.pyc':'c','.pytest_cache/v/x':'c','tests/.pytest_cache/y':'c'}))
        assert rc==0 and r['ok']and r['differences']==[],r
        for name,change,path,kind in (('tool',lambda d:mk(d,{'tools/x.py':'x=2\n'}),'tools/x.py','changed'),('src',lambda d:mk(d,{'src/new.cpp':'int n;\n'}),'src/new.cpp','added'),
                                      ('makefile',lambda d:(d/'Makefile').unlink(),'Makefile','removed'),('inputs',lambda d:mk(d,{'inputs/manifest.json':'{"a":1}\n'}),'inputs/manifest.json','changed'),
                                      ('nested_bin',lambda d:mk(d,{'tools/bin/x':'1'}),'tools/bin/x','added'),('pack_l7',lambda d:mk(d,{'inputs/packs/free_L7.pack':'p'}),'inputs/packs/free_L7.pack','added')):
            rc,r=do(name,change);assert rc==1 and not r['ok']and r['outside']==[path]and any(x['path']==path and x['change']==kind and x['class']=='outside'for x in r['differences']),(name,r)
        cp=T('cost_identity.py','data-only','--base',td/'nonexistent','--data',base,check=False);assert cp.returncode==2,(cp.returncode,cp.stderr)
        cp=T('cost_identity.py','data-only','--base',base,'--data',base,'--output',td/'do_same.json',check=False);assert cp.returncode==2 and 'never overwritten'in cp.stderr
        ok('J-BLD data-only check: identical trees, cost_models/ and benchmarks/ changes and the carry set (docs/, README.md, CHANGELOG.md, '
           'a grown designs/forbidden_seeds.json, DELIVERY_MANIFEST.json, SHA256SUMS) pass; the seed mirror only grows: a dropped, changed or '
           'reordered entry, a removed file, a symlink and a non-log refuse, as seeds.py mirror does; bin/, bin.bld_failed_*/, the L8 pack links, '
           '__pycache__/ and .pytest_cache/ are skipped; a changed tools/ file, an added src/ file, a removed Makefile, a changed inputs/manifest.json, '
           'a nested bin/ file and an L7 pack fail naming the path; a missing base and an existing --output exit 2')
        # cost_summary.py's CPU label (the model's own CPU) and unchanged numbers
        summ={}
        for tag,cpu in (('7742','AMD EPYC 7742 64-Core Processor'),('7543','AMD EPYC 7543 32-Core Processor'),('m1','Apple M1 Max')):
            m=json.loads((td/'M_Y.json').read_text());m['cpu_model']=cpu;(td/f'M_Y_{tag}.json').write_text(json.dumps(m))
            T('cost_summary.py',td/'sweepY',td/f'M_Y_{tag}.json','--output',td/f'cs_{tag}.json');summ[tag]=json.loads((td/f'cs_{tag}.json').read_text())
        assert 'busy core-hours on EPYC 7742 from the measured model'in summ['7742']['note']and 'busy core-hours on EPYC 7543 from'in summ['7543']['note']
        assert 'busy core-hours on Apple M1 Max from'in summ['m1']['note'],summ['m1']['note']
        assert summ['7742']['note'].startswith('busy core-hours on EPYC 7742 from the measured model (the sweep at 512 points, 2 replicates, both campaigns, --mp-check on); SU = busy x eta ')
        strip=lambda s:{k:v for k,v in s.items()if k not in('note','cpu_model','model','model_sha256','made_utc','made_on')}
        assert strip(summ['7742'])==strip(summ['7543'])==strip(summ['m1'])
        ok('cost_summary.py: the note names the model\'s own CPU (EPYC 7742 as before, EPYC 7543, else the whole name); every number is the same')
        # Z: --refresh-bootstrap
        sz=install(pkg,'Z');cp=sweep(td/'sweepZ','--refresh',td/'M_Y.json','--refresh-bootstrap','--output',td/'M_Z.json','--report',td/'R_Z.json',C8_FAKE_SPP='0.002')
        MZ=json.loads((td/'M_Z.json').read_text());mz=manifest(td/'sweepZ')
        assert mz['plan_role']=='cost_refresh'and mz['cost_basis']=='bootstrap'and MZ['executable_sha256']==sz and MZ['scheduled_with']['basis']=='bootstrap'
        assert json.loads((td/'R_Z.json').read_text())['previous_executable_sha256']==sy
        ok('D.14 refresh Y -> Z with --refresh-bootstrap: role cost_refresh on the bootstrap basis; the fresh model has Z\'s sha256 and scheduled_with '
           'bootstrap; the report names Y as the previous executable')
    finally:
        if a.keep:print('kept',td,file=sys.stderr)
        else:shutil.rmtree(td,ignore_errors=True)
    print(json.dumps({'status':'passed','tests':len(RESULTS)}));return 0
if __name__=='__main__':sys.exit(main())
