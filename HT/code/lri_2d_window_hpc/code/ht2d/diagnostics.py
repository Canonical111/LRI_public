"""Untuned 2D descendant candidates at the SAME cutoff/window as the primaries.
No angular buffers or fitted charge corrections are introduced.
"""
from collections import Counter
import math
import numpy as np
from scipy.sparse import csr_matrix
from ht2d.operators import ProductOperator


def projector(op):
    if op.S is not None:return op.S
    return csr_matrix((np.ones(op.nB),(op.keep,np.arange(op.nB))),shape=(op.fullB,op.nB))


def translation_parts(b,x,side):
    idx={s:i for i,s in enumerate(b.states)};labs={ab:k for k,ab in enumerate(b.labels)}
    rows=[];cols=[];data=[];zr=[];zc=[];zd=[]
    k0=labs[(1,0) if side==0 else (0,1)]
    for col,st in enumerate(b.states):
        if b.N[col]>=b.cutoff:continue
        counts=Counter(st)
        for src,num in counts.items():
            ab=list(b.labels[src]);fac=math.sqrt((ab[side]+1)*(x+ab[side]));ab[side]+=1
            dest=labs.get(tuple(ab))
            if dest is None:continue
            t=list(st);t.remove(src);t.append(dest);t.sort()
            rows.append(idx[tuple(t)]);cols.append(col);data.append(fac*math.sqrt(num*(counts.get(dest,0)+1)))
        t=tuple(sorted(st+(k0,)));zr.append(idx[t]);zc.append(col);zd.append(math.sqrt(x*(counts.get(k0,0)+1)))
    shape=(len(b.N),len(b.N))
    return csr_matrix((data,(rows,cols)),shape=shape),csr_matrix((zd,(zr,zc)),shape=shape)


def tensor_cross(W,Q,v,opout,opin,field):
    z=opin.nz;X=v.reshape(opin.nB,z);Y=np.zeros((opout.nB,z))
    for po in (0,1):
        rr=np.flatnonzero((opout.kpar^field)==po)
        for pi in (0,1):
            cc=np.flatnonzero((opin.kpar^field)==pi)
            if len(rr) and len(cc):
                Y[rr]+=(W[rr][:,cc]@X[cc])@Q[po*z:(po+1)*z,pi*z:(pi+1)*z].T
    return Y.ravel()


def diagnose(solver,theta,k=6,second=True):
    """Continuously tracked free-generator ancestry, not exact interacting charges."""
    _,info,base,U=solver.spectrum(theta,k=k,diagnostics=True)
    w,vertices,U,linfo=solver.local_problem.evaluate(solver.delta,theta)
    ops={0:solver.op};spectra={(0,f):base[f] for f in (0,1)}
    window=base.get('window');window_d=window['D'] if window is not None else None
    for J in ((1,2) if second else (1,)):
        op=ProductOperator(solver.basis,solver.delta,solver.nz,J,solver.backend)
        if window_d is not None:op.set_bath_shift(window_d[op.basis.N])
        ops[J]=op
        for f in (0,1):
            ev,vec,res,orth=solver.sector_solve(op,w,vertices,f,k,diagnostics=True)
            if res>solver.residual_tol or orth>1e-9:raise RuntimeError('Angular eigenpair gate')
            spectra[J,f]=(ev,vec)
    osc=solver.osc;t=linfo['local_scale'];ann=np.diag(np.sqrt(np.arange(1,osc)),1)
    a0=U.T@(((t+1/t)/2)*ann+((t-1/t)/2)*ann.T)@U
    parts={}
    legacy=None if hasattr(solver.basis,'rank') else {side:translation_parts(solver.basis,solver.delta,side) for side in (0,1)}
    def translate(v,Jout,Jin,f):
        side=0 if Jout-Jin==1 else 1
        a=ops[Jout];b=ops[Jin]
        key=(Jout,Jin)
        if key not in parts:
            if legacy is None:parts[key]=projected_translation(a,b,side)
            else:
                B,Z=legacy[side];So,Si=projector(a),projector(b)
                parts[key]=(So.T@B@Si,So.T@Z@Si)
        B,Z=parts[key]
        return tensor_cross(B,np.eye(2*solver.nz),v,a,b,f)+tensor_cross(Z,a0,v,a,b,f)
    refs=[('sigma',1,0),('thermal',0,1),('chi',1,1)]
    E0=float(base[0][0][0]);records=[]
    for family,f,idx in refs:
        E=float(base[f][0][idx]);v=base[f][1][:,idx]
        va=translate(v,1,0,f)
        cases=[('A',1,1,va)]
        if second:cases.extend([('AA',2,2,translate(va,2,1,f)),('AB',0,2,translate(va,0,1,f))])
        for name,J,level,y in cases:
            n2=float(y@y)
            if n2<1e-24:raise RuntimeError('Vanishing descendant candidate')
            energies,vectors=spectra[J,f];p=(vectors.T@y)**2/n2;rank=int(p.argmax())
            records.append({'family':family,'branch':name,'J':J,'level':level,'rank':rank,
                            'primary_gap':E-E0,'descendant_gap':float(energies[rank]-E0),
                            'spacing_error':float(energies[rank]-E-level),
                            'overlap_probability':float(p[rank]),'captured_probability':float(p.sum()),
                            'ambiguous':bool(p[rank]<.5),'roots_tested':len(energies)})
    return {'scope':'Free-generator ancestry; no interacting-charge or continuum claim; same cutoff in all J sectors',
            'records':records,'scalar_eigen_residual':info['max_eigenvector_residual'],
            'angular_spectra':{str(J):{str(f):(spectra[J,f][0]-E0).tolist() for f in (0,1)} for J in ops}}


def projected_translation(opout, opin, side):
    """Build only the requested angular transition, with exact ranked endpoints.

    Scalar reflection columns contain at most two nonzeros. No full Fock-state
    dictionary or full-angular translation matrix is constructed here.
    """
    basis=opin.basis
    if basis is not opout.basis:
        raise ValueError('Translation endpoints require the same circle basis')
    So,Si=projector(opout).tocsr(),projector(opin).tocsc()
    dest_col=np.full(opout.fullB,-1,np.int64);dest_amp=np.zeros(opout.fullB)
    for row in np.flatnonzero(np.diff(So.indptr)):
        q=So.indptr[row];dest_col[row]=So.indices[q];dest_amp[row]=So.data[q]
    labs={ab:k for k,ab in enumerate(basis.labels)}
    k0=labs[(1,0) if side==0 else (0,1)]
    rows=[];cols=[];data=[];zr=[];zc=[];zd=[]
    for col in range(opin.nB):
        for pos in range(Si.indptr[col],Si.indptr[col+1]):
            srcrow=Si.indices[pos];samp=Si.data[pos]
            if basis.N[srcrow]>=basis.cutoff:continue
            st=basis.states[srcrow];counts=Counter(st)
            for src,num in counts.items():
                ab=list(basis.labels[src]);fac=math.sqrt((ab[side]+1)*(opin.delta+ab[side]));ab[side]+=1
                dst=labs.get(tuple(ab))
                if dst is None:continue
                t=list(st);t.remove(src);t.append(dst);t.sort()
                rr=basis.rank(t);o=dest_col[rr]
                if o>=0:
                    rows.append(o);cols.append(col);data.append(samp*dest_amp[rr]*fac*math.sqrt(num*(counts.get(dst,0)+1)))
            rr=basis.rank(sorted(st+(k0,)));o=dest_col[rr]
            if o>=0:
                zr.append(o);zc.append(col);zd.append(samp*dest_amp[rr]*math.sqrt(opin.delta*(counts.get(k0,0)+1)))
    shape=(opout.nB,opin.nB)
    return csr_matrix((data,(rows,cols)),shape=shape),csr_matrix((zd,(zr,zc)),shape=shape)
