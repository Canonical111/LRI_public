#!/usr/bin/env python3
"""Stage-3a integration checks of the worker contract between the native worker and the orchestration (Mac, seconds;
the fake worker in a scratch package, tests/c8pkg.py; nothing in the package is written).

  * A-KER-3 refusals at use time in production.describe (plan): a GMP worker whose runtime gmp block differs from its
    build record is refused (bin/<exe>.buildinfo.json keeps the block under describe.gmp, tools/buildinfo.py), an
    equal one is accepted; a GMP worker without its gmp block, a decimal worker whose gmp.applicable is not false, and
    diagnostic (no_tail_fields, order_trace), sanitizer and self-test builds are refused.
  * A-KER-3 at run time: `production.py run` refuses a block whose worker reports a runtime gmp block other than the
    planned build's (validate_checkpoint), and commits nothing; the same index then runs.
  * The C.3 row forms: a worker run with --mp-check off omits the MP self-check fields, and such rows are valid class-B
    rows whose run-file and graph_promotions.csv fields are 0/null; a checked row's mp_min_log10 may be "-inf" (an exact
    zero at the MP tier, kernel.hpp mp_check_record); NaN is not accepted; tools/tails.py and production.py's merge
    format agree on these rows.
  * A-EXP-1 (Mac part of the scratch check; the Expanse job is slurm/scratch_probe.sh): slurm/common.sh computes
    C8_SCRATCH inside the job from SLURM_TMPDIR and ignores an inherited login-node value; scratch_probe.sh records the
    inherited and computed values and passes, and fails when nothing was inherited.
  * The native jobs on symmetry (A1 repair round 2): slurm/native_job.sh's preamble and val1 run with C8_SITE=symmetry,
    symmetry's env.sh variables (no C8_GMP, no LDFLAGS), fake lscpu/g++/make/python3, a mkdir that refuses the node
    disks outside the test's own temporary tree (C8_TEST_OWN: on a cluster node that tree is itself under the job's
    TMPDIR on /local1 or /scratch) and a PATH of the shims and /usr/bin:/bin only: without SLURM_TMPDIR the scratch is
    /local1/$USER/job_<id> (never /scratch; 74 when it cannot be made), with it val1 runs to its summary in the L8 work
    copy $C8_ROOT/work/val1_<id> (make link-l8 STORE=$C8_STORE before the builds; kept when a step failed, never the
    node-local copy); check_build gets symmetry's expectations (g++ 11.4.0, Boost 107700, the system GMP
    6.2.1 in /usr/lib/x86_64-linux-gnu, --gmp-search system); a Mac fake refused with "this host is symmetry" is
    SITE_REFUSED and one refused with another site's text is FAIL; Expanse without C8_GMP stops with a message (never
    "unbound variable"), C8_SITE=fake is refused (64); basestore needs C8_BASE_PKG; the per-site baseline (Expanse
    24adff54..., symmetry refused 65 until J-BASE-sym records it); the val1 list of unit_orchestration tests equals
    unit_orchestration.TESTS.
  * The CPU pin (HD11; Stage 5 "Fix package first"): slurm/site.sh c8_cpu_guard reads ${C8_PROC:-/proc}/cpuinfo's first
    vendor_id and model name, passes symmetry's EPYC 7543 (tabs and doubled spaces collapsed) and its Intel nodes,
    stops (68, one line naming the host, both CPUs and C8_AMD_EXCLUDE_EXTRA, "nothing was claimed or written") an EPYC
    7532, an EPYC 8534P, an "EPYC 7543P" (no substring match), an unreadable cpuinfo and an inherited C8_CPU_EXPECT,
    checks Expanse's EPYC 7742 the same way, and does nothing for C8_SITE=fake or unset; the constants are bound to
    cost_models/<C8_SITE_MODEL>'s cpu_model whenever that model exists. lane_worker.sh, scratch_probe.sh and
    native_job.sh on a 7532 stop with 68 before any scratch, claim, evidence, work copy or build; on a 7543 they proceed.
    A set C8_PROC (this file's seam) is never silent: one WARNING line on stderr, and C8_CPU_SOURCE (environment.txt's
    cpu_source) says "TEST SEAM"; without it no warning.
  * One CPU vendor per campaign, job side (S2-001): slurm/site.sh c8_vendor_guard (via slurm/common.sh) stops (68)
    lane_worker.sh, merge.sh and run_array.sh of a campaign whose $C8_RUN/cpu_vendor.json names another vendor than the
    node's vendor_id, before any mkdir or tool; the pinned vendor and a campaign without a pin pass; C8_SITE=fake is
    untouched.
  * Stage 5 native modes (sweep2, bld; the site-named model of sweep1, argmax and argmaxre): call order, PREV and lane
    defaults per site, an inherited C8_LANES ignored, no $C8_STORE/baseline, the data-only check before anything is
    linked or built (the BASE export's tool; the data export itself refused as base), bin/ moved aside after a failed
    build or check (kept, with the rerun named, when only the sweep's bookkeeping failed), the 64 refusals before any
    evidence, refresh_record.json's checks, and copy_export (a built export's bin/ and L8 pack links are never copied,
    also by basestore's BASE, opt's PREV and variant copies; a pristine one takes cp -a).
Usage: python3 -B tests/integration_3a.py
"""
from __future__ import annotations
import json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg  # noqa: E402
import production as prod  # noqa: E402
import tails  # noqa: E402
RESULTS=[]
def ok(name):RESULTS.append(name);print('PASS',name,flush=True)

GMP={'applicable':True,'header_version':'6.2.1','runtime_version':'6.2.1','library':'/spack/gmp-6.2.1/lib/libgmp.so.10.4.1'}
def describe_doc(**kw)->dict:
    d={'schema':'c8-d3-build-1','dimension':3,'orders':[7,8],'lmax':8,'kmax':6,'numerics':'exact','diagnostic':False,'long_double_bits':64,
       'mp_backend':'gmp350','mp_digits10':350,'gmp':dict(GMP)}
    d.update(kw);return {k:v for k,v in d.items()if v is not None}

def fake_exe(td:Path,name:str,doc:dict)->Path:
    f=td/name;f.write_text(f'#!{sys.executable}\nimport sys\nprint({json.dumps(json.dumps(doc))})\n');f.chmod(0o755);return f

def refused(fn,*needles):
    try:fn()
    except ValueError as e:
        assert all(n in str(e)for n in needles),(str(e),needles);return str(e)
    raise AssertionError(f'accepted, expected a refusal naming {needles}')

def test_describe(td:Path):
    exe=fake_exe(td,'c8d3_gmp',describe_doc())
    record={'describe':describe_doc()}   # tools/buildinfo.py: the gmp block is under describe
    assert prod.describe(exe,'exact',record)['gmp']==GMP and prod.describe(exe,'exact',None)['gmp']==GMP
    other={'describe':describe_doc(gmp=dict(GMP,library='/lib64/libgmp.so.10.3.2',runtime_version='6.1.2'))}
    refused(lambda:prod.describe(exe,'exact',other),'runtime GMP','build record')
    refused(lambda:prod.describe(fake_exe(td,'g_nogmp',describe_doc(gmp=None)),'exact',None),'without its runtime gmp block')
    dec=describe_doc(mp_backend='decimal300',mp_digits10=300,gmp={'applicable':False})
    assert prod.describe(fake_exe(td,'c8d3_decimal',dec),'exact',{'describe':dec})['gmp']=={'applicable':False}
    refused(lambda:prod.describe(fake_exe(td,'d_gmp',dict(dec,gmp=dict(GMP))),'exact',None),'gmp.applicable is not false')
    for kind in ('no_tail_fields','order_trace','sanitize'):
        refused(lambda:prod.describe(fake_exe(td,f'diag_{kind}',describe_doc(diagnostic=True,diagnostic_kind=kind)),'exact',None),'diagnostic or self-test build')
    refused(lambda:prod.describe(fake_exe(td,'selftest',describe_doc(diagnostic=True,diagnostic_kind='unguarded_index_selftest',unguarded_index_selftest=True)),
                                 'exact',None),'diagnostic or self-test build')
    ok('A-KER-3 (plan): production.describe refuses a GMP worker whose runtime gmp block differs from its build record (describe.gmp), '
       'a GMP worker without the block, a decimal worker with gmp.applicable true, and diagnostic, sanitizer and self-test builds; '
       'equal records are accepted')

def test_run_gmp(td:Path):
    pkg=c8pkg.make(td/'p');scratch=td/'scratch';scratch.mkdir();d=td/'camp'
    c8pkg.tool(pkg,'production.py','plan',d,'--seed',7611827,'--pilot','--points',16,'--replicates',2,'--test-graphs',1,'--shards',1,'--threads',2,
               '--checkpoint-tasks',8,'--plan-role','validation','--bootstrap-chunk',8,'--backend','gmp','--scratch',scratch)
    j=c8pkg.manifest(d)['jobs'][0];ck=d/'groups'/j['group']/'checkpoints'
    cp=c8pkg.tool(pkg,'production.py','run',d,'--index',j['id'],'--threads',2,'--scratch',scratch,check=False,C8_FAKE_RUNTIME_GMP_LIBRARY='/lib64/libgmp.so.10')
    assert cp.returncode!=0 and 'runtime GMP'in cp.stderr and 'differs from the planned build'in cp.stderr,cp.stderr[-800:]
    assert not list(ck.glob('*.json'))if ck.exists()else True,'a block with a foreign runtime GMP was committed'
    c8pkg.tool(pkg,'production.py','run',d,'--index',j['id'],'--threads',2,'--scratch',scratch)
    assert list(ck.glob('*.json'))
    ok('A-KER-3 (run): a block whose worker reports another loaded libgmp than the planned build is refused and not committed; '
       'the index then runs with the planned library')

def test_row_forms(td:Path):
    pkg=c8pkg.make(td/'q');scratch=td/'scratch_q';scratch.mkdir();d=td/'off'
    c8pkg.tool(pkg,'production.py','plan',d,'--seed',7611828,'--pilot','--points',16,'--replicates',2,'--test-graphs',1,'--shards',1,'--threads',2,
               '--checkpoint-tasks',8,'--plan-role','validation','--bootstrap-chunk',8,'--backend','gmp','--mp-check','off','--scratch',scratch)
    c8pkg.run_all(pkg,d,scratch=scratch)
    c8pkg.tool(pkg,'production.py','merge',d,'--scratch',scratch)
    rows=[]
    for g in sorted((d/'groups').iterdir()):
        rr=[r for f in sorted((g/'checkpoints').glob('*.json'))for r in json.loads(f.read_text())['native']['rows']];rows+=rr
        assert all(not any(k in r for k in prod.MP_FIELDS)for r in rr),'the fake worker kept MP self-check fields under off'
        assert (g/'graph_promotions.csv').read_text()==tails.promotions_csv(rr)and (g/'graph_tails.csv').read_text()==tails.tails_csv(rr),g.name
        for line in (g/'graph_promotions.csv').read_text().splitlines()[1:]:
            f=line.split(',');assert f[6:9]==['0','0','null']and set(f[9:])=={'0'},line
    assert rows
    r=dict(rows[0]);fields=prod._row_fields(r).rstrip('\n').split('\t')
    assert fields[14:]==['0','0','null',' '.join(['0']*prod.MP_BINS)],fields[14:]
    assert prod._min_log10_ok('-inf')and prod._min_log10_ok('-35.25')and prod._min_log10_ok(-25)
    assert not prod._min_log10_ok('nan')and not prod._min_log10_ok('inf')
    a=dict(r,rep=0,graph=1,begin=0,end=4,total=8,mp=2,quad=2,mp_checked=2,mp_alarm=1,mp_min_log10='-inf',mp_hist=[1]+[0]*16+[1])
    b=dict(r,rep=0,graph=1,begin=4,end=8,total=8,mp=1,quad=1,mp_checked=1,mp_alarm=0,mp_min_log10='-40.5',mp_hist=[0,1]+[0]*16)
    line=tails.promotions_csv([a,b]).splitlines()[1].split(',')
    assert line[6:9]==['3','1','-Infinity']and line[9:11]==['1','1']and line[-1]=='1',line
    ok('C.3 row forms: --mp-check off rows carry no MP self-check fields and run, merge and validate (0/null in the run file and in '
       'graph_promotions.csv, equal to tools/tails.py); mp_min_log10 "-inf" is a valid checked value, NaN and +inf are not')

def test_scratch(td:Path):
    import os,subprocess
    tmp=td/'slurm_tmpdir';tmp.mkdir();out=td/'probe.json'
    base={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','C8_'))}
    env=dict(base,C8_PACKAGE=str(ROOT),C8_PYTHON=sys.executable,C8_SCRATCH='/tmp/login-value',C8_PROBE_OUT=str(out),SLURM_JOB_ID='4242',SLURM_TMPDIR=str(tmp))
    cp=subprocess.run(['bash',str(ROOT/'slurm/scratch_probe.sh')],capture_output=True,text=True,env=env)
    rec=json.loads(out.read_text())
    assert cp.returncode==0 and rec['passed']and rec['inherited_C8_SCRATCH']=='/tmp/login-value'and rec['computed_C8_SCRATCH']==str(tmp),(cp.returncode,cp.stderr[-500:],rec)
    env.pop('C8_SCRATCH');out.unlink()
    cp=subprocess.run(['bash',str(ROOT/'slurm/scratch_probe.sh')],capture_output=True,text=True,env=env)
    assert cp.returncode==1 and json.loads(out.read_text())['passed']is False,(cp.returncode,cp.stderr[-300:])
    ok('A-EXP-1 (Mac part): slurm/common.sh sets C8_SCRATCH to $SLURM_TMPDIR inside the job, not the inherited login value; '
       'scratch_probe.sh records both and passes, and fails when no login value was inherited (the test would not be real)')

NATIVE_SHIMS={
    'lscpu':'printf "Model name: AMD EPYC 7543 32-Core Processor\\nCPU(s): 64\\nNUMA node(s): 8\\n"',
    'g++':'[ "${1:-}" = --version ] && echo "g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0"; echo "g++ $*" >> "$C8_TEST_CALLS"; exit 0',
    # make: logs its arguments and directory; C8_TEST_MAKEFAIL=<text> fails a call naming it; creates bin/c8d3_gmp when asked
    'make':'echo "make $* @ $PWD" >> "$C8_TEST_CALLS"\n'
           'case " $* " in *" ${C8_TEST_MAKEFAIL:-<none>} "*) echo "make: forced failure (test)" >&2; exit 2 ;; esac\n'
           'for a in "$@"; do [ "$a" = bin/c8d3_gmp ] && { mkdir -p bin && echo "fake worker $PWD" > bin/c8d3_gmp; }; done; exit 0',
    # the node-local disks are never touched outside the test's own temporary tree $C8_TEST_OWN (a cluster node running val1
    # would otherwise create /local1/$USER/job_4242 or /scratch/$USER/job_4242; there the test's tree is itself under the
    # job's TMPDIR on /local1 or /scratch, so it is exempt by name); without C8_TEST_OWN every mkdir is refused
    'mkdir':'[ -n "${C8_TEST_OWN:-}" ] || { echo "mkdir: C8_TEST_OWN unset (test)" >&2; exit 1; }\n'
            'for a in "$@"; do case "$a" in */..|*/../*) echo "mkdir: $a: no .. (test)" >&2; exit 1 ;; "$C8_TEST_OWN"|"$C8_TEST_OWN"/*) ;; '
            '/local1|/local1/*|/scratch|/scratch/*) echo "mkdir-refused $a" >> "$C8_TEST_CALLS"; '
            'echo "mkdir: $a: Permission denied (test)" >&2; exit 1 ;; esac; done; exec /bin/mkdir "$@"',
    # python3: logs its arguments (newlines folded) and directory; the real interpreter for tools/baseline.py and for
    # cost_identity.py data-only, the fake sweep (C8_TEST_FAKE_SWEEP) for tools/sweep.py, C8_TEST_PYFAIL=<text> fails a call naming it
    'python3':'printf "python3 %s@ %s\\n" "$(printf "%s " "$@" | tr "\\n" " ")" "$PWD" >> "$C8_TEST_CALLS"\n'
              'case " $* " in *" ${C8_TEST_PYFAIL:-<none>} "*) echo "python3: forced failure (test)" >&2; exit 1 ;; *"tools/cost_identity.py data-only "*) exec "$C8_TEST_REALPY" "$@" ;; esac\n'
              'for a in "$@"; do case "$a" in\n'
              '  tools/baseline.py) exec "$C8_TEST_REALPY" "$@" ;;\n'
              '  tools/sweep.py) [ -n "${C8_TEST_FAKE_SWEEP:-}" ] && exec "$C8_TEST_REALPY" "$C8_TEST_FAKE_SWEEP" "$@"; exit 0 ;;\n'
              '  tests/test_submit.py) echo "C8: this host is symmetry but C8_SITE is \'fake\': source ~/c8d3/env.sh (C8_SITE=symmetry) first" >&2; exit 64 ;;\n'
              '  tests/test_ledger.py) echo "C8: this host is expanse but C8_SITE is \'fake\': source ~/c8d3/env.sh (C8_SITE=expanse) first" >&2; exit 64 ;;\n'
              'esac; done\nexit 0'}

CPU_7543='AMD EPYC 7543 32-Core Processor';CPU_7532='AMD EPYC 7532 32-Core Processor';CPU_7742='AMD EPYC 7742 64-Core Processor'
def cpuinfo(d:Path,model:str,vendor:str='AuthenticAMD',n:int=64)->Path:
    """A directory holding a Linux-style cpuinfo of n processor entries (the C8_PROC seam of slurm/site.sh and tools/lanes.py)."""
    d.mkdir(parents=True,exist_ok=True)
    (d/'cpuinfo').write_text(''.join(f'processor\t: {i}\nvendor_id\t: {vendor}\ncpu family\t: 25\nmodel\t\t: 1\nmodel name\t: {model}\n'
                                     f'physical id\t: {i//32}\nflags\t\t: fpu sse2 avx2\n\n'for i in range(n)))
    return d

def guard_run(site,proc,**env)->subprocess.CompletedProcess:
    """slurm/site.sh's c8_cpu_guard under errexit, nounset and pipefail, as a job runs it."""
    e={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','C8_'))};e.update({'C8_PROC':str(proc)}if proc is not None else{});e.update(env)
    if site is not None:e['C8_SITE']=site
    return subprocess.run(['bash','-c','set -euo pipefail; source "$0"; c8_cpu_guard; echo ok',str(ROOT/'slurm/site.sh')],capture_output=True,text=True,env=e)

def test_cpu_guard(td:Path):
    g=td/'guard'
    P=lambda name,model,vendor='AuthenticAMD':cpuinfo(g/name,model,vendor)
    p43=P('7543','AMD  EPYC\t7543 32-Core  Processor ');p32=P('7532',CPU_7532);p8534=P('8534P','AMD EPYC 8534P 64-Core Processor')
    p43p=P('7543P','AMD EPYC 7543P 32-Core Processor');pint=P('intel','Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz','GenuineIntel');p42=P('7742',CPU_7742)
    pempty=g/'empty';pempty.mkdir();(pempty/'cpuinfo').write_text('processor\t: 0\nvendor_id\t: AuthenticAMD\n')
    # C8_PROC (this test's seam) is never silent: one loud WARNING line naming it, and C8_CPU_SOURCE says "TEST SEAM"
    seam=lambda proc:f'C8: WARNING: C8_PROC={proc} is set: the CPU pin reads {proc}/cpuinfo, a TEST SEAM'
    cp=guard_run('symmetry',p43);assert cp.returncode==0 and cp.stdout.strip()=='ok',(cp.returncode,cp.stderr)
    assert len(cp.stderr.strip().splitlines())==1 and cp.stderr.startswith(seam(p43))and 'unset C8_PROC'in cp.stderr,cp.stderr
    cp=guard_run('symmetry',p32,SLURM_JOB_ID='77',SLURM_JOB_PARTITION='amdq');import socket
    st=cp.stderr.strip().splitlines()
    assert cp.returncode==68 and 'ok'not in cp.stdout and len(st)==2 and st[0].startswith(seam(p32))and 'nothing was claimed or written'in st[1],(cp.returncode,cp.stdout,cp.stderr)
    for need in (CPU_7532,CPU_7543,'nothing was claimed or written','C8_AMD_EXCLUDE_EXTRA','partition amdq, job 77','C8_SITE=symmetry','HD11'):assert need in st[1],(need,cp.stderr)
    rd=lambda site,proc,**x:subprocess.run(['bash','-c','set -euo pipefail; source "$0"; c8_cpu_guard; printf "%s|%s" "$C8_CPU_SOURCE" "$C8_CPU_READ"',str(ROOT/'slurm/site.sh')],
                                          capture_output=True,text=True,env={**{k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','C8_'))},
                                                                             **({'C8_PROC':str(proc)}if proc is not None else{}),'C8_SITE':site,**x})
    cp=rd('symmetry',p43,C8_CPU_SOURCE='stale',C8_CPU_READ='stale')
    assert cp.returncode==0 and cp.stdout==f'{p43}/cpuinfo (C8_PROC={p43}: TEST SEAM, not the node\'s /proc/cpuinfo)|{CPU_7543}',(cp.stdout,cp.stderr)
    cp=rd('fake',p43,C8_CPU_SOURCE='stale',C8_CPU_READ='stale');assert cp.returncode==0 and cp.stdout=='|'and not cp.stderr,(cp.stdout,cp.stderr)   # inherited values cleared; fake reads nothing
    cp=guard_run('symmetry',None)   # control: without C8_PROC no warning (the node's /proc/cpuinfo: 68 on the Mac, its own verdict on a cluster node)
    assert cp.returncode in (0,68)and 'WARNING'not in cp.stderr and 'C8_PROC'not in cp.stderr,(cp.returncode,cp.stderr)
    assert cp.returncode==0 or socket.gethostname().split('.')[0]in cp.stderr,cp.stderr   # the refusal names the host (a 7543 node passes silently)
    for proc in (p8534,p43p):cp=guard_run('symmetry',proc);assert cp.returncode==68 and 'ok'not in cp.stdout,(proc,cp.returncode,cp.stderr)   # 7543P: no substring match
    cp=guard_run('symmetry',pint);assert cp.returncode==0 and cp.stdout.strip()=='ok',(cp.returncode,cp.stderr)   # Intel defq/debugq: outside the pin
    for proc in (g/'missing',pempty):cp=guard_run('symmetry',proc);assert cp.returncode==68 and "is 'unreadable'"in cp.stderr,(proc,cp.returncode,cp.stderr)
    cp=guard_run('symmetry',p32,C8_CPU_EXPECT=CPU_7532,C8_SITE_MODEL='x.json');assert cp.returncode==68,(cp.returncode,cp.stderr)   # an inherited value is overwritten
    cp=guard_run('expanse',p42);assert cp.returncode==0 and cp.stdout.strip()=='ok',cp.stderr
    for proc in (p43,pint):cp=guard_run('expanse',proc);assert cp.returncode==68 and CPU_7742 in cp.stderr and "Expanse: -x <node>"in cp.stderr,(proc,cp.returncode,cp.stderr)
    for site in ('fake',None):cp=guard_run(site,g/'nonexistent');assert cp.returncode==0 and cp.stdout.strip()=='ok',(site,cp.returncode,cp.stderr)   # cpuinfo never read
    # the constants, and their binding to the site's committed cost model (Expanse's now; symmetry's after J-SWEEP-2's data-only commit)
    out=subprocess.run(['bash','-c','source "$0"; for s in expanse symmetry fake ""; do C8_SITE=$s; c8_site_cpu; echo "$s|$C8_CPU_EXPECT|$C8_SITE_MODEL"; done',
                        str(ROOT/'slurm/site.sh')],capture_output=True,text=True,check=True).stdout.splitlines()
    consts={l.split('|')[0]:tuple(l.split('|')[1:])for l in out}
    assert consts=={'expanse':(CPU_7742,'gmp_expanse_epyc7742_c8.json'),'symmetry':(CPU_7543,'gmp_symmetry_epyc7543_c8.json'),'fake':('',''),'':('','')},consts
    assert json.loads((ROOT/'cost_models/gmp_expanse_epyc7742_c8.json').read_text())['cpu_model']==CPU_7742
    bound=[]
    for site in ('expanse','symmetry'):
        cpu,model=consts[site];f=ROOT/'cost_models'/model
        if f.is_file():assert prod.norm_cpu(json.loads(f.read_text())['cpu_model'])==cpu,(site,f);bound.append(site)
    assert 'expanse'in bound
    # nothing claimed or written: lane_worker.sh, scratch_probe.sh (common.sh) and native_job.sh val1 on a 7532 stop with 68
    pkg=td/'gpkg';(pkg/'slurm').mkdir(parents=True);shutil.copy2(ROOT/'slurm/site.sh',pkg/'slurm');shutil.copy2(ROOT/'slurm/common.sh',pkg/'slurm')
    shims=td/'gshims';shims.mkdir();calls=td/'gcalls.log'
    for name in ('mkdir','python3'):(shims/name).write_text('#!/bin/bash\n'+NATIVE_SHIMS[name]+'\n');(shims/name).chmod(0o755)
    run=td/'grun';run.mkdir();base={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','C8_','BASH_FUNC_'))and k not in('TMPDIR','BASH_ENV','ENV')}
    base.update(PATH=f'{shims}:/usr/bin:/bin',C8_SITE='symmetry',C8_PACKAGE=str(pkg),C8_RUN=str(run),SLURM_JOB_ID='4242',USER='zzheng1',C8_TEST_CALLS=str(calls),
                C8_TEST_REALPY=sys.executable,C8_TEST_OWN=str(td))
    def job(script,**x):
        calls.write_text('');cp=subprocess.run(['bash',str(ROOT/'slurm'/script)],capture_output=True,text=True,env={**base,**x});return cp,calls.read_text()
    cp,log=job('lane_worker.sh',C8_PROC=str(p32))
    assert cp.returncode==68 and 'mkdir'not in log and 'lanes.py'not in log and not (run/'lanes').exists(),(cp.returncode,cp.stderr[-400:],log)
    cp,log=job('lane_worker.sh',C8_PROC=str(p43))                                     # control: past the guard, the /local1 scratch (refused here, 74)
    assert cp.returncode==74 and 'mkdir-refused /local1/zzheng1/job_4242'in log,(cp.returncode,cp.stderr[-400:],log)
    tmp=td/'gtmp';tmp.mkdir()
    cp,log=job('lane_worker.sh',C8_PROC=str(p43),SLURM_TMPDIR=str(tmp));assert cp.returncode==0 and 'tools/lanes.py worker'in log,(cp.returncode,cp.stderr[-400:],log)
    out=td/'gprobe.json'
    cp,log=job('scratch_probe.sh',C8_PROC=str(p32),C8_PROBE_OUT=str(out),C8_SCRATCH='/tmp/login-value',C8_PYTHON=sys.executable,SLURM_TMPDIR=str(tmp))
    assert cp.returncode==68 and not out.exists()and 'nothing was claimed or written'in cp.stderr,(cp.returncode,cp.stderr[-400:])
    cp,log=job('scratch_probe.sh',C8_PROC=str(p43),C8_PROBE_OUT=str(out),C8_SCRATCH='/tmp/login-value',C8_PYTHON=sys.executable,SLURM_TMPDIR=str(tmp))
    assert cp.returncode==0 and json.loads(out.read_text())['passed'],(cp.returncode,cp.stderr[-400:])
    ok('the CPU pin (HD11): c8_cpu_guard passes EPYC 7543 (whitespace collapsed as production.norm_cpu) and symmetry\'s Intel nodes, stops (68, one line: '
       'host, both CPUs, the remedy, "nothing was claimed or written") EPYC 7532, 8534P, "7543P" (exact match only), an unreadable cpuinfo and an '
       'inherited C8_CPU_EXPECT; a set C8_PROC seam prints one WARNING line and marks C8_CPU_SOURCE "TEST SEAM" (none without it; inherited values '
       'cleared); Expanse checks EPYC 7742; fake and unset sites never read cpuinfo; the constants equal the committed models\' '
       f'cpu_model ({", ".join(bound)}); lane_worker.sh and scratch_probe.sh stop before any mkdir, lanes.py claim or probe record (controls proceed)')

def test_vendor_guard(td:Path):
    """S2-001's job side: slurm/site.sh c8_vendor_guard, run by slurm/common.sh right after c8_cpu_guard, stops (68, one
    line naming the host, both vendors and the pin; "nothing was claimed or written") every job script of a campaign
    pinned to one CPU vendor ($C8_RUN/cpu_vendor.json, its first work admission's) on a node of the other: an Intel node
    (which symmetry's CPU pin lets through) for an amd campaign (lane_worker.sh, merge.sh, run_array.sh), an AMD node for
    an intel one; it passes the pinned vendor and a campaign without a pin, refuses an unreadable pin, and does nothing
    under C8_SITE=fake."""
    g=td/'vguard';p43=cpuinfo(g/'7543',CPU_7543);pint=cpuinfo(g/'intel','Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz','GenuineIntel')
    pkg=td/'vpkg';(pkg/'slurm').mkdir(parents=True);shutil.copy2(ROOT/'slurm/site.sh',pkg/'slurm');shutil.copy2(ROOT/'slurm/common.sh',pkg/'slurm')
    shims=td/'vshims';shims.mkdir();calls=td/'vcalls.log'
    for name in ('mkdir','python3'):(shims/name).write_text('#!/bin/bash\n'+NATIVE_SHIMS[name]+'\n');(shims/name).chmod(0o755)
    run=td/'vrun';run.mkdir();tmp=td/'vtmp';tmp.mkdir();pin=run/'cpu_vendor.json'
    base={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','C8_','BASH_FUNC_'))and k not in('TMPDIR','BASH_ENV','ENV')}
    base.update(PATH=f'{shims}:/usr/bin:/bin',C8_SITE='symmetry',C8_PACKAGE=str(pkg),C8_RUN=str(run),SLURM_JOB_ID='4343',SLURM_JOB_PARTITION='defq',USER='zzheng1',
                C8_TEST_CALLS=str(calls),C8_TEST_REALPY=sys.executable,C8_TEST_OWN=str(td),SLURM_TMPDIR=str(tmp))
    def job(script,**x):
        calls.write_text('');cp=subprocess.run(['bash',str(ROOT/'slurm'/script)],capture_output=True,text=True,env={**base,**x});return cp,calls.read_text()
    def write_pin(v):pin.write_text(json.dumps({'schema':'c8-d3-cpu-vendor-1','vendor':v,'site':'symmetry'},indent=1)+'\n')
    write_pin('amd')
    for script,tool in (('lane_worker.sh','tools/lanes.py worker'),('merge.sh','tools/production.py status'),('run_array.sh','tools/production.py run')):
        x={'SLURM_ARRAY_TASK_ID':'0'}if script=='run_array.sh'else{}
        cp,log=job(script,C8_PROC=str(pint),**x);st=[l for l in cp.stderr.splitlines()if 'WARNING'not in l]
        assert cp.returncode==68 and tool not in log and 'mkdir'not in log and len(st)==1,(script,cp.returncode,cp.stderr[-500:],log)
        for need in ("has CPU vendor 'intel'","pinned to 'amd'",'nothing was claimed or written','job 4343','partition defq',str(pin)):assert need in st[0],(script,need,st[0])
        cp,log=job(script,C8_PROC=str(p43),**x);assert tool in log,(script,cp.returncode,cp.stderr[-400:],log)   # control: the pinned vendor passes
    write_pin('intel');cp,log=job('lane_worker.sh',C8_PROC=str(p43));assert cp.returncode==68 and "pinned to 'intel'"in cp.stderr and 'lanes.py'not in log,(cp.returncode,cp.stderr[-300:])
    cp,log=job('lane_worker.sh',C8_PROC=str(pint));assert cp.returncode==0 and 'tools/lanes.py worker'in log,(cp.returncode,cp.stderr[-300:])
    pin.write_text('not a record\n');cp,log=job('lane_worker.sh',C8_PROC=str(pint));assert cp.returncode==68 and "pinned to 'unreadable'"in cp.stderr,(cp.returncode,cp.stderr[-300:])
    pin.unlink();cp,log=job('lane_worker.sh',C8_PROC=str(pint));assert cp.returncode==0 and 'tools/lanes.py worker'in log,(cp.returncode,cp.stderr[-300:])   # no pin yet
    write_pin('amd');cp,log=job('lane_worker.sh',C8_PROC=str(pint),C8_SITE='fake');assert cp.returncode==0 and 'tools/lanes.py worker'in log,(cp.returncode,cp.stderr[-300:])   # the Mac fakes
    ok('one CPU vendor per campaign, job side (S2-001): c8_vendor_guard stops (68, one line: host, both vendors, the pin, "nothing was claimed or '
       'written") lane_worker.sh, merge.sh and run_array.sh of an amd-pinned campaign on an Intel node before any mkdir or tool, and an intel-pinned '
       'one on an AMD node; the pinned vendor and a campaign without a pin pass; an unreadable pin 68; C8_SITE=fake untouched')

def test_native_job_symmetry(td:Path):
    import os,re,subprocess
    import unit_orchestration as uo
    d=td/'native_sym';root=d/'root';sha12='0123456789ab';pkg=root/'pkg'/sha12;shims=d/'shims';calls=d/'calls.log'
    for x in (pkg/'slurm',pkg/'tools',pkg/'reference',shims):x.mkdir(parents=True)
    shutil.copy2(ROOT/'slurm/site.sh',pkg/'slurm/site.sh');shutil.copy2(ROOT/'tools/baseline.py',pkg/'tools/baseline.py')
    shutil.copy2(ROOT/'reference/baseline_c8_stage3.json',pkg/'reference/baseline_c8_stage3.json')
    for name,body in NATIVE_SHIMS.items():(shims/name).write_text('#!/bin/bash\n'+body+'\n');(shims/name).chmod(0o755)
    envf=d/'env.sh'
    def env_file(site,**x):   # symmetry's env.sh (slurm/sites/symmetry/env.sh.example) without its module and venv lines
        lines=[f'export PATH={shims}:$PATH C8_SITE={site} C8_ROOT={root} C8_STORE={root}/store C8_SEEDS={root}/forbidden_seeds.json',
               'export CPATH=/cm/local/apps/boost/1.77.0//include']+[f'export {k}={v}'for k,v in x.items()]
        envf.write_text('\n'.join(lines)+'\n')
    # the real job's environment stays out: its Slurm and C8 settings, TMPDIR, the module system's BASH_ENV/ENV and exported
    # shell functions, Python and make settings; PATH is the shims and the system directories only (no real Slurm client,
    # no module toolchain)
    base={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','C8_','BASH_FUNC_'))
          and k not in('TMPDIR','LDFLAGS','CPATH','BASH_ENV','ENV','PYTHONPATH','PYTHONHOME','MAKEFLAGS','MFLAGS')}
    p43=cpuinfo(d/'proc7543',CPU_7543);p42=cpuinfo(d/'proc7742',CPU_7742);p32=cpuinfo(d/'proc7532',CPU_7532)
    base.update(C8_ENV_SETUP=str(envf),C8_PACKAGE=str(pkg),SLURM_JOB_ID='4242',SLURM_CPUS_PER_TASK='4',USER='zzheng1',C8_JOB='val1',
                C8_TEST_CALLS=str(calls),C8_TEST_REALPY=sys.executable,C8_TEST_OWN=str(d),PATH=f'{shims}:/usr/bin:/bin',C8_PROC=str(p43))
    def run(drop=(),**x):
        calls.write_text('');ev=root/'evidence'/sha12/x.get('C8_JOB','val1')
        if ev.exists():shutil.rmtree(ev)
        env={k:v for k,v in {**base,**x}.items()if k not in drop}
        return subprocess.run(['bash',str(ROOT/'slurm/native_job.sh')],capture_output=True,text=True,env=env),calls.read_text(),ev
    # (1) no SLURM_TMPDIR (symmetry sets none): the scratch is /local1/zzheng1/job_4242, never /scratch; 74 if it cannot be made
    env_file('symmetry')
    cp,log,_=run()
    assert cp.returncode==74 and 'cannot create the job scratch /local1/zzheng1/job_4242'in cp.stderr and 'mkdir-refused /local1/zzheng1/job_4242'in log,(cp.returncode,cp.stderr[-800:],log)
    assert '/scratch'not in log and 'unbound variable'not in cp.stderr,(log,cp.stderr[-400:])
    # (2) with SLURM_TMPDIR: val1 runs to its summary in the L8 work copy (the store's packs linked in before the builds; kept,
    # since a step fails); symmetry's toolchain expectations; SITE_REFUSED only for this site's text
    node=d/'node';node.mkdir()
    cp,log,ev=run(SLURM_TMPDIR=str(node))
    assert 'unbound variable'not in cp.stderr and (ev/'summary.json').is_file(),(cp.returncode,cp.stderr[-1500:])
    assert f'make link-l8 PYTHON=python3 STORE={root}/store'in log and log.index('make link-l8')<log.index('make -j 4 CXX=g++ all'),(log,cp.stderr[-600:])
    assert (root/'work'/'val1_4242').is_dir()and not (node/'pkg').exists(),(sorted(map(str,root.rglob('val1_*'))),cp.stderr[-600:])
    envtxt=(ev/'environment.txt').read_text();summ={s['step']:s['status']for s in json.loads((ev/'summary.json').read_text())['steps']}
    want='--expect-gcc 11.4.0 --expect-boost 107700 --expect-gmp-lib /usr/lib/x86_64-linux-gnu --expect-gmp-version 6.2.1 --gmp-search system'
    assert 'site: symmetry'in envtxt and f'scratch: {node}'in envtxt and f'toolchain expectations: {want}'in envtxt and 'g++ (Ubuntu 11.4.0'in envtxt,envtxt
    assert f'cpu_expect: {CPU_7543}'in envtxt and 'site_model: gmp_symmetry_epyc7543_c8.json'in envtxt and f'Model name: {CPU_7543}'in envtxt,envtxt
    assert f'cpu_source: {p43}/cpuinfo (C8_PROC={p43}: TEST SEAM'in envtxt and f'cpu_read: {CPU_7543}\n'in envtxt and f'C8_PROC={p43} is set'in cp.stderr,(envtxt,cp.stderr[-600:])
    cb=[l for l in log.splitlines()if 'tests/check_build.py'in l and '--selftest'not in l]
    assert len(cb)==1 and want in cb[0]and 'bin/ref/c7d3_gmp.buildinfo.json'in cb[0]and 'C8_GMP'not in cb[0],cb
    assert summ.get('test_submit')=='SITE_REFUSED'and summ.get('test_ledger')=='FAIL'and summ.get('uo_seed_logs_two_sites')=='PASS'and summ.get('link_l8')=='PASS',summ
    assert [k for k,v in summ.items()if v=='FAIL']==['test_ledger']and cp.returncode==1,(summ,cp.returncode)
    assert 'make -j 4 CXX=g++ all bin/c8d3_decimal c7ref inspect test-builds'in log and 'no symmetry baseline record'in (ev/'baseline_record.log').read_text()
    # (3) Expanse without C8_GMP: a message naming it (never "unbound variable"); C8_SITE=fake and unknown sites refused (64)
    env_file('expanse');cp,_,_=run(SLURM_TMPDIR=str(node),C8_PROC=str(p42))
    assert cp.returncode!=0 and 'C8_GMP (the Spack GMP 6.2.1'in cp.stderr and 'unbound variable'not in cp.stderr,(cp.returncode,cp.stderr[-600:])
    env_file('expanse',C8_GMP='/spack/gmp-6.2.1');cp,log,ev=run(C8_PROC=str(p42))   # Expanse without SLURM_TMPDIR: /scratch/zzheng1/job_4242
    assert cp.returncode==74 and 'mkdir-refused /scratch/zzheng1/job_4242'in log,(cp.returncode,log)
    cp,log,ev=run(C8_PROC=str(p43),SLURM_TMPDIR=str(node));assert cp.returncode==68 and CPU_7742 in cp.stderr and not ev.exists()and 'make'not in log,(cp.returncode,cp.stderr[-300:])
    # the CPU pin before anything is written: val1 on a 7532 stops (68) with no evidence, no work copy, no make or g++ call
    env_file('symmetry');shutil.rmtree(root/'work'/'val1_4242',ignore_errors=True)
    cp,log,ev=run(SLURM_TMPDIR=str(node),C8_PROC=str(p32))
    assert cp.returncode==68 and 'nothing was claimed or written'in cp.stderr and not ev.exists()and not (root/'work'/'val1_4242').exists(),(cp.returncode,cp.stderr[-400:])
    assert 'make 'not in log and 'g++'not in log and 'mkdir'not in log,log
    for site in ('fake','other'):
        env_file(site);cp,_,_=run(SLURM_TMPDIR=str(node));assert cp.returncode==64 and 'expanse or symmetry only'in cp.stderr,(site,cp.returncode,cp.stderr[-300:])
    # (4) basestore's arguments
    env_file('symmetry')
    for x in ({},{'C8_BASE_PKG':'zz'},{'C8_BASE_PKG':'fedcba987654'}):
        cp,_,_=run(SLURM_TMPDIR=str(node),C8_JOB='basestore',**x);assert cp.returncode==64 and 'C8_BASE_PKG'in cp.stderr,(x,cp.returncode,cp.stderr[-300:])
    # (5) the per-site baseline record (tools/baseline.py): Expanse's B0 24adff54...; symmetry's (J-BASE-sym 570275 and the
    # symmetry J-VAL-3 570319, recorded 2026-10-05) 3a9a556b...; a package without a site's record refuses (65) every reader
    def bl(*a,at=ROOT,**e):return subprocess.run([sys.executable,'-B',str(at/'tools/baseline.py'),*a],capture_output=True,text=True,env={**base,**e})
    exp=json.loads((ROOT/'reference/baseline_c8_stage3.json').read_text())['files']['c8d3_gmp']
    for e in ({'C8_SITE':'expanse'},{'C8_SITE':'fake'},{}):cp=bl('sha',**e);assert cp.returncode==0 and cp.stdout.strip()==exp==('24adff544a0a5637ea352ac8826e91d78599a28211d77d598f2e60861f67ccf1'),(e,cp.stdout,cp.stderr)
    sym=json.loads((ROOT/'reference/baseline_c8_stage3_symmetry.json').read_text())
    cp=bl('sha',C8_SITE='symmetry');assert cp.returncode==0 and cp.stdout.strip()==sym['files']['c8d3_gmp']=='3a9a556b134db77c4f37c8790ec1936a2d8db2e1f514f45ebda6938a70a98b60',(cp.returncode,cp.stdout,cp.stderr)
    cp=bl('val3',C8_SITE='symmetry');assert cp.returncode==0 and cp.stdout.strip()==sym['forced_tiers_record']and (ROOT/sym['forced_tiers_record']).is_file(),(cp.stdout,cp.stderr)
    cp=bl('install','--store',str(d),C8_SITE='symmetry');assert cp.returncode==65,(cp.returncode,cp.stderr)   # a store without the binaries
    cp=bl('sha',C8_SITE='symmetry',at=pkg);assert cp.returncode==65 and 'no symmetry baseline record'in cp.stderr and not cp.stdout.strip(),(cp.returncode,cp.stderr)
    for a in (('val3',),('check',),('install','--store',str(d))):
        cp=bl(*a,C8_SITE='symmetry',at=pkg);assert cp.returncode==65 and 'symmetry'in cp.stderr,(a,cp.returncode,cp.stderr)
    cp=bl('val3',C8_SITE='expanse');assert cp.returncode==0 and cp.stdout.strip()=='benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/val3/forced_tiers.json'
    s=[l for l in (ROOT/'slurm/sites/symmetry/env.sh.example').read_text().splitlines()if not l.lstrip().startswith('#')]   # no Spack GMP, no RPATH
    assert not any('C8_GMP='in l or 'LDFLAGS='in l for l in s)and 'export C8_SITE=symmetry'in s,s
    # (6) val1's list of unit_orchestration tests (streams and the completeness step) equals unit_orchestration.TESTS
    nj=(ROOT/'slurm/native_job.sh').read_text()
    stream=re.search(r'for t in ([a-z_ \\\n]+); do pstep "uo_\$t"',nj).group(1).replace('\\',' ').split()
    listed=re.search(r"w='([a-z_ ]+)'\.split\(\)",nj).group(1).split()
    assert stream==listed==uo.TESTS,(stream,listed,uo.TESTS)
    ok('native jobs on symmetry: native_job.sh takes slurm/site.sh\'s rules (scratch /local1/$USER/job_<id> without SLURM_TMPDIR, 74 when it cannot '
       'be made; symmetry\'s check_build expectations, no C8_GMP needed; SITE_REFUSED only for this site\'s refusal text); val1 works in the L8 '
       'work copy $C8_ROOT/work/val1_<id> with make link-l8 before the builds; Expanse without C8_GMP '
       'stops with a message, C8_SITE=fake is refused; basestore needs C8_BASE_PKG; the per-site baseline record (symmetry 65 until '
       'J-BASE-sym); val1 runs every unit_orchestration test')

FAKE_SWEEP=r"""# tests/integration_3a.py's stand-in for tools/sweep.py (run by the python3 shim in the job's work copy)
import hashlib,json,os,sys
a=sys.argv[1:];a=a[a.index('tools/sweep.py')+1:];run=a[0];opt=lambda k:a[a.index(k)+1]if k in a else None
exe='bin/c8d3_gmp';sha=hashlib.sha256(open(exe,'rb').read()).hexdigest()if os.path.exists(exe)else None
basis=os.environ.get('C8_TEST_BASIS','bootstrap');role='cost_refresh'if opt('--refresh')else'cost_sweep'
if '--choose-only'in a:
    print(json.dumps({'sweep':'refresh','executable_sha256':sha,'previous_model':opt('--refresh'),'previous_executable_sha256':'24adff54','role':role,'basis':basis,'why':'fake'}));sys.exit(0)
with open(os.environ['C8_TEST_CALLS'],'a')as f:f.write('C8_LANES='+os.environ.get('C8_LANES','<unset>')+'\n')
os.makedirs(run);json.dump({'plan_role':role,'cost_basis':basis,'executable_sha256':sha},open(run+'/manifest.json','w'))
json.dump({'schema':'c8-d3-cost-model-1','measured':True,'cpu_model':os.environ.get('C8_TEST_MODEL_CPU','AMD EPYC 7543 32-Core Processor'),'executable_sha256':sha,
           'mp_check':'on','source':{'plan_role':role},'scheduled_with':{'basis':basis}},open(opt('--output'),'w'))
"""

def test_native_job_stage5(td:Path):
    """Stage 5's native modes with the shims of test_native_job_symmetry: sweep2 (J-SWEEP-2), bld (J-BLD, in place),
    copy_export, and the site-named model of sweep1, argmax and argmaxre."""
    d=td/'native_s5';root=d/'root';shims=d/'shims';calls=d/'calls.log';shims.mkdir(parents=True)
    for name,body in NATIVE_SHIMS.items():(shims/name).write_text('#!/bin/bash\n'+body+'\n');(shims/name).chmod(0o755)
    (shims/'fake_sweep.py').write_text(FAKE_SWEEP)
    p43=cpuinfo(d/'proc7543',CPU_7543);p42=cpuinfo(d/'proc7742',CPU_7742);node=d/'node';node.mkdir();seeds=root/'forbidden_seeds.json'
    root.mkdir(parents=True,exist_ok=True);seeds.write_text('{"schema":"c8-d3-seeds-1","seeds":[]}\n')
    exp_model={'schema':'c8-d3-cost-model-1','measured':True,'cpu_model':CPU_7742,'executable_sha256':'24adff54'*8,'mp_check':'on','source':{'plan_role':'cost_sweep'}}
    def export(sha12,model=None,extra=None)->Path:
        """A fake export $C8_ROOT/pkg/<sha12>: the files native_job.sh and its real tools need here (the rest is shimmed)."""
        pkg=root/'pkg'/sha12
        if pkg.exists():shutil.rmtree(pkg)
        for x in ('slurm','tools','reference','cost_models','docs'):(pkg/x).mkdir(parents=True)
        shutil.copy2(ROOT/'slurm/site.sh',pkg/'slurm/site.sh');(pkg/'Makefile').write_text('# fake\n');(pkg/'marker.txt').write_text('marker\n')
        for f in ('tools/baseline.py','tools/cost_identity.py','reference/baseline_c8_stage3.json'):shutil.copy2(ROOT/f,pkg/f)
        (pkg/'cost_models/gmp_expanse_epyc7742_c8.json').write_text(json.dumps(exp_model)+'\n')
        if model:(pkg/'cost_models'/model).write_text(json.dumps({**exp_model,'cpu_model':CPU_7742 if 'expanse'in model else CPU_7543,'source':{'plan_role':'cost_refresh'}})+'\n')
        for rel,text in (extra or{}).items():(pkg/rel).parent.mkdir(parents=True,exist_ok=True);(pkg/rel).write_text(text)
        return pkg
    envf=d/'env.sh'
    def env_file(site,**x):
        envf.write_text('\n'.join([f'export PATH={shims}:$PATH C8_SITE={site} C8_ROOT={root} C8_STORE={root}/store C8_SEEDS={seeds}']+
                                  [f'export {k}={v}'for k,v in x.items()])+'\n')
    base={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','C8_','BASH_FUNC_'))
          and k not in('TMPDIR','LDFLAGS','CPATH','BASH_ENV','ENV','PYTHONPATH','PYTHONHOME','MAKEFLAGS','MFLAGS')}
    base.update(C8_ENV_SETUP=str(envf),SLURM_JOB_ID='4242',SLURM_CPUS_PER_TASK='4',USER='zzheng1',C8_TEST_CALLS=str(calls),C8_TEST_REALPY=sys.executable,
                C8_TEST_OWN=str(d),C8_TEST_FAKE_SWEEP=str(shims/'fake_sweep.py'),PATH=f'{shims}:/usr/bin:/bin',C8_PROC=str(p43),SLURM_TMPDIR=str(node))
    def run(pkg:Path,job:str,**x):
        calls.write_text('')
        for w in (root/'work').glob('*_4242*')if (root/'work').exists()else[]:shutil.rmtree(w)
        cp=subprocess.run(['bash',str(ROOT/'slurm/native_job.sh')],capture_output=True,text=True,env={**base,'C8_PACKAGE':str(pkg),'C8_JOB':job,**x})
        return cp,calls.read_text()
    def lines(log,needle):return [l for l in log.splitlines()if needle in l]
    def order(log,*needles):
        pos=[next((i for i,l in enumerate(log.splitlines())if n in l),None)for n in needles];assert None not in pos and pos==sorted(pos),(list(zip(needles,pos)),log)
    def ev_of(sha12,name):return root/'evidence'/sha12/name
    SYM_TC='--expect-gcc 11.4.0 --expect-boost 107700 --expect-gmp-lib /usr/lib/x86_64-linux-gnu --expect-gmp-version 6.2.1 --gmp-search system'
    # ---------------------------------------------------------------- sweep2 on symmetry, a pristine export (no site model)
    env_file('symmetry');F=export('5e5e5e5e5e5e');runs=root/'runs';runs.mkdir(parents=True,exist_ok=True)
    R=runs/'sweep2-a';cp,log=run(F,'sweep2',C8_SWEEP_RUN=str(R),C8_SWEEP_SEED='777',C8_LANES='1')
    ev=ev_of('5e5e5e5e5e5e','sweep2_4242');W=root/'work'/'sweep2_4242';out=ev/'gmp_symmetry_epyc7543_c8.json'
    assert cp.returncode==0 and (ev/'summary.json').is_file()and out.is_file(),(cp.returncode,cp.stderr[-800:],cp.stdout[-1500:])
    order(log,'make link-l8 PYTHON=python3 STORE=','make -j 4 CXX=g++ bin/c8d3_gmp bin/c8d3_decimal','tests/check_build.py','--choose-only',
          f'tools/sweep.py {R} --seed 777 --refresh cost_models/gmp_expanse_epyc7742_c8.json --output {out} --report {ev}/refresh_report.json --forbid-seeds-from {seeds} '
          f'--reserve-seed {seeds} --scratch {node}',
          'C8_LANES=numa','tools/seeds.py add','tools/cost_identity.py check --model','tools/assemble.py','tools/cost_summary.py')
    assert SYM_TC in lines(log,'tests/check_build.py')[0]and lines(log,'C8_LANES=')==['C8_LANES=numa'],log   # an inherited C8_LANES=1 is ignored
    assert f'tools/cost_identity.py check --model {out} --exe bin/c8d3_gmp --host-cpu --mp-check on'in log and f'@ {W}'in lines(log,'tools/sweep.py')[0],log
    assert not (root/'store'/'baseline').exists()and W.is_dir()and ev.name=='sweep2_4242'and 'work copy kept'in cp.stdout,(cp.stdout[-600:])
    envtxt=(ev/'environment.txt').read_text();assert 'sweep_prev: cost_models/gmp_expanse_epyc7742_c8.json'in envtxt and 'sweep_lanes: numa'in envtxt,envtxt
    # refresh_record.json (native_job.sh's REFRESH_PY, real Python, in the kept work copy): ok on the sweep's files; fails on a model
    # of another role, and when the basis log names another basis
    py=re.search(r"REFRESH_PY='(.*?)'\n",(ROOT/'slurm/native_job.sh').read_text(),re.S).group(1)
    rr=lambda model,basis,o:subprocess.run([sys.executable,'-B','-c',py,str(R),str(model),str(basis),'cost_models/gmp_expanse_epyc7742_c8.json',str(o)],cwd=W,capture_output=True,text=True)
    c=rr(out,ev/'basis.log',d/'rr1.json');rec=json.loads((d/'rr1.json').read_text())
    assert c.returncode==0 and rec['ok']and rec['basis']['basis']=='bootstrap'and rec['previous_executable_sha256']=='24adff54'*8 and rec['executable_sha256']==rec['manifest_executable_sha256'],(c.stderr,rec)
    m2=json.loads(out.read_text());m2['source']['plan_role']='cost_sweep';(d/'m2.json').write_text(json.dumps(m2));(d/'b2.log').write_text('{"basis": "prior_model"}\n')
    assert rr(d/'m2.json',ev/'basis.log',d/'rr2.json').returncode==1 and rr(out,d/'b2.log',d/'rr3.json').returncode==1
    # a site model in the export is PREV; C8_SWEEP_PREV is honoured
    F2=export('5e5e5e5e5e5f',model='gmp_symmetry_epyc7543_c8.json',extra={'cost_models/x.json':'{}\n'})
    cp,log=run(F2,'sweep2',C8_SWEEP_RUN=str(runs/'sweep2-b'),C8_SWEEP_SEED='778');assert cp.returncode==0 and '--refresh cost_models/gmp_symmetry_epyc7543_c8.json --output'in log,(cp.stderr[-500:],log)
    cp,log=run(F2,'sweep2',C8_SWEEP_RUN=str(runs/'sweep2-c'),C8_SWEEP_SEED='779',C8_SWEEP_PREV='cost_models/x.json');assert cp.returncode==0 and '--refresh cost_models/x.json --output'in log,log
    # Expanse: its model name, its PREV, 16 lanes (P4's 16 x 8), C8_SWEEP_LANES honoured
    env_file('expanse',C8_GMP='/spack/gmp-6.2.1');FE=export('5e5e5e5e5e60',model='gmp_expanse_epyc7742_c8.json')
    cp,log=run(FE,'sweep2',C8_SWEEP_RUN=str(runs/'sweep2-e'),C8_SWEEP_SEED='780',C8_PROC=str(p42),C8_TEST_MODEL_CPU=CPU_7742)
    eve=ev_of('5e5e5e5e5e60','sweep2_4242')
    assert cp.returncode==0 and f'--refresh cost_models/gmp_expanse_epyc7742_c8.json --output {eve}/gmp_expanse_epyc7742_c8.json'in log and lines(log,'C8_LANES=')==['C8_LANES=16'],(cp.stderr[-500:],log)
    cp,log=run(FE,'sweep2',C8_SWEEP_RUN=str(runs/'sweep2-f'),C8_SWEEP_SEED='781',C8_PROC=str(p42),C8_SWEEP_LANES='numa');assert lines(log,'C8_LANES=')==['C8_LANES=numa'],log
    # a failed build: no sweep
    env_file('symmetry');shutil.rmtree(root/'evidence'/'5e5e5e5e5e5e',ignore_errors=True)
    cp,log=run(F,'sweep2',C8_SWEEP_RUN=str(runs/'sweep2-g'),C8_SWEEP_SEED='782',C8_TEST_MAKEFAIL='bin/c8d3_gmp')
    assert cp.returncode==1 and 'tools/sweep.py'not in log and 'build or check_build failed: no sweep'in cp.stdout,(cp.returncode,log)
    # refusals (64) before any evidence
    shutil.rmtree(root/'evidence'/'5e5e5e5e5e5e',ignore_errors=True);(runs/'exists').mkdir()
    for x,why in (({'C8_SWEEP_RUN':str(runs/'r1')},'C8_SWEEP_SEED'),({'C8_SWEEP_RUN':str(runs/'exists'),'C8_SWEEP_SEED':'1'},'exists'),
                  ({'C8_SWEEP_RUN':str(root/'other/r2'),'C8_SWEEP_SEED':'1'},'C8_SWEEP_RUN'),({'C8_SWEEP_RUN':str(runs/'../r3'),'C8_SWEEP_SEED':'1'},'C8_SWEEP_RUN'),
                  ({'C8_SWEEP_RUN':str(runs/'r4'),'C8_SWEEP_SEED':'1','C8_SWEEP_PREV':'../a.json'},'C8_SWEEP_PREV'),
                  ({'C8_SWEEP_RUN':str(runs/'r5'),'C8_SWEEP_SEED':'1','C8_SWEEP_PREV':'/abs.json'},'C8_SWEEP_PREV'),
                  ({'C8_SWEEP_RUN':str(runs/'r6'),'C8_SWEEP_SEED':'1','C8_SWEEP_PREV':'cost_models/missing.json'},'not in the export'),
                  ({'C8_SWEEP_RUN':str(runs/'r7'),'C8_SWEEP_SEED':'1','C8_SWEEP_LANES':'8x8'},'C8_SWEEP_LANES')):
        cp,log=run(F,'sweep2',**x);assert cp.returncode==64 and why in cp.stderr and not (root/'evidence'/'5e5e5e5e5e5e').exists()and 'make'not in log,(x,cp.returncode,cp.stderr[-300:])
    ok('sweep2 (J-SWEEP-2): link-l8, the builds, check_build (symmetry), --choose-only, then sweep.py --refresh PREV --output $EV/<site model> --report '
       'refresh_report.json with C8_LANES numa (an inherited C8_LANES ignored), seeds.py add, cost_identity.py check --host-cpu --mp-check on, '
       'assemble.py, cost_summary.py; no $C8_STORE/baseline; work copy kept; EV sweep2_<id>; PREV = the site model when the export has one, '
       'C8_SWEEP_PREV honoured; Expanse: its model name and PREV, 16 lanes; refresh_record.json\'s checks; a failed build runs no sweep; 64 refusals')
    # ---------------------------------------------------------------- bld (J-BLD) in place
    env_file('symmetry');BASE='b0b0b0b0b0b0';export(BASE)
    data=lambda sha12,extra=None:export(sha12,model='gmp_symmetry_epyc7543_c8.json',extra={'benchmarks/x/y.json':'{}\n',**(extra or{})})
    D=data('d0d0d0d0d0d0');cp,log=run(D,'bld',C8_BLD_BASE_PKG=BASE);ev=ev_of('d0d0d0d0d0d0','bld_4242')
    assert cp.returncode==0 and (D/'bin/c8d3_gmp').is_file(),(cp.returncode,cp.stderr[-600:],cp.stdout[-1500:])
    assert not (root/'work').exists()or not list((root/'work').glob('bld*')),list((root/'work').iterdir())   # no work copy: built in place
    order(log,'tools/cost_identity.py data-only','make link-l8 PYTHON=python3 STORE=','make verify-inputs PYTHON=python3','make -j 4 CXX=g++ PYTHON=python3 bin/c8d3_gmp bin/c8d3_decimal',
          'tests/check_build.py','tools/cost_identity.py check --model cost_models/gmp_symmetry_epyc7543_c8.json --exe bin/c8d3_gmp --host-cpu --mp-check on')
    assert SYM_TC in lines(log,'tests/check_build.py')[0]and all(l.endswith(f'@ {D}')for l in log.splitlines()if l.startswith(('make ','python3 -B tools/','python3 -B tests/'))),log
    dd=json.loads((ev/'data_only_diff.json').read_text());assert dd['ok']and {x['path']for x in dd['differences']}=={'cost_models/gmp_symmetry_epyc7543_c8.json','benchmarks/x/y.json'},dd
    assert 'export built in place'in cp.stdout and not (root/'work'/'bld_4242').exists()
    # negative controls: HD11's check fails (bin/ moved aside); a code change in the data export (nothing linked or built); the 64s
    assert lines(log,'cost_identity.py data-only')[0].startswith(f'python3 -B {root}/pkg/{BASE}/tools/cost_identity.py data-only --base {root}/pkg/{BASE} --data {D}'),log   # the BASE's tool
    D=data('d1d1d1d1d1d1');cp,log=run(D,'bld',C8_BLD_BASE_PKG=BASE,C8_TEST_PYFAIL='tools/cost_identity.py check')
    assert cp.returncode==1 and not (D/'bin').exists()and (D/'bin.bld_failed_4242/c8d3_gmp').is_file()and 'moved aside'in cp.stdout and 'risk 32'in cp.stdout,(cp.returncode,cp.stdout[-600:])
    # only the optional bookkeeping fails (the sweep's accounting): bin/ stays, no risk-32 loop, the two commands to rerun are named
    spb=d/'swpkg_bld';(spb/'tools').mkdir(parents=True,exist_ok=True)
    D=data('d9d9d9d9d9d9');cp,log=run(D,'bld',C8_BLD_BASE_PKG=BASE,C8_SWEEP_RUN=str(R),C8_SWEEP_PKG=str(spb),C8_TEST_PYFAIL='tools/accounting.py')
    summ={x['step']:x['status']for x in json.loads((ev_of('d9d9d9d9d9d9','bld_4242')/'summary.json').read_text())['steps']}
    assert cp.returncode==1 and summ['sweep_accounting']=='FAIL'and all(v=='PASS'for k,v in summ.items()if k!='sweep_accounting'),(summ,cp.stdout[-800:])
    assert (D/'bin/c8d3_gmp').is_file()and not list(D.glob('bin.bld_failed_*'))and 'moved aside'not in cp.stdout and 'risk 32'not in cp.stdout,(cp.stdout[-800:])
    assert "only the sweep's bookkeeping"in cp.stdout and f'cd {spb} && python3 -B tools/accounting.py {R} --json'in cp.stdout and 'tools/cost_summary.py'in cp.stdout,cp.stdout[-800:]
    # the base's tool judges: a data export whose own (changed) tools/cost_identity.py approves anything still fails, naming the tool
    fake_ci="import json,sys\na=sys.argv;open(a[a.index('--output')+1],'w').write(json.dumps({'ok':True,'outside':[],'differences':[]}));print('{\"ok\": true}')\n"
    D=data('dadadadadada',extra={'tools/cost_identity.py':fake_ci});cp,log=run(D,'bld',C8_BLD_BASE_PKG=BASE)
    dd=json.loads((ev_of('dadadadadada','bld_4242')/'data_only_diff.json').read_text())
    assert cp.returncode==1 and dd['outside']==['tools/cost_identity.py']and 'link-l8'not in log and not (D/'bin').exists(),(cp.returncode,dd,log)
    D=data('d2d2d2d2d2d2',extra={'tools/foo.py':'x=1\n'});cp,log=run(D,'bld',C8_BLD_BASE_PKG=BASE)
    dd=json.loads((ev_of('d2d2d2d2d2d2','bld_4242')/'data_only_diff.json').read_text())
    assert cp.returncode==1 and 'link-l8'not in log and 'make 'not in log and not (D/'bin').exists()and dd['outside']==['tools/foo.py'],(cp.returncode,log,dd)
    D=data('d3d3d3d3d3d3');(D/'bin').mkdir();(D/'bin/c8d3_gmp').write_text('x')
    Dm=export('d4d4d4d4d4d4',extra={'benchmarks/x/y.json':'{}\n'})
    Ds=data('dbdbdbdbdbdb');(root/'pkg'/'a1a1a1a1a1a1').symlink_to(Ds)   # the data export itself, by its own name or through an alias
    old_base=export('b1b1b1b1b1b1',extra={'tools/cost_identity.py':'# an older cost_identity.py without the data-only check\n'})
    for pkg,x,why in ((D,{'C8_BLD_BASE_PKG':BASE},'bin/c8d3_gmp exists'),(Dm,{'C8_BLD_BASE_PKG':BASE},'gmp_symmetry_epyc7543_c8.json is missing'),
                      (data('d5d5d5d5d5d5'),{},'C8_BLD_BASE_PKG'),(data('d6d6d6d6d6d6'),{'C8_BLD_BASE_PKG':'abcabcabcabc'},'C8_BLD_BASE_PKG'),
                      (data('d7d7d7d7d7d7'),{'C8_BLD_BASE_PKG':BASE,'C8_SWEEP_RUN':str(R)},'together, or neither'),
                      (data('d8d8d8d8d8d8'),{'C8_BLD_BASE_PKG':'d8d8d8d8d8d8'},'is the data export itself'),
                      (Ds,{'C8_BLD_BASE_PKG':'a1a1a1a1a1a1'},'is the data export itself'),
                      (data('dcdcdcdcdcdc'),{'C8_BLD_BASE_PKG':'b1b1b1b1b1b1'},'no data-only check')):
        cp,log=run(pkg,'bld',**x);assert cp.returncode==64 and why in cp.stderr and not (root/'evidence'/pkg.name).exists(),(pkg.name,cp.returncode,cp.stderr[-300:])
    ok('bld (J-BLD): in the export itself, the BASE export\'s data-only check first, then make link-l8, make verify-inputs, the workers, check_build '
       '(symmetry), cost_identity.py check --model cost_models/<site model> --host-cpu --mp-check on; rc 0 with bin/ kept; HD11 failing moves bin/ to '
       'bin.bld_failed_<id> (risk 32); a failed sweep bookkeeping step alone keeps bin/ and names the rerun (no risk 32); a tools/ change fails the '
       'data-only check with nothing linked or built, even when the data export\'s own cost_identity.py would approve it; 64 for an existing '
       'bin/c8d3_gmp, a missing site model, a missing or foreign base, the data export itself as base (by name or alias), a base without the '
       'data-only check, C8_SWEEP_RUN without C8_SWEEP_PKG, with no evidence')
    # ---------------------------------------------------------------- copy_export: a built export is copied without bin/ and the L8 links
    B=data('e0e0e0e0e0e0');(B/'bin').mkdir();(B/'bin/c8d3_gmp').write_text('stale');(B/'inputs/packs').mkdir(parents=True);(B/'inputs/packs/free_L8.pack').write_text('pack')
    cp,log=run(B,'val1');W=root/'work'/'val1_4242'
    assert 'built export: bin/ and the L8 pack links are not copied'in cp.stdout and (W/'marker.txt').is_file(),(cp.returncode,cp.stdout[-800:])
    assert not (W/'bin/c8d3_gmp').exists()and not (W/'inputs/packs/free_L8.pack').exists(),sorted(str(p.relative_to(W))for p in W.rglob('*'))[:40]
    P=export('e1e1e1e1e1e1');cp,log=run(P,'val1');W=root/'work'/'val1_4242'
    assert 'built export'not in cp.stdout and (W/'marker.txt').is_file()and (W/'Makefile').is_file(),cp.stdout[-600:]
    # every other copy of an export takes copy_export too: basestore's BASE copy and opt's PREV copy of a built export carry
    # neither its bin/ nor its L8 pack links (both are rebuilt there); opt's variant copy calls it as well (static: the only
    # cp -a of the script is copy_export's own)
    def built(sha12):
        X=export(sha12);(X/'bin').mkdir();(X/'bin/c8d3_gmp').write_text('stale');(X/'bin/stale_marker').write_text('x')
        (X/'inputs/packs').mkdir(parents=True);(X/'inputs/packs/free_L8.pack').write_text('pack');return X
    XB=built('e2e2e2e2e2e2');cp,log=run(P,'basestore',C8_BASE_PKG=XB.name);BP=node/f'base_{XB.name}'
    assert 'built export: bin/ and the L8 pack links are not copied'in cp.stdout and (BP/'marker.txt').is_file(),(cp.returncode,cp.stdout[-800:],cp.stderr[-400:])
    assert not (BP/'bin/stale_marker').exists()and not (BP/'inputs/packs/free_L8.pack').exists()and f'make -j 4 CXX=g++ PYTHON=python3 bin/c8d3_gmp bin/c8d3_decimal @ {BP}'in log,(sorted(str(x.relative_to(BP))for x in BP.rglob('*')),log)
    sh2=d/'shims_opt';sh2.mkdir(exist_ok=True)   # what opt's preamble needs beyond the shared shims (no numactl, BSD ps and no sha256sum on the Mac PATH)
    for name,body in (('numactl','exit 0'),('ps','exit 0'),('sha256sum','for f in "$@"; do echo "0000  $f"; done; exit 0')):(sh2/name).write_text('#!/bin/bash\n'+body+'\n');(sh2/name).chmod(0o755)
    XP=built('e3e3e3e3e3e3');cp,log=run(P,'opt',C8_OPT_STEP='final',C8_OPT_PREV_PKG=XP.name,PATH=f'{shims}:{sh2}:/usr/bin:/bin');PB=node/f'prev_{XP.name}'
    assert lines(cp.stdout,'built export')and (PB/'marker.txt').is_file()and not (PB/'bin/stale_marker').exists()and not (PB/'inputs/packs/free_L8.pack').exists(),(cp.returncode,cp.stdout[-800:],cp.stderr[-400:])
    assert f'make -j 32 CXX=g++ PYTHON=python3 bin/c8d3_gmp bin/c8d3_decimal @ {PB}'in log,log
    nj=(ROOT/'slurm/native_job.sh').read_text();code=[l for l in nj.splitlines()if not l.lstrip().startswith('#')]
    cpa=[l for l in code if 'cp -a'in l];assert len(cpa)==1 and 'then cp -a "$s/." "$d/"; return; fi'in cpa[0]and len([l for l in code if 'copy_export "$C8_'in l])==4,[l for l in code if 'cp -a'in l or 'copy_export'in l]
    assert 'step variant_copy copy_export "$C8_PACKAGE" "$VW"'in nj
    ok('copy_export: native jobs on a built export copy neither bin/ nor the L8 pack links (logged "built export"); a pristine export takes cp -a; '
       'basestore\'s BASE copy and opt\'s PREV copy of a built export skip them too (rebuilt there), and opt\'s variant copy uses copy_export (the '
       'script\'s only cp -a is copy_export\'s own)')
    # ---------------------------------------------------------------- the site-named model of sweep1, argmax and argmaxre
    for site,proc,sha12,model in (('expanse',p42,'f0f0f0f0f0f0','gmp_expanse_epyc7742_c8.json'),('symmetry',p43,'f1f1f1f1f1f1','gmp_symmetry_epyc7543_c8.json')):
        env_file(site,**({'C8_GMP':'/spack/gmp-6.2.1'}if site=='expanse'else{}));X=export(sha12,model=model)
        cp,log=run(X,'sweep1',C8_SWEEP_RUN=str(runs/f'sweep1-{site}'),C8_SWEEP_SEED='5',C8_PROC=str(proc))
        ev1=ev_of(sha12,'sweep1')
        assert f'tools/sweep.py {runs}/sweep1-{site} --seed 5 --output {ev1}/{model} --forbid-seeds-from {seeds} --reserve-seed {seeds} --scratch {node} @'in log,(site,log)
        am=runs/f'argmax-{site}';sw=runs/f'sweep1-{site}';spkg=root/'work'/'sweep1_4242'
        (root/'store/baseline/aaaaaaaaaaaa').mkdir(parents=True,exist_ok=True);(root/'store/baseline/aaaaaaaaaaaa/SHA256SUMS').write_text('')
        sp=d/f'swpkg_{site}';(sp/'tools').mkdir(parents=True,exist_ok=True)
        cp,log=run(X,'argmax',C8_ARGMAX_RUN=str(am),C8_ARGMAX_SEED='6',C8_SWEEP_RUN=str(sw),C8_SWEEP_PKG=str(sp),C8_BASELINE_SHA12='aaaaaaaaaaaa',C8_PROC=str(proc))
        assert f'tools/cost_identity.py check --model cost_models/{model} --exe bin/c8d3_gmp @'in log and f'--cost-model cost_models/{model} --seed 6'in log,(site,cp.stderr[-400:],log)
        assert f'tools/cost_summary.py {sw} cost_models/{model} --symmetry-model cost_models/gmp_symmetry_epyc7532.json'in log,(site,log)
        (am).mkdir(exist_ok=True);(am/'manifest.json').write_text('{}')
        cp,log=run(X,'argmaxre',C8_ARGMAX_RUN=str(am),C8_ARGMAX_SEED='6',C8_PROC=str(proc));assert f'--reinspect --cost-model cost_models/{model} --seed 6'in log,(site,log)
    ok('sweep1, argmax and argmaxre name the site\'s model: Expanse $EV/gmp_expanse_epyc7742_c8.json and cost_models/gmp_expanse_epyc7742_c8.json (as before), '
       'symmetry gmp_symmetry_epyc7543_c8.json')

def main()->int:
    td=Path(tempfile.mkdtemp(prefix='c8d3_integration_3a_'))
    try:
        test_describe(td);test_run_gmp(td);test_row_forms(td);test_scratch(td);test_cpu_guard(td);test_vendor_guard(td);test_native_job_symmetry(td);test_native_job_stage5(td)
    finally:shutil.rmtree(td,ignore_errors=True)
    print(json.dumps({'status':'passed','tests':len(RESULTS)}));return 0
if __name__=='__main__':sys.exit(main())
