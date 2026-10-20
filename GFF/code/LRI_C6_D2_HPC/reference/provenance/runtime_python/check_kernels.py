"""Fresh comparison with independently assembled Kirchhoff determinants."""
import sys,json,ctypes,math,time
import mpmath as mp
from pathlib import Path
W=Path(__file__).resolve().parents[1];B=Path('/mnt/data/c6_method_work/lri_C6_precision_update/baseline/lri_C6_d3_complete_update')
sys.path.insert(0,str(B/'vendor'))
from mom_control_prepare import parse
suffix=sys.argv[1]if len(sys.argv)>1 else ''
forests=json.load(open(B/'inputs/powerfree_forests.json'));records=[];start=time.time()
for d in (2,3):
 lib=ctypes.CDLL(str(W/f'code/bridge_d{d}{suffix}.so'));lib.load_check.argtypes=[ctypes.c_char_p,ctypes.c_char_p];lib.eval_check.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int)];lib.eval_check.restype=ctypes.c_double
 for L in range(2,7):
  path=B/f'inputs/forest_L{L}.txt';_,gs=parse(path)
  # Rates cancel out of the tested pointwise normalized kernel.
  lib.load_check(str(path).encode(),str(B/f'inputs/rates_L{L}_0.8.txt').encode())
  errs=[];extra=[]
  for i,g in enumerate(gs):
   configs=[0]+([80,130]if i in {0,len(gs)//2,len(gs)-1} else [])
   for scale in configs:
    mp.mp.dps=70 if scale==0 else 650
    lx=[math.log((3+(j*11+g['id'])%29)/32)for j in range(2*L)]
    if scale:
     for j in range(min(L,len(lx))):lx[j]-=scale*math.log(10)
    x=[mp.exp(mp.mpf(v))for v in lx];S=sum(x);cache={}
    def U(keep,edges):
     key=tuple(keep)
     if key in cache:return cache[key]
     vs=sorted({v for pair in edges for v in pair});ind={v:j for j,v in enumerate(vs)};n=len(vs);a=mp.matrix(n)
     for ei,(u,v)in zip(keep,edges):
      u,v=ind[u],ind[v];z=1/x[ei];a[u,u]+=z;a[v,v]+=z;a[u,v]-=z;a[v,u]-=z
     r=mp.det(a[:n-1,:n-1])*mp.fprod(x[j]for j in keep);cache[key]=r;return r
    gid=f'L{L}G{g["id"]+1:03d}';ref=mp.mpf(0)
    for fs in forests[gid]:
     den=mp.fprod(U(*block)for block in fs['blocks']if block[0]);ref+=fs['sign']*sum(x[j]for j in fs['remaining_edges'])/(S*den**(mp.mpf(d)/2))
    ref*=mp.exp(mp.mpf(d)/4*sum(map(mp.mpf,lx)))
    a=(ctypes.c_double*len(lx))(*lx);lev=ctypes.c_int();val=lib.eval_check(i,a,ctypes.byref(lev));err=abs(mp.mpf(val)-ref)/max(1,abs(ref));errs.append(err)
    if err>mp.mpf('3e-12'):raise AssertionError((d,gid,scale,str(err)))
    if scale:extra.append({'graph':gid,'scale':scale,'normalized_error':mp.nstr(err,12),'fallback':lev.value})
  records.append({'d':d,'L':L,'kernels':len(gs),'checks':len(errs),'max_normalized_error':mp.nstr(max(errs),12),'endpoint_checks':extra})
  (W/f'verification/kernel_checks{suffix}.json').write_text(json.dumps({'records':records,'reference':'Independent Kirchhoff cofactor determinants; no sampler cotree masks.','seconds':time.time()-start},indent=2));print(d,L,len(errs),mp.nstr(max(errs),7),flush=True)
