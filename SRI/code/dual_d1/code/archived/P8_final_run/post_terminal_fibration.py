from pathlib import Path
import json,subprocess,time,concurrent.futures,sys
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');folder=R/'P8_terminal_fibration'
while not (folder/'report.json').exists():time.sleep(3)
subprocess.run(['python','-u','precompute_terminal_apart.py',str(folder)],cwd=R/'engine',check=True)
logdir=folder/'terminal_logs';logdir.mkdir(exist_ok=True)
def work(i):
 with (logdir/f'b{i:03d}.log').open('w') as f:subprocess.run(['python','-u','/mnt/data/P8_final_run/evaluate_terminal_bucket.py',str(folder),str(i),'7','0','1'],stdout=f,stderr=subprocess.STDOUT,check=True)
 return i
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for i in pool.map(work,range(256)):print('P8_TERMINAL_DONE',i,flush=True)
