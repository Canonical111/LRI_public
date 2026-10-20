import os,sys
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('MKL_NUM_THREADS','1')
os.environ.setdefault('NUMBA_NUM_THREADS','4')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'reference/original_code'),str(ROOT/'reference'),str(ROOT/'reference/original_tests')]
import numba
numba.set_num_threads(2)
