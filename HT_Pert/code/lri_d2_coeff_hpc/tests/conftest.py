from pathlib import Path
import os,sys
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('MKL_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','4');os.environ.setdefault('NUMBA_NUM_THREADS','4')
os.environ.setdefault('LRI_COEFF_NATIVE_CACHE',str(ROOT.parent/'lri_coeff_nativecache'))
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'reference/lri_d2_perturbative_C8/code'))
