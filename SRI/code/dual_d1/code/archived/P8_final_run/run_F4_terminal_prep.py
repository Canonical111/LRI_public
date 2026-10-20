from pathlib import Path
import subprocess,time,json
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion')
for name in ['F4_Z8','F4_EZ6','F4_EA7','F4_A9']:
 folder=R/name
 while not (folder/'source_manifest.json').exists():time.sleep(2)
 meta=json.loads((folder/'source_manifest.json').read_text());nb=meta['buckets']
 while len(list(folder.glob('moving_b*.report.json')))<nb:time.sleep(3)
 if not (folder/'moving_total_report.json').exists():
  with (folder/'collect.log').open('w') as f:subprocess.run(['python','-u','collect_F4_moving.py',name],cwd=R/'engine',stdout=f,stderr=subprocess.STDOUT,check=True)
 dest=folder/'terminal_fibration';dest.mkdir(exist_ok=True)
 if not (dest/'report.json').exists():
  with (folder/'fibrate.log').open('w') as f:subprocess.run(['python','-u','/mnt/data/P8_final_run/terminal_fibration.py',str(folder/'moving_total.jsonl'),str(dest),'64'],stdout=f,stderr=subprocess.STDOUT,check=True)
 with (folder/'apart.log').open('w') as f:subprocess.run(['python','-u','precompute_terminal_apart.py',str(dest)],cwd=R/'engine',stdout=f,stderr=subprocess.STDOUT,check=True)
 print('F4_READY_TERMINAL',name,flush=True)
