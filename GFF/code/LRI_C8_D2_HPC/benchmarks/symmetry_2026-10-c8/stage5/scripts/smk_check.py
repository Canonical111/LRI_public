#!/usr/bin/env python3
"""A-SMK-1 / A-ORC-5 record of the L8 smoke (symmetry Stage 5), read-only on the campaign:
  smk_check.py PACKAGE RUN --rchar-dir DIR --submit-log FILE --seeds LOG --output OUT.json
- production.py status RUN (exit code), the 24 merged.json, C8_test_result.json (its label and gate blocks),
  tools/verify_result.py on it (exit code), lanes/failures/ empty, lane-worker logs ("8 lane(s) of [8 x 8] CPUs");
- the smoke seed (manifest seed) in the seed log;
- the admission line(s) of the submission log (amd_live + k <= amd_cap);
- per index: the measured peak RSS = the run process's own ru_maxrss + its largest reaped child's ru_maxrss (the native),
  from the measurement hook (scripts/rchar_hook), against 1.2 x est_peak_bytes."""
import argparse,glob,json,re,subprocess,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('package',type=Path);ap.add_argument('run',type=Path);ap.add_argument('--rchar-dir',type=Path)
ap.add_argument('--submit-log',type=Path);ap.add_argument('--seeds',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
run=a.run.resolve();py=[sys.executable,'-B'];m=json.loads((run/'manifest.json').read_text());rec={'campaign':str(run)}
st=subprocess.run([*py,str(a.package/'tools/production.py'),'status',str(run),'--fast'],capture_output=True,text=True);rec['status_exit']=st.returncode;rec['status_tail']=st.stdout[-600:]
mj=sorted(glob.glob(str(run/'groups/*/merged.json')));rec['merged_json']=len(mj)
res=run/'C8_test_result.json'
if res.exists():
    d=json.loads(res.read_text());rec['result_label']=d.get('label')or d.get('kind')or d.get('status');rec['result_keys']=sorted(d.keys())
    rec['result_gate_blocks']=sorted(k for k in d if 'gate'in k.lower()or k in('checks','assembly_gates','compatibility','power_protocol'))
    vr=subprocess.run([*py,str(a.package/'tools/verify_result.py'),str(res)],capture_output=True,text=True);rec['verify_result_exit']=vr.returncode;rec['verify_result_tail']=(vr.stdout+vr.stderr)[-600:]
fails=list((run/'lanes/failures').glob('*'))if (run/'lanes/failures').exists()else[];rec['lane_failures']=len(fails)
shapes=[]
for f in sorted(glob.glob(str(run/'slurm_logs/lane-*.log'))):
    t=Path(f).read_text(errors='replace');mt=re.search(r'(\d+) lane\(s\) of (\[[^\]]*\]) CPUs \(([^)]*)\)',t);shapes.append({'log':Path(f).name,'lanes':mt and int(mt.group(1)),'cpus':mt and mt.group(2),'how':mt and mt.group(3),
        'cpu_model':(re.search(r'on (\S+) \(([^)]*)\)',t)or[None,None,None])[2],'exit_codes':(re.search(r'lane exit codes (\[[^\]]*\])',t)or[None,None])[1]})
rec['lane_workers']=shapes
seed=int(m['seed']);rec['seed']=seed
if a.seeds and a.seeds.exists():
    lg=json.loads(a.seeds.read_text());rec['seed_in_log']=[e.get('source')for e in lg.get('seeds',[])if int(e['seed'])==seed]
if a.submit_log and a.submit_log.exists():
    adm=[json.loads(l.split('C8: admission ',1)[1])for l in a.submit_log.read_text().splitlines()if l.startswith('C8: admission ')]
    rec['admission']=adm;rec['admission_within_cap']=all((x.get('amd_live',0)+x.get('k',0))<=x.get('amd_cap',4)for x in adm)
rss=[]
if a.rchar_dir and a.rchar_dir.exists():
    for f in sorted(a.rchar_dir.glob('rchar.*.json')):
        r=json.loads(f.read_text());i=int(r['index']);est=m['jobs'][i]['est_peak_bytes'];meas=(r['ru_maxrss_self_kb']+r['ru_maxrss_children_kb'])*1024
        rss.append({'index':i,'group':m['jobs'][i]['group'],'measured_bytes':meas,'python_kb':r['ru_maxrss_self_kb'],'native_kb':r['ru_maxrss_children_kb'],'est_peak_bytes':est,'ratio':meas/est})
rec['peak_rss']={'indices':len(rss),'max_ratio':max((x['ratio']for x in rss),default=None),'all_within_1.2':all(x['ratio']<=1.2 for x in rss)if rss else None,'rows':rss}
a.output.write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps({k:v for k,v in rec.items()if k not in('peak_rss','result_keys')}|{'peak_rss_max_ratio':rec['peak_rss']['max_ratio'],'peak_rss_indices':rec['peak_rss']['indices']},indent=1)[:4000])
