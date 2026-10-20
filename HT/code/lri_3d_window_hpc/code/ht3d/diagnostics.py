"""Untuned spherical descendants using projected FREE translations.
Same bath cutoff/window in every rotational sector. No angular buffer or fitted charge.
"""
from collections import Counter
import math
import numpy as np
from scipy.sparse import csr_matrix
from .operators import ProductOperator,canonical


def zero_m_projector(op):
    """Lower highest-weight J,M=J to M=0, keeping the same column gauge."""
    if hasattr(op,'_Szero'):return op._Szero
    b=op.basis;S=op.S.tocsr();labs={lab:i for i,lab in enumerate(b.labels)}
    for a in range(op.angular):
        rows=np.flatnonzero(np.diff(S.indptr));rr=[];cc=[];dd=[]
        for col in rows:
            st=b.states[col];occ=Counter(st)
            for mode,count in occ.items():
                n,l,m=b.labels[mode]
                if m==-l:continue
                dest=labs[n,l,m-1];tmp=list(st);tmp.remove(mode);tmp.append(dest);tmp.sort()
                rr.append(b.rank(tmp));cc.append(col)
                dd.append(math.sqrt((l+m)*(l-m+1)*count*(occ.get(dest,0)+1)))
        Jm=csr_matrix((dd,(rr,cc)),shape=(op.fullB,op.fullB))
        S=canonical(Jm@S/math.sqrt((2*op.angular-a)*(a+1)))
    op._Szero=S
    return S


def projected_translation(opout,opin):
    """P_z in M=0 representatives, via all supported intermediate states.
    Coefficients are the known Gaussian spherical-mode representation; not a
    derived interacting conformal charge. The zero-mode annihilator is separate.
    """
    b=opin.basis
    if b is not opout.basis:raise ValueError('Translation requires a common bath')
    Si=zero_m_projector(opin);So=zero_m_projector(opout)
    labs=((0,0,0),)+b.labels;idx={lab:k for k,lab in enumerate(labs)}
    weights=np.r_[1.,b.weights(opin.delta)];transitions={};zero_mode=None;zero_coeff=None
    for src,(n,l,m) in enumerate(labs):
        tg=[((n,l+1,m),(2*n+2*l+3)*math.sqrt(((l+1)**2-m*m)/(4*(l+1)**2-1)))]
        if l>0:tg.append(((n+1,l-1,m),2*(n+1)*math.sqrt((l*l-m*m)/(4*l*l-1))))
        for lab,v in tg:
            if lab not in idx:continue
            dst=idx[lab];amp=v*weights[dst]/weights[src]
            if src==0:zero_mode=dst-1;zero_coeff=amp
            else:transitions.setdefault(src-1,[]).append((dst-1,amp))
    rr=[];cc=[];dd=[];zr=[];zc=[];zd=[]
    for col in np.flatnonzero(np.diff(Si.indptr)):
        if b.N[col]>=b.cutoff:continue
        st=b.states[col];occ=Counter(st)
        for src,num in occ.items():
            for dst,amp in transitions.get(src,[]):
                out=list(st);out.remove(src);out.append(dst);out.sort()
                rr.append(b.rank(out));cc.append(col);dd.append(amp*math.sqrt(num*(occ.get(dst,0)+1)))
        if zero_mode is not None:
            zr.append(b.rank(sorted(st+(zero_mode,))));zc.append(col)
            zd.append(zero_coeff*math.sqrt(occ.get(zero_mode,0)+1))
    shape=(len(b.N),len(b.N))
    W=csr_matrix((dd,(rr,cc)),shape=shape);Z=csr_matrix((zd,(zr,zc)),shape=shape)
    return canonical(So.T@W@Si),canonical(So.T@Z@Si)


def tensor_cross(W,A,v,dst,src,field):
    z=src.nz;X=v.reshape(src.nB,z);Y=np.zeros((dst.nB,z))
    for po in (0,1):
        ro=np.flatnonzero((dst.kpar^field)==po)
        for pi in (0,1):
            ri=np.flatnonzero((src.kpar^field)==pi)
            if len(ro) and len(ri):
                Y[ro]+=(W[ro][:,ri]@X[ri])@A[po*z:(po+1)*z,pi*z:(pi+1)*z].T
    return Y.ravel()


def diagnose(solver,theta,k=6,second=True):
    _,info,base,U=solver.spectrum(theta,k=k,diagnostics=True)
    w,V,U,linfo=solver.local_problem.evaluate(solver.delta,theta)
    ops={0:solver.op};spectra={(0,f):base[f] for f in (0,1)};checks={}
    D=base['window']['D'] if 'window' in base else None
    for J in ((1,2) if second else (1,)):
        op=ProductOperator(solver.basis,solver.delta,solver.nz,J,solver.backend)
        if D is not None:op.set_bath_shift(D[op.basis.N])
        ops[J]=op
        for f in (0,1):
            ev,vec,res,orth=solver.sector_solve(op,w,V,f,k,diagnostics=True)
            if res>solver.residual_tol or orth>1e-9:raise RuntimeError('Angular eigenpair gate')
            spectra[J,f]=(ev,vec);checks[f'J{J}_f{f}']={'residual':res,'orthogonality':orth,'dimension':op.dim,'projector_checks':op.projection_tests}
    t=linfo['local_scale'];osc=solver.osc;a=np.diag(np.sqrt(np.arange(1,osc)),1)
    a0=U.T@(((t+1/t)/2)*a+((t-1/t)/2)*a.T)@U
    parts={}
    def translate(v,jo,ji,f):
        if (jo,ji) not in parts:parts[jo,ji]=projected_translation(ops[jo],ops[ji])
        W,Z=parts[jo,ji]
        return tensor_cross(W,np.eye(2*solver.nz),v,ops[jo],ops[ji],f)+tensor_cross(Z,a0,v,ops[jo],ops[ji],f)
    E0=float(base[0][0][0]);records=[]
    for family,f,idx in [('sigma',1,0),('thermal',0,1),('chi',1,1)]:
        E=float(base[f][0][idx]);v=base[f][1][:,idx];v1=translate(v,1,0,f)
        cases=[('P',1,1,v1)]
        if second:cases.extend([('PP_spin2',2,2,translate(v1,2,1,f)),('P2_trace',0,2,3*translate(v1,0,1,f))])
        for name,J,level,y in cases:
            norm=float(y@y)
            if norm<1e-24:raise RuntimeError('Vanishing descendant vector')
            ev,vectors=spectra[J,f];p=(vectors.T@y)**2/norm;rank=int(np.argmax(p))
            same=bool(J==0 and rank==idx)
            records.append({'family':family,'branch':name,'J':J,'level':level,'rank':rank,
                'primary_gap':E-E0,'descendant_gap':float(ev[rank]-E0),'spacing_error':float(ev[rank]-E-level),
                'overlap_probability':float(p[rank]),'captured_probability':float(p.sum()),'norm2_in_projected_target_sector':norm,
                'ambiguous':bool(p[rank]<.5 or same),'same_primary_selected':same,'roots_tested':len(ev)})
    return {'scope':'Free-generator ancestry in M=0 representatives. Not interacting conformal charges. Same L in all sectors.',
        'records':records,'checks':checks,'scalar_eigen_residual':info['max_eigenvector_residual'],
        'angular_spectra':{str(J):{str(f):(spectra[J,f][0]-E0).tolist() for f in (0,1)} for J in ops},
        'stress_candidate_gap':float(spectra[2,0][0][0]-E0) if second else None}
