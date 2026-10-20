"""Check optimized log/product evaluation against the original 128-bit kernel."""
import sys,ctypes as C,mpmath as mp,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import mellin as M
mp.mp.dps=50
ss=M.sectors(5,False,False,None);dd=[M.prepare(s) for s in ss];old=M.fn
fastlib=C.CDLL(str(M.ROOT/'quad_sector_fast.so'));fast=fastlib.integrate;fast.argtypes=old.argtypes
worst=mp.mpf(0);start=time.time()
for theta in [mp.mpf('.03'),mp.mpf('1.5'),mp.mpf('3.0'),mp.mpf('4.6')]:
 q=mp.mpf('.17')*mp.exp(1j*theta);dv=mp.mpf('1e-5')*mp.exp(mp.mpf('.31')*1j);cache={}
 so=mp.mpc(0);sf=mp.mpc(0)
 for sec,dat in zip(ss,dd):
  M.fn=old;a=M.evalsector(sec,dat,q,dv,mp.mpc(0),12,cache)
  M.fn=fast;b=M.evalsector(sec,dat,q,dv,mp.mpc(0),12,cache)
  err=abs(a-b)/(1+abs(a));worst=max(worst,err);so+=sec['mult']*a;sf+=sec['mult']*b
 print('angle',theta,'relative error',mp.nstr(abs(so-sf)/(1+abs(so)),10),flush=True)
M.fn=old
print('Worst sector relative difference:',mp.nstr(worst,15));print('seconds',time.time()-start)
assert worst<mp.mpf('1e-23')
print('Original/optimized 128-bit integrands agree; no logarithm-branch mismatch detected.')
