#!/usr/bin/env python3
"""Stage-6 fix round 4, group G4: the defects W14, W15 (with its class in tests/test_profiling.py's tool()) and W19
(with its class in P3) shown directly on the fakes of tests/test_profiling.py and the Owned helper of
tests/unit_orchestration.py (Mac; no measurement). Run once with 945e526's files and once with the fixed ones; each
run prints one JSON object.

  w19     p1 without perf (FAKE_PERF_REFUSE=1), the tier-timer worker differing on heavy_free_L8, --blocks heavy_free_L8
          (the finding's counterexample): exit code, errors, per-block binding
  w19_p3  p3 with a stale ratio-histogram build (one value of random_power_L8 differs): exit code, errors (945e526's p3
          has no --worker-exe; it then runs without it)
  tool    tests/test_profiling.py tool() with a 3 s timeout on a stand-in tool that starts a 120 s worker and hangs:
          whether the worker survives the timeout (it is killed afterwards either way)
  w14     Owned: a session leader starts an unmarked helper and is reaped; survivors() then, and whether the helper
          survives a failure inside the scope (it is killed afterwards either way)
Usage: C8_ALLOW_NO_L8=1 python3 -B benchmarks/mac_2026-10-c8/fx4g4/fx4g4_demo.py"""
import json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_profiling as tp  # noqa: E402

def alive(pid):
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True

def gone_within(pid,seconds=5.):
    t0=time.time()
    while alive(pid)and time.time()-t0<seconds:time.sleep(0.05)
    return not alive(pid)

def main()->int:
    out={}
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=tp.mini_fixture(td);f=tp.fakes(td);base=['--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--perf',f['perf'],'--scratch',td]
        cp=tp.tool('perf_profile.py','p1',*base,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_free_L8','--output',td/'w19',
                   env={'C8_FAKE_DIAG_SKEW':'heavy_free_L8','FAKE_PERF_REFUSE':'1'})
        r=json.loads((td/'w19/p1.json').read_text())
        out['w19']={'exit':cp.returncode,'errors':r['errors'],'rows_identical':{b:x.get('rows_identical_worker_vs_prof')for b,x in r['blocks'].items()},
                    'fallback_binding':r['fallback'].get('binding')}
        p3=['p3',*base,'--threads',8,'--exe',f['ratio'],'--blocks','random_power_L8','--rates','.8']
        cp=tp.tool('perf_profile.py',*p3,*(['--worker-exe',f['rel']]if 'rel'in f else[]),'--output',td/'p3',env={'C8_FAKE_DIAG_SKEW':'random_power_L8'})
        if cp.returncode==2 and 'unrecognized arguments'in cp.stderr:cp=tp.tool('perf_profile.py',*p3,'--output',td/'p3',env={'C8_FAKE_DIAG_SKEW':'random_power_L8'})
        r=json.loads((td/'p3/p3.json').read_text())if (td/'p3/p3.json').is_file()else{}
        out['w19_p3']={'exit':cp.returncode,'errors':r.get('errors'),'all_checks_ok':r.get('all_checks_ok'),
                       'rows_identical':{k:x.get('rows_identical_worker_vs_ratiohist')for k,x in (r.get('results')or{}).items()}}
        hang=td/'hang.py';hang.write_text(tp.HANG if hasattr(tp,'HANG')else'import subprocess,sys,time\nc=subprocess.Popen([sys.executable,"-c","import time;time.sleep(120)","fx4g4-grandchild"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\nopen(sys.argv[1],"w").write(str(c.pid))\ntime.sleep(120)\n')
        pidf=td/'worker.pid';t0=time.time()
        try:tp.tool(hang,pidf,timeout=3)if 'timeout'in tp.tool.__code__.co_varnames else subprocess.run([sys.executable,'-B',str(hang),str(pidf)],capture_output=True,text=True,timeout=3)
        except subprocess.TimeoutExpired:pass
        w=int(pidf.read_text());survived=not gone_within(w)
        if alive(w):os.kill(w,signal.SIGKILL)
        out['tool']={'worker_survived_the_timeout':survived,'seconds':round(time.time()-t0,1)}
    # W14 (imports the orchestration test module only for its Owned and proc_table; no package copy, no test run)
    import unit_orchestration as uo
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);src=td/'leader.py';src.write_text(uo.W14_LEADER if hasattr(uo,'W14_LEADER')else
            "import subprocess,sys\nh=subprocess.Popen([sys.executable,'-c','import time;time.sleep(300)','w14-unmarked-helper'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\nopen(sys.argv[1],'w').write(str(h.pid))\n")
        pidf=td/'helper.pid';dn=subprocess.DEVNULL;own=uo.Owned(markers=(str(pidf),));helper=None;listed=None
        try:
            with own:
                leader=own.add(subprocess.Popen([sys.executable,'-S',str(src),str(pidf)],stdin=dn,stdout=dn,stderr=dn,start_new_session=True))
                leader.wait(timeout=60);helper=int(pidf.read_text());listed=[pid for pid,pg,_ in own.survivors()if pg==leader.pid]
                raise AssertionError('deliberate failure after the leader was reaped')
        except AssertionError as e:msg=str(e)
        survived=helper is not None and not gone_within(helper)
        if helper is not None and alive(helper):os.kill(helper,signal.SIGKILL)
        out['w14']={'survivors_in_the_leaders_group_after_reaping':listed==[helper]if listed is not None else None,'helper_in_failure_evidence':str(helper)in msg,
                    'helper_survived_the_cleanup':survived,'killed':[pid for pid,_ in own.killed]==[helper]}
    print(json.dumps(out,indent=1));return 0

if __name__=='__main__':sys.exit(main())
