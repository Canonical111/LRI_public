"""Independent assembly and sampling diagnostics; no fitted controls."""
from analyze import *
from analysis import base_module
import math,hashlib

def lagrange(d,means):
    N=7;B2=base_module(d).B2
    b={1:np.array([3.]),2:B2};c={1:np.array([1.]),2:B2/6}
    for L,a in means.items():k=7-L;b[L]=a[:k];c[L]=a[k:]
    BB=np.zeros((N,N));GG=np.zeros_like(BB);BB[0,0]=3
    for L,a in b.items():
        if L>=2:BB[L-1,:len(a)]=a
    for L,a in c.items():GG[L-1,:len(a)]=L*a
    def mul(a,b):
        out=np.zeros_like(a)
        for j in range(N):
            for k in range(N-j):out[j+k]+=np.convolve(a[j],b[k])[:N]
        return out
    H=BB/3;H[0,0]-=1;ans=np.zeros(N);ans[0]=d/2;ans[1]=-.5
    for n in range(1,N):
        power=np.zeros_like(H);power[0,0]=1;inv=power.copy()
        for k in range(1,N):power=mul(power,H);inv+=(-1)**k*math.comb(n+k-1,k)*power
        pp=mul(GG,inv)/(n*3**n)
        for j in range(N-n):ans[n+j]+=pp[n-1,j]
    return ans

def main():
    result=json.load(open(W/'verification/method_precision_results.json'));out={}
    tags=('prod_a','prod_b','new_a','new_b')
    for d in (2,3):
        j=result[str(d)];means={int(L):np.array(v)for L,v in j['means'].items()};raw={t:load(d,t)[1]for t in tags}
        ans=lagrange(d,means);ans[6]+=j['d2_offset']
        # Sampling-error bootstrap, resampling each loop/campaign independently.
        rng=np.random.default_rng(144097197+d);vals=[]
        for _ in range(4096):
            mm={L:sum(raw[t][L][rng.integers(0,len(raw[t][L]),len(raw[t][L]))].mean(0)/4 for t in tags)for L in means}
            cc=F[d](mm)[6]
            if d==2:cc+=P+rng.normal(0,SP)+.5*(S+rng.normal(0,SS))
            vals.append(cc)
        vals=np.array(vals)
        # Delete-one-loop-replicate nonlinear jackknife; additive common terms have no curvature.
        base=np.array(j['coefficients']);bias=np.zeros(7)
        for t in tags:
            for L,a in raw[t].items():
                leaves=[];n=len(a)
                for row in a:
                    mm={k:x.copy()for k,x in means.items()};mm[L]+=.25*(a.mean(0)-row)/(n-1)
                    cc=F[d](mm);cc[6]+=j['d2_offset'];leaves.append(cc)
                bias+=(n-1)*(np.mean(leaves,axis=0)-base)
        out[str(d)]={'bootstrap_resamples':4096,'bootstrap_se':float(vals.std(ddof=1)),'delta_se':j['sampling_standard_error'],'bootstrap_mean_shift':float(vals.mean()-j['C6']),'bootstrap_percentile_2_5_97_5':np.quantile(vals,[.025,.975]).tolist(),'bootstrap_interpretation':'Approximate diagnostic, not an interval enclosure; retained primitive and 66-kernel uncertainties are sampled once with correct weights.', 'independent_Lagrange_coefficients':ans.tolist(),'max_Lagrange_difference':float(max(abs(ans-base))),'nonlinear_jackknife_bias':bias.tolist()}
        print(d,out[str(d)],flush=True)
    frozen=json.load(open(W/'verification/production_source_hashes.json'))
    mismatch={p:[sha,hashlib.sha256((W/p).read_bytes()).hexdigest()]for p,sha in frozen.items()if hashlib.sha256((W/p).read_bytes()).hexdigest()!=sha}
    source_mismatch={p:v for p,v in mismatch.items()if p not in ['code/experiment_d2','code/experiment_d3']}
    out['frozen_production_source_hash_mismatches']=source_mismatch
    out['rebuilt_binary_hash_mismatches']={p:v for p,v in mismatch.items()if p not in source_mismatch}
    assert not source_mismatch
    (W/'verification/extra_checks.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
