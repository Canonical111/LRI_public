from pathlib import Path
W=Path(__file__).resolve().parents[1]
s=(W/'provenance/kernel_previous.hpp').read_text()
s=s.replace('vector<ld>alpha,dp;};','vector<ld>alpha,dp;vector<pair<int,int>> prod_ops;vector<int>mon_ids;};')
needle='Eval evaluate(const Graph&g,const vector<ld>&logx,ld factor){'
new=r'''// Shared product DAG, retaining the previous extended-precision fallbacks.
pair<ld,ld> calculate_products(const Graph&g,const vector<ld>&logx,ld shift){
 vector<ld>x(g.E),xs(g.E),p(g.prod_ops.size()+1);p[0]=1;ld S=0;
 for(int j=0;j<g.E;j++){x[j]=expl(logx[j]);S+=x[j];xs[j]=expl(logx[j]-shift/g.L);}
 for(size_t j=0;j<g.prod_ops.size();j++){auto o=g.prod_ops[j];p[j+1]=p[o.first]*xs[o.second];}
 ld val=0,err=0;
 for(const auto&t:g.terms){ld U=0,n=0,na=0;for(int i:t.ids)U+=p[g.mon_ids[i]];
 for(int j=0;j<g.E;j++)if(t.co[j]){ld z=ld(t.co[j])*x[j];n+=z;na+=abs(z);}
 ld den=D==2?U:U*sqrtl(U);val+=n/den;err+=na/den;}
 return{val/S,err/S};
}
Eval evaluate(const Graph&g,const vector<ld>&logx,ld factor){'''
s=s.replace(needle,new)
s=s.replace('auto v=calculate<ld>(g,logx,shift);','bool moderate=true;for(ld x:logx)if(abs(x-shift/g.L)>500)moderate=false;\n #ifdef REFERENCE_EVAL\n auto v=calculate<ld>(g,logx,shift);\n #else\n auto v=moderate?calculate_products(g,logx,shift):calculate<ld>(g,logx,shift);\n #endif\n')
s=s.replace('g.Z=g.dp.back();}',r'''g.Z=g.dp.back();
  vector<int> ind(1<<g.E,-1);ind[0]=0;
  function<int(unsigned)> get=[&](unsigned mask)->int{if(ind[mask]>=0)return ind[mask];int j=__builtin_ctz(mask);int prev=get(mask^(1u<<j));g.prod_ops.push_back({prev,j});return ind[mask]=int(g.prod_ops.size());};
  for(unsigned mask:g.masks){if(__builtin_popcount(mask)!=g.L)throw runtime_error("nonhomogeneous mask");g.mon_ids.push_back(get(mask));}
 }''')
(W/'code/kernel.hpp').write_text(s)
