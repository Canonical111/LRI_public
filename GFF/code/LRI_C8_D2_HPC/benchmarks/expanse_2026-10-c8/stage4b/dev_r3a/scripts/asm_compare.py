#!/usr/bin/env python3
"""R3a evidence: the same translation unit compiled before and after R3a (g++ -S with the worker's flags), compared
function by function (standard library only).

  asm_compare.py BASELINE.s CANDIDATE.s [--output FILE]

A function is the text from its label (declared `.type NAME, @function`) to its `.size NAME, .-NAME`; hot and cold parts
(NAME.cold) are separate functions, and jump tables emitted inside a function belong to it. Normalization: every
constant-pool reference .LC<n> is replaced by the content of its definition (the data directives under the label), and
every other local label (.L<n>, .LFB<n>, .LCOLDB<n>, .LEHB<n>, ...) is renumbered by order of first appearance inside the
function, because GCC numbers labels across the whole translation unit. Identical normalized text means identical
instructions, operands, constants and control flow. The record lists the identical and different functions, those in
one file only, and the watched groups: MP-backend code (gmp_float, cpp_dec_float, mpf), calculate_shared of each type,
and the worker's long-double code (main._omp_fn.0 holds the inlined sample/evaluate/calculate_products/
calculate_reference; load_graph, prepare, rates).
"""
import argparse,difflib,hashlib,json,re,subprocess,sys
LABEL=re.compile(r'^([^\s:]+):\s*$')
def demangle(names):
    try:
        out=subprocess.run(['c++filt'],input='\n'.join(names),capture_output=True,text=True,check=True).stdout.splitlines()
        return dict(zip(names,out))if len(out)==len(names)else{n:n for n in names}
    except Exception:return {n:n for n in names}
def parse(path):
    lines=open(path).read().splitlines();funcs={};consts={};types=set();cur=None;body=[];lc=None;lcbody=[]
    for ln in lines:
        s=ln.strip()
        m=re.match(r'^\.type\s+([^,\s]+),\s*@function',s)
        if m:types.add(m.group(1))
        lm=LABEL.match(ln)
        if lc is not None:
            if lm or s.startswith('.section')or s.startswith('.text')or s.startswith('.align')or s.startswith('.p2align'):
                consts[lc]=' | '.join(lcbody);lc=None
            else:lcbody.append(re.sub(r'\s+',' ',s));continue
        if lm and re.fullmatch(r'\.LC\d+',lm.group(1)):lc=lm.group(1);lcbody=[];continue
        if cur is None:
            if lm and lm.group(1)in types:cur=lm.group(1);body=[]
            continue
        m=re.match(r'^\.size\s+([^,\s]+),\s*\.-',s)
        if m and m.group(1)==cur:funcs[cur]=body;cur=None;continue
        if not s or s.startswith('#')or s.startswith('.cfi_')or s.startswith('.loc')or s.startswith('.file'):continue
        body.append(re.sub(r'\s+',' ',s))
    if lc is not None:consts[lc]=' | '.join(lcbody)
    return funcs,consts
def normalize(body,consts):
    out=[];ren={}
    def lc(m):return 'LC['+hashlib.sha256(consts.get(m.group(0),'?'+m.group(0)).encode()).hexdigest()[:16]+']'
    def lab(m):
        k=m.group(0)
        if k not in ren:ren[k]=f'L{len(ren)}'
        return ren[k]
    for s in body:
        s=re.sub(r'\.LC\d+\b',lc,s)
        s=re.sub(r'\.L[A-Za-z_]*\d+\b',lab,s)
        out.append(s)
    return out
WATCH={'mp_backend':re.compile(r'gmp_float|cpp_dec_float|__gmp|\bmpf_'),
       'calculate_shared':re.compile(r'calculate_shared<'),
       'worker_long_double':re.compile(r'^main\._omp_fn|^main$|^main\.cold|evaluate\(|sample\(|calculate_products|calculate_reference|load_graph|prepare\(|rates\(|tail_add')}
def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('baseline');p.add_argument('candidate');p.add_argument('--output')
    a=p.parse_args();(FA,CA),(FB,CB)=parse(a.baseline),parse(a.candidate)
    names=sorted(set(FA)|set(FB));dm=demangle(names)
    same,diff=[],{}
    for k in sorted(set(FA)&set(FB)):
        x,y=normalize(FA[k],CA),normalize(FB[k],CB)
        if x==y:same.append(k)
        else:diff[k]={'demangled':dm[k],'baseline_lines':len(x),'candidate_lines':len(y),'diff_head':list(difflib.unified_diff(x,y,lineterm='',n=1))[:40]}
    only_a=sorted(set(FA)-set(FB));only_b=sorted(set(FB)-set(FA))
    watch={}
    for g,rx in WATCH.items():
        ks=[k for k in names if rx.search(dm[k])]
        watch[g]={'functions':len(ks),'identical':sum(k in same for k in ks),'different':[dm[k]for k in ks if k in diff],
                  'only_baseline':[dm[k]for k in ks if k in only_a],'only_candidate':[dm[k]for k in ks if k in only_b]}
    rec={'schema':'c8-d2-asm-compare-1','baseline':a.baseline,'candidate':a.candidate,'baseline_sha256':hashlib.sha256(open(a.baseline,'rb').read()).hexdigest(),
         'candidate_sha256':hashlib.sha256(open(a.candidate,'rb').read()).hexdigest(),'functions_baseline':len(FA),'functions_candidate':len(FB),
         'identical':len(same),'different':diff,'only_baseline':[dm[k]for k in only_a],'only_candidate':[dm[k]for k in only_b],'watched':watch}
    if a.output:open(a.output,'w').write(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({'functions':[len(FA),len(FB)],'identical':len(same),'different':[dm[k][:160]for k in diff],
                      'only_baseline':[x[:160]for x in rec['only_baseline']],'only_candidate':[x[:160]for x in rec['only_candidate']],
                      'watched':{g:{k:(v if not isinstance(v,list)else[x[:160]for x in v])for k,v in w.items()}for g,w in watch.items()}},indent=1))
if __name__=='__main__':main()
