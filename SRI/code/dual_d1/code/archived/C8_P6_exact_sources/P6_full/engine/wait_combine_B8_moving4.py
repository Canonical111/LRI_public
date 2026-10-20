from pathlib import Path
import time,subprocess,sys
ROOT=Path(__file__).resolve().parent.parent
while not all((ROOT/'B8_moving4'/f'b{i:03}'/'report.json').exists() for i in range(64)):time.sleep(4)
subprocess.run([sys.executable,'-u',str(ROOT/'engine/combine_B8_moving4.py')],check=True)
