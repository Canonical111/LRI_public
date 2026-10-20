import json, glob
S='<TMP>/scratchpad/eps5'
VM={'raw':'raw','g2D':'g2D','g2D3W':'g2D+g3W','Dconn':'Dconn','Dfull':'Dfull_raw'}
D={}
for f in glob.glob(S+'/A/res5_*.json'):
    o=json.load(open(f)); lam=float(o['Lam']); s=o['summary']
    D[lam]={v:{q:s[v][q] for q in ('v_dphi1','v_dphi2','v_d2phi','v_d3phi')} for v in VM}
    D[lam]['src']='A'
for f in glob.glob(S+'/B/full5_c*.json'):
    o=json.load(open(f)); lam=float(o['Lambda'])
    if lam in D: continue
    V=o['variants']
    D[lam]={v:{'v_dphi1':V[VM[v]]['spacing_d1'],'v_dphi2':V[VM[v]]['spacing_d2']} for v in VM}; D[lam]['src']='B'
json.dump({str(k):v for k,v in sorted(D.items())},open(S+'/reconcile/ident_union.json','w'))
for ph in (0,0.25,0.75):
    print('phase',ph)
    for lam in sorted(D):
        if abs((lam%2)-ph)>1e-9 and not (ph==0.75 and abs(lam%2-0.75)<1e-9): continue
        if lam%2!=ph: continue
        d=D[lam]
        if lam<20 or lam%8 in (0,0.25,0.75) or lam>58:
            print(f"{lam:7.2f} {d['src']} dphi raw {d['raw']['v_dphi1'][5]:+.6f} g2D3W {d['g2D3W']['v_dphi1'][5]:+.6f} Dconn {d['Dconn']['v_dphi1'][5]:+.6f} | eps4 Dconn {d['Dconn']['v_dphi1'][4]:+.6f}" + (f" | d2phi Dconn {d['Dconn']['v_d2phi'][5]:+.5f} d3phi {d['Dconn']['v_d3phi'][5]:+.5f}" if 'v_d2phi' in d['Dconn'] else ''))
