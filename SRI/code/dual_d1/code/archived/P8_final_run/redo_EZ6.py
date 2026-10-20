from pathlib import Path
import subprocess,json,os,concurrent.futures
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');folder=R/'F4_EZ6';e=R/'engine';dest=folder/'terminal_fibration'
subprocess.run(['python','-u','integrate_F4_lastinner.py','F4_EZ6','0'],cwd=e,check=True)
subprocess.run(['python','-u','collect_F4_moving.py','F4_EZ6'],cwd=e,check=True)
subprocess.run(['python','-u','/mnt/data/P8_final_run/terminal_fibration.py',str(folder/'moving_total.jsonl'),str(dest),'64'],check=True)
subprocess.run(['python','-u','precompute_terminal_apart.py',str(dest)],cwd=e,check=True)
ld=dest/'terminal_logs';ld.mkdir(exist_ok=True)
def work(i):
 with (ld/f'b{i:03d}.log').open('w') as f:subprocess.run(['python','-u','/mnt/data/P8_final_run/evaluate_terminal_bucket.py',str(dest),str(i),'5','0','0'],stdout=f,stderr=subprocess.STDOUT,check=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(work,range(64)))
subprocess.run(['python','-u','/mnt/data/P8_final_run/finalize_terminal_target.py',str(folder),'EZ6_Gonly','1'],check=True)
subprocess.run(['python','/mnt/data/P8_final_run/restore_endpoint_offsets.py'],check=True)
print('CORRECTED_EZ6_COMPLETE',flush=True)
