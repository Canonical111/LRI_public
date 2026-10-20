from pathlib import Path
import time,subprocess,sys
W=Path(__file__).resolve().parents[1]
while not (W/'records/power_coarseA_L7_N1.json').exists():time.sleep(2)
subprocess.run([sys.executable,str(W/'code/run_power_production.py'),'refine5'],check=True)
