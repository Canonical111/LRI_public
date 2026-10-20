#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>
#include <omp.h>
using namespace std;
struct Job {int L,id,den,s,aut;vector<pair<int,int>> edges;};
struct Sub {unsigned vm,em;int h;bool power;};
struct Result {int logs=0,powers=0,monomials=0,terms=0;long long forests=0;bool zerochannel=false;string sector,file;long clamped=0;int minrate=1000;};
struct DSU {int p[9];DSU(){iota(p,p+9,0);}int f(int a){return p[a]==a?a:p[a]=f(p[a]);}bool join(int a,int b){a=f(a);b=f(b);if(a==b)return false;p[a]=b;return true;}};
bool onepi(const array<array<int,9>,9>&a,int n,unsigned vm){
 array<int,9>disc{},low{};int timer=0;bool bridge=false;
 function<void(int,int)>dfs=[&](int v,int parent){disc[v]=low[v]=++timer;for(int w=0;w<n;w++)if((vm>>w&1)&&a[v][w]){if(!disc[w]){dfs(w,v);low[v]=min(low[v],low[w]);if(low[w]>disc[v]&&a[v][w]==1)bridge=true;}else if(w!=parent||a[v][w]>1)low[v]=min(low[v],disc[w]);}};
 dfs(__builtin_ctz(vm),-1);return timer==__builtin_popcount(vm)&&!bridge;
}
Result build(const Job&g,const string&root,bool rates,bool topzero,bool all_edge){
 Result r;int n=g.L+1,E=2*g.L,ALL=(1<<E)-1;array<array<int,9>,9>a{};for(auto[u,v]:g.edges){a[u][v]++;a[v][u]++;}
 vector<unsigned>masks;for(int m=0;m<=ALL;m++)if(__builtin_popcount((unsigned)m)==g.L){DSU d;bool good=true;unsigned t=ALL^m;while(t){int i=__builtin_ctz(t);t&=t-1;if(!d.join(g.edges[i].first,g.edges[i].second)){good=false;break;}}if(good)masks.push_back(m);}
 r.monomials=masks.size();vector<Sub>subs;
 if(!all_edge){
  for(unsigned vm=1;vm<(1u<<n)-1;vm++){int v=__builtin_popcount(vm);if(v<2)continue;unsigned em=0;for(int k=0;k<E;k++)if((vm>>g.edges[k].first&1)&&(vm>>g.edges[k].second&1))em|=1u<<k;int e=__builtin_popcount(em);if(e!=2*v-2&&e!=2*v-1)continue;if(!onepi(a,n,vm))continue;bool p=e==2*v-1;subs.push_back({vm,em,e-v+1,p});if(p)r.powers++;else r.logs++;}
 }else{
  vector<unsigned>vs(ALL+1);for(unsigned em=1;em<(unsigned)ALL;em++){int k=__builtin_ctz(em);vs[em]=vs[em&(em-1)]|(1u<<g.edges[k].first)|(1u<<g.edges[k].second);unsigned vm=vs[em];int v=__builtin_popcount(vm),e=__builtin_popcount(em);if(e!=2*v-2&&e!=2*v-1)continue;array<array<int,9>,9>b{};for(int j=0;j<E;j++)if(em>>j&1){auto[u,w]=g.edges[j];b[u][w]++;b[w][u]++;}if(!onepi(b,n,vm))continue;bool p=e==2*v-1;subs.push_back({vm,em,e-v+1,p});if(p)r.powers++;else r.logs++;}
 }
 int H=subs.size();if(H>63)throw runtime_error("too many divergent subgraphs");vector<uint64_t>compat(H,0);
 for(int i=0;i<H;i++)for(int j=i+1;j<H;j++){auto&x=subs[i];auto&y=subs[j];if((x.em&y.em)==x.em||(x.em&y.em)==y.em||(!(x.em&y.em)&&__builtin_popcount(x.vm&y.vm)<=1))compat[i]|=1ull<<j;}
 vector<vector<char>>keep(H,vector<char>(masks.size()));for(int j=0;j<H;j++)for(int k=0;k<(int)masks.size();k++)keep[j][k]=__builtin_popcount(masks[k]&subs[j].em)==subs[j].h;
 map<vector<int>,array<int,16>>terms;
 function<void(uint64_t,const vector<int>&,unsigned,int)>forest=[&](uint64_t candidates,const vector<int>&basis,unsigned removed,int sign){
  r.forests++;auto[it,added]=terms.try_emplace(basis,array<int,16>{});for(int e=0;e<E;e++)if(!(removed>>e&1))it->second[e]+=sign;
  while(candidates){int j=__builtin_ctzll(candidates);candidates&=candidates-1;vector<int>b;b.reserve(basis.size());for(int k:basis)if(keep[j][k])b.push_back(k);if(b.empty())throw runtime_error("empty forest denominator");forest(candidates&compat[j],b,removed|(subs[j].power?0:subs[j].em),-sign);}
 };
 vector<int>basis(masks.size());iota(basis.begin(),basis.end(),0);forest(H==64?~0ull:((1ull<<H)-1),basis,0,1);
 for(auto it=terms.begin();it!=terms.end();){bool nonzero=false;for(int e=0;e<E;e++)nonzero|=it->second[e]!=0;if(!nonzero)it=terms.erase(it);else ++it;}
 r.terms=terms.size();r.zerochannel=g.s==4;r.sector=r.powers?"power":"free";
 if(terms.empty()||(topzero&&r.zerochannel))return r;
 r.file=r.sector+"/L"+to_string(g.L)+"/G"+to_string(g.id)+".txt";filesystem::create_directories(filesystem::path(root)/r.sector/("L"+to_string(g.L)));ofstream out(filesystem::path(root)/r.file);out<<setprecision(22)<<"C8D3GRAPH1 "<<g.L<<' '<<g.id<<' '<<24.L/g.den<<' '<<2.L*g.s/g.den<<' '<<masks.size()<<' '<<terms.size()<<'\n';for(auto m:masks)out<<m<<' ';out<<'\n';
 for(auto&[b,co]:terms){out<<b.size();for(int k:b)out<<' '<<k;for(int e=0;e<E;e++)out<<' '<<co[e];out<<'\n';}
 if(rates){vector<int8_t>positive(ALL+1,100),raw(ALL+1,100),pc(ALL+1);for(int s=0;s<=ALL;s++)pc[s]=__builtin_popcount((unsigned)s);
  for(auto&[b,co]:terms){vector<int8_t>dist(ALL+1,100);for(int k:b)dist[masks[k]]=0;
   for(int bit=1;bit<=ALL;bit<<=1)for(int base=0;base<=ALL;base+=2*bit)for(int j=0;j<bit;j++){int s=base+j,t=s+bit,x=dist[s],y=dist[t];dist[s]=min(x,y+1);dist[t]=min(y,x+1);}
   unsigned supp=0;for(int e=0;e<E;e++)if(co[e])supp|=1u<<e;
   for(int s=1;s<ALL;s++){int h=(g.L-E+pc[s]+int(dist[ALL^s]))/2;int nuN=(supp&~s)?0:1;int p4=3*pc[s]+4*nuN-6*h;raw[s]=min(int(raw[s]),p4);if(p4<=0){p4=(p4%4+4)%4;if(!p4)p4=4;}positive[s]=min(int(positive[s]),p4);}
  }
  out<<ALL+1<<'\n';for(int s=0;s<=ALL;s++){if(s&&s<ALL){r.clamped+=raw[s]<=0;r.minrate=min(r.minrate,int(positive[s]));out<<int(positive[s])*.25L<<' ';}else out<<"0 ";}out<<'\n';
 }
 return r;
}
int main(int argc,char**argv){if(argc<3){cerr<<"usage build_forests jobs.txt output_directory [--rates] [--topzero] [--all-edge] [--threads N]\n";return 2;}string jobfile=argv[1],root=argv[2];bool rates=false,topzero=false,all_edge=false;int threads=8;for(int i=3;i<argc;i++){string a=argv[i];if(a=="--rates")rates=true;else if(a=="--topzero")topzero=true;else if(a=="--all-edge")all_edge=true;else if(a=="--threads")threads=stoi(argv[++i]);else throw runtime_error("unknown option");}
 ifstream f(jobfile);vector<Job>jobs;Job g;while(f>>g.L>>g.id>>g.den>>g.s>>g.aut){g.edges.resize(2*g.L);for(auto&[u,v]:g.edges)f>>u>>v;jobs.push_back(g);}vector<Result>results(jobs.size());atomic<int>done=0;auto start=chrono::steady_clock::now();filesystem::create_directories(root);
#pragma omp parallel for num_threads(threads) schedule(dynamic,1)
 for(size_t k=0;k<jobs.size();k++){results[k]=build(jobs[k],root,rates,topzero,all_edge);int d=++done;if(d%1000==0){
#pragma omp critical
 cerr<<d<<"/"<<jobs.size()<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<" s\n";
 }}
 ofstream inv(filesystem::path(root)/"complete_inventory.json");inv<<"[\n";long long terms=0,forests=0;int power=0,primitive=0,zeros=0,active=0,zerochannel=0;
 for(size_t k=0;k<jobs.size();k++){auto&g=jobs[k];auto&r=results[k];terms+=r.terms;forests+=r.forests;power+=r.powers>0;primitive+=!(r.logs+r.powers);zeros+=r.terms==0;active+=!r.file.empty();zerochannel+=r.zerochannel;
 if(k)inv<<",\n";inv<<"{\"id\":"<<g.id<<",\"L\":"<<g.L<<",\"denominator\":"<<g.den<<",\"mass_numerator\":"<<g.s<<",\"automorphisms\":"<<g.aut<<",\"sector\":\""<<r.sector<<"\",\"primitive\":"<<(r.logs+r.powers?"false":"true")<<",\"log_subgraphs\":"<<r.logs<<",\"power_subgraphs\":"<<r.powers<<",\"masks\":"<<r.monomials<<",\"forests\":"<<r.forests<<",\"terms\":"<<r.terms<<",\"zero_top_channel\":"<<(r.zerochannel?"true":"false")<<",\"file\":\""<<r.file<<"\",\"rate_clamped_subsets\":"<<r.clamped<<",\"minimum_rate_quarters\":"<<r.minrate<<",\"edges\":[";for(size_t j=0;j<g.edges.size();j++){if(j)inv<<',';inv<<'['<<g.edges[j].first<<','<<g.edges[j].second<<']';}inv<<"]}";}
 inv<<"\n]\n";cerr<<"all "<<jobs.size()<<" power "<<power<<" primitive "<<primitive<<" zeros "<<zeros<<" zerochannel "<<zerochannel<<" active "<<active<<" terms "<<terms<<" forests "<<forests<<" seconds "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"\n";
}
