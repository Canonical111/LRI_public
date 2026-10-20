from pathlib import Path
import subprocess,time
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');f=R/'P8_terminal_fibration';ld=f/'terminal_middle_logs';ld.mkdir(exist_ok=True)
while not (f/'prefactor_apart_report.json').exists():time.sleep(2)
for i in range(128,192):
 with (ld/f'b{i:03d}.log').open('w') as log:subprocess.run(['python','-u','/mnt/data/P8_final_run/evaluate_terminal_bucket.py',str(f),str(i),'7','0','1'],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('MIDDLE_TERMINAL',i,flush=True)
