#include "low_basis.hpp"
string trim(string s){auto k=s.find_first_not_of(" \t");return k==string::npos?"":s.substr(k);}
U quotient(U big,U small){auto a=monvec(big);for(W w:monvec(small)){auto p=find(a.begin(),a.end(),w);if(p==a.end())throw runtime_error("not monomial divisor");a.erase(p);}return moncode(a);}
int degree(U m){int n=0;for(W w:monvec(m))n+=wn(w);return n;}
int main(int argc,char**argv){if(argc<4){cerr<<"input.poly base_dir output_prefix\n";return 2;}string root=argv[2],pref=argv[3];auto start=chrono::steady_clock::now();auto sec=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};QBasis b[4];for(int k=1;k<=3;k++)b[k].load(root+"/low"+to_string(k)+".basis");
 map<W,pair<QP,string>>binary;PolyWord wp;{ifstream f(root+"/binary.rows");string header;while(getline(f,header)){if(header.empty())continue;istringstream st(header);U dummy;string kind;int n,bs,d;st>>dummy>>kind>>n>>bs>>d;vector<int>w(n);for(int&a:w)st>>a;int nr;f>>nr;QP row;for(int i=0;i<nr;i++){W v;string co;f>>v>>co;mpq_class c(co);c.canonicalize();for(auto[m,a]:wp.get(v))qadd(row,m,c*a);}string discard;getline(f,discard);if(!row.empty()){string label=header.substr(header.find(' ')+1);W word=makew(w);if(row[moncode({word})]!=1)throw runtime_error("binary pivot");binary[word]={row,label};}}}
 QP todo=read_poly(argv[1]),normal;size_t original=todo.size();using CK=pair<U,string>;map<CK,mpq_class>cert;map<U,map<int,mpq_class>>history[4];long steps=0;
 while(!todo.empty()){
  U m=todo.rbegin()->first;mpq_class q=todo.rbegin()->second;auto factors=monvec(m);U sub=0;int k=0,j=-1;const QP*row=nullptr;string direct;
  for(W w:factors){auto it=binary.find(w);if(it==binary.end()&&wn(w)>=4){auto aa=vecw(w);int g=0;for(int a:aa)g=std::gcd(g,a);if(g>1){for(int&a:aa)a/=g;W small=makew(aa);QP sr;for(auto[m,c]:wp.get(w))qadd(sr,m,mpq_class(c));for(int j=0;j<=wn(w);j++){QP tail;for(auto[m,c]:wp.get(tailw(small,j)))qadd(tail,m,mpq_class(c));vector<W>logs(j,makew({g}));qmuladd(sr,tail,moncode(logs),-1,false);}ostringstream lab;lab<<"S "<<wn(w)<<" 0 "<<g;for(int a:aa)lab<<" "<<a;binary[w]={move(sr),lab.str()};it=binary.find(w);}}if(it!=binary.end()){sub=moncode({w});row=&it->second.first;direct=it->second.second;break;}}
  if(!row){set<U,greater<U>>candidates;for(int mask=1;mask<(1<<(int)factors.size());mask++){vector<W>v;int n=0;for(int i=0;i<(int)factors.size();i++)if(mask>>i&1){v.push_back(factors[i]);n+=wn(factors[i]);}if(n<=3)candidates.insert(moncode(v));}
   for(U cand:candidates){int n=degree(cand);auto it=b[n].leads.find(cand);if(it!=b[n].leads.end()){sub=cand;k=n;j=it->second;row=&b[n].basis[j];break;}}
  }
  if(!row){qadd(normal,m,q);todo.erase(m);continue;}
  U outer=quotient(m,sub);auto[check,div]=monmul(sub,outer);if(check!=m)throw runtime_error("monomial division");mpq_class fac=q/div;qmuladd(todo,*row,outer,-fac,false);mpq_class coeff=fac/monfact(outer);
  if(k)history[k][outer][j]+=coeff;else cert[{outer,direct}]+=coeff;
  if(++steps%20000==0)cerr<<"NORMALIZE steps="<<steps<<" todo="<<todo.size()<<" normal="<<normal.size()<<" sec="<<sec()<<"\n";
 }
 for(int k=1;k<=3;k++)for(auto&[outer,weights]:history[k])while(!weights.empty()){
  auto it=prev(weights.end());int j=it->first;mpq_class q=it->second;weights.erase(it);if(q==0)continue;auto&d=b[k].defs[j];istringstream st(b[k].labels[d.src]);U inside;st>>inside;string label;getline(st,label);label=trim(label);auto f=monvec(outer),g=monvec(inside);f.insert(f.end(),g.begin(),g.end());cert[{moncode(f),label}]+=q*d.inv;for(auto[i,c]:d.par)weights[i]+=q*c;
 }
 save_poly(pref+".poly",normal);ofstream out(pref+".certificate.txt");long count=0;for(auto&[key,c]:cert)if(c!=0){out<<c<<" "<<key.first<<" "<<key.second<<"\n";count++;}
 map<int,int>types;for(auto[m,c]:normal){int n=0;for(W w:monvec(m))n=max(n,wn(w));types[n]++;}
 ofstream report(pref+".report.json");report<<"{\"input_terms\":"<<original<<",\"remaining_terms\":"<<normal.size()<<",\"rewrite_steps\":"<<steps<<",\"certificate_rows\":"<<count<<",\"seconds\":"<<sec()<<"}\n";
 cerr<<"NORMAL FORM input="<<original<<" remain="<<normal.size()<<" steps="<<steps<<" cert="<<count<<" seconds="<<sec()<<"\n";for(auto[n,c]:types)cerr<<"MAX_FACTOR_WEIGHT "<<n<<" "<<c<<"\n";
}
