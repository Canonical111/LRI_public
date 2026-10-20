import os,sys
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('MKL_NUM_THREADS','1')
os.environ.setdefault('NUMBA_NUM_THREADS','4')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'reference')]
from threadpoolctl import threadpool_limits
from numba import set_num_threads
threadpool_limits(1);set_num_threads(1)
