// Generalization of reference/code/build_coordinate_forests.cpp from n<=8 to n<=9 vertices (L<=8).
// Same forest enumeration, ordering and output formats (inventory, coord, summary json with
// setprecision(22)/(20) long double). Class keys and quotient keys (2 bits per vertex pair, 36 pairs
// for n=9) are unsigned __int128 read/written in decimal, arrays are sized for 9 vertices / 36 pairs,
// so for n<=8 the output is byte-identical to the reference (except the timing field "seconds").
// Usage: build_coordinate_forests <classesL.txt> <output prefix>
#include <bits/stdc++.h>
using namespace std; using U=unsigned __int128; using LD=long double;
static string u128s(U x){if(!x)return "0";char b[48];int p=47;b[p]=0;while(x){b[--p]=char('0'+int(x%10));x/=10;}return string(b+p);}
static U readu128(istream&in){string s;if(!(in>>s)||s.empty())throw runtime_error("missing key");U x=0;for(char c:s){if(c<'0'||c>'9')throw runtime_error("bad key "+s);U y=x*10+U(c-'0');if((y-U(c-'0'))/10!=x)throw runtime_error("key overflow "+s);x=y;}return x;}
const int NV=9,NP=36;
int n,L,E,NE; vector<pair<int,int>> pairs; int ix[NV][NV];
int root(int *p,int a){while(p[a]!=a)a=p[a];return a;}
void unite(int*p,int a,int b){a=root(p,a);b=root(p,b);if(a!=b)p[max(a,b)]=min(a,b);}
bool onepi(unsigned mask,const vector<pair<int,int>>&ed){
 if(__builtin_popcount(mask)<2)return false;
 unsigned low=mask&-mask;
 for(unsigned sub=(mask-1)&mask;sub;sub=(sub-1)&mask){if(sub&low)continue;int cross=0;for(auto[a,b]:ed)if((mask>>a&1)&&(mask>>b&1)&&((sub>>a&1)!=(sub>>b&1)))cross++;if(cross<2)return false;}
 return true;
}
struct R {U key;int aut,orbit;};
int main(int argc,char**argv){
 if(argc<3){cerr<<"usage: build_coordinate_forests classesL.txt prefix\n";return 2;}
 ifstream in(argv[1]);int NG;in>>n>>NG; if(!in||n<1||n>NV){cerr<<"bad classes file\n";return 2;} L=n-1; E=2*L;
 for(int a=0;a<n;a++)for(int b=a+1;b<n;b++){ix[a][b]=ix[b][a]=pairs.size();pairs.push_back({a,b});}NE=pairs.size();
 vector<R>rows(NG);for(auto&r:rows){r.key=readu128(in);in>>r.aut>>r.orbit;}if(!in){cerr<<"truncated classes file\n";return 2;}
 string pre=argv[2];ofstream inv(pre+"_inventory.txt"),out(pre+"_coord.txt"),status(pre+"_summary.json");inv<<n<<' '<<NG<<'\n';out<<L<<' '<<NG<<'\n';out<<setprecision(22);
 long long totforest=0,keptforest=0,totalterms=0;int powerN=0,primitiveN=0;LD sa=0,sb=0;auto start=chrono::steady_clock::now();
 for(int gi=0;gi<NG;gi++){
  auto row=rows[gi];vector<pair<int,int>>ed;int deg[NV]={},mult[NP]={}; long long den=row.aut;int fact[]={1,1,2,6,24};
  for(int k=0;k<NE;k++){mult[k]=int((row.key>>(2*k))&3);den*=fact[mult[k]];auto[a,b]=pairs[k];for(int j=0;j<mult[k];j++){ed.push_back({a,b});deg[a]++;deg[b]++;}}
  int ss=0;for(int a=0;a<n;a++){den*=fact[4-deg[a]];ss+=(4-deg[a])*(3-deg[a]);}LD wa=24.L/den,wb=wa*ss/12.L;sa+=wa;sb+=wb;
  vector<unsigned>subs,powers;unsigned full=(1u<<n)-1;
  for(unsigned s=1;s<full;s++){int v=__builtin_popcount(s);if(v<2)continue;int e=0;for(auto[a,b]:ed)if((s>>a&1)&&(s>>b&1))e++;if(e<2*(v-1)||!onepi(s,ed))continue;(e==2*(v-1)?subs:powers).push_back(s);}
  if(!powers.empty())powerN++;if(subs.empty()&&powers.empty())primitiveN++;
  inv<<gi<<' '<<u128s(row.key)<<' '<<row.aut<<' '<<row.orbit<<' '<<den<<' '<<ss<<' '<<subs.size()<<' '<<powers.size()<<'\n';for(auto s:subs)inv<<s<<' ';inv<<'\n';for(auto s:powers)inv<<s<<' ';inv<<'\n';
  vector<vector<bool>>comp(subs.size(),vector<bool>(subs.size()));for(int i=0;i<(int)subs.size();i++)for(int j=0;j<(int)subs.size();j++){unsigned a=subs[i],b=subs[j];comp[i][j]=((a&b)==a)||((a&b)==b)||(__builtin_popcount(a&b)<=1);}
  map<U,array<int,NP>> terms;vector<int>sel;
  auto emit=[&](){
   totforest++;vector<unsigned>sets;for(int j:sel)sets.push_back(subs[j]);sets.push_back(full);
   array<int,NP>mv{},rv{};bool valid=true;int rootsE=0;
   for(auto P:sets){
    vector<unsigned>children;for(auto s:sets)if(s!=P&&(s&P)==s){bool maximal=true;for(auto z:sets)if(z!=P&&z!=s&&(z&P)==z&&(s&z)==s){maximal=false;break;}if(maximal)children.push_back(s);}
    int par[NV];iota(par,par+NV,0);for(auto s:children){int r=__builtin_ctz(s);for(int i=0;i<n;i++)if(s>>i&1)unite(par,r,i);}
    for(auto[a,b]:ed){if(!(P>>a&1)||!(P>>b&1))continue;bool inside=false;for(auto s:children)if((s>>a&1)&&(s>>b&1)){inside=true;break;}if(inside)continue;
     int x=root(par,a),y=root(par,b);if(x==y){valid=false;break;}int k=ix[x][y];mv[k]++;if(P==full){rv[k]++;rootsE++;}}
    if(!valid)break;
   }
   if(!valid||!rootsE)return;U key=0;for(int k=0;k<NE;k++){if(mv[k]>3){cerr<<"multiplicity overflow";exit(3);}key|=U(mv[k])<<(2*k);}auto&co=terms[key];int sign=(sel.size()%2)?-1:1;for(int k=0;k<NE;k++)co[k]+=sign*rv[k];keptforest++;
  };
  function<void(vector<int>)>rec=[&](vector<int>cand){emit();for(int k=0;k<(int)cand.size();k++){int j=cand[k];sel.push_back(j);vector<int>next;for(int h=k+1;h<(int)cand.size();h++)if(comp[j][cand[h]])next.push_back(cand[h]);rec(next);sel.pop_back();}};
  vector<int>all(subs.size());iota(all.begin(),all.end(),0);rec(all);
  vector<pair<U,array<int,NP>>>keep;for(auto [key,co]:terms){bool nonzero=false;for(int k=0;k<NE;k++)if(co[k])nonzero=true;if(nonzero)keep.push_back({key,co});}
  totalterms+=keep.size();out<<gi<<' '<<wa<<' '<<wb<<' '<<(!powers.empty())<<' '<<subs.empty()<<' '<<keep.size()<<'\n';for(auto[key,co]:keep){out<<u128s(key);for(int k=0;k<NE;k++)out<<' '<<co[k];out<<'\n';}
  if(gi%200==199)cerr<<"L "<<L<<" graphs "<<gi+1<<" forests "<<totforest<<" terms "<<totalterms<<" seconds "<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<'\n';
 }
 double sec=chrono::duration<double>(chrono::steady_clock::now()-start).count();status<<setprecision(20)<<"{\"L\":"<<L<<",\"classes\":"<<NG<<",\"power_classes\":"<<powerN<<",\"primitive_classes\":"<<primitiveN<<",\"forests\":"<<totforest<<",\"kept_forests\":"<<keptforest<<",\"coordinate_terms\":"<<totalterms<<",\"sum_weight_A\":"<<sa<<",\"sum_weight_B\":"<<sb<<",\"seconds\":"<<sec<<"}\n";cerr<<"DONE "<<status.tellp()<<' '<<sec<<" s\n";
 inv.close();out.close();status.close();if(!inv||!out||!status){cerr<<"write failed\n";return 1;}
}
