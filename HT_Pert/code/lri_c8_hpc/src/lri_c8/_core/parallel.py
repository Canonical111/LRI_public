"""MPI halo exchange for row-distributed ladder operators.

No full-vector allgather and no Python-object communication in the hot path.
Requires mpi4py only when --mpi is requested. This backend must be smoke-tested
with the user's MPI implementation before a production cluster campaign.
"""
from __future__ import annotations
import time
import numpy as np

def mpi_world(enabled):
    if not enabled:return None
    try:
        from mpi4py import MPI
    except ImportError as e:
        raise RuntimeError('--mpi requires mpi4py built against your cluster MPI') from e
    if MPI.Query_thread()<MPI.THREAD_FUNNELED:
        raise RuntimeError('At least MPI_THREAD_FUNNELED is required')
    return MPI.COMM_WORLD

class Halo:
    def __init__(self,basis,edges):
        self.comm=basis.comm;self.nlocal=basis.dim;self.calls=0;self.bytes_sent=0;self.seconds=0.
        self.remote_count=0
        if self.comm is None or basis.size==1:
            # A single MPI rank also has no halo.
            self.comm=None
            return
        from mpi4py import MPI
        self.MPI=MPI
        idx=edges.index
        remote=np.unique(idx[(idx<basis.begin)|(idx>=basis.end)]).astype(np.int64)
        self.remote_count=len(remote)
        # Exact owners for boundaries floor(D*r/size), including empty ranks.
        bounds=np.array([basis.global_dim*r//basis.size for r in range(basis.size+1)],dtype=np.int64)
        owners=np.searchsorted(bounds[1:],remote,side='right')
        self.need_counts=np.bincount(owners,minlength=basis.size).astype(np.int64)
        self.need_displs=np.r_[0,np.cumsum(self.need_counts[:-1])].astype(np.int64)
        self.send_counts=np.empty_like(self.need_counts)
        self.comm.Alltoall([self.need_counts,MPI.INT64_T],[self.send_counts,MPI.INT64_T])
        self.send_displs=np.r_[0,np.cumsum(self.send_counts[:-1])].astype(np.int64)
        requests=np.empty(int(self.send_counts.sum()),dtype=np.int64)
        self._check_counts(self.need_counts,self.need_displs)
        self._check_counts(self.send_counts,self.send_displs)
        self.comm.Alltoallv([remote,self.need_counts,self.need_displs,MPI.INT64_T],
                           [requests,self.send_counts,self.send_displs,MPI.INT64_T])
        self.send_indices=requests-basis.begin
        if np.any(self.send_indices<0) or np.any(self.send_indices>=basis.dim):
            raise RuntimeError('Invalid halo ownership')
        # In-place remap, in chunks to avoid E-sized temporary arrays.
        # Local rows [0,nlocal), ghosts [nlocal,nlocal+remote_count).
        mapped_type=np.int32 if basis.dim+len(remote)<=np.iinfo(np.int32).max else np.int64
        mapped=np.empty(len(idx),dtype=mapped_type)
        for start in range(0,len(idx),1_000_000):
            a=idx[start:start+1_000_000]
            local=(a>=basis.begin)&(a<basis.end)
            out=mapped[start:start+len(a)]
            out[local]=a[local]-basis.begin
            out[~local]=basis.dim+np.searchsorted(remote,a[~local])
        edges.index=mapped

    @staticmethod
    def _check_counts(counts,displs):
        # Conservative portability: refuse rather than overflow legacy MPI int counts.
        if max(np.max(counts,initial=0),np.max(displs+counts,initial=0))>np.iinfo(np.int32).max:
            raise OverflowError('Halo transfer exceeds portable MPI count range; use more ranks')

    def exchange(self,x):
        if self.comm is None:return np.empty((0,x.shape[1]),dtype=np.float64)
        t=time.perf_counter();w=x.shape[1]
        sc=self.send_counts*w;sd=self.send_displs*w;rc=self.need_counts*w;rd=self.need_displs*w
        self._check_counts(sc,sd);self._check_counts(rc,rd)
        send=np.ascontiguousarray(x[self.send_indices,:])
        ghost=np.empty((self.remote_count,w),dtype=np.float64)
        self.comm.Alltoallv([send,sc,sd,self.MPI.DOUBLE],[ghost,rc,rd,self.MPI.DOUBLE])
        self.calls+=1;self.bytes_sent+=send.nbytes;self.seconds+=time.perf_counter()-t
        return ghost

def global_sum(comm,array):
    array=np.asarray(array,dtype=np.float64)
    if comm is None or comm.Get_size()==1:return array
    from mpi4py import MPI
    out=np.empty_like(array);comm.Allreduce([array,MPI.DOUBLE],[out,MPI.DOUBLE],op=MPI.SUM)
    return out
