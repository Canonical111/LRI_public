"""Order-eight finite fixed-point assembly shared by the C8 tools.

coefficients() is the archived reference/code/assemble_coordinate.py algorithm with the slot count NW as a parameter
(NW=7 reproduces the C7 function exactly). A loop vector holds 2*NW values: channel A (beta) slots 0..NW-1 and
channel B (gamma) slots NW..2NW-1; slot i is the coefficient of z^(i-(L-1)), so b_L(z)=a[L-1:NW], c_L(z)=a[NW+L-1:2NW].
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
NW=8;NV=2*NW;TOP=8
# Reference values for the lower-order checks (exact unless stated).
REFS={2:0.6571312639810638,3:-3.719856322902,4:45.42488010356,5:-731.13947662454,6:14331.68703277}
REF_NOTES={2:'exact',3:'exact',4:'exact',5:'exact closed form',6:'exact all-graph sums, allowance 4.9e-7 (LRI_C6_1D_HPC)',7:'C7(1) = -322550 +/- 41 (SE 10.09), sampled, degree-6 estimator'}
C7_REF=(-322549.88881298894,10.087912951713953)

def coefficients(vals:dict,nw:int=NW)->np.ndarray:
    dtype=np.result_type(*[np.asarray(v).dtype for v in vals.values()]) if vals else float
    N=nw+1
    b={1:np.array([3.],dtype=dtype)};c={1:np.array([1.],dtype=dtype)}
    for L,a in vals.items():
        L=int(L);a=np.asarray(a)
        if a.shape!=(2*nw,):raise ValueError(f'loop {L}: expected {2*nw} values, got {a.shape}')
        b[L]=a[L-1:nw];c[L]=a[nw+L-1:2*nw]
    def mul(x,y):
        v=np.convolve(x,y)[:N];return np.pad(v,(0,N-len(v)))
    g=np.zeros(N,dtype=dtype);e=g.copy();e[1]=1
    for _ in range(N):
        gp=g.copy();temp=np.zeros(N,dtype=dtype)
        for L in range(2,N):
            gp=mul(gp,g);temp+=mul(b.get(L,np.zeros(1,dtype=dtype)),gp)
        g=(e-temp)/3
    ga=np.zeros(N,dtype=dtype);gp=np.zeros(N,dtype=dtype);gp[0]=1
    for L in range(1,N):
        gp=mul(gp,g);ga+=mul(c.get(L,np.zeros(1,dtype=dtype)),gp)
    ga[0]+=.5;ga[1]-=.5
    return ga

def jacobian(lower:dict,L:int,nw:int=NW)->np.ndarray:
    """d C / d v_L at the lower-loop point (complex step); exact for L>=5 because C_n (n<=8) is affine in those jets."""
    j=np.zeros((nw+1,2*nw))
    for k in range(2*nw):
        vv={i:np.asarray(a,dtype=complex) for i,a in lower.items()};vv[L]=np.zeros(2*nw,complex);vv[L][k]=1e-20j
        j[:,k]=coefficients(vv,nw).imag/1e-20
    return j

def load_vector(path:Path)->np.ndarray:
    d=json.loads(Path(path).read_text());b=np.array(d['batches'],dtype=float)
    if b.shape[1:]!=(NV,):raise ValueError(f'{path}: not a 16-value record')
    return b.mean(0)

def pole_columns(L:int)->list[int]:return list(range(L-1))+list(range(NW,NW+L-1))

# Canonical sampled-campaign specification shared by planning (production8) and assembly (assemble8):
# level -> (mode, role, degrees). Telescoping: coarse Q1 + (Q3-Q1) + (Q5-Q3) + (Q6-Q5) + (Q7-Q6) + (Q8-Q7) = Q8;
# refine9 (Q9-Q8) is a convergence check that never enters the estimate.
LEVEL_SPEC={'free':('qmc','estimator',[0]),'coarse':('power','estimator',[1]),'refine3':('power','estimator',[1,3]),'refine5':('power','estimator',[3,5]),
            'refine6':('power','estimator',[5,6]),'refine7':('power','estimator',[6,7]),'refine8':('power','estimator',[7,8]),'refine9':('power','check',[8,9])}
SAMPLED_LOOPS=(6,7,8)
def check_level(level:str,mode:str,role:str,degrees:list)->None:
    """Raise unless (mode, role, degrees) is exactly the canonical specification of the level."""
    if level=='exact':
        if mode!='exact' or role!='input' or not degrees or sorted(degrees)!=list(degrees) or min(degrees)<1:raise ValueError('exact level: mode exact, role input, increasing positive degrees')
        return
    if level not in LEVEL_SPEC:raise ValueError('unknown level '+level)
    m,r,d=LEVEL_SPEC[level]
    if (mode,role,sorted(degrees))!=(m,r,d):raise ValueError(f'level {level} requires mode {m}, role {r}, degrees {d}; got {mode}, {role}, {sorted(degrees)}')

def shared_input_names(L:int,degrees)->list[str]:
    """Numerical inputs whose content must be identical across every campaign of one loop order (overlapping degrees)."""
    return [f'L{L}_coord.txt',f'L{L}_coord.txt.idx',f'cgamma_L{L}.txt',f'exact_zero_L{L}.txt']+[f'cw_L{L}_N{N}.txt' for N in degrees if N]
