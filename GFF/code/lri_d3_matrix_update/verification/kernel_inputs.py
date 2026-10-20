"""Exact graph weights and precision-preserving meromorphic quadrature rows."""
from __future__ import annotations
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from pathlib import Path
import sys
import numpy as np
import mpmath as mp
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source'))
import ising_five_loop as original

def graph_file(folder:Path,combined:bool=False)->Path:
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'graphs6.bin'
    if path.exists():
        count=49605 if combined else 59145
        if path.stat().st_size!=count*17*4:raise ValueError('Graph cache has an unexpected size')
        return path
    gg=original.graphs(6)
    if len(gg)!=59145:raise AssertionError('Graph enumeration count changed')
    if not all((144*a).denominator==1 and (144*b).denominator==1 for _,a,b in gg):
        raise AssertionError('Scaled graph weights are not all integers')
    data=np.asarray([list(w)+[int(144*a),int(144*b)]for w,a,b in gg],dtype='<i4')
    if combined:
        weights=3*data[:,16]-data[:,15]
        keep=weights!=0
        data=data[keep].copy();data[:,15]=weights[keep];data[:,16]=0
        if len(data)!=49605:raise AssertionError('Combined graph count changed')
    data.tofile(path)
    return path

def weight_file(folder:Path,N:int,extended:bool=True)->Path:
    if N<4 or N>32:raise ValueError('Use an interpolation degree between 4 and 32')
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/f'qweights5_{N}.bin'
    dtype=np.longdouble if extended else np.float64
    expected=4*11*5*(N+1)*np.dtype(dtype).itemsize
    if path.exists():
        if path.stat().st_size!=expected:raise ValueError('Weight cache precision/size mismatch')
        return path
    if not extended:
        original.prepare_weights(folder,N)
        return path
    if np.finfo(np.longdouble).nmant<63:
        raise RuntimeError('This control requires at least a 64-bit long-double significand')
    mp.mp.dps=max(80,2*N+30)
    polynomials=original.chebpoly(N)
    cosines=[[mp.cos(mp.pi*k*i/N)for k in range(N+1)]for i in range(N+1)]
    half=mp.mpf('.5');out=np.zeros((4,11,5,N+1),dtype=dtype)
    for axis in range(4):
        for b2 in range(11):
            a2=2*(3-axis)-b2;a=mp.mpf(a2)/2;b=mp.mpf(b2)/2
            jr=int(-a-1) if a2<=-2 and a2%2==0 else -1
            moments=[]
            for poly in polynomials:
                row=[]
                for r in (-1,0,1,2,3):
                    if r==-1:value=mp.mpf(poly[jr])/b if 0<=jr<len(poly)else mp.mpf(0)
                    else:value=mp.fsum(mp.mpf(c)*(-b)**r/(mp.mpf(k)+a+1)**(r+1)for k,c in enumerate(poly)if k!=jr)
                    row.append(value)
                moments.append(row)
            for i in range(N+1):
                factor=mp.mpf(2)/N*(half if i in (0,N)else 1)
                for r in range(5):
                    value=factor*mp.fsum((half if k in (0,N)else 1)*cosines[i][k]*moments[k][r]for k in range(N+1))
                    out[axis,b2,r,i]=np.longdouble(str(value))
            if jr==0:
                out[axis,b2,0,:]=0;out[axis,b2,0,-1]=np.longdouble(str(1/b))
    out.tofile(path)
    return path
