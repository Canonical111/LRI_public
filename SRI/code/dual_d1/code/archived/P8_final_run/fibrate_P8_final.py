from pathlib import Path
import json,hashlib,time,subprocess
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion');src=R/'P8_moving5_sum';out=src/'moving_total.jsonl'
while len(list(src.glob('b*.report.json')))<64:time.sleep(2)
with out.with_suffix('.tmp').open('wb') as f:
 n=0
 for i in range(64):
  p=src/f'b{i:03d}.jsonl';rep=json.loads((src/f'b{i:03d}.report.json').read_text());assert rep['complete'] and rep['output_sha256']==hashlib.sha256(p.read_bytes()).hexdigest();f.write(p.read_bytes());n+=rep['output_rows']
out.with_suffix('.tmp').replace(out)
print('ALL_MOVING5',n,flush=True)
subprocess.run(['python','-u','/mnt/data/P8_final_run/terminal_fibration.py',str(out),str(R/'P8_terminal_fibration'),'256'],check=True)
