// Size probe for the C8(3) cost model (RECON section 6.3.4). NOT a payload generator: it writes no G-files and
// no rate tables. For every class of classesL.txt it rebuilds, with the exact logic of
//   LRI_C7_D2_HPC/reference/LRI_C7_d2_progress/code/build_schwinger.cpp   (free sector)
//   LRI_C7_D2_HPC/reference/power_mass/code/build_power_mass.cpp          (power sector)
// the spanning-tree masks and the forest terms of the d-independent kernel body, generalized to n<=9 vertices and
// 128-bit keys (2 bits per vertex pair, as LRI_C8_HPC/gen/build_coordinate_forests.cpp), and reports per class:
//   M (masks), T (terms), forests, max forest size, products and trie addends as counted by the kernel's prepare()
//   (the same counts as the C63d recon's opcount.py), log/power subgraph counts, s_G, status.
// Usage: size_probe classesL.txt [masks_L.txt] > sizes_L.csv      (light: L8 takes well under a minute with OpenMP)
// Repair round 3 (gate 5): with a second argument it also writes, per class and in the layout of LRI_C8_HPC's
// L*_inventory.txt, a header line "gi nlog npow forests_log", the log-subgraph vertex masks and the power-subgraph
// vertex masks, where forests_log counts the compatible families of log subgraphs alone (the d=1 "forests" count).
// The CSV on stdout is unchanged.
// S1-01 (A.2 step 0, A-INV-6): the masks output is refused (exit 2, nothing written) when it lies under C62d's trees
// (/expanse/lustre/scratch/zzheng8/temp_project/c8d2 and any .../LRI_C8_shared/inventory), lexically or after resolving
// existing symlinks (g3common.under_c62d, regenerate_rates.cpp's under_c62d): checked first and again just before
// the file is opened.
// R2-S1-01: a final-component symbolic link is followed through every hop (a dangling one too, its target taken against
// the link's directory) and each target checked as above; the output is then refused when it is a symbolic link at all,
// and opened with O_NOFOLLOW (O_CREAT|O_TRUNC), so no link is ever written through.
#include <bits/stdc++.h>
#include <filesystem>
#include <fcntl.h>
#include <unistd.h>
#include <omp.h>
using namespace std; using U=unsigned __int128; namespace fs=std::filesystem;
static string under_c62d(const string&p){
 auto check=[](const fs::path&q)->string{
  string s=q.generic_string();const string c8d2="/expanse/lustre/scratch/zzheng8/temp_project/c8d2";
  if(s==c8d2||s.rfind(c8d2+"/",0)==0)return c8d2;
  vector<string>parts;for(auto&x:q)parts.push_back(x.string());
  for(size_t i=0;i+1<parts.size();i++)if(parts[i]=="LRI_C8_shared"&&parts[i+1]=="inventory")return ".../LRI_C8_shared/inventory";
  return "";
 };
 error_code ec;fs::path a=fs::absolute(fs::path(p),ec);if(ec)return "";
 for(int hop=0;hop<40;hop++){   // R2-S1-01: the path, then each final-link target (weakly_canonical stops at a dangling one)
  string r=check(a.lexically_normal());if(!r.empty())return r;
  fs::path w=fs::weakly_canonical(a,ec);if(!ec){r=check(w);if(!r.empty())return r;}
  auto st=fs::symlink_status(a,ec);if(ec||!fs::is_symlink(st))break;
  fs::path l=fs::read_symlink(a,ec);if(ec)break;a=l.is_absolute()?l:a.parent_path()/l;
 }
 return "";
}
static int refused(const char*p){
 string r=under_c62d(p);if(!r.empty()){cerr<<p<<": masks output is under C62d's tree "<<r<<" (refused: nothing of this package writes there)\n";return 2;}
 error_code ec;if(fs::is_symlink(fs::symlink_status(p,ec))){cerr<<p<<": masks output is a symbolic link (refused: never written through, R2-S1-01)\n";return 2;}
 return 0;
}
static U readu128(istream&in){string s;if(!(in>>s)||s.empty())throw runtime_error("missing key");U x=0;for(char c:s){if(c<'0'||c>'9')throw runtime_error("bad key "+s);U y=x*10+U(c-'0');if((y-U(c-'0'))/10!=x)throw runtime_error("key overflow "+s);x=y;}return x;}
static int root(int*p,int a){while(p[a]!=a)a=p[a];return a;}
static bool join(int*p,int a,int b){a=root(p,a);b=root(p,b);if(a==b)return false;p[max(a,b)]=min(a,b);return true;}
static bool onepi(unsigned mask,const vector<pair<int,int>>&ed){unsigned low=mask&-mask;for(unsigned sub=(mask-1)&mask;sub;sub=(sub-1)&mask){if(sub&low)continue;int cross=0;for(auto[a,b]:ed)if((mask>>a&1)&&(mask>>b&1)&&((sub>>a&1)!=(sub>>b&1)))cross++;if(cross<2)return false;}return true;}
int main(int ac,char**av){
 if(ac<2){cerr<<"usage: size_probe classesL.txt [masks_L.txt]\n";return 2;}
 if(ac>2&&refused(av[2]))return 2;
 ifstream f(av[1]);int n,NG;f>>n>>NG;if(!f||n<2||n>9){cerr<<"bad classes file\n";return 2;}
 int L=n-1,E=2*L;unsigned ALL=(1u<<E)-1;vector<U>keys(NG);for(auto&k:keys){k=readu128(f);long long a,o;f>>a>>o;}
 if(!f){cerr<<"truncated\n";return 2;}
 vector<string>out(NG),mout(NG);
 #pragma omp parallel for schedule(dynamic,1)
 for(int gi=0;gi<NG;gi++){
  U key=keys[gi];vector<pair<int,int>>ed;int deg[9]={},ix=0;
  for(int a=0;a<n;a++)for(int b=a+1;b<n;b++,ix++){int m=int((key>>(2*ix))&3);for(int j=0;j<m;j++){ed.push_back({a,b});deg[a]++;deg[b]++;}}
  if((int)ed.size()!=E){fprintf(stderr,"edge count mismatch %d\n",gi);exit(3);}
  int ss=0;for(int a=0;a<n;a++)ss+=(4-deg[a])*(3-deg[a]);
  vector<unsigned>subs,powers;unsigned full=(1u<<n)-1;
  for(unsigned s=1;s<full;s++){int v=__builtin_popcount(s);if(v<2)continue;int e=0;for(auto[a,b]:ed)if((s>>a&1)&&(s>>b&1))e++;if(e<2*(v-1)||!onepi(s,ed))continue;(e==2*(v-1)?subs:powers).push_back(s);}
  bool power=!powers.empty();size_t nlog=subs.size(),npow=powers.size();
  {ostringstream ms;ms<<gi<<' '<<nlog<<' '<<npow<<' ';
   // forests of log subgraphs alone, with the builders' compatibility rule (nested or at most one common vertex)
   function<long(vector<int>)>cnt=[&](vector<int>cand)->long{long c=1;for(size_t k=0;k<cand.size();k++){unsigned a=subs[cand[k]];vector<int>nn;for(size_t h=k+1;h<cand.size();h++){unsigned b=subs[cand[h]];if(((a&b)==a)||((a&b)==b)||(__builtin_popcount(a&b)<=1))nn.push_back(cand[h]);}c+=cnt(nn);}return c;};
   vector<int>lall(nlog);iota(lall.begin(),lall.end(),0);ms<<cnt(lall)<<'\n';
   for(auto x:subs)ms<<x<<' ';ms<<'\n';for(auto x:powers)ms<<x<<' ';ms<<'\n';mout[gi]=ms.str();}
  if(power)subs.insert(subs.end(),powers.begin(),powers.end());
  // spanning-tree complement masks (Gosper enumeration of L-subsets, as in the builders)
  vector<unsigned>masks;
  for(unsigned tr=(1u<<L)-1;tr<=ALL;){int p[9];iota(p,p+9,0);bool ok=true;unsigned bits=tr;while(bits){int e=__builtin_ctz(bits);bits&=bits-1;if(!join(p,ed[e].first,ed[e].second)){ok=false;break;}}if(ok)masks.push_back(ALL^tr);unsigned v=tr&-tr,w=tr+v;if(w>ALL)break;tr=w+(((w^tr)/v)>>2);}
  sort(masks.begin(),masks.end());
  size_t ns=subs.size();vector<vector<bool>>comp(ns,vector<bool>(ns));vector<unsigned>ems;vector<int>hs;
  for(size_t i=0;i<ns;i++){unsigned s=subs[i],em=0;for(int k=0;k<E;k++)if((s>>ed[k].first&1)&&(s>>ed[k].second&1))em|=1u<<k;ems.push_back(em);
   // each builder's own formula: free h = |V(s)|-1; power h = |E(s)|-|V(s)|+1 (equal for log subgraphs, e = 2(v-1))
   hs.push_back(power?(__builtin_popcount(em)-__builtin_popcount(s)+1):(__builtin_popcount(s)-1));}
  for(size_t i=0;i<ns;i++)for(size_t j=0;j<ns;j++){auto a=subs[i],b=subs[j];comp[i][j]=((a&b)==a)||((a&b)==b)||(__builtin_popcount(a&b)<=1);}
  map<vector<int>,vector<int>>terms;vector<int>sel;long nf=0;int fmax=0;
  auto emit=[&](){nf++;fmax=max(fmax,(int)sel.size());vector<int>basis;for(size_t k=0;k<masks.size();k++){bool ok=true;for(int j:sel)if(__builtin_popcount(masks[k]&ems[j])!=hs[j]){ok=false;break;}if(ok)basis.push_back((int)k);}
   if(basis.empty()){fprintf(stderr,"empty forest basis %d\n",gi);exit(4);}
   unsigned rootedges=ALL;for(int j:sel)if(!power||size_t(j)<nlog)rootedges&=~ems[j];auto&co=terms[basis];if(co.empty())co.resize(E);int sign=sel.size()%2?-1:1;for(int j=0;j<E;j++)if(rootedges>>j&1)co[j]+=sign;};
  function<void(vector<int>)>rec=[&](vector<int>cand){emit();for(size_t k=0;k<cand.size();k++){int j=cand[k];sel.push_back(j);vector<int>nn;for(size_t h=k+1;h<cand.size();h++)if(comp[j][cand[h]])nn.push_back(cand[h]);rec(nn);sel.pop_back();}};
  vector<int>all(ns);iota(all.begin(),all.end(),0);rec(all);
  for(auto it=terms.begin();it!=terms.end();){bool nz=any_of(it->second.begin(),it->second.end(),[](int v){return v;});if(!nz)it=terms.erase(it);else ++it;}
  // prepare() counts: products = union of lowest-bit peeling chains; addends = trie nodes over the ordered bases
  unordered_set<unsigned>prods;for(unsigned m:masks){unsigned x=m;while(x&&!prods.count(x)){prods.insert(x);x&=x-1;}}
  unordered_map<uint64_t,int>trie;long addends=0,uncompressed=0;
  for(auto&[basis,co]:terms){uint64_t at=0;for(int k:basis){uint64_t kk=(at<<16)|uint64_t(k);auto itn=trie.find(kk);if(itn==trie.end()){trie.emplace(kk,++addends);at=addends;}else at=itn->second;}uncompressed+=basis.size();}
  const char*status=terms.empty()?"zero":(power?"power":"free");
  char buf[256];snprintf(buf,sizeof buf,"%d,%d,%s,%d,%d,%zu,%zu,%zu,%zu,%ld,%d,%zu,%ld,%ld\n",L,gi,status,ss,(nlog==0&&npow==0)?1:0,nlog,npow,masks.size(),terms.size(),nf,fmax,prods.size(),addends,uncompressed);
  out[gi]=buf;
 }
 printf("L,id,status,sG,primitive,nlog,npow,M,T,forests,fmax,products,addends,uncompressed\n");
 for(auto&s:out)fputs(s.c_str(),stdout);
 if(ac>2){if(refused(av[2]))return 2;
  int fd=::open(av[2],O_WRONLY|O_CREAT|O_TRUNC|O_NOFOLLOW|O_CLOEXEC,0666);   // R2-S1-01: a link swapped in since is not followed
  if(fd<0){int e=errno;cerr<<av[2]<<": cannot open the masks output ("<<strerror(e)<<(e==ELOOP?"; a symbolic link is never followed":"")<<")\n";return e==ELOOP?2:1;}
  FILE*mf=fdopen(fd,"w");if(!mf){::close(fd);cerr<<"cannot write masks\n";return 1;}
  bool good=fprintf(mf,"%d %d\n",n,NG)>0;for(auto&s:mout)good=good&&fputs(s.c_str(),mf)>=0;
  if(fclose(mf)!=0||!good){cerr<<"cannot write masks\n";return 1;}}
}
