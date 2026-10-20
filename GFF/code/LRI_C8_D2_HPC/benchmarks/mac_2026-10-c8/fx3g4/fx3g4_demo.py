#!/usr/bin/env python3
"""Stage-6 fix round 3, group G4: the three defects (Z20, Z21, Z22) and the swept --interleave-probe case shown directly
on the fake worker, fake diagnostics and fake perf of tests/test_profiling.py (Mac; no measurement). Run once with the
tools of a42cfb7 (git stash of tools/) and once with the fixed tools; each run prints one JSON object.

  z20  p1, perf available, the tier-timer worker changes one value of one row on heavy_power_L8: exit code, errors
  z21  p3 with --expect-sha256 0000000000000000: exit code, whether p3.json was written, whether the worker ran
  z22  p1 --keep-perf-data without --keep-scratch: whether any perf.data survives (scratch or output)
  probe  benchmark.py --interleave-probe with --expect-sha256 0000000000000000: exit code, output written
Usage: C8_ALLOW_NO_L8=1 python3 -B benchmarks/mac_2026-10-c8/fx3g4/fx3g4_demo.py"""
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import test_profiling as tp  # noqa: E402

def main()->int:
    out={}
    with tempfile.TemporaryDirectory()as td:
        td=Path(td);fx=tp.mini_fixture(td);f=tp.fakes(td);base=['--fake-topology','2x2x2','--no-pin','--fixtures',fx,'--perf',f['perf']]
        cp=tp.tool('perf_profile.py','p1',*base,'--scratch',td,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_free_L8,heavy_power_L8',
                   '--no-srcline','--output',td/'z20',env={'C8_FAKE_DIAG_SKEW':'heavy_power_L8'})
        r=json.loads((td/'z20/p1.json').read_text())
        out['z20']={'exit':cp.returncode,'errors':r['errors'],'rows_identical':{b:x.get('rows_identical_worker_vs_prof')for b,x in r['blocks'].items()}}
        flog=td/'z21.log'
        cp=tp.tool('perf_profile.py','p3',*base,'--scratch',td,'--threads',8,'--exe',f['ratio'],'--blocks','random_power_L8','--rates','.8',
                   '--expect-sha256','0'*16,'--output',td/'z21',env={'C8_FAKE_LOG':str(flog)})
        out['z21']={'exit':cp.returncode,'p3_json_written':(td/'z21/p3.json').is_file(),'worker_runs':len(flog.read_text().splitlines())if flog.is_file()else 0,
                    'stderr':cp.stderr.strip()[-300:]}
        s=td/'s22';s.mkdir()
        cp=tp.tool('perf_profile.py','p1',*base,'--scratch',s,'--threads',4,'--exe',f['gmp'],'--prof-exe',f['prof'],'--blocks','heavy_free_L8,heavy_power_L8',
                   '--no-srcline','--keep-perf-data','--output',td/'z22')
        out['z22']={'exit':cp.returncode,'perf_data_files_surviving':sorted(str(p.relative_to(td))for p in td.rglob('*.perf.data'))}
        probe=tp.write_exe(td/'probe','import json\nprint(json.dumps({"speedup":{"2":1.1,"4":1.3},"identical":{"2":True,"4":True}}))\n')
        cp=tp.tool('benchmark.py','--interleave-probe','--probe-exe',probe,'--probe-graphs','nopromo_free_L8:1','--fake-topology','1x2x4','--no-pin','--fixtures',fx,
                   '--scratch',td,'--expect-sha256','0'*16,'--output',td/'probe_out')
        out['probe']={'exit':cp.returncode,'output_written':(td/'probe_out').exists(),'stderr':cp.stderr.strip()[-300:]}
    print(json.dumps(out,indent=1));return 0

if __name__=='__main__':sys.exit(main())
