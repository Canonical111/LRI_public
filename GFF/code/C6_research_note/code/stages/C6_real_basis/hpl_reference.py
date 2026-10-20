"""Inherited independent reference evaluator; see README for provenance."""
import mpmath as mp

def indices(word):
    out=[];n=1
    for digit in word:
        if digit==0:n+=1
        else:out.append(n);n=1
    if n!=1:raise ValueError('Series word must end in 1.')
    return tuple(out)

def mpl_series(idx,z,N):
    h=[mp.mpf(0)]*len(idx);power=mp.mpc(1);terms=[]
    for n in range(1,N+1):
        power*=z
        terms.append(power*(h[1] if len(idx)>1 else 1)/mp.mpf(n)**idx[0])
        for j in range(1,len(idx)):
            h[j]+=(h[j+1] if j+1<len(idx) else 1)/mp.mpf(n)**idx[j]
    return mp.fsum(terms)

def at_i(words,N):
    suffixes={()}
    for w in words:
        suffixes.update(w[j:] for j in range(len(w)))
    ordered=sorted(suffixes,key=lambda w:(len(w),w))
    center=mp.j/2;step=mp.j/4
    values={w:mpl_series(indices(w),center,N) if w else mp.mpc(1) for w in ordered}
    for _ in range(2):
        coefficients={():[mp.mpc(1)]+[mp.mpc(0)]*N}
        for w in ordered[1:]:
            arr=[values[w]];tail=coefficients[w[1:]]
            for n in range(N):
                if w[0]==0:
                    arr.append(step*(tail[n]-n*arr[n])/(center*(n+1)))
                else:
                    arr.append(step*(tail[n]+n*arr[n])/((1-center)*(n+1)))
            coefficients[w]=arr
        values={w:mp.fsum(v) for w,v in coefficients.items()}
        center+=step
    return values

