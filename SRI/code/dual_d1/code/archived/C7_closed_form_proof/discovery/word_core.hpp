#pragma once
#include <bits/stdc++.h>
#include <gmpxx.h>
using namespace std;
using W=uint32_t;using U=uint64_t;using Z=int64_t;
using IV=vector<pair<W,Z>>;
int wn(W w){return w>>24;}
int wa(W w,int i){return (w>>(4*(wn(w)-1-i)))&15;}
W makew(const vector<int>&a){W w=0;for(int c:a)w=w*16+c;return w|((W)a.size()<<24);}
vector<int> vecw(W w){vector<int>a;for(int i=0;i<wn(w);i++)a.push_back(wa(w,i));return a;}
W tailw(W w,int k=1){int n=wn(w)-k;return ((W)n<<24)|(w&((1u<<(4*n))-1));}
W prefixw(W w,int n){return ((W)n<<24)|((w&0xffffff)>>(4*(wn(w)-n)));}
W prew(int a,W w){int n=wn(w);return ((W)(n+1)<<24)|((W)a<<(4*n))|(w&0xffffff);}
int maxw(W w){int m=0;for(int a:vecw(w))m=max(m,a);return m;}
vector<W> factorw(W w){vector<int>a=vecw(w);vector<W>out;int n=a.size(),i=0;while(i<n){int j=i+1,k=i;while(j<n&&a[k]<=a[j]){if(a[k]<a[j])k=i;else k++;j++;}int step=j-k;while(i<=k){out.push_back(makew(vector<int>(a.begin()+i,a.begin()+i+step)));i+=step;}}return out;}
void shrec(const vector<int>&a,const vector<int>&b,int i,int j,W acc,map<W,Z>&out){if(i==(int)a.size()&&j==(int)b.size()){out[acc|((W)(a.size()+b.size())<<24)]++;return;}if(i<(int)a.size())shrec(a,b,i+1,j,(acc<<4)|a[i],out);if(j<(int)b.size())shrec(a,b,i,j+1,(acc<<4)|b[j],out);}
IV shwords(W a,W b){map<W,Z>out;shrec(vecw(a),vecw(b),0,0,0,out);return IV(out.begin(),out.end());}
struct Primitive{
 unordered_map<W,IV>cache;long long calls=0;
 const IV& get(W w){auto it=cache.find(w);if(it!=cache.end())return it->second;calls++;auto ff=factorw(w);IV res;
 if(ff.size()==1){res={{w,1}};}else{W a=ff[0],b=tailw(w,wn(a));auto sh=shwords(a,b);map<W,Z> out;Z div=0;
 for(auto[v,c]:sh){if(v==w){div=c;continue;}if(v>w)throw runtime_error("shuffle order");const IV&p=get(v);for(auto[k,d]:p)out[k]-=c*d;}
 if(!div)throw runtime_error("no divisor");for(auto[k,c]:out)if(c){if(c%div)throw runtime_error("primitive denominator");res.push_back({k,c/div});}}
 return cache.emplace(w,move(res)).first->second;}
};
struct Aff{int b,a;bool operator==(const Aff&o)const{return b==o.b&&a==o.a;}};
using AW=vector<Aff>;
U affcode(const AW&a){U out=a.size();for(auto t:a)out=(out<<5)|((t.b<<4)|t.a);return out;}
AW affdecode(U code){AW rev;while(code>=32){rev.push_back({int((code>>4)&1),int(code&15)});code>>=5;}reverse(rev.begin(),rev.end());if(code!=rev.size())throw runtime_error("affcode");return rev;}
struct Fib{
 unordered_map<U,IV>cache;
 IV get(const AW&a){if(a.empty())return {{0,1}};U ac=affcode(a);auto it=cache.find(ac);if(it!=cache.end())return it->second;
 map<W,Z>out;int n=a.size();for(int i=0;i<n;i++){AW tail=a;tail.erase(tail.begin()+i);IV lo=get(tail);Aff self=a[i];for(int side=0;side<2;side++){Aff nb=side?(i+1<n?a[i+1]:Aff{0,0}):(i?a[i-1]:Aff{1,0});if(nb.b==self.b)continue;int root=self.a+nb.a;for(auto[w,c]:lo)out[prew(root,w)]+=(side?-c:c);}}
 IV res;for(auto[w,c]:out)if(c)res.push_back({w,c});if(n<=4 || (n==5&&cache.size()<200000))cache.emplace(ac,res);return res;}
};
IV project_row(const AW&a,int m,Primitive&p,Fib&f){map<W,Z>out;auto raw=f.get(a);for(auto[w,c]:raw){if(maxw(w)!=m)continue;for(auto[v,d]:p.get(w))out[v]+=c*d;}IV res;for(auto[w,c]:out)if(c)res.push_back({w,c});return res;}
vector<U> invfib(W word,int M){unordered_set<U>cur{0};auto ww=vecw(word);for(int k=ww.size()-1;k>=0;k--){unordered_set<U>next;for(U sc:cur){AW a=sc?affdecode(sc):AW{};for(int i=0;i<=(int)a.size();i++){for(int side=0;side<2;side++){Aff nb=side?(i<(int)a.size()?a[i]:Aff{0,0}):(i?a[i-1]:Aff{1,0});Aff nn{1-nb.b,ww[k]-nb.a};if(nn.a<nn.b)continue;AW ns=a;ns.insert(ns.begin()+i,nn);int mx[2]={0,0};for(auto t:ns)mx[t.b]=max(mx[t.b],t.a);if(mx[0]+mx[1]<=M)next.insert(affcode(ns));}}}cur=move(next);}
 vector<U>out;for(U sc:cur){auto a=affdecode(sc);if(a[0].b==0&&a.back().b==1)out.push_back(sc);}return out;}
bool scaling_source(U sc){return sc>>63;}
U scale_code(int d,W w){return (1ULL<<63)|((U)d<<32)|w;}
void write_label(ostream&o,U sc){if(scaling_source(sc)){W w=(W)sc;int d=(sc>>32)&15;o<<"S "<<wn(w)<<" 0 "<<d;for(int a:vecw(w))o<<" "<<a;return;}auto a=affdecode(sc);int bits=0;for(auto t:a)bits=bits*2+t.b;o<<"D "<<a.size()<<" "<<bits<<" 0";for(auto t:a)o<<" "<<t.a;}
U read_label(istream&i){string kind;int n,bs,d;i>>kind>>n>>bs>>d;if(!i)throw runtime_error("label");if(kind=="S"){vector<int>a(n);for(int&v:a)i>>v;return scale_code(d,makew(a));}if(kind!="D")throw runtime_error("label type");AW a;for(int j=0;j<n;j++){int v;i>>v;a.push_back({(bs>>(n-1-j))&1,v});}return affcode(a);}
IV raw_source(U sc,Fib&f){if(!scaling_source(sc))return f.get(affdecode(sc));W w=(W)sc;int d=(sc>>32)&15;vector<int>a=vecw(w);for(int&v:a)v*=d;map<W,Z>r;r[makew(a)]++;for(int j=0;j<=wn(w);j++)for(auto[v,c]:shwords(makew(vector<int>(j,d)),tailw(w,j)))r[v]-=c;IV out;for(auto[v,c]:r)if(c)out.push_back({v,c});return out;}
IV project_source(U sc,int m,Primitive&p,Fib&f){if(!scaling_source(sc))return project_row(affdecode(sc),m,p,f);W w=(W)sc;int d=(sc>>32)&15;auto a=vecw(w);for(int&v:a)v*=d;map<W,Z>out;W big=makew(a);if(maxw(big)==m)for(auto[v,c]:p.get(big))out[v]+=c;if(maxw(w)==m)for(auto[v,c]:p.get(w))out[v]-=c;IV r;for(auto[v,c]:out)if(c)r.push_back({v,c});return r;}
map<W,mpq_class> read_target(string file,int weight,int maxletter){ifstream in(file);string c;map<W,mpq_class>out;while(in>>c){int n;in>>n;vector<int>a(n);for(int&i:a)in>>i;if(n!=weight||(maxletter>=0&&*max_element(a.begin(),a.end())!=maxletter))continue;mpq_class q(c);q.canonicalize();out[makew(a)]+=q;}return out;}
void save_target(string file,const map<W,mpq_class>&t){ofstream o(file);for(auto[w,c]:t)if(c!=0){o<<c<<" "<<wn(w);for(int v:vecw(w))o<<" "<<v;o<<"\n";}}
U moncode(vector<W>a){sort(a.rbegin(),a.rend());U out=0;int used=0;for(W w:a){int n=wn(w),k=3+4*n;U token=((U)n<<(4*n))|(w&0xffffff);used+=k;if(used>64)throw runtime_error("monomial overflow");out|=token<<(64-used);}return out;}
vector<W> monvec(U code){vector<W>out;while(code){int n=code>>61;if(n<1||n>6)throw runtime_error("mondecode");int count=3+4*n;W raw=(code>>(64-count))&((1u<<(4*n))-1);out.push_back(((W)n<<24)|raw);code<<=count;}return out;}
int binom(int n,int k){int v=1;for(int j=1;j<=k;j++)v=v*(n-j+1)/j;return v;}
Z fact(int n){Z r=1;for(int i=2;i<=n;i++)r*=i;return r;}
Z monfact(U m){auto a=monvec(m);map<W,int>count;for(W w:a)count[w]++;Z fac=1;for(auto[w,n]:count)fac*=fact(n);return fac;}
pair<U,Z> monmul(U a,U b){auto x=monvec(a),y=monvec(b);map<W,pair<int,int>>ct;for(W w:x)ct[w].first++;for(W w:y)ct[w].second++;Z c=1;for(auto[w,k]:ct)c*=binom(k.first+k.second,k.first);x.insert(x.end(),y.begin(),y.end());return {moncode(x),c};}
using PV=vector<pair<U,Z>>;
struct PolyWord{
 unordered_map<W,PV>cache;long long calls=0;
 const PV&get(W w){auto it=cache.find(w);if(it!=cache.end())return it->second;calls++;auto ff=factorw(w);PV res;
 if(wn(w)==0){res={{0,1}};}else if(ff.size()==1){res={{moncode({w}),1}};}else{W a=ff[0],b=tailw(w,wn(a));map<U,Z>out;for(auto[m,c]:get(b)){auto[k,d]=monmul(moncode({a}),m);out[k]+=c*d;}auto sh=shwords(a,b);Z div=0;for(auto[v,c]:sh){if(v==w){div=c;continue;}if(v>w)throw runtime_error("poly shuffle order");for(auto[k,d]:get(v))out[k]-=c*d;}if(!div)throw runtime_error("poly division zero");for(auto[k,c]:out)if(c){if(c%div)throw runtime_error("nonintegral divided power");res.push_back({k,c/div});}}
 return cache.emplace(w,move(res)).first->second;}
};
using QP=map<U,mpq_class>;
void qadd(QP&out,U m,const mpq_class&c){out[m]+=c;if(out[m]==0)out.erase(m);}
void qmuladd(QP&out,const QP&r,U mon,const mpq_class&fac,bool ordinary=false){mpq_class co=fac;if(ordinary)co*=monfact(mon);for(auto[m,c]:r){auto[k,d]=monmul(m,mon);qadd(out,k,co*c*d);}}
void save_poly(string file,const QP&p){ofstream o(file);for(auto[m,c]:p)if(c!=0)o<<c<<" "<<m<<"\n";}
QP read_poly(string file){ifstream f(file);string c;U m;QP out;while(f>>c>>m){mpq_class q(c);q.canonicalize();qadd(out,m,q);}return out;}
