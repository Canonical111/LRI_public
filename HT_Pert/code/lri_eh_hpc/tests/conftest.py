import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'reference/original/code'));sys.path.insert(0,str(ROOT/'reference/original/tests'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('MKL_NUM_THREADS','1');os.environ.setdefault('NUMBA_NUM_THREADS','4')
from numba import set_num_threads
set_num_threads(4)
