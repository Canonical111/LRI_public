"""Exact ranked S^2 Fock graph and species-block SO(3) highest weights.
One oscillator (n,ell,m) of level 2n+ell; zero mode excluded. No particle cap.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Sequence
import math
import numpy as np
from numba import njit
from scipy.sparse import csr_matrix
from scipy.linalg import null_space
from collections import Counter,defaultdict


def dimension(cutoff: int) -> int:
    if isinstance(cutoff, bool) or int(cutoff) != cutoff or cutoff < 0:
        raise ValueError('cutoff must be a nonnegative integer')
    dp=[0]*(int(cutoff)+1);dp[0]=1
    for level in range(1,int(cutoff)+1):
        for _ in range((level+1)*(level+2)//2):
            for n in range(level,int(cutoff)+1):dp[n]+=dp[n-level]
    return sum(dp)

@njit(cache=True)
def _counts(levels, cut):
    # count[k,l]: suffix multisets of labels >=k with total level <=l.
    d = np.ones((len(levels) + 1, cut + 1), np.int64)
    for k in range(len(levels) - 1, -1, -1):
        for l in range(cut + 1):
            d[k, l] = d[k + 1, l]
            if l >= levels[k]:
                d[k, l] += d[k, l - levels[k]]
    return d


@njit(cache=True)
def _enumerate(levels, spins, cut, N, P, J, tree, last, ptr):
    # Iterative preorder: identical row numbering to the original recursive code.
    path = np.empty(cut + 1, np.int64)
    nodes = np.zeros(cut + 1, np.int64)
    choices = np.zeros(cut + 1, np.int64)
    used = np.zeros(cut + 1, np.int64)
    spin = np.zeros(cut + 1, np.int64)
    unique = np.zeros(cut + 1, np.int64)
    row = 1
    depth = 0
    edges = 0
    while depth >= 0:
        k = choices[depth]
        if k >= len(levels) or used[depth] + levels[k] > cut:
            depth -= 1
            continue
        choices[depth] = k + 1
        parent = nodes[depth]
        oldlast = path[depth - 1] if depth else -1
        path[depth] = k
        used[depth + 1] = used[depth] + levels[k]
        spin[depth + 1] = spin[depth] + spins[k]
        unique[depth + 1] = unique[depth] + (k != oldlast)
        depth += 1
        nodes[depth] = row
        choices[depth] = k
        N[row] = used[depth]
        P[row] = depth
        J[row] = spin[depth]
        tree[row] = parent
        last[row] = k
        ptr[row] = edges
        edges += unique[depth]
        row += 1
    ptr[row] = edges
    return row, edges


@njit(cache=True)
def _rank_path(path, n, levels, counts, cut, skip=-1):
    rank = 0
    left = cut
    start = 0
    for i in range(n):
        if i == skip:
            continue
        k = path[i]
        rank += 1 + counts[start, left] - counts[k, left]
        left -= levels[k]
        start = k
    return rank



@njit(cache=True)
def _fill_edges(tree,last,P,ptr,levels,counts,cut,parent,mode,sqocc):
    path=np.empty(cut+1,np.int64)
    for row in range(1,len(tree)):
        node=row;n=int(P[row])
        for j in range(n-1,-1,-1):path[j]=last[node];node=tree[node]
        q=ptr[row];at=0
        while at<n:
            end=at+1
            while end<n and path[end]==path[at]:end+=1
            parent[q]=_rank_path(path,n,levels,counts,cut,at)
            mode[q]=path[at];sqocc[q]=math.sqrt(end-at)
            q+=1;at=end

class OccupationView(Sequence):
    """Reconstruct tuples on demand; does not cache an exponentially large list."""
    def __init__(self, tree, last, particles):
        self.tree, self.last, self.particles = tree, last, particles

    def __len__(self):
        return len(self.tree)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[j] for j in range(*i.indices(len(self))) ]
        i = int(i)
        if i < 0:
            i += len(self)
        if not 0 <= i < len(self):
            raise IndexError(i)
        path = [0] * int(self.particles[i])
        for k in range(len(path) - 1, -1, -1):
            path[k] = int(self.last[i])
            i = int(self.tree[i])
        return tuple(path)



class _RankIndex:
    def __init__(self,basis):self.basis=basis
    def __getitem__(self,state):return self.basis.rank(state)

@dataclass
class SphereBathBasis:
    cutoff:int
    labels:tuple
    states:Sequence
    N:np.ndarray
    P:np.ndarray
    M:np.ndarray
    ptr:np.ndarray
    parents:np.ndarray
    modes:np.ndarray
    sqocc:np.ndarray
    tree:np.ndarray
    last:np.ndarray
    counts:np.ndarray
    mode_levels:np.ndarray

    @classmethod
    def build(cls,cutoff,max_states=2_000_000,max_bytes=2*1024**3,cache_dir=None):
        size=dimension(cutoff);cutoff=int(cutoff)
        if size>max_states or size>=np.iinfo(np.int64).max:
            raise MemoryError(f'{size} spherical bath states exceeds guard {max_states}')
        labels=tuple((n,k-2*n,m) for k in range(1,cutoff+1)
                     for n in range(k//2+1) for m in range(-(k-2*n),k-2*n+1))
        levels=np.array([2*n+l for n,l,m in labels],np.int64)
        spins=np.array([m for n,l,m in labels],np.int64)
        idx=np.int32 if size<2**31 else np.int64
        mt=np.uint16 if len(labels)<65536 else np.uint32
        preliminary=size*(4+2+4+2*np.dtype(idx).itemsize+np.dtype(mt).itemsize+8)+(len(labels)+1)*(cutoff+1)*8
        if preliminary>max_bytes:raise MemoryError('Spherical basis initial-array memory guard')
        names=('N','P','M','ptr','parents','modes','sqocc','tree','last','counts','mode_levels')
        cache=None
        if cache_dir is not None:
            from .cache import ArrayCache
            cache=ArrayCache(cache_dir);saved=cache.load('graph',{'L':cutoff})
            if saved is not None:
                a,_=saved
                if set(a)!=set(names) or len(a['N'])!=size or sum(x.nbytes for x in a.values())>max_bytes:
                    raise MemoryError('Cached graph violates requested dimensions or memory guard')
                obj=cls(cutoff,labels,OccupationView(a['tree'],a['last'],a['P']),*[a[n] for n in names])
                obj._cache_dir=str(cache.root)
                return obj
        counts=_counts(levels,cutoff)
        if counts[0,cutoff]!=size:raise OverflowError('Dimension/rank-table mismatch')
        N=np.zeros(size,np.int32);P=np.zeros(size,np.int16);M=np.zeros(size,np.int32)
        tree=np.zeros(size,idx);last=np.zeros(size,mt);ptr=np.zeros(size+1,np.int64)
        rows,edges=_enumerate(levels,spins,cutoff,N,P,M,tree,last,ptr)
        if rows!=size:raise AssertionError('Enumeration count mismatch')
        if preliminary+edges*(np.dtype(idx).itemsize+np.dtype(mt).itemsize+8)>max_bytes:
            raise MemoryError('Spherical basis edge-array memory guard')
        parent=np.empty(edges,idx);mode=np.empty(edges,mt);sqocc=np.empty(edges,np.float64)
        _fill_edges(tree,last,P,ptr,levels,counts,cutoff,parent,mode,sqocc)
        obj=cls(cutoff,labels,OccupationView(tree,last,P),N,P,M,ptr,parent,mode,sqocc,tree,last,counts,levels)
        if cache is not None:
            cache.save('graph',{'L':cutoff},{name:getattr(obj,name) for name in names})
            obj._cache_dir=str(cache.root)
        return obj

    @property
    def index(self):return _RankIndex(self)

    def rank(self,state):
        p=np.asarray(state,np.int64)
        if p.ndim!=1 or np.any(p<0) or np.any(p>=len(self.labels)) or np.any(p[:-1]>p[1:]) or self.mode_levels[p].sum()>self.cutoff:
            raise ValueError('Invalid occupation state')
        return int(_rank_path(p,len(p),self.mode_levels,self.counts,self.cutoff))

    def weights(self,x):
        from scipy.special import poch
        if not np.isfinite(x) or x<=.5:raise ValueError('Positive 3D GFF norms require x>1/2')
        # Cache only by exact x; no approximate/stale covariance reuse.
        if getattr(self,'_weight_x',None)!=x:
            self._weight_x=x
            self._weights=np.array([math.sqrt(poch(x,n+l)*poch(x-.5,n)/(math.factorial(n)*poch(1.5,n+l))) for n,l,m in self.labels])
        return self._weights

    def angular_values(self,z):
        from scipy.special import gammaln,lpmv
        cache={};out=[]
        for n,l,m in self.labels:
            key=l,m
            if key not in cache:
                k=abs(m);v=math.sqrt(2*l+1)*math.exp(.5*(gammaln(l-k+1)-gammaln(l+k+1)))*lpmv(k,l,z)
                if m<0:v*=(-1)**k
                cache[key]=v
            out.append(cache[key])
        return np.array(out)

    def ladders(self,x,z):
        amp=self.weights(x)*self.angular_values(z)
        C=csr_matrix((self.sqocc*amp[self.modes],self.parents.copy(),self.ptr.copy()),shape=(len(self.N),len(self.N)))
        C.sort_indices();return C.T.tocsr(),C

    @property
    def nbytes(self):
        return sum(a.nbytes for a in (self.N,self.P,self.M,self.ptr,self.parents,self.modes,self.sqocc,self.tree,self.last,self.counts,self.mode_levels))

    def highest_weight(self,spin=0,inversion=None):
        return _ranked_highest_weight(self,spin,inversion)

    def highest_weight_legacy(self,spin=0,inversion=None):
        if inversion is None:inversion=spin%2
        key=(spin,inversion)
        if hasattr(self,'_projectors') and key in self._projectors:return self._projectors[key]
        if spin<0:raise ValueError('Spin is nonnegative')
        # J_+ preserves the occupation count in each radial/angular species
        # (n,ell). Resolving these exact blocks avoids huge disconnected SVDs.
        signatures={}
        candidate_rows=np.flatnonzero(((self.M==spin)|(self.M==spin+1)) & (self.N%2==inversion))
        for i in candidate_rows:
            signatures[int(i)]=tuple(sorted(Counter(self.labels[k][:2] for k in self.states[int(i)]).items()))
        groups=defaultdict(list);target_groups=defaultdict(list)
        for i in np.flatnonzero((self.M==spin)&(self.N%2==inversion)):
            groups[(int(self.N[i]),int(self.P[i]),signatures[i])].append(int(i))
        for i in np.flatnonzero((self.M==spin+1)&(self.N%2==inversion)):
            target_groups[(int(self.N[i]),int(self.P[i]),signatures[i])].append(int(i))
        lookup={key:k for k,key in enumerate(self.labels)}
        rows=[];cols=[];data=[];sn=[];sp=[];rep=[];offset=0;maxres=0.;maxorth=0.
        for (N,P,sig),inds in sorted(groups.items()):
            targets=target_groups.get((N,P,sig),[])
            tid={int(i):j for j,i in enumerate(targets)}
            jp=np.zeros((len(targets),len(inds)))
            for j,i in enumerate(inds):
                occ=Counter(self.states[i])
                for k,count in occ.items():
                    n,l,m=self.labels[k]
                    if m==l:continue
                    kp=lookup[(n,l,m+1)]
                    ss=list(self.states[i]);ss.remove(k);ss.append(kp);ss.sort()
                    ip=self.index[tuple(ss)]
                    jp[tid[ip],j]+=math.sqrt((l-m)*(l+m+1)*count*(occ.get(kp,0)+1))
            Q=np.eye(len(inds)) if not len(targets) else null_space(jp,rcond=5e-13)
            if Q.shape[1]==0:continue
            for j in range(Q.shape[1]):
                im=int(np.argmax(abs(Q[:,j])))
                if Q[im,j]<0:Q[:,j]*=-1
            maxres=max(maxres,float(np.max(abs(jp@Q),initial=0.)))
            maxorth=max(maxorth,float(np.max(abs(Q.T@Q-np.eye(Q.shape[1])),initial=0.)))
            ii,jj=np.nonzero(Q)
            rows.extend(np.array(inds)[ii]);cols.extend(offset+jj);data.extend(Q[ii,jj])
            sn.extend([N]*Q.shape[1]);sp.extend([P]*Q.shape[1]);rep.extend([inds[0]]*Q.shape[1])
            offset+=Q.shape[1]
        S=csr_matrix((data,(rows,cols)),shape=(len(self.N),offset))
        if maxres>1e-10 or maxorth>1e-10:raise RuntimeError('Highest-weight projection failed')
        ans=(S,np.array(sn,np.int32),np.array(sp,np.int16),np.array(rep,np.int64),dict(Jplus_residual=maxres,orthogonality=maxorth))
        if not hasattr(self,'_projectors'):self._projectors={}
        self._projectors[key]=ans
        return ans


@njit(cache=True)
def _species_ranks(tree,last,particles,rows,species,levels,counts,cut):
    result=np.empty(len(rows),np.int64);path=np.empty(cut+1,np.int64)
    for a in range(len(rows)):
        row=rows[a];node=row;p=int(particles[row])
        for k in range(p-1,-1,-1):path[k]=species[last[node]];node=tree[node]
        # Species labels are contiguous in the original mode ordering.
        result[a]=_rank_path(path,p,levels,counts,cut)
    return result

@njit(cache=True)
def _make_jplus_block(columns,ptr,rows,data,target_local,ntarget):
    a=np.zeros((ntarget,len(columns)),np.float64)
    for j in range(len(columns)):
        c=columns[j]
        for e in range(ptr[c],ptr[c+1]):a[target_local[rows[e]],j]+=data[e]
    return a


def _ranked_highest_weight(self,spin=0,inversion=None):
    """Same species blocks, order, rcond and gauge as the reference implementation.

    Combinatorial species signatures and magnetic ladder destinations are evaluated
    in compiled loops; no global occupation tuple list/dictionary is introduced.
    """
    from .rotational_vertices import _magnetic_edges
    if inversion is None:inversion=spin%2
    if int(spin)!=spin or spin<0 or inversion not in (0,1):raise ValueError('Invalid spin/inversion sector')
    key=(spin,inversion)
    if hasattr(self,'_projectors') and key in self._projectors:return self._projectors[key]
    cache=None;params={'L':self.cutoff,'spin':int(spin),'inversion':int(inversion)}
    if getattr(self,'_cache_dir',None):
        from .cache import ArrayCache
        cache=ArrayCache(self._cache_dir);saved=cache.load('projector',params)
        if saved is not None:
            a,meta=saved
            S=csr_matrix((a['data'],a['indices'],a['indptr']),shape=(len(self.N),len(a['N'])))
            ans=(S,a['N'],a['P'],a['keep'],meta)
            if not hasattr(self,'_projectors'):self._projectors={}
            self._projectors[key]=ans
            return ans
    src=np.flatnonzero((self.M==spin)&(self.N%2==inversion))
    dst=np.flatnonzero((self.M==spin+1)&(self.N%2==inversion))
    labels=np.asarray(self.labels,dtype=np.int64).reshape(-1,3)
    spkeys=list(dict.fromkeys((n,l) for n,l,m in self.labels));spi={s:i for i,s in enumerate(spkeys)}
    modespecies=np.array([spi[n,l] for n,l,m in self.labels],np.int64)
    splevels=np.array([2*n+l for n,l in spkeys],np.int64)
    counts=_counts(splevels,self.cutoff)
    srcsig=_species_ranks(self.tree,self.last,self.P,src,modespecies,splevels,counts,self.cutoff)
    dstsig=_species_ranks(self.tree,self.last,self.P,dst,modespecies,splevels,counts,self.cutoff)
    groups=defaultdict(list);targets=defaultdict(list)
    for i,k in enumerate(srcsig):groups[int(k)].append(i)
    for i,k in enumerate(dstsig):targets[int(k)].append(i)
    # Compute each sorting signature ONCE per exact species block, preserving
    # the legacy column order (N,P,lexical Counter(n,l)).
    def order(k):
        row=int(src[groups[k][0]])
        sig=tuple(sorted(Counter(self.labels[j][:2] for j in self.states[row]).items()))
        return int(self.N[row]),int(self.P[row]),sig
    lookup=np.full(len(self.N),-1,np.int64);lookup[dst]=np.arange(len(dst))
    r,c,d=_magnetic_edges(self.tree,self.last,self.P,src,lookup,self.mode_levels,
        self.counts,self.cutoff,labels[:,1],labels[:,2],1)
    jpall=csr_matrix((d,(r,c)),shape=(len(dst),len(src))).tocsc()
    local=np.empty(len(dst),np.int64)
    for ids in targets.values():local[ids]=np.arange(len(ids))
    rows=[];cols=[];data=[];sn=[];sp=[];rep=[];offset=0;maxres=0.;maxorth=0.
    for keysp in sorted(groups,key=order):
        indices=np.asarray(groups[keysp],np.int64);inds=src[indices]
        target=targets.get(keysp,[])
        jp=_make_jplus_block(indices,jpall.indptr,jpall.indices,jpall.data,local,len(target))
        Q=np.eye(len(inds)) if not len(target) else null_space(jp,rcond=5e-13)
        if Q.shape[1]==0:continue
        for j in range(Q.shape[1]):
            im=int(np.argmax(abs(Q[:,j])))
            if Q[im,j]<0:Q[:,j]*=-1
        maxres=max(maxres,float(np.max(abs(jp@Q),initial=0.)))
        maxorth=max(maxorth,float(np.max(abs(Q.T@Q-np.eye(Q.shape[1])),initial=0.)))
        ii,jj=np.nonzero(Q)
        rows.extend(inds[ii]);cols.extend(offset+jj);data.extend(Q[ii,jj])
        sn.extend([self.N[inds[0]]]*Q.shape[1]);sp.extend([self.P[inds[0]]]*Q.shape[1]);rep.extend([inds[0]]*Q.shape[1])
        offset+=Q.shape[1]
    S=csr_matrix((data,(rows,cols)),shape=(len(self.N),offset))
    if maxres>1e-10 or maxorth>1e-10:raise RuntimeError('Highest-weight projection failed')
    ans=(S,np.array(sn,np.int32),np.array(sp,np.int16),np.array(rep,np.int64),dict(Jplus_residual=maxres,orthogonality=maxorth))
    if not hasattr(self,'_projectors'):self._projectors={}
    self._projectors[key]=ans
    if cache is not None:
        cache.save('projector',params,{'data':S.data,'indices':S.indices,'indptr':S.indptr,
                   'N':ans[1],'P':ans[2],'keep':ans[3]},ans[4])
        # A simultaneous writer may have chosen an equivalent SVD gauge. Always
        # consume the published winner before constructing/caching its vertices.
        a,meta=cache.load('projector',params)
        S=csr_matrix((a['data'],a['indices'],a['indptr']),shape=(len(self.N),len(a['N'])))
        ans=(S,a['N'],a['P'],a['keep'],meta)
        self._projectors[key]=ans
    return ans

