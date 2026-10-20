#include <bits/stdc++.h>
using namespace std;
using U=uint64_t;using I=uint32_t;
static constexpr U P=2305843009213693951ULL;
inline U add(U a,U b){U c=a+b;return c>=P?c-P:c;}
inline U sub(U a,U b){return a>=b?a-b:a+P-b;}
inline U mul(U a,U b){__uint128_t t=(__uint128_t)a*b;U x=((U)t&P)+(U)(t>>61);return x>=P?x-P:x;}
U power(U a,U e){U v=1;while(e){if(e&1)v=mul(v,a);a=mul(a,a);e>>=1;}return v;}
U fromint(int64_t a){if(a<0)return P-((U)(-a)%P);return a%P;}
struct __attribute__((packed)) Ent {I w;U c;};
static_assert(sizeof(Ent)==12);
struct Def {uint64_t src;U inv;uint64_t offset;uint32_t count;};
struct Engine {
  vector<vector<Ent>> basis;vector<Def> defs;vector<int> leads;
  vector<U> val;vector<char> queued;priority_queue<I> heap;
  string parentpath;ofstream parentout;uint64_t parentpos=0;
  size_t nnz=0,pnz=0;int rank=0;size_t elims=0;
  Engine(int N,const string& pref):leads(N,-1),val(N,0),queued(N,0),parentpath(pref+".parents.bin"),parentout(parentpath,ios::binary){}
  void push(I w,U c){if(!c)return;val[w]=add(val[w],c);if(!queued[w]){queued[w]=1;heap.push(w);}}
  void decrease(I w,U c){if(!c)return;val[w]=sub(val[w],c);if(!queued[w]){queued[w]=1;heap.push(w);}}
  I top(){while(!heap.empty()&&!val[heap.top()]){queued[heap.top()]=0;heap.pop();}return heap.empty()?UINT32_MAX:heap.top();}
  void clear(){while(!heap.empty()){I w=heap.top();heap.pop();queued[w]=0;val[w]=0;}}
  void eliminate(int j,U fac){++elims;for(auto &e:basis[j])decrease(e.w,mul(fac,e.c));}
  bool insert(const vector<Ent>& r,uint64_t src){
    for(auto &e:r)push(e.w,e.c);
    vector<Ent> parents, remainder;
    while(true){I w=top();if(w==UINT32_MAX)break;
      int j=leads[w];U fac=val[w];
      if(j<0){remainder.push_back({w,fac});heap.pop();queued[w]=0;val[w]=0;}
      else{parents.push_back({(I)j,fac});eliminate(j,fac);}
    }
    clear();
    if(remainder.empty())return false;
    U inv=power(remainder.front().c,P-2);int idx=basis.size();
    leads[remainder.front().w]=idx;
    for(auto &e:remainder)e.c=mul(e.c,inv);
    remainder.shrink_to_fit();nnz+=remainder.size();basis.push_back(move(remainder));
    for(auto &e:parents){e.c=mul(e.c,inv);if(e.c)e.c=P-e.c;}
    pnz+=parents.size();
    defs.push_back({src,inv,parentpos,(uint32_t)parents.size()});
    parentout.write((const char*)parents.data(),parents.size()*sizeof(Ent));
    parentpos+=parents.size()*sizeof(Ent);
    rank++;return true;
  }
  bool certificate(const vector<Ent>&tar,const string&path){
    for(auto&e:tar)push(e.w,e.c);
    vector<U> weights(basis.size(),0);
    while(true){I w=top();if(w==UINT32_MAX)break;
      int j=leads[w];if(j<0){clear();return false;}
      U fac=val[w];weights[j]=add(weights[j],fac);eliminate(j,fac);
    }
    clear();map<uint64_t,U> sources;
    parentout.flush();ifstream parentsin(parentpath,ios::binary);
    for(int j=(int)basis.size()-1;j>=0;j--){U fac=weights[j];if(!fac)continue;auto&d=defs[j];
      sources[d.src]=add(sources[d.src],mul(fac,d.inv));
      vector<Ent> par(d.count);parentsin.seekg(d.offset);parentsin.read((char*)par.data(),d.count*sizeof(Ent));
      for(auto&e:par)weights[e.w]=add(weights[e.w],mul(fac,e.c));
    }
    ofstream f(path);f<<P<<"\n";int nz=0;
    for(auto&[k,c]:sources)if(c){f<<k<<" "<<c<<"\n";nz++;}
    cerr<<"CERTIFICATE FOUND rank="<<rank<<" source_count="<<nz<<"\n";
    return true;
  }
};
int main(int argc,char**argv){
 if(argc<2){cerr<<"usage: sparse_certificate prefix [start-check]\n";return 2;}
 string pref=argv[1];ifstream t(pref+".target.txt");int N,nt;t>>N>>nt;if(!t){cerr<<"bad target\n";return 2;}
 vector<Ent>tar;for(int i=0;i<nt;i++){I w;int64_t c;t>>w>>c;tar.push_back({w,fromint(c)});}
 Engine e(N,pref);ifstream f(pref+".rows.bin",ios::binary);uint64_t i=0;auto start=chrono::steady_clock::now();
 size_t checkpoint=1000;
 while(true){I len;f.read((char*)&len,4);if(!f)break;vector<Ent>row;row.reserve(len);
   for(I j=0;j<len;j++){I w;int64_t c;f.read((char*)&w,4);f.read((char*)&c,8);row.push_back({w,fromint(c)});}if(!f){cerr<<"truncated\n";return 3;}
   e.insert(row,i);i++;
   if(i%checkpoint==0){double sec=chrono::duration<double>(chrono::steady_clock::now()-start).count();cerr<<"row="<<i<<" rank="<<e.rank<<" nnz="<<e.nnz<<" parents="<<e.pnz<<" elims="<<e.elims<<" sec="<<sec<<"\n";
     if(e.certificate(tar,pref+".modcert.txt"))return 0;
   }
 }
 if(e.certificate(tar,pref+".modcert.txt"))return 0;
 cerr<<"TARGET UNREDUCED after "<<i<<" rows rank="<<e.rank<<"\n";return 1;
}
