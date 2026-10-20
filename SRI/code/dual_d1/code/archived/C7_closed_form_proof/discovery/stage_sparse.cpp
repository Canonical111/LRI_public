#include "word_core.hpp"
struct Ent {uint32_t w;U c;};
struct Def {int src;U inv;vector<Ent> par;};
U P=2305843009213693951ULL;
inline U addm(U a,U b){U c=a+b;return c>=P?c-P:c;}
inline U subm(U a,U b){return a>=b?a-b:a+P-b;}
inline U mulm(U a,U b){return (U)((__uint128_t)a*b%P);}
U powm(U a,U e){U v=1;while(e){if(e&1)v=mulm(v,a);a=mulm(a,a);e>>=1;}return v;}
U im(Z a){if(a<0)return P-((U)(-a)%P);return a%P;}
U qm(const mpq_class&q){return mulm(mpz_fdiv_ui(q.get_num_mpz_t(),P),powm(mpz_fdiv_ui(q.get_den_mpz_t(),P),P-2));}
struct Engine{
 vector<vector<Ent>>basis;vector<Def>defs;vector<int>leads;vector<uint32_t>pivot;vector<U>val;vector<char>active_flag,queued;vector<uint32_t>active;priority_queue<int,vector<int>,greater<int>>heap;vector<int>frequency;vector<Ent>last_residual;long long nnz=0,pnz=0;
 Engine(int n,const vector<int>&freq):leads(n,-1),val(n,0),active_flag(n,0),queued(n,0),frequency(freq){}
 void push(uint32_t w,U c,bool neg=false){if(!c)return;if(!active_flag[w]){active_flag[w]=1;active.push_back(w);}val[w]=neg?subm(val[w],c):addm(val[w],c);int j=leads[w];if(j>=0&&!queued[j]){queued[j]=1;heap.push(j);}}
 void clear(){for(auto w:active){val[w]=0;active_flag[w]=0;}active.clear();while(!heap.empty()){queued[heap.top()]=0;heap.pop();}}
 void eliminate(int j,U f){for(auto e:basis[j])push(e.w,mulm(f,e.c),true);}
 vector<Ent> reduction(){vector<Ent>par;while(!heap.empty()){int j=heap.top();heap.pop();queued[j]=0;U f=val[pivot[j]];if(!f)continue;par.push_back({(uint32_t)j,f});eliminate(j,f);}return par;}
 bool insert(const vector<Ent>&r,int src){for(auto e:r)push(e.w,e.c);auto par=reduction();vector<Ent>rem;for(auto w:active)if(val[w]){if(leads[w]>=0)throw runtime_error("unreduced pivot");rem.push_back({w,val[w]});}clear();if(rem.empty())return false;
 auto best=min_element(rem.begin(),rem.end(),[&](Ent a,Ent b){return frequency[a.w]!=frequency[b.w]?frequency[a.w]<frequency[b.w]:a.w>b.w;});uint32_t lead=best->w;U inv=powm(best->c,P-2);int idx=basis.size();leads[lead]=idx;pivot.push_back(lead);for(auto&e:rem)e.c=mulm(e.c,inv);sort(rem.begin(),rem.end(),[](Ent a,Ent b){return a.w<b.w;});for(auto&e:par){e.c=mulm(e.c,inv);if(e.c)e.c=P-e.c;}nnz+=rem.size();pnz+=par.size();basis.push_back(move(rem));defs.push_back({src,inv,move(par)});return true;}
 bool solve(const vector<Ent>&tar,map<int,U>&out){for(auto e:tar)push(e.w,e.c);auto par=reduction();bool ok=true;last_residual.clear();for(auto w:active)if(val[w]){ok=false;last_residual.push_back({w,val[w]});}clear();if(!ok)return false;vector<U>weights(basis.size());for(auto e:par)weights[e.w]=addm(weights[e.w],e.c);out.clear();for(int j=(int)basis.size()-1;j>=0;j--){U f=weights[j];if(!f)continue;auto&d=defs[j];out[d.src]=addm(out[d.src],mulm(f,d.inv));for(auto e:d.par)weights[e.w]=addm(weights[e.w],mulm(f,e.c));}return true;}
};

#include <omp.h>
struct Row{U sc;IV r;int overlap;int fresh=0;};
int main(int argc,char**argv){if(argc<5){cerr<<"weight max target prefix [prime] [selected.labels]\n";return 2;}int n=stoi(argv[1]),m=stoi(argv[2]);string file=argv[3],pref=argv[4];if(argc>=6)P=stoull(argv[5]);bool selected=argc>=7;auto start=chrono::steady_clock::now();auto sec=[&](){return chrono::duration<double>(chrono::steady_clock::now()-start).count();};Primitive pp;Fib ff;
 auto raw=read_target(file,n,m);map<W,mpq_class>tar;for(auto[w,c]:raw)for(auto[v,d]:pp.get(w))tar[v]+=c*d;for(auto it=tar.begin();it!=tar.end();)if(it->second==0)it=tar.erase(it);else ++it;
 vector<Row>rows;string cache=pref+".rowcache";ifstream cached(cache,ios::binary);
 if(!selected&&cached){U count;cached.read((char*)&count,8);rows.resize(count);for(auto&r:rows){uint32_t size;cached.read((char*)&r.sc,8);cached.read((char*)&size,4);r.r.resize(size);for(auto&[w,c]:r.r){cached.read((char*)&w,4);cached.read((char*)&c,8);}if(!cached)throw runtime_error("cache truncated");}cerr<<"CACHE rows="<<rows.size()<<" sec="<<sec()<<"\n";}
 else{
 vector<U>cand;
 if(selected){ifstream f(argv[6]);while(f.peek()!=EOF){U c=read_label(f);cand.push_back(c);f>>ws;}}
 else if(raw.size()>300||getenv("FORCE_ALL")){for(int bs=1;bs<(1<<(n-1));bs+=2)for(int pn=0;pn<m;pn++){int qp=m-pn;AW a(n);function<void(int,int,int)>rec=[&](int i,int mn,int mp){if(i==n){if(mn==pn&&mp==qp)cand.push_back(affcode(a));return;}int b=(bs>>(n-1-i))&1;for(int v=b;v<=(b?qp:pn);v++){a[i]={b,v};rec(i+1,b?mn:max(mn,v),b?max(mp,v):mp);}};rec(0,-1,0);}sort(cand.begin(),cand.end());}
 else{unordered_set<U>s;for(auto[w,c]:raw){auto a=vecw(w);for(int r=0;r<2;r++){for(U sc:invfib(makew(a),m))s.insert(sc);reverse(a.begin(),a.end());}}cand.assign(s.begin(),s.end());sort(cand.begin(),cand.end());}
 cerr<<"CANDIDATES "<<cand.size()<<" target="<<tar.size()<<" seconds="<<sec()<<"\n";
 rows.resize(cand.size());atomic<int>done(0);int threads=selected?1:2;
 #pragma omp parallel num_threads(threads)
 {Primitive localp;Fib localf;
 #pragma omp for schedule(dynamic,512)
 for(size_t i=0;i<cand.size();i++){rows[i].sc=cand[i];rows[i].r=project_source(cand[i],m,localp,localf);int k=++done;if(k%50000==0){
 #pragma omp critical
 cerr<<"GENERATED "<<k<<" sec="<<sec()<<"\n";}}
 }
 if(!selected){rows.erase(remove_if(rows.begin(),rows.end(),[](const Row&r){return r.r.empty();}),rows.end());ofstream o(cache,ios::binary);U count=rows.size();o.write((char*)&count,8);for(auto&r:rows){uint32_t size=r.r.size();o.write((char*)&r.sc,8);o.write((char*)&size,4);for(auto[w,c]:r.r){o.write((char*)&w,4);o.write((char*)&c,8);}}cerr<<"CACHE SAVED rows="<<rows.size()<<" seconds="<<sec()<<"\n";}
 }
 if(!selected){unordered_set<U>have;for(auto&r:rows)have.insert(r.sc);for(int d=2;d<=m;d++)if(m%d==0){int mx=m/d;vector<int>a(n);function<void(int,int)>rec=[&](int i,int high){if(i==n){if(high!=mx||a.back()==0)return;W w=makew(a);if(factorw(w).size()!=1)return;U sc=scale_code(d,w);if(have.insert(sc).second)rows.push_back({sc,project_source(sc,m,pp,ff),0,0});return;}for(int v=0;v<=mx;v++){a[i]=v;rec(i+1,max(high,v));}};rec(0,0);}cerr<<"WITH SCALING "<<rows.size()<<" rows\n";}
 set<W>cols;for(auto[w,c]:tar)cols.insert(w);for(auto&r:rows){r.overlap=0;for(auto[w,c]:r.r){cols.insert(w);r.overlap+=tar.count(w);}}
 if(!selected)sort(rows.begin(),rows.end(),[](const Row&a,const Row&b){return make_tuple(a.overlap==0,(int)a.r.size()-a.overlap,a.r.size(),-a.overlap,a.sc)<make_tuple(b.overlap==0,(int)b.r.size()-b.overlap,b.r.size(),-b.overlap,b.sc);});
 unordered_map<W,uint32_t>ids;int idx=0;for(W w:cols)ids[w]=idx++;vector<int>frequency(ids.size());for(auto&r:rows)for(auto[w,c]:r.r)frequency[ids[w]]++;
 vector<Ent>target;for(auto[w,c]:tar)target.push_back({ids[w],qm(c)});Engine eng(ids.size(),frequency);map<int,U>sol;bool ok=false;int last=0;
 cerr<<"ELIMINATING rows="<<rows.size()<<" cols="<<cols.size()<<" seconds="<<sec()<<"\n";pp.cache.clear();ff.cache.clear();
 for(int i=0;i<(int)rows.size();i++){vector<Ent>r;for(auto[w,c]:rows[i].r)r.push_back({ids[w],im(c)});eng.insert(r,i);rows[i].r.clear();rows[i].r.shrink_to_fit();if(i%2500==0||i==(int)rows.size()-1){if(eng.solve(target,sol)){ok=true;last=i;break;}if(i%2500==0)cerr<<"ELIM row="<<i<<" rank="<<eng.basis.size()<<" nnz="<<eng.nnz<<" parents="<<eng.pnz<<" sec="<<sec()<<"\n";if(!selected&&i>0&&i+1<(int)rows.size()){
 vector<char>mask(ids.size(),0);for(auto e:eng.last_residual)mask[e.w]=1;
 for(int j=i+1;j<(int)rows.size();j++){int hits=0,fresh=0;for(auto[w,c]:rows[j].r){auto id=ids[w];if(eng.leads[id]>=0)continue;if(mask[id])hits++;else fresh++;}rows[j].overlap=hits;rows[j].fresh=fresh;}
 auto cmp=[](const Row&a,const Row&b){if((a.overlap==0)!=(b.overlap==0))return a.overlap!=0;if(!a.overlap)return a.sc<b.sc;return make_tuple(a.fresh,a.r.size(),-a.overlap,a.sc)<make_tuple(b.fresh,b.r.size(),-b.overlap,b.sc);};
 partial_sort(rows.begin()+i+1,rows.begin()+min((int)rows.size(),i+2501),rows.end(),cmp);
 cerr<<"ADAPT remaining_target="<<eng.last_residual.size()<<" next_hits="<<rows[i+1].overlap<<" next_fresh="<<rows[i+1].fresh<<" sec="<<sec()<<"\n";
 }}}
 if(!ok){cerr<<"UNSOLVED rank="<<eng.basis.size()<<" secs="<<sec()<<"\n";return 1;}
 ofstream labels(pref+".labels.txt"),cert(pref+".modcert.txt");cert<<P<<"\n";int count=0;for(auto[i,c]:sol)if(c){write_label(labels,rows[i].sc);labels<<"\n";cert<<c<<" ";write_label(cert,rows[i].sc);cert<<"\n";count++;}cerr<<"SOLVED rows="<<last+1<<" rank="<<eng.basis.size()<<" cert="<<count<<" seconds="<<sec()<<"\n";return 0;
}
