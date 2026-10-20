from pathlib import Path
W=Path(__file__).resolve().parents[1];D=W/'code/precision_quad';D.mkdir(exist_ok=True)
(D/'quad_support.hpp').write_text('''#pragma once\n#include <bits/stdc++.h>\n#include <quadmath.h>\nusing LD=__float128;\ninline LD abs(LD v){return fabsq(v);}\ninline std::ostream& operator<<(std::ostream&o,LD v){char b[180];quadmath_snprintf(b,sizeof b,"%.*Qg",(int)o.precision(),v);o<<b;return o;}\ninline std::istream& operator>>(std::istream&i,LD&v){std::string s;i>>s;v=strtoflt128(s.c_str(),nullptr);return i;}\n''')
for fn in ['coordinate_integrate.cpp','coordinate_point_common.hpp','tree_common.hpp','coordinate_tree_integrate_allocated.cpp']:
 s=(W/'code'/fn).read_text()
 s=s.replace('using namespace std;using LD=long double;','#include "quad_support.hpp"\nusing namespace std;')
 for a,b in [('cosl(','cosq('),('acosl(','acosq('),('sqrtl(','sqrtq('),('logl(','logq('),('expl(','expq('),('powl(','powq('),('fabsl(','fabsq(')]:s=s.replace(a,b)
 s=s.replace('max(.5L,','max(LD(.5L),')
 s=s.replace('in.read((char*)w.data(),w.size()*sizeof(LD));','vector<long double>tmp(w.size());in.read((char*)tmp.data(),tmp.size()*sizeof(long double));for(size_t i=0;i<w.size();i++)w[i]=tmp[i];')
 (D/fn).write_text(s)
