"""Explicit unweighted one/two-variable Horn arrays for finite sampling.
This is a parameter-array compiler, NOT an infinite-sum numerical evaluator.
Every row is (Pochhammer parameter, integer index vector).  Negative integer
index components are allowed in the middle primitive channel.
"""
import sympy as sp
from dataclasses import dataclass,replace
import json
from pathlib import Path
q,t=sp.symbols('q t')
G=sp.gamma

@dataclass
class Term:
    name:str
    pref:object
    upper:list
    lower:list
    z:tuple
    def dump(self):
        return {'name':self.name,'prefactor':str(self.pref),
                'upper':[[str(a),list(v)] for a,v in self.upper],
                'lower':[[str(a),list(v)] for a,v in self.lower],
                'arguments':list(self.z)}

def rows(a,v,n=1):return [(a,tuple(v)) for _ in range(n)]

def right_templates(r):
    u=rows(1,[1])+rows(q+t,[1],r)+rows(1-q+t,[1],r)
    l=rows(2*q+t,[1],r)+rows(1+t,[1],r)
    zero=Term('right_spin_zero',(G(q+t)*G(-t)/G(2*q+t)/G(q-t))**r,u,l,(1,))
    u=rows(q+t+1,[1,1],r)+rows(1,[1,0])+rows(2*q+1,[1,0])+rows(4*q-1,[1,0])+rows(1,[0,1])+rows(1-q+t,[0,1],r)
    l=rows(2*q+t+1,[1,1],r)+rows(2*q,[1,0])+rows(2,[1,0])+rows(1+t,[0,1],r)
    pos=Term('right_positive_spin',4*q*(G(q+t+1)*G(-t)/G(2*q+t+1)/G(q-t))**r,u,l,(1,1))
    return zero,pos

def middle_template(r):
    u=rows(2*q+1,[1,1])+rows(4*q-1,[1,1])+rows(1,[1,0])+rows(1-t,[1,0],r)+rows(1,[0,1])+rows(q+t,[0,1],r)
    l=rows(2*q,[1,1])+rows(2,[1,1])+rows(1+q-t,[1,0],r)+rows(2*q+t,[0,1],r)
    return Term('middle',4*q*(G(q+t)*G(1-t)/G(2*q+t)/G(1+q-t))**r,u,l,(1,1))

def substitute(term,s):
    return Term(term.name+'_'+str(s),term.pref.subs(t,s),[(a.subs(t,s) if hasattr(a,'subs') else a,v) for a,v in term.upper],[(a.subs(t,s) if hasattr(a,'subs') else a,v) for a,v in term.lower],term.z)

def measure(theta,v):return G(theta+v)*G(theta-v)/(G(v)*G(-v))

def add_right_measure(term,theta,v,w):
    u=term.upper+rows(theta+v,w)+rows(1+v,w)
    l=term.lower+rows(v,w)+rows(1+v-theta,w)
    return Term(term.name+'_theta_'+str(theta),term.pref*measure(theta,v),u,l,term.z)

def add_middle_measure(term,theta,v):
    return Term(term.name+'_theta_'+str(theta),term.pref*measure(theta,v),
        term.upper+rows(theta+v,[-1,1])+rows(theta-v,[1,-1]),
        term.lower+rows(v,[-1,1])+rows(-v,[1,-1]),term.z)

def primitive_templates():
    z,p=right_templates(7);c=middle_template(7);v=q+2*t
    z=add_right_measure(z,2*q,v,[2])
    p=replace(p,pref=-p.pref,z=(-1,1));c=replace(c,pref=-c.pref,z=(-1,-1))
    p0=add_right_measure(p,2*q,v+1,[1,2])
    c0=add_middle_measure(c,2*q,v-1)
    def weighted(a,index):
        return replace(a,pref=a.pref*(4*q-1),
          upper=[(4*q if par==4*q-1 and vec==index else par,vec) for par,vec in a.upper],
          lower=[(sp.Integer(1) if par==2 and vec==index else par,vec) for par,vec in a.lower])
    p1=add_right_measure(weighted(p,(1,0)),2*q-1,v+1,[1,2])
    c1=add_middle_measure(weighted(c,(1,1)),2*q-1,v-1)
    return [z,p0,p1],[c0,c1]

def sample_templates(which):
    if which in [3,4]:
        right=list(right_templates(which));mid=[middle_template(which)]
    elif which==7:right,mid=primitive_templates()
    else:raise ValueError('which must be 3, 4 or 7')
    return right+[substitute(x,1-q-t) for x in right]+mid

def coefficient(term,inds,qv,tv,mp):
    subs={q:sp.Float(str(qv.real),70)+sp.I*sp.Float(str(qv.imag),70),t:sp.Float(str(tv.real),70)+sp.I*sp.Float(str(tv.imag),70)}
    def ev(expr):
        z=sp.N(sp.sympify(expr).subs(subs),65)
        return mp.mpc(str(sp.re(z)),str(sp.im(z)))
    val=ev(term.pref)
    for a,v in term.upper:val*=mp.rf(ev(a),sum(vi*ni for vi,ni in zip(v,inds)))
    for b,v in term.lower:val/=mp.rf(ev(b),sum(vi*ni for vi,ni in zip(v,inds)))
    for n,z in zip(inds,term.z):val*=z**n/mp.factorial(n)
    return val

if __name__=='__main__':
    dest=Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/arrays');dest.mkdir(parents=True,exist_ok=True)
    for r in [3,4,7]:
        ts=sample_templates(r)
        data={'q':'d/4','node':'t_j=-q/2+j/(2r-1)+I/(8*pi*r), 0<=j<r',
          'sampling':'take real parts; cosine transform in note','r':r,
          'blocks_per_node':len(ts),'nodes':r,'maximum_function_values':r*len(ts),
          'templates':[a.dump() for a in ts]}
        (dest/f'primitive_r{r}.json').write_text(json.dumps(data,indent=2))
        print(r,len(ts),r*len(ts))
