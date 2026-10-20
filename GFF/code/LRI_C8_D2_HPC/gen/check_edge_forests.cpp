#include <bits/stdc++.h>
#include <omp.h>
#include "c8gen.hpp"
using namespace std;using U=Key;
int root(int*p,int a){while(p[a]!=a)a=p[a];return a;}
bool join(int*p,int a,int b){a=root(p,a);b=root(p,b);if(a==b)return false;p[max(a,b)]=min(a,b);return true;}
struct Sub{unsigned vs,es;int h;bool log;};
bool onepi(unsigned s,const vector<pair<int,int>>&ed,unsigned vs){vector<pair<int,int>>adj[NV];for(int i=0;i<int(ed.size());i++)if(s>>i&1){auto[a,b]=ed[i];adj[a].push_back({b,i});adj[b].push_back({a,i});}int seen[NV]={},low[NV]={},timer=0;bool bridge=false;function<void(int,int)> dfs=[&](int v,int pe){seen[v]=low[v]=++timer;for(auto[w,e]:adj[v])if(e!=pe){if(seen[w])low[v]=min(low[v],seen[w]);else{dfs(w,e);low[v]=min(low[v],low[w]);if(low[w]>seen[v])bridge=true;}}};dfs(__builtin_ctz(vs),-1);for(int v=0;v<NV;v++)if((vs>>v&1)&&!seen[v])return false;return !bridge;}
// W6 (S6R4-B-03, Stage-6 fix round 4): the existing G-file of a power class is read with every extraction checked
// before its value is used, and every allocation bounded by the native loader's header limits (src/kernel.hpp
// load_graph: 1 <= M <= 16384 masks, 1 <= T <= 10000 terms, a denominator of 1 <= k <= M masks; the magic, L and id
// those of the class). A malformed file (cut after its magic, before a term's k, a hostile count) is that graph's
// failure (matches_induced false, with an "error"), and so is any exception of one graph's check: nothing is thrown
// out of the OpenMP region, nothing is read uninitialized and nothing is allocated from an unchecked count.
constexpr int GF_MAXMASKS=16384,GF_MAXTERMS=10000;
struct OldFile{bool present=false;string error;vector<unsigned>masks;map<vector<int>,vector<int>>terms;};
static OldFile read_old(const string&path,int L,int id,int E){
    OldFile o;ifstream f(path);if(!f)return o;o.present=true;
    string magic;int ll=0,gid=0,M=0,T=0;long double wa=0,wb=0;
    if(!(f>>magic>>ll>>gid>>wa>>wb>>M>>T)){o.error="truncated or malformed header";return o;}
    if(magic!="C7D2GRAPH1"||ll!=L||gid!=id){o.error="header magic, L or id is not the class's";return o;}
    if(M<1||M>GF_MAXMASKS||T<1||T>GF_MAXTERMS){o.error="header counts M="+to_string(M)+", T="+to_string(T)+" outside the loader's bounds";return o;}
    o.masks.resize(M);
    for(auto&m:o.masks)if(!(f>>m)){o.error="truncated or malformed mask line";return o;}
    for(int t=0;t<T;t++){
        int k=0;if(!(f>>k)){o.error="truncated or malformed term "+to_string(t)+" (its denominator size)";return o;}
        if(k<1||k>M){o.error="term "+to_string(t)+": denominator size "+to_string(k)+" outside [1, M]";return o;}
        vector<int>b(k),c(E);
        for(int&x:b)if(!(f>>x)){o.error="truncated or malformed term "+to_string(t);return o;}
        for(int&x:c)if(!(f>>x)){o.error="truncated or malformed term "+to_string(t);return o;}
        o.terms[b]=c;}
    return o;}
static string json_text(const string&s){string o;for(char ch:s){unsigned char c=ch;if(c=='"'||c=='\\'){o+='\\';o+=ch;}else if(c<0x20||c>=0x7f)o+='?';else o+=ch;}return o;}
int main(int ac,char**av){if(ac!=4)return 2;ClassFile cf;try{cf=read_generator_classes(av[1]);}catch(const InputError&e){cerr<<e.what()<<'\n';return 2;}int n=cf.n,NG=cf.NG;int L=n-1,E=2*L,ALL=(1<<E)-1;struct Rec{U k;long long a,o;};vector<Rec>r(NG);for(int i=0;i<NG;i++)r[i]={cf.rows[i].key,cf.rows[i].aut,cf.rows[i].orbit};vector<string>out(NG);atomic<int>done(0),fail(0);double start=omp_get_wtime();
#pragma omp parallel for schedule(dynamic,1)
for(int gi=0;gi<NG;gi++){try{
vector<pair<int,int>>ed;int ix=0;for(int a=0;a<n;a++)for(int b=a+1;b<n;b++,ix++)for(int j=0;j<int((r[gi].k>>(2*ix))&3);j++)ed.push_back({a,b});vector<Sub>subs;int powers=0;for(unsigned s=1;s<unsigned(ALL);s++){int e=__builtin_popcount(s);if(e<2)continue;unsigned vs=0;for(unsigned q=s;q;q&=q-1){int i=__builtin_ctz(q);vs|=(1<<ed[i].first)|(1<<ed[i].second);}int v=__builtin_popcount(vs);if(e<2*(v-1))continue;if(!onepi(s,ed,vs))continue;subs.push_back({vs,s,e-v+1,e==2*(v-1)});powers+=(e>2*(v-1));}if(!powers)continue;
vector<unsigned>masks;for(unsigned t=(1u<<L)-1;t<=unsigned(ALL);){int p[NV];iota(p,p+NV,0);bool ok=true;for(unsigned q=t;q;q&=q-1){auto[a,b]=ed[__builtin_ctz(q)];if(!join(p,a,b)){ok=false;break;}}if(ok)masks.push_back(ALL^t);unsigned v=t&-t,w=t+v;if(w>unsigned(ALL))break;t=w+(((w^t)/v)>>2);}sort(masks.begin(),masks.end());
vector<vector<bool>>co(subs.size(),vector<bool>(subs.size()));for(size_t i=0;i<subs.size();i++)for(size_t j=0;j<subs.size();j++){auto a=subs[i],b=subs[j];co[i][j]=((a.es&b.es)==a.es)||((a.es&b.es)==b.es)||(__builtin_popcount(a.vs&b.vs)<=1);}
map<vector<int>,vector<int>>terms;vector<int>sel;long long nf=0;function<void(vector<int>)>emit=[&](vector<int>cand){nf++;vector<int>basis;for(size_t k=0;k<masks.size();k++){bool good=true;for(int j:sel)if(__builtin_popcount(masks[k]&subs[j].es)!=subs[j].h){good=false;break;}if(good)basis.push_back(k);}if(basis.empty())throw runtime_error("empty basis");unsigned rt=ALL;for(int j:sel)if(subs[j].log)rt&=~subs[j].es;auto&v=terms[basis];if(v.empty())v.resize(E);for(int i=0;i<E;i++)if(rt>>i&1)v[i]+=(sel.size()%2?-1:1);for(size_t k=0;k<cand.size();k++){int j=cand[k];sel.push_back(j);vector<int>nn;for(size_t p=k+1;p<cand.size();p++)if(co[j][cand[p]])nn.push_back(cand[p]);emit(nn);sel.pop_back();}};vector<int>cs(subs.size());iota(cs.begin(),cs.end(),0);emit(cs);for(auto it=terms.begin();it!=terms.end();)if(!any_of(it->second.begin(),it->second.end(),[](int v){return v;}))it=terms.erase(it);else ++it;
string path=string(av[2])+"/G"+to_string(gi)+".txt";OldFile old=read_old(path,L,gi,E);bool same;
if(!old.present)same=terms.empty();else if(!old.error.empty())same=false;else same=old.masks==masks&&old.terms==terms;
ostringstream s;s<<"{\"id\":"<<gi<<",\"subgraphs\":"<<subs.size()<<",\"forests\":"<<nf<<",\"terms\":"<<terms.size()<<",\"matches_induced\":"<<(same?"true":"false");
if(!old.error.empty())s<<",\"error\":\""<<json_text(old.error)<<"\"";s<<"}";out[gi]=s.str();if(!same)fail++;done++;
}catch(const std::exception&e){out[gi]="{\"id\":"+to_string(gi)+",\"matches_induced\":false,\"error\":\""+json_text(e.what())+"\"}";fail++;done++;}
catch(...){out[gi]="{\"id\":"+to_string(gi)+",\"matches_induced\":false,\"error\":\"unknown exception\"}";fail++;done++;}}
ofstream o(av[3]);o<<"{\"L\":"<<L<<",\"graphs\":"<<done<<",\"failures\":"<<fail<<",\"seconds\":"<<omp_get_wtime()-start<<",\"rows\":[";bool first=true;for(auto&s:out)if(!s.empty()){if(!first)o<<',';first=false;o<<s;}o<<"]}\n";cerr<<"L "<<L<<" done "<<done<<" fail "<<fail<<" time "<<omp_get_wtime()-start<<'\n';return fail?1:0;}
