// Construct finite logarithmic-forest kernels from retained canonical classes.
// No dimensional or statistical interpolation. Integer graph/forest operations.
#include <bits/stdc++.h>
#include <omp.h>
#include <filesystem>
#include "c8gen.hpp"
using namespace std;using U=Key;using LD=long double;
int root(int*p,int a){while(p[a]!=a)a=p[a];return a;}
bool join(int*p,int a,int b){a=root(p,a);b=root(p,b);if(a==b)return false;p[max(a,b)]=min(a,b);return true;}
bool onepi(unsigned mask,const vector<pair<int,int>>&ed){unsigned low=mask&-mask;for(unsigned sub=(mask-1)&mask;sub;sub=(sub-1)&mask){if(sub&low)continue;int cross=0;for(auto[a,b]:ed)if((mask>>a&1)&&(mask>>b&1)&&((sub>>a&1)!=(sub>>b&1)))cross++;if(cross<2)return false;}return true;}
struct Rec{U key;long long aut,orbit;};
int main(int ac,char**av){if(ac<3)return 1;ClassFile cf;try{cf=read_generator_classes(av[1]);}catch(const InputError&e){cerr<<e.what()<<'\n';return 2;}int n=cf.n,NG=cf.NG;int L=n-1,E=2*L,NE=n*(n-1)/2,ALL=(1<<E)-1;vector<Rec> recs(NG);for(int i=0;i<NG;i++)recs[i]={cf.rows[i].key,cf.rows[i].aut,cf.rows[i].orbit};filesystem::create_directories(av[2]);vector<string>meta(NG),subl(NG);double st=omp_get_wtime();
#pragma omp parallel for schedule(dynamic,1)
for(int gi=0;gi<NG;gi++){auto row=recs[gi];vector<pair<int,int>>ed;int deg[NV]={},ix=0;long long den=row.aut;int fact[]={1,1,2,6,24};for(int a=0;a<n;a++)for(int b=a+1;b<n;b++,ix++){int m=(row.key>>(2*ix))&3;den*=fact[m];for(int j=0;j<m;j++){ed.push_back({a,b});deg[a]++;deg[b]++;}}
int ss=0;for(int a=0;a<n;a++){den*=fact[4-deg[a]];ss+=(4-deg[a])*(3-deg[a]);}LD wa=24.L/den,wb=wa*ss/12.L;vector<unsigned>subs,powers;unsigned full=(1<<n)-1;for(unsigned s=1;s<full;s++){int v=__builtin_popcount(s);if(v<2)continue;int e=0;for(auto[a,b]:ed)if((s>>a&1)&&(s>>b&1))e++;if(e<2*(v-1)||!onepi(s,ed))continue;(e==2*(v-1)?subs:powers).push_back(s);}if(ac>3){ostringstream q;q<<gi<<' '<<u128s(row.key)<<' '<<row.aut<<' '<<row.orbit<<' '<<den<<' '<<ss<<' '<<subs.size()<<' '<<powers.size()<<'\n';for(auto s:subs)q<<s<<' ';q<<'\n';for(auto s:powers)q<<s<<' ';q<<'\n';subl[gi]=q.str();}
ostringstream mm;mm<<setprecision(22)<<"{\"id\":"<<gi<<",\"L\":"<<L<<",\"key\":"<<u128s(row.key)<<",\"denominator\":"<<den<<",\"mass_numerator\":"<<ss<<",\"orbit\":"<<row.orbit<<",\"wa\":"<<wa<<",\"wb\":"<<wb<<",\"power_subgraphs\":"<<powers.size()<<",\"log_subgraphs\":"<<subs.size()<<",\"primitive\":"<<((subs.empty()&&powers.empty())?"true":"false");
// Retain even zero channel weight: mass and coupling jets separately needed below 7.
if(!powers.empty()){mm<<",\"status\":\"power-sector-not-integrated\"}";meta[gi]=mm.str();continue;}
vector<unsigned>masks;for(unsigned tr=(1u<<L)-1;tr<=unsigned(ALL);){int p[NV];iota(p,p+NV,0);bool ok=true;unsigned bits=tr;while(bits){int e=__builtin_ctz(bits);bits&=bits-1;if(!join(p,ed[e].first,ed[e].second)){ok=false;break;}}if(ok)masks.push_back(ALL^tr);unsigned v=tr&-tr,w=tr+v;if(w>unsigned(ALL))break;tr=w+(((w^tr)/v)>>2);}
sort(masks.begin(),masks.end());vector<vector<bool>>comp(subs.size(),vector<bool>(subs.size()));vector<unsigned>ems;vector<int>hs;for(auto s:subs){unsigned em=0;for(int i=0;i<E;i++)if((s>>ed[i].first&1)&&(s>>ed[i].second&1))em|=1<<i;ems.push_back(em);hs.push_back(__builtin_popcount(s)-1);}for(size_t i=0;i<subs.size();i++)for(size_t j=0;j<subs.size();j++){auto a=subs[i],b=subs[j];comp[i][j]=((a&b)==a)||((a&b)==b)||(__builtin_popcount(a&b)<=1);}
map<vector<int>,vector<int>> terms;vector<int>sel;long nf=0;auto emit=[&](){nf++;vector<int>basis;for(size_t k=0;k<masks.size();k++){bool ok=true;for(int j:sel)if(__builtin_popcount(masks[k]&ems[j])!=hs[j]){ok=false;break;}if(ok)basis.push_back(k);}if(basis.empty())throw runtime_error("empty forest basis");unsigned rootedges=ALL;for(int j:sel)rootedges&=~ems[j];auto&co=terms[basis];if(co.empty())co.resize(E);int sign=sel.size()%2?-1:1;for(int j=0;j<E;j++)if(rootedges>>j&1)co[j]+=sign;};
function<void(vector<int>)>recurse=[&](vector<int>cand){emit();for(size_t k=0;k<cand.size();k++){int j=cand[k];sel.push_back(j);vector<int>nn;for(size_t h=k+1;h<cand.size();h++)if(comp[j][cand[h]])nn.push_back(cand[h]);recurse(nn);sel.pop_back();}};vector<int>all(subs.size());iota(all.begin(),all.end(),0);recurse(all);
for(auto i=terms.begin();i!=terms.end();){bool nz=any_of(i->second.begin(),i->second.end(),[](int v){return v;});if(!nz)i=terms.erase(i);else ++i;}mm<<",\"masks\":"<<masks.size()<<",\"forests\":"<<nf<<",\"terms\":"<<terms.size();if(terms.empty()){mm<<",\"status\":\"exact-zero-kernel\"}";meta[gi]=mm.str();continue;}
// A conservative forest-aware valuation: p >= min_F(|S|/2 + nu(N_F)-nu(U_F)).
// After logarithmic subtraction analytic rational kernels have at least half-unit
// positive exponent. Nonpositive lower bounds are NOT certified here: tracked.
vector<int> twice(ALL+1,100);long clamped=0;for(const auto&[basis,co]:terms){vector<int8_t>dist(ALL+1,100);for(int k:basis)dist[masks[k]]=0;for(int b=0;b<E;b++){int bit=1<<b;for(int s=0;s<=ALL;s++)if(!(s&bit)){int t=s|bit;int a=dist[s],c=dist[t];dist[s]=min(a,c+1);dist[t]=min(c,a+1);}}unsigned supp=0;for(int i=0;i<E;i++)if(co[i])supp|=1<<i;for(int s=1;s<ALL;s++){int pc=__builtin_popcount(unsigned(s));int h=(L-E+pc+int(dist[ALL^s]))/2;int a=(supp&~s)?0:1;twice[s]=min(twice[s],pc+2*a-2*h);}}
for(int s=1;s<ALL;s++)if(twice[s]<=0)clamped++;
string path=string(av[2])+"/G"+to_string(gi)+".txt";ofstream out(path);out<<setprecision(22)<<"C7D2GRAPH1 "<<L<<' '<<gi<<' '<<wa<<' '<<wb<<' '<<masks.size()<<' '<<terms.size()<<'\n';for(auto m:masks)out<<m<<' ';out<<'\n';for(auto&[basis,co]:terms){out<<basis.size();for(auto k:basis)out<<' '<<k;for(auto c:co)out<<' '<<c;out<<'\n';}out<<ALL+1<<'\n';for(int s=0;s<=ALL;s++){if(s)out<<' ';out<<(s&&s<ALL?max((__builtin_popcount(unsigned(s))%2?1:2),twice[s])*.5L:0);}out<<'\n';mm<<",\"rate_clamped_subsets\":"<<clamped<<",\"status\":\"finite-kernel\",\"file\":\"L"<<L<<"/G"<<gi<<".txt\",\"edges\":[";for(int i=0;i<E;i++){if(i)mm<<',';mm<<'['<<ed[i].first<<','<<ed[i].second<<']';}mm<<"]}";meta[gi]=mm.str();if(gi%100==0){
#pragma omp critical
cerr<<"L "<<L<<" graph "<<gi<<" terms "<<terms.size()<<" sec "<<omp_get_wtime()-st<<'\n';}
}
ofstream mo(string(av[2])+"/inventory.json");mo<<"[";for(int i=0;i<NG;i++){if(i)mo<<',';mo<<meta[i];}mo<<"]\n";if(ac>3){ofstream so(av[3]);so<<n<<' '<<NG<<'\n';for(auto&s:subl)so<<s;}cerr<<"FINISHED L "<<L<<" sec "<<omp_get_wtime()-st<<'\n';}
