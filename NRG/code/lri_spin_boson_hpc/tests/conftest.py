from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
sys.path.insert(0,str(root/'reference'))
