#!/usr/bin/env python3
"""Verify the full C7 period identity and input map without third-party packages."""
from pathlib import Path
import argparse,json,subprocess,sys,time

def main():
 if not __debug__:raise RuntimeError('Do not run this program with Python -O')
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--algebra',action='store_true',help='Also run optional SymPy fixed-point/thermal algebra checks')
 p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'verification/replay')
 args=p.parse_args();root=Path(__file__).resolve().parent;out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 jobs=[('input_map',[sys.executable,str(root/'code/verify_input_map.py'),'--report',str(out/'input_map.json')]),
 ('free_word_certificate',[sys.executable,str(root/'proof/verify_C7_certificate.py'),'--prefix',str(root/'proof/C7'),'--report',str(out/'free_word.json')])]
 if args.algebra:jobs += [('full_jacobian',[sys.executable,str(root/'code/derive_D4.py')]),('thermal_conversion',[sys.executable,str(root/'code/check_thermal_algebra.py')])]
 records=[]
 for name,cmd in jobs:
  print('RUN',name,flush=True);start=time.perf_counter()
  with (out/(name+'.log')).open('w') as stream:
   proc=subprocess.Popen(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   for line in proc.stdout:print(line,end='',flush=True);stream.write(line)
   code=proc.wait()
  records.append({'check':name,'exit_status':code,'seconds':time.perf_counter()-start})
  (out/'summary.json').write_text(json.dumps({'status':'PASS' if all(x['exit_status']==0 for x in records) else 'FAIL','checks':records},indent=2)+'\n')
  if code:raise SystemExit(code)
 print('PASS: all requested checks completed.',flush=True)
if __name__=='__main__':main()
