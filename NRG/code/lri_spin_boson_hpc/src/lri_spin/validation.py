"""Numerical acceptance, deliberately separate from physical convergence."""
import numpy as np


def validate_result(r,cfg,*,tangent=False,observers=True,eigen_atol=1e-8,orth_atol=1e-9):
    if r.get('config')!=cfg.asdict():raise ValueError('Output configuration mismatch')
    rr=r.get('records',[])
    if len(rr)!=cfg.nsites:raise ValueError('Incomplete trajectory')
    for i,v in enumerate(rr):
        if v.get('iteration')!=i:raise ValueError('Misordered trajectory')
        keys=['odd_gap','last_boson_occupation','last_boson_edge']
        if observers:keys+=['log_spin_scale_correlation','log_thermal_scale_correlation']
        if tangent:keys+=['d_alpha_odd_gap','log_abs_d_alpha_odd_gap']
        if not all(np.isfinite(v.get(k,np.nan)) for k in keys):raise ValueError('Nonfinite or absent observable')
        if not (-1e-12<=v['last_boson_edge']<=1+1e-12):raise ValueError('Invalid oscillator-edge probability')
        if not (-1e-12<=v['last_boson_occupation']<=cfg.nb-1+1e-10):raise ValueError('Invalid occupation')
        for key in ('even_levels','odd_levels'):
            a=np.array(v.get(key,[]))
            if a.size==0 or not np.all(np.isfinite(a)) or np.min(a)<-1e-9 or np.min(np.diff(a),initial=0)<-1e-9:
                raise ValueError('Invalid sorted spectrum')
    val=r.get('validation',{})
    for key,limit in [('max_checked_eigen_residual',eigen_atol),('max_checked_orthogonality',orth_atol)]:
        if not np.isfinite(val.get(key,np.nan)) or val[key]>limit:raise ValueError(f'Gate failed: {key}={val.get(key)} > {limit}')
    gap=r.get('minimum_kept_discarded_gap')
    if tangent and gap is not None and (not np.isfinite(gap) or gap<=0):raise ValueError('Invalid retained-space derivative')
    return {'passed':True,'eigen_atol':eigen_atol,'orth_atol':orth_atol,
            'meaning':'finite-map numerical acceptance only; not continuum/NRG convergence'}


def audit_tangent(d):
    """Same target-free window formulas and selection as the supplied analyzer."""
    R=d['records'];n=len(R);lnL=np.log(d['config']['Lambda'])
    gap=np.array([r['odd_gap'] for r in R]);der=np.array([r['d_alpha_odd_gap'] for r in R]);lg=np.log(np.maximum(abs(der),1e-290))
    width=max(12,int(.13*n));windows=[]
    for start in range(max(8,int(.13*n)),int(.76*n)-width):
        ii=np.arange(start,start+width)
        if np.any(gap[ii]<=0) or np.any(~np.isfinite(lg[ii])):continue
        c=np.polyfit(ii,lg[ii],1);res=float(np.max(abs(lg[ii]-np.polyval(c,ii))))
        variation=float(np.ptp(gap[ii])/max(abs(np.mean(gap[ii])),1e-30));cg=np.polyfit(ii,np.log(gap[ii]),1)
        windows.append({'start':start,'stop':start+width,'Delta_E':float(1-c[0]/lnL),'y_t':float(c[0]/lnL),
                        'log_response_residual':res,'gap_relative_variation':variation,'score':res+variation,
                        'plateau_score':abs(cg[0])+variation/width})
    passed=[w for w in windows if w['gap_relative_variation']<.005 and w['log_response_residual']<.003]
    return {'config':d['config'],'alpha':d['alpha'],'x':(1-d['config']['s'])/2,
            'selected':min(windows,key=lambda r:r['score']) if windows else None,
            'number_of_quality_windows':len(passed),
            'quality_window_range':[min(w['Delta_E'] for w in passed),max(w['Delta_E'] for w in passed)] if passed else None,
            'windows':windows,'scope':'finite-resolution scaling diagnostic, not a physical uncertainty interval'}
