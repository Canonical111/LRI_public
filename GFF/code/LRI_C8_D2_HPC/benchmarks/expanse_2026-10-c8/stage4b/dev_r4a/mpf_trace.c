/* mpf call tracer for the R4a call-sequence evidence (Stage 4b, development only; never part of a worker build).
 *
 * LD_PRELOAD shim that interposes every __gmpf_* function the worker imports (nm -D bin/c8d2_gmp: 26 of them) plus
 * mpf_abs, and records each top-level call (calls GMP makes internally are passed through unrecorded). A record is
 *   <op> <class> d=<prec>:<size>:<exp>:<h> a=<...> b=<...> i=<integer argument> r=<return value>
 * with the destination's precision and its representation after the call (sign and size, exponent, FNV-1a-64 hash of
 * its |size| limbs) and the representation of every mpf operand before the call (captured before the call, so an
 * aliased destination is seen as the operand it was). Addresses are never recorded: two runs give the same records
 * exactly when the same calls were made on operands of identical representation into destinations of the same
 * precision, with identical results.
 * Classes: L (lifetime: init2, clear), C (pure copies: set, swap, and get_prec, the precision query that Boost's
 * gmp_float copy constructor and copy assignment make before their mpf_set), Q (queries: cmp, cmp_si, get_si, get_str,
 * fits_slong_p), V (every other call: arithmetic, conversions from integers, strings and long doubles, neg, abs, trunc).
 * (The first version, run in job 54666232, put get_prec in Q; its V digests are unaffected.)
 * Environment:
 *   MPF_TRACE_OUT   output file (required); "<file>" gets the summary JSON, "<file>.log" the records when
 *                   MPF_TRACE_FULL=1.
 *   MPF_TRACE_FULL  1: also write every record (one line each) to <file>.log.
 * The summary has per-op call counts and, per class, the record count and a 128-bit digest (two FNV-1a-64 streams
 * with different offsets) of the class's records in call order, plus the digest of the V and Q records together
 * ("VQ": the value-producing calls and the queries interleaved in order).
 * Build: gcc -O2 -fPIC -shared mpf_trace.c -o mpf_trace.so -I$C8_GMP/include -ldl -lpthread
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <gmp.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static __thread int depth;
static FILE *full;
static int full_on = -1;
enum { NOPS = 32 };
static const char *op_names[NOPS];
static unsigned long long op_count[NOPS];
static int nops;
typedef struct { uint64_t h1, h2, n; } dig_t;
static dig_t dig[5]; /* L C Q V VQ */
static const char *cls_names = "LCQV";

static uint64_t fnv(uint64_t h, const void *p, size_t n) {
    const unsigned char *c = (const unsigned char *)p;
    for (size_t i = 0; i < n; ++i) { h ^= c[i]; h *= 1099511628211ULL; }
    return h;
}
static void dig_add(dig_t *d, const char *s, size_t n) {
    if (d->n == 0) { d->h1 = 14695981039346656037ULL; d->h2 = 0x6c62272e07bb0142ULL; }
    d->h1 = fnv(d->h1, s, n); d->h1 = fnv(d->h1, "\n", 1);
    d->h2 = fnv(d->h2, s, n); d->h2 = fnv(d->h2, "\n", 1);
    d->n++;
}
static int repr(char *b, size_t m, mpf_srcptr x) {
    int sz = x->_mp_size, n = sz < 0 ? -sz : sz;
    uint64_t h = fnv(14695981039346656037ULL, x->_mp_d, (size_t)n * sizeof(mp_limb_t));
    return snprintf(b, m, "%d:%d:%ld:%016llx", x->_mp_prec, sz, (long)x->_mp_exp, (unsigned long long)h);
}
static int op_index(const char *name) {
    for (int k = 0; k < nops; ++k) if (op_names[k] == name) return k;
    if (nops < NOPS) { op_names[nops] = name; return nops++; }
    return NOPS - 1;
}
static void emit(const char *name, char cls, const char *rec) {
    pthread_mutex_lock(&lock);
    op_count[op_index(name)]++;
    size_t n = strlen(rec);
    int c = (int)(strchr(cls_names, cls) - cls_names);
    dig_add(&dig[c], rec, n);
    if (cls == 'V' || cls == 'Q') dig_add(&dig[4], rec, n);
    if (full_on < 0) {
        const char *f = getenv("MPF_TRACE_FULL"), *o = getenv("MPF_TRACE_OUT");
        full_on = (f && f[0] == '1' && o) ? 1 : 0;
        if (full_on) {
            char path[4096]; snprintf(path, sizeof path, "%s.log", o);
            full = fopen(path, "w");
            if (!full) full_on = 0;
        }
    }
    if (full_on) { fputs(rec, full); fputc('\n', full); }
    pthread_mutex_unlock(&lock);
}
__attribute__((destructor)) static void summary(void) {
    const char *o = getenv("MPF_TRACE_OUT");
    if (!o) return;
    FILE *f = fopen(o, "w");
    if (!f) return;
    fprintf(f, "{\"schema\":\"c8-d2-mpf-trace-1\",\"counts\":{");
    for (int k = 0; k < nops; ++k) fprintf(f, "%s\"%s\":%llu", k ? "," : "", op_names[k], op_count[k]);
    fprintf(f, "},\"classes\":{");
    const char *cn[5] = {"L", "C", "Q", "V", "VQ"};
    for (int k = 0; k < 5; ++k)
        fprintf(f, "%s\"%s\":{\"records\":%llu,\"digest\":\"%016llx%016llx\"}", k ? "," : "", cn[k],
                (unsigned long long)dig[k].n, (unsigned long long)dig[k].h1, (unsigned long long)dig[k].h2);
    fprintf(f, "}}\n");
    fclose(f);
    if (full) fclose(full);
}
#define REAL(name) static __typeof__(&mpf_##name) real_##name; \
    if (!real_##name) real_##name = (__typeof__(&mpf_##name))dlsym(RTLD_NEXT, "__gmpf_" #name)
#define R(x, buf) repr(buf, sizeof buf, x)

/* d = f(a, b) */
#define OP2(name, cls)                                                                      \
    void mpf_##name(mpf_ptr r, mpf_srcptr u, mpf_srcptr v) {                               \
        REAL(name);                             \
        if (depth) { real_##name(r, u, v); return; }                                       \
        char a[96], b[96], d[96], rec[400];                                                \
        R(u, a); R(v, b); depth++; real_##name(r, u, v); depth--; R(r, d);                 \
        snprintf(rec, sizeof rec, "%s %c d=%s a=%s b=%s", #name, cls, d, a, b);            \
        emit(#name, cls, rec);                                                             \
    }
/* d = f(a) */
#define OP1(name, cls)                                                                      \
    void mpf_##name(mpf_ptr r, mpf_srcptr u) {                                             \
        REAL(name);                                         \
        if (depth) { real_##name(r, u); return; }                                          \
        char a[96], d[96], rec[300];                                                       \
        R(u, a); depth++; real_##name(r, u); depth--; R(r, d);                             \
        snprintf(rec, sizeof rec, "%s %c d=%s a=%s", #name, cls, d, a);                    \
        emit(#name, cls, rec);                                                             \
    }
/* d = f(a, unsigned long / bitcount) */
#define OP1U(name, cls, T)                                                                  \
    void mpf_##name(mpf_ptr r, mpf_srcptr u, T i) {                                        \
        REAL(name);                                      \
        if (depth) { real_##name(r, u, i); return; }                                       \
        char a[96], d[96], rec[300];                                                       \
        R(u, a); depth++; real_##name(r, u, i); depth--; R(r, d);                          \
        snprintf(rec, sizeof rec, "%s %c d=%s a=%s i=%lu", #name, cls, d, a, (unsigned long)i); \
        emit(#name, cls, rec);                                                             \
    }
OP2(add, 'V')
OP2(sub, 'V')
OP2(mul, 'V')
OP2(div, 'V')
OP1(neg, 'V')
OP1(abs, 'V')
OP1(trunc, 'V')
OP1(set, 'C')
OP1U(add_ui, 'V', unsigned long)
OP1U(sub_ui, 'V', unsigned long)
OP1U(mul_ui, 'V', unsigned long)
OP1U(div_ui, 'V', unsigned long)
OP1U(mul_2exp, 'V', mp_bitcnt_t)
OP1U(div_2exp, 'V', mp_bitcnt_t)

void mpf_ui_div(mpf_ptr r, unsigned long i, mpf_srcptr u) {
    REAL(ui_div);
    if (depth) { real_ui_div(r, i, u); return; }
    char a[96], d[96], rec[300];
    R(u, a); depth++; real_ui_div(r, i, u); depth--; R(r, d);
    snprintf(rec, sizeof rec, "ui_div V d=%s a=%s i=%lu", d, a, i);
    emit("ui_div", 'V', rec);
}
void mpf_set_si(mpf_ptr r, long i) {
    REAL(set_si);
    if (depth) { real_set_si(r, i); return; }
    char d[96], rec[200];
    depth++; real_set_si(r, i); depth--; R(r, d);
    snprintf(rec, sizeof rec, "set_si V d=%s i=%ld", d, i);
    emit("set_si", 'V', rec);
}
void mpf_set_ui(mpf_ptr r, unsigned long i) {
    REAL(set_ui);
    if (depth) { real_set_ui(r, i); return; }
    char d[96], rec[200];
    depth++; real_set_ui(r, i); depth--; R(r, d);
    snprintf(rec, sizeof rec, "set_ui V d=%s i=%lu", d, i);
    emit("set_ui", 'V', rec);
}
int mpf_set_str(mpf_ptr r, const char *s, int base) {
    REAL(set_str);
    if (depth) return real_set_str(r, s, base);
    char d[96], rec[600];
    depth++; int ret = real_set_str(r, s, base); depth--; R(r, d);
    snprintf(rec, sizeof rec, "set_str V d=%s i=%d s=%.300s r=%d", d, base, s, ret);
    emit("set_str", 'V', rec);
    return ret;
}
void mpf_init2(mpf_ptr r, mp_bitcnt_t bits) {
    REAL(init2);
    if (depth) { real_init2(r, bits); return; }
    char d[96], rec[200];
    depth++; real_init2(r, bits); depth--; R(r, d);
    snprintf(rec, sizeof rec, "init2 L d=%s i=%lu", d, (unsigned long)bits);
    emit("init2", 'L', rec);
}
void mpf_clear(mpf_ptr r) {
    REAL(clear);
    if (depth) { real_clear(r); return; }
    char d[96], rec[200];
    R(r, d); depth++; real_clear(r); depth--;
    snprintf(rec, sizeof rec, "clear L a=%s", d);
    emit("clear", 'L', rec);
}
void mpf_swap(mpf_ptr u, mpf_ptr v) {
    REAL(swap);
    if (depth) { real_swap(u, v); return; }
    char a[96], b[96], rec[300];
    R(u, a); R(v, b); depth++; real_swap(u, v); depth--;
    snprintf(rec, sizeof rec, "swap C a=%s b=%s", a, b);
    emit("swap", 'C', rec);
}
int mpf_cmp(mpf_srcptr u, mpf_srcptr v) {
    REAL(cmp);
    if (depth) return real_cmp(u, v);
    char a[96], b[96], rec[300];
    R(u, a); R(v, b); depth++; int ret = real_cmp(u, v); depth--;
    snprintf(rec, sizeof rec, "cmp Q a=%s b=%s r=%d", a, b, ret);
    emit("cmp", 'Q', rec);
    return ret;
}
int mpf_cmp_si(mpf_srcptr u, long i) {
    REAL(cmp_si);
    if (depth) return real_cmp_si(u, i);
    char a[96], rec[300];
    R(u, a); depth++; int ret = real_cmp_si(u, i); depth--;
    snprintf(rec, sizeof rec, "cmp_si Q a=%s i=%ld r=%d", a, i, ret);
    emit("cmp_si", 'Q', rec);
    return ret;
}
int mpf_fits_slong_p(mpf_srcptr u) {
    REAL(fits_slong_p);
    if (depth) return real_fits_slong_p(u);
    char a[96], rec[300];
    R(u, a); depth++; int ret = real_fits_slong_p(u); depth--;
    snprintf(rec, sizeof rec, "fits_slong_p Q a=%s r=%d", a, ret);
    emit("fits_slong_p", 'Q', rec);
    return ret;
}
mp_bitcnt_t mpf_get_prec(mpf_srcptr u) {
    REAL(get_prec);
    if (depth) return real_get_prec(u);
    char a[96], rec[300];
    R(u, a); depth++; mp_bitcnt_t ret = real_get_prec(u); depth--;
    snprintf(rec, sizeof rec, "get_prec C a=%s r=%lu", a, (unsigned long)ret);
    emit("get_prec", 'C', rec);
    return ret;
}
long mpf_get_si(mpf_srcptr u) {
    REAL(get_si);
    if (depth) return real_get_si(u);
    char a[96], rec[300];
    R(u, a); depth++; long ret = real_get_si(u); depth--;
    snprintf(rec, sizeof rec, "get_si Q a=%s r=%ld", a, ret);
    emit("get_si", 'Q', rec);
    return ret;
}
char *mpf_get_str(char *s, mp_exp_t *e, int base, size_t n, mpf_srcptr u) {
    REAL(get_str);
    if (depth) return real_get_str(s, e, base, n, u);
    char a[96], rec[1024];
    R(u, a); depth++; char *ret = real_get_str(s, e, base, n, u); depth--;
    uint64_t h = ret ? fnv(14695981039346656037ULL, ret, strlen(ret)) : 0;
    snprintf(rec, sizeof rec, "get_str Q a=%s i=%d:%lu r=%ld:%016llx", a, base, (unsigned long)n, e ? (long)*e : 0L,
             (unsigned long long)h);
    emit("get_str", 'Q', rec);
    return ret;
}
