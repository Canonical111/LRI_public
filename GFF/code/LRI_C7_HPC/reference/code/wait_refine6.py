from pathlib import Path
import time,sys,subprocess
W=Path(__file__).resolve().parents[1]
while not (W/'records/tprodB_L7.json').exists():time.sleep(2)
subprocess.run([sys.executable,str(W/'code/run_power_production.py'),'refine6'],check=True)
