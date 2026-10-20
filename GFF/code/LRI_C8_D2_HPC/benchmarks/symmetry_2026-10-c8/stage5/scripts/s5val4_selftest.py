#!/usr/bin/env python3
"""J-VAL-4 self-test on symmetry's GCC 11.4, run beside tests/sanitize.py (which ran without --selftest in this job).
tests/sanitize.py --selftest reads only the probe's stderr; libstdc++ of GCC <= 12 reports a failed _GLIBCXX_ASSERTIONS
check with __builtin_printf on STDOUT (std::__replacement_assert) and then aborts, so with stdout on a pipe the buffered
message is discarded and the glibcxx probe aborts (SIGABRT) with no visible report (job 570030). This helper builds
the same three probes with sanitize.py's own san_command and PROBES (imported, unchanged) and runs each twice:
  piped:  exactly as sanitize.py does (capture_output) -> exit code, stderr, stdout;
  pty:    under `script -qec PROBE /dev/null` (stdout a terminal, line-buffered) -> the combined text.
Pass: every probe exits non-zero in both runs, and its expected report appears in the piped stderr or (for the
glibcxx probe) in the pty text. Writes JSON to argv[2].   python3 s5val4_selftest.py PACKAGE OUT.json"""
import json,os,shlex,subprocess,sys,tempfile
from pathlib import Path
pkg=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]);sys.path.insert(0,str(pkg/'tests'));sys.path.insert(0,str(pkg/'tools'))
os.chdir(pkg)
import sanitize as S
res=[];ok=True
with tempfile.TemporaryDirectory(prefix='c8d2_selftest_')as td:
    td=Path(td)
    for name,(code,expect) in S.PROBES.items():
        src=td/f'probe_{name}.cpp';src.write_text(code);exe=td/f'probe_{name}'
        cmd=S.san_command([src],exe)+[f'-I{pkg}'];subprocess.run(cmd,check=True)
        p=subprocess.run([exe],capture_output=True,text=True,env=S.ENV)
        q=subprocess.run(['script','-qec',shlex.quote(str(exe)),'/dev/null'],capture_output=True,text=True,env=S.ENV)
        piped_hit=expect in p.stderr;pty_hit=expect in q.stdout
        passed=p.returncode!=0 and q.returncode!=0 and (piped_hit or pty_hit)
        ok&=passed
        line=next((l for l in (p.stderr+q.stdout).splitlines()if expect in l),'')
        res.append({'probe':name,'expected':expect,'compile':cmd,'piped':{'exit':p.returncode,'stderr_has_report':piped_hit,'stderr_tail':p.stderr[-400:],'stdout_tail':p.stdout[-400:]},
                    'pty':{'exit':q.returncode,'has_report':pty_hit,'tail':q.stdout[-600:]},'report':line[:300],'passed':passed})
        print(json.dumps({k:res[-1][k]for k in('probe','report','passed')}|{'piped_exit':p.returncode,'pty_exit':q.returncode}),flush=True)
doc={'test':'sanitize self-test (symmetry GCC 11.4 helper)','passed':ok,'probes':res,'compiler':subprocess.run(['g++','--version'],capture_output=True,text=True).stdout.splitlines()[0]}
out.write_text(json.dumps(doc,indent=1)+'\n');sys.exit(0 if ok else 1)
