// c8d2_inspect: per-graph kernel sizes from the worker's own load_graph/prepare (PLAN.md components B and C).
//   c8d2_inspect PACK INDEX [THREADS]
// INDEX holds one line "id L offset length" per graph (the graph's bytes in PACK). For every line, in INDEX order,
// one JSON line is printed: {"id","L","masks","terms","products","segments","addends","numerators","kernel_bytes"}.
// Each graph's bytes are copied from PACK to its thread's file in a private directory and read by kernel.hpp's
// load_graph at rate scale 1, which runs rates() and prepare() exactly as the worker does; the header's id and L must
// equal the INDEX line. kernel_bytes is the size of the graph's heap tables after prepare(): masks, terms (struct and
// both vectors), the three 2^E long-double tables (alpha, dp, choice_total), products, mon_ids, segments, addends and
// numerators (vector and pairs). addends.size() is the worker's in-block ordering key.
// Temporary files (checkpoint review CK-K03): the directory is made by mkdtemp(3) under $TMPDIR (default /tmp), mode
// 0700 with an unpredictable name, and holds one file per thread, created once before the parallel loop with
// O_CREAT|O_EXCL|O_NOFOLLOW (mode 0600) and rewritten in place for each graph; nothing is created afterwards. The
// files and the directory are removed on every exit: normal completion, an error (exit 2), and the terminating signals
// (the handler unlinks them, then the signal takes its default action; a signal the caller ignores stays ignored, and
// the previous dispositions return once the directory is gone); only SIGKILL leaves the directory behind.
//   c8d2_inspect --describe   prints the build identity.
#include "kernel.hpp"
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <omp.h>

static size_t kernel_bytes(const Graph&g){
    size_t b=g.masks.size()*sizeof(unsigned)+(g.alpha.size()+g.dp.size()+g.choice_total.size())*sizeof(ld)
        +g.products.size()*sizeof(std::pair<int,int>)+g.mon_ids.size()*sizeof(int)+g.segments.size()*sizeof(Segment)
        +g.addends.size()*sizeof(int);
    for(const auto&t:g.terms)b+=sizeof(Term)+(t.ids.size()+t.co.size())*sizeof(int);
    for(const auto&n:g.numerators)b+=sizeof(n)+n.size()*sizeof(std::pair<int,int>);
    return b;
}

struct Item{long id;int L;unsigned long long offset,length;};

// ---- the private directory. Its paths live in buffers fixed before any handler can read them, so the handler uses
// only async-signal-safe calls (unlink, rmdir, sigaction, raise).
constexpr int MAXTHREADS=4096;
constexpr int TERMINATING[]={SIGHUP,SIGINT,SIGQUIT,SIGTERM,SIGUSR1,SIGUSR2,SIGPIPE,SIGALRM,SIGXCPU,SIGXFSZ,SIGABRT,SIGSEGV,
                             SIGBUS,SIGFPE,SIGILL};
static char g_dir[4096];          // the mkdtemp directory; empty when there is none
static char*g_files=nullptr;      // g_nfiles paths of g_stride bytes each
static size_t g_stride=0;
static volatile sig_atomic_t g_nfiles=0;
static void remove_private(){
    if(!g_dir[0])return;
    for(int i=0;i<g_nfiles;++i)unlink(g_files+size_t(i)*g_stride);
    rmdir(g_dir);
}
extern "C" void on_signal(int sig){  // the raised signal takes its default action (SIGILL is never reset by SA_RESETHAND)
    remove_private();
    struct sigaction dfl{};dfl.sa_handler=SIG_DFL;sigemptyset(&dfl.sa_mask);sigaction(sig,&dfl,nullptr);
    raise(sig);
}
class PrivateDir{
public:
    // Creates base/c8d2_inspect.XXXXXX (0700) and its n files (0600, opened for writing), with the terminating signals
    // blocked until the paths are recorded and the handlers installed.
    PrivateDir(const std::string&base,int n){
        if(n<1||n>MAXTHREADS)throw std::runtime_error("bad thread count");
        std::string tmpl=base+"/c8d2_inspect.XXXXXX";
        if(tmpl.size()+32>sizeof(g_dir))throw std::runtime_error("TMPDIR path too long: "+base);
        sigset_t block,old;sigemptyset(&block);for(int s:TERMINATING)sigaddset(&block,s);
        if(sigprocmask(SIG_BLOCK,&block,&old)!=0)throw std::runtime_error("cannot block signals");
        std::string err;
        std::memcpy(g_dir,tmpl.c_str(),tmpl.size()+1);
        if(!mkdtemp(g_dir)){err=std::string("cannot create a private directory under ")+base+": "+std::strerror(errno);g_dir[0]=0;}
        else{
            g_stride=std::strlen(g_dir)+32;buffer.reset(new char[size_t(n)*g_stride]);g_files=buffer.get();
            for(int t=0;t<n;++t)std::snprintf(g_files+size_t(t)*g_stride,g_stride,"%s/g%d.txt",g_dir,t);
            g_nfiles=n;
            // a signal the caller ignores (nohup's SIGHUP, say) stays ignored; the others get the cleanup handler
            for(size_t k=0;k<NSIGNALS;++k){struct sigaction sa{};sa.sa_handler=on_signal;sigemptyset(&sa.sa_mask);sa.sa_flags=SA_RESETHAND;
                if(sigaction(TERMINATING[k],nullptr,&saved[k])!=0){if(err.empty())err="cannot read the signal dispositions";continue;}
                if(saved[k].sa_handler==SIG_IGN)continue;
                if(sigaction(TERMINATING[k],&sa,nullptr)!=0){if(err.empty())err="cannot install the signal handlers";continue;}
                installed[k]=true;}
            for(int t=0;t<n&&err.empty();++t){
                int fd=open(path(t),O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
                if(fd<0){err=std::string("cannot create ")+path(t)+": "+std::strerror(errno);break;}
                fds.push_back(fd);
            }
        }
        sigprocmask(SIG_SETMASK,&old,nullptr);  // a signal that arrived meanwhile is delivered now, to the handler
        if(!err.empty()){cleanup();throw std::runtime_error(err);}
    }
    ~PrivateDir(){cleanup();}
    PrivateDir(const PrivateDir&)=delete;PrivateDir&operator=(const PrivateDir&)=delete;
    const char*path(int t)const{return g_files+size_t(t)*g_stride;}
    // Replace thread t's file content with buf (the file keeps its inode; no new file is ever created).
    void write(int t,const std::string&buf)const{
        int fd=fds.at(t);
        if(ftruncate(fd,0)!=0)throw std::runtime_error(std::string("cannot truncate ")+path(t)+": "+std::strerror(errno));
        size_t done=0;
        while(done<buf.size()){ssize_t w=pwrite(fd,buf.data()+done,buf.size()-done,off_t(done));
            if(w<0&&errno==EINTR)continue;
            if(w<=0)throw std::runtime_error(std::string("cannot write ")+path(t)+": "+std::strerror(errno));
            done+=size_t(w);}
    }
private:
    static constexpr size_t NSIGNALS=sizeof(TERMINATING)/sizeof(TERMINATING[0]);
    std::unique_ptr<char[]>buffer;std::vector<int>fds;struct sigaction saved[NSIGNALS]{};bool installed[NSIGNALS]{};
    void cleanup(){
        for(int fd:fds)close(fd);
        fds.clear();
        remove_private();
        g_nfiles=0;g_dir[0]=0;
        for(size_t k=0;k<NSIGNALS;++k)if(installed[k]){sigaction(TERMINATING[k],&saved[k],nullptr);installed[k]=false;}  // as before
    }
};

int main(int argc,char**argv){try{
    if(argc==2&&std::string(argv[1])=="--describe"){
        std::cout<<"{\"schema\":\"c8-d2-inspect-1\",\"dimension\":2,\"lmax\":"<<LMAX<<",\"emax\":"<<EMAX<<",\"compiler\":\""<<__VERSION__
                 <<"\",\"long_double_bits\":"<<std::numeric_limits<ld>::digits<<",\"sizeof_ld\":"<<sizeof(ld)<<",\"openmp\":"<<_OPENMP<<"}\n";
        return 0;}
    if(argc<3||argc>4){std::cerr<<"usage: c8d2_inspect PACK INDEX [THREADS]\n";return 1;}
    std::string pack=argv[1];int threads=argc>3?std::stoi(argv[3]):omp_get_max_threads();
    if(threads<1||threads>MAXTHREADS)throw std::runtime_error("bad thread count");
    std::ifstream idx(argv[2]);std::vector<Item>items;Item it;
    while(idx>>it.id>>it.L>>it.offset>>it.length){if(it.L<2||it.L>LMAX||!it.length)throw std::runtime_error("bad index line");items.push_back(it);}
    if(!idx.eof())throw std::runtime_error("unreadable index line");
    const char*td=std::getenv("TMPDIR");std::string tmpdir=td&&*td?td:"/tmp";
    std::vector<std::string>out(items.size());std::string error;
    {
        PrivateDir dir(tmpdir,threads);
        #pragma omp parallel num_threads(threads)
        {
            const int me=omp_get_thread_num();
            std::ifstream pk(pack,std::ios::binary);std::string buf;
            #pragma omp for schedule(dynamic,1)
            for(size_t i=0;i<items.size();++i){try{
                const auto&x=items[i];buf.resize(x.length);
                pk.seekg(x.offset);pk.read(&buf[0],x.length);if(!pk)throw std::runtime_error("cannot read graph "+std::to_string(x.id)+" from the pack");
                dir.write(me,buf);
                Graph g=load_graph(dir.path(me),1.0L);
                if(g.id!=x.id||g.L!=x.L)throw std::runtime_error("graph identity mismatch at id "+std::to_string(x.id));
                std::ostringstream o;
                o<<"{\"id\":"<<x.id<<",\"L\":"<<x.L<<",\"masks\":"<<g.masks.size()<<",\"terms\":"<<g.terms.size()<<",\"products\":"<<g.products.size()
                 <<",\"segments\":"<<g.segments.size()<<",\"addends\":"<<g.addends.size()<<",\"numerators\":"<<g.numerators.size()
                 <<",\"kernel_bytes\":"<<kernel_bytes(g)<<"}";
                out[i]=o.str();
            }catch(const std::exception&e){
                #pragma omp critical
                {if(error.empty())error=e.what();}
            }}
        }
    }  // the private directory is gone from here on
    if(!error.empty())throw std::runtime_error(error);
    for(const auto&s:out)std::cout<<s<<'\n';
    if(!std::cout)throw std::runtime_error("output write failed");
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
