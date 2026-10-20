from pathlib import Path
import subprocess,json,time,concurrent.futures
R=Path('/mnt/data/P8_final_run/F3_six_kink_completion')
for name in ['F4_Z8','F4_EZ6','F4_EA7','F4_A9']:
 folder=R/name;src=folder/'terminal_fibration'
 while not (src/'prefactor_apart_report.json').exists():time.sleep(3)
 meta=json.loads((folder/'source_manifest.json').read_text());nb=json.loads((src/'report.json').read_text())['sum_buckets'];ld=src/'terminal_logs';ld.mkdir(exist_ok=True)
 def work(i):
  with (ld/f'b{i:03d}.log').open('w') as f:subprocess.run(['python','-u','/mnt/data/P8_final_run/evaluate_terminal_bucket.py',str(src),str(i),str(meta['dimensionless_endpoint_offset']),str(meta['kappa']),str(int(meta['interval_factor']))],stdout=f,stderr=subprocess.STDOUT,check=True)
  return i
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for i in pool.map(work,range(nb)):print('F4_TERMINAL',name,i,flush=True)
