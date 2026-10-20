// gen3/regenerate_rates.cpp: the d=3 rate line of C7(2)/C8(2) G-files (PLAN.md component A.1; C63d).
// Port of LRI_C7_D3_HPC/reference/src/regenerate_rates.cpp (byte copy at c8-rb, sha256 71810982...).
//
// Unchanged, so the outputs at L <= 7 keep their bytes: the d=3 rate formula (p4 = 3|s| + 4 nu_N - 6 h in quarter
// units, a non-positive p4 lifted into (0, 4] by the mod-4 clamp, the minimum over the forest terms), the header copy
// (wa and wb copied as text) and the printing of the header, masks, terms and rate line.
// Changed (A.1):
//  - no num_threads(3): OMP_NUM_THREADS from the job applies;
//  - L <= 8 (E = 2L <= 16, so 2^E <= 65,536 subsets); ids are read as uint64_t and the 2^E arrays sized as size_t;
//  - a checked reader (round-1 R11). Every extraction goes through one helper; every check comes before any
//    allocation sized by a file value and before any index use: magic; L in [2,8]; id a non-negative integer; wa and
//    wb finite decimal numbers (still copied as text); M in [1,16384] and T in [1,10000]; exactly M masks, each
//    < 2^E with popcount L, strictly increasing; per term a length n in [1,M] (before the term is sized), n indices in
//    [0,M) strictly increasing, exactly E coefficients; then the input's rate block, which the original never read:
//    a count equal to 2^E, exactly 2^E numbers, then only whitespace to the end of the file. Integers must be written
//    canonically (no sign on non-negative fields, no leading zero, no "-0"), so an output's body repeats its input's
//    tokens. Each failure: exit 2 with "<input path>: <field> <reason>" on stderr;
//  - the job list opens, holds an even, non-zero number of tokens and no repeated output path; no output (or its
//    .tmp) may lie under C62d's trees (A.2 step 0: /expanse/lustre/scratch/zzheng8/temp_project/c8d2 and any
//    .../LRI_C8_shared/inventory);
//  - S1-02: no two roles share a file. Outputs and their temporaries are compared as directory entries (the parent
//    resolved through existing symbolic links, so two symlinked spellings of one directory collide) and existing outputs
//    also by identity (st_dev, st_ino); an input is followed through every symbolic link (a dangling one included) and
//    may be neither an output nor a temporary file, by path or by identity; an existing <output>.tmp (another run's, or
//    left by a failed one) is refused, never overwritten;
//  - no exception leaves the OpenMP region (each job catches into its own error slot); each output is written to
//    <name>.tmp, created exclusively (O_CREAT|O_EXCL: it never replaces a file or follows a link) and checked through
//    close(); the renames happen, in job-list order, only after every job succeeded; otherwise the messages are printed
//    in job order, every .tmp THIS run created is removed (no other file), nothing is printed on stdout and the exit
//    status is 2;
//  - the per-file record keeps cancelled_nonpositive_subsets and minimum_rate_quarters and adds raw_histogram (the
//    number of subsets 0 < s < 2^E-1 by raw p4 <= 0), min_raw and double_lift_subsets (raw p4 <= -5; the d=3 double
//    lift is raw -6, RECON:1346-1350); the file name is JSON-escaped.
// Test-only macro C8_TEST_UNGUARDED_INDEX (PLAN.md C.7, coverage self-test; only in
// bin/selftest/regenerate_rates_unguarded_san): it removes the reader's term-index range check, the only guard of the
// mask lookup that clears the distance table (the self-test finds that line). It cannot enter a build without
// _GLIBCXX_ASSERTIONS.
//
// Usage:  regenerate_rates JOBLIST        JOBLIST: whitespace-separated pairs "<input G-file> <output G-file>"
// Output: on success a JSON array of per-file records on stdout (job-list order), progress on stderr, exit 0.
// Build:  g++ -O2 -std=c++17 -fopenmp -Wall -Wextra gen3/regenerate_rates.cpp -o bin/gen3/regenerate_rates
#include <bits/stdc++.h>
#include <omp.h>
#include <filesystem>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#if defined(C8_TEST_UNGUARDED_INDEX) && !defined(_GLIBCXX_ASSERTIONS)
#error "C8_TEST_UNGUARDED_INDEX is for bin/selftest/regenerate_rates_unguarded_san only (it needs _GLIBCXX_ASSERTIONS)"
#endif
using namespace std;
namespace fs=std::filesystem;

struct Bad:runtime_error{using runtime_error::runtime_error;};

static string shown(const string&s){  // a token as it may appear in a message: printable ASCII, at most 40 bytes
 string o;for(unsigned char c:s){if(o.size()>=40){o+="...";break;}if(c>=32&&c<127)o+=char(c);else{char b[8];snprintf(b,sizeof b,"\\x%02x",c);o+=b;}}
 return "'"+o+"'";
}
static bool canonical_int(const string&s,bool allow_negative){
 size_t i=0;if(allow_negative&&s.size()>1&&s[0]=='-')i=1;
 if(i>=s.size())return false;
 for(size_t j=i;j<s.size();j++)if(s[j]<'0'||s[j]>'9')return false;
 if(s[i]=='0'&&s.size()>i+1)return false;   // no leading zero
 if(i==1&&s=="-0")return false;
 return true;
}
static bool decimal_number(const string&s){  // [-]digits[.digits][(e|E)[+-]digits], or [-].digits[...]
 size_t i=0,n=s.size();if(i<n&&(s[i]=='-'||s[i]=='+'))i++;
 size_t d0=i;while(i<n&&isdigit((unsigned char)s[i]))i++;size_t lead=i-d0,frac=0;
 if(i<n&&s[i]=='.'){i++;size_t f0=i;while(i<n&&isdigit((unsigned char)s[i]))i++;frac=i-f0;}
 if(lead+frac==0)return false;
 if(i<n&&(s[i]=='e'||s[i]=='E')){i++;if(i<n&&(s[i]=='-'||s[i]=='+'))i++;size_t e0=i;while(i<n&&isdigit((unsigned char)s[i]))i++;if(i==e0)return false;}
 if(i!=n)return false;
 errno=0;char*end=nullptr;long double v=strtold(s.c_str(),&end);
 return end==s.c_str()+n&&isfinite(v);
}

// The checked reader. Every extraction goes through tok(), which fails with "<path>: truncated or malformed <field>".
struct Reader{
 ifstream f;string path;
 explicit Reader(const string&p):path(p){
  error_code ec;if(fs::is_directory(p,ec))throw Bad(path+": cannot open (a directory)");
  f.open(p,ios::binary);if(!f)throw Bad(path+": cannot open");
 }
 [[noreturn]] void fail(const string&field,const string&reason)const{throw Bad(path+": "+field+" "+reason);}
 string tok(const string&field){
  string s;
  if(!(f>>s)){if(f.bad())fail(field,"read error");fail("truncated or malformed",field+" (end of file)");}
  return s;
 }
 long long integer(const string&field,long long lo,long long hi,bool allow_negative=true){
  string s=tok(field);
  if(!canonical_int(s,allow_negative))fail("truncated or malformed",field+" "+shown(s));
  long long v=0;auto r=from_chars(s.data(),s.data()+s.size(),v);
  if(r.ec!=errc()||r.ptr!=s.data()+s.size())fail("truncated or malformed",field+" "+shown(s)+" (not a 64-bit integer)");
  if(v<lo||v>hi)fail(field,to_string(v)+" out of range ["+to_string(lo)+","+to_string(hi)+"]");
  return v;
 }
 uint64_t unsigned_integer(const string&field){
  string s=tok(field);
  if(!canonical_int(s,false))fail(field,shown(s)+" is not a non-negative integer");
  uint64_t v=0;auto r=from_chars(s.data(),s.data()+s.size(),v);
  if(r.ec!=errc()||r.ptr!=s.data()+s.size())fail(field,shown(s)+" is not a 64-bit non-negative integer");
  return v;
 }
 string number(const string&field){
  string s=tok(field);
  if(!decimal_number(s))fail(field,shown(s)+" is not a finite decimal number");
  return s;
 }
 void at_end(){
  string s;if(f>>s)fail("trailing data",shown(s)+" after the rate list");
  if(f.bad())fail("trailing data","read error");
 }
};

static string json_escape(const string&s){
 string o;for(unsigned char c:s){if(c=='"'||c=='\\'){o+='\\';o+=char(c);}else if(c<32){char b[8];snprintf(b,sizeof b,"\\u%04x",c);o+=b;}else o+=char(c);}
 return o;
}

// C62d's trees (A.2 step 0): nothing of this package writes under them.
static string under_c62d(const string&p){
 auto check=[](const fs::path&q)->string{
  string s=q.generic_string();const string c8d2="/expanse/lustre/scratch/zzheng8/temp_project/c8d2";
  if(s==c8d2||s.rfind(c8d2+"/",0)==0)return c8d2;
  vector<string>parts;for(auto&x:q)parts.push_back(x.string());
  for(size_t i=0;i+1<parts.size();i++)if(parts[i]=="LRI_C8_shared"&&parts[i+1]=="inventory")return ".../LRI_C8_shared/inventory";
  return "";
 };
 error_code ec;fs::path a=fs::absolute(fs::path(p),ec);if(ec)return "";
 string r=check(a.lexically_normal());if(!r.empty())return r;
 fs::path w=fs::weakly_canonical(a,ec);if(!ec){r=check(w);if(!r.empty())return r;}
 return "";
}

// S1-02: an output's or temporary file's directory entry (absolute; the parent resolved through existing symbolic links,
// the name kept), an input's target (every symbolic link of the final component followed, a dangling one included, then
// its entry) and an existing file's identity.
static string entry_key(const fs::path&p){
 error_code ec;fs::path a=fs::absolute(p,ec);if(ec)return p.generic_string();
 fs::path parent=fs::weakly_canonical(a.parent_path(),ec);if(ec)parent=a.parent_path().lexically_normal();
 return (parent/a.filename()).generic_string();
}
static string target_key(const string&p){
 error_code ec;fs::path a=fs::absolute(fs::path(p),ec);if(ec)return p;
 for(int hop=0;hop<40;hop++){auto st=fs::symlink_status(a,ec);if(ec||!fs::is_symlink(st))break;fs::path l=fs::read_symlink(a,ec);if(ec)break;a=l.is_absolute()?l:a.parent_path()/l;}
 return entry_key(a);
}
static bool identity(const string&p,pair<dev_t,ino_t>&id){struct stat st;if(::stat(p.c_str(),&st)!=0)return false;id={st.st_dev,st.st_ino};return true;}

static string read_jobs(const string&list,vector<pair<string,string>>&jobs){
 error_code ec;if(fs::is_directory(list,ec))return list+": job list cannot be opened (a directory)";
 ifstream in(list,ios::binary);if(!in)return list+": job list cannot be opened";
 vector<string>t;string s;while(in>>s)t.push_back(s);
 if(in.bad())return list+": job list read error";
 if(t.empty())return list+": job list is empty";
 if(t.size()%2)return list+": job list has an odd number of tokens ("+to_string(t.size())+")";
 set<string>seen,seen_abs;
 for(size_t i=0;i<t.size();i+=2)jobs.emplace_back(t[i],t[i+1]);
 for(auto&[a,b]:jobs){
  string key=fs::absolute(fs::path(b),ec).lexically_normal().generic_string();if(ec)key=b;
  if(!seen.insert(b).second||!seen_abs.insert(key).second)return list+": output path "+b+" is repeated";
 }
 for(auto&[a,b]:jobs){
  string key=fs::absolute(fs::path(b+".tmp"),ec).lexically_normal().generic_string();if(ec)key=b+".tmp";
  if(seen_abs.count(key))return list+": output path "+b+".tmp is another job's temporary file";
  for(const string&p:{b,b+".tmp"}){string r=under_c62d(p);if(!r.empty())return list+": output path "+p+" is under C62d's tree "+r+" (refused)";}
 }
 // S1-02: outputs and temporaries by entry (and existing outputs by identity), then the inputs against both.
 map<string,string>entry;map<pair<dev_t,ino_t>,string>file;
 for(size_t k=0;k<jobs.size();k++){const string&b=jobs[k].second;const string job=" of job "+to_string(k);
  for(auto&[p,what]:{pair<string,string>{b,"output"+job},{b+".tmp","temporary file"+job}}){
   auto [it,fresh]=entry.emplace(entry_key(fs::path(p)),what);if(!fresh)return list+": "+what+" "+p+" is the same path as the "+it->second;}
  pair<dev_t,ino_t>id;if(identity(b,id)){auto [it,fresh]=file.emplace(id,"output"+job);if(!fresh)return list+": output"+job+" "+b+" is the same file as the "+it->second;}
  error_code ec;if(fs::exists(fs::symlink_status(b+".tmp",ec)))return list+": temporary file "+b+".tmp"+job+" exists (never overwritten: another run's, or left by a failed one)";
 }
 for(size_t k=0;k<jobs.size();k++){const string&a=jobs[k].first;
  auto it=entry.find(target_key(a));if(it!=entry.end())return list+": input path "+a+" of job "+to_string(k)+" is the "+it->second;
  pair<dev_t,ino_t>id;if(identity(a,id)){auto jt=file.find(id);if(jt!=file.end())return list+": input path "+a+" of job "+to_string(k)+" is the same file as the "+jt->second;}
 }
 return "";
}

static string regenerate(const string&input,const string&output,char&tmp_made){
 Reader r(input);
 // Header: magic L id wa wb M T.
 string magic=r.tok("magic");
 if(magic!="C7D2GRAPH1"&&magic!="C7D3GRAPH1")r.fail("magic",shown(magic)+" unknown (expected C7D2GRAPH1 or C7D3GRAPH1)");
 int L=int(r.integer("L",2,8));int E=2*L,ALL=(1<<E)-1;   // E <= 16, so ALL+1 <= 65,536
 uint64_t id=r.unsigned_integer("id");
 string wa=r.number("wa"),wb=r.number("wb");
 int M=int(r.integer("M",1,16384)),T=int(r.integer("T",1,10000));
 // Masks: exactly M, each < 2^E with popcount L, strictly increasing.
 const size_t nM=size_t(M);vector<unsigned>masks(nM,0u);
 for(int k=0;k<M;k++){
  string field="mask "+to_string(k);long long v=r.integer(field,0,ALL,false);
  if(__builtin_popcount(unsigned(v))!=L)r.fail(field,to_string(v)+" has popcount "+to_string(__builtin_popcount(unsigned(v)))+", expected L = "+to_string(L));
  if(k&&unsigned(v)<=masks[size_t(k)-1])r.fail(field,to_string(v)+" is not above the previous mask "+to_string(masks[size_t(k)-1])+" (masks strictly increasing)");
  masks[size_t(k)]=unsigned(v);
 }
 // Terms: a length n in [1,M], n indices in [0,M) strictly increasing, exactly E coefficients.
 const size_t nT=size_t(T);vector<vector<int>>basis(nT),cos(nT);
 for(int i=0;i<T;i++){
  string ti="term "+to_string(i);
  int n=int(r.integer(ti+" length",1,M));
  basis[size_t(i)].resize(size_t(n));
  for(int j=0;j<n;j++){
   string field=ti+" index "+to_string(j);
#ifndef C8_TEST_UNGUARDED_INDEX
   long long v=r.integer(field,0,M-1);
#else
   long long v=r.integer(field,LLONG_MIN,LLONG_MAX);   // test-only: no range check (the self-test's index M)
#endif
   if(j&&v<=basis[size_t(i)][size_t(j)-1])r.fail(field,to_string(v)+" is not above the previous index (indices strictly increasing)");
   basis[size_t(i)][size_t(j)]=int(v);
  }
  cos[size_t(i)].resize(size_t(E));
  for(int j=0;j<E;j++)cos[size_t(i)][size_t(j)]=int(r.integer(ti+" coefficient "+to_string(j),INT_MIN,INT_MAX));
 }
 // The input's rate block: a count equal to 2^E, exactly 2^E numbers (unused: the d=3 line is recomputed), then EOF.
 r.integer("rate count",ALL+1,ALL+1);
 for(int s=0;s<=ALL;s++)r.number("rate "+to_string(s));
 r.at_end();

 vector<int>positive(size_t(ALL)+1,1000),raw(size_t(ALL)+1,1000),pc(size_t(ALL)+1);for(int s=0;s<=ALL;s++)pc[s]=__builtin_popcount(unsigned(s));
 for(int ti=0;ti<T;ti++){
  vector<int8_t>dist(size_t(ALL)+1,100);for(int m:basis[ti])dist[masks[m]]=0;
  for(int bit=1;bit<=ALL;bit<<=1)for(int base=0;base<=ALL;base+=2*bit)for(int j=0;j<bit;j++){int s=base+j,t=s+bit,x=dist[s],y=dist[t];dist[s]=min(x,y+1);dist[t]=min(y,x+1);}
  unsigned supp=0;for(int j=0;j<E;j++)if(cos[ti][j])supp|=1u<<j;
  for(int s=1;s<ALL;s++){int h=(L-E+pc[s]+int(dist[ALL^s]))/2;int nuN=(supp&~unsigned(s))?0:1;int p4=3*pc[s]+4*nuN-6*h;raw[s]=min(raw[s],p4);if(p4<=0){p4=(p4%4+4)%4;if(!p4)p4=4;}positive[s]=min(positive[s],p4);}
 }
 string tmp=output+".tmp";
 long clamped=0;int minp=1000;
 {
  ostringstream out;   // the same formatting as the former ofstream (classic locale), written below through an exclusive fd
  out<<setprecision(22)<<"C7D3GRAPH1 "<<L<<' '<<id<<' '<<wa<<' '<<wb<<' '<<M<<' '<<T<<'\n';for(auto m:masks)out<<m<<' ';out<<'\n';
  for(int i=0;i<T;i++){out<<basis[i].size();for(auto v:basis[i])out<<' '<<v;for(auto v:cos[i])out<<' '<<v;out<<'\n';}out<<ALL+1<<'\n';
  for(int s=0;s<=ALL;s++){if(s&&s<ALL){clamped+=raw[s]<=0;minp=min(minp,positive[s]);out<<positive[s]*.25L<<' ';}else out<<"0 ";}out<<'\n';
  if(!out)throw Bad(output+": formatting failed");
  const string bytes=out.str();
  int fd=::open(tmp.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0666);
  if(fd<0){int e=errno;throw Bad(output+": cannot create "+tmp+(e==EEXIST?" (it exists: never overwritten)":" ("+string(strerror(e))+")"));}
  tmp_made=1;   // from here on this run owns the file (and only then may remove it)
  size_t at=0;bool good=true;
  while(at<bytes.size()){ssize_t w=::write(fd,bytes.data()+at,bytes.size()-at);if(w<0){if(errno==EINTR)continue;good=false;break;}at+=size_t(w);}
  if(::close(fd)!=0)good=false;
  if(!good)throw Bad(output+": write failed ("+tmp+")");
 }
 map<int,long>hist;int min_raw=INT_MAX;long double_lift=0;
 for(int s=1;s<ALL;s++){min_raw=min(min_raw,raw[s]);if(raw[s]<=0)hist[raw[s]]++;if(raw[s]<=-5)double_lift++;}
 string h="{";bool first=true;for(auto&[v,c]:hist){if(!first)h+=',';first=false;h+="\""+to_string(v)+"\":"+to_string(c);}h+="}";
 return "{\"file\":\""+json_escape(output)+"\",\"L\":"+to_string(L)+",\"id\":"+to_string(id)+",\"cancelled_nonpositive_subsets\":"+to_string(clamped)
       +",\"minimum_rate_quarters\":"+to_string(minp)+",\"raw_histogram\":"+h+",\"min_raw\":"+to_string(min_raw)+",\"double_lift_subsets\":"+to_string(double_lift)+"}";
}

int main(int ac,char**av){
 if(ac!=2){cerr<<"usage: regenerate_rates JOBLIST   (whitespace-separated pairs: input G-file, output G-file)\n";return 2;}
 vector<pair<string,string>>jobs;
 string err=read_jobs(av[1],jobs);if(!err.empty()){cerr<<err<<'\n';return 2;}
 const size_t nj=jobs.size();vector<string>records(nj),errors(nj);vector<char>tmp_made(nj,0);
 atomic<long>done{0};double start=omp_get_wtime();
#pragma omp parallel for schedule(dynamic,1)
 for(size_t k=0;k<nj;k++){
  try{records[k]=regenerate(jobs[k].first,jobs[k].second,tmp_made[k]);}
  catch(const Bad&e){errors[k]=e.what();}
  catch(const bad_alloc&){errors[k]=jobs[k].first+": out of memory";}
  catch(const exception&e){errors[k]=jobs[k].first+": "+e.what();}
  catch(...){errors[k]=jobs[k].first+": unknown error";}
  long d=++done;if(d%100==0){
#pragma omp critical
   cerr<<d<<'/'<<nj<<" seconds "<<omp_get_wtime()-start<<'\n';}
 }
 bool bad=false;for(auto&e:errors)bad|=!e.empty();
 if(!bad){
  for(size_t k=0;k<nj;k++){
   error_code ec;fs::rename(jobs[k].second+".tmp",jobs[k].second,ec);
   if(ec){errors[k]=jobs[k].second+": rename failed ("+ec.message()+")";bad=true;break;}
   tmp_made[k]=0;
  }
 }
 if(bad){
  for(auto&e:errors)if(!e.empty())cerr<<e<<'\n';
  for(size_t k=0;k<nj;k++)if(tmp_made[k]){error_code ec;fs::remove(jobs[k].second+".tmp",ec);}
  return 2;
 }
 cout<<"[";for(size_t i=0;i<records.size();i++){if(i)cout<<',';cout<<records[i];}cout<<"]\n";cout.flush();
 if(!cout){cerr<<"stdout: write failed\n";return 2;}
 return 0;
}
