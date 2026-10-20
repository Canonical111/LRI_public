from pathlib import Path
import subprocess,time
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');f=R/'P8_terminal_fibration'
while not (f/'prefactor_apart_report.json').exists():time.sleep(3)
ld=f/'terminal_reverse_logs';ld.mkdir(exist_ok=True)
for i in reversed(range(128,256)):
 with (ld/f'b{i:03d}.log').open('w') as log:subprocess.run(['python','-u','/mnt/data/P8_final_run/evaluate_terminal_bucket.py',str(f),str(i),'7','0','1'],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('REVERSE_TERMINAL',i,flush=True)
