/* C twin of the v3 polish cores (src/sat/ls_v3.py): walksat_v3 and dls_v3.
 *
 * docs/current2/STRONGER_MEMETIC_DESIGN.md §7 (repo). Every decision, random
 * draw and data-structure order follows the Python code line by line, with the
 * portable RNG of src/sat/rng.py (xoshiro256** seeded by splitmix64). So, for
 * the same instance, start, seed and flip budget (no time limit), this core and
 * the Python core run with PortableRng return the same assignment and counters;
 * tests/test_native.py checks it. B5 changes speed, nothing else.
 *
 * Target hit (MSE26_RHO_PLAN.md §4, §7; 2026-10-28): with target_unsat >= 0, each
 * core also reports the first step at which the TRUE cost (no hard clause
 * falsified, original-weight unsatisfied soft weight <= target_unsat) held:
 * out[7] = that step (0 = the start assignment, -1 = never), out[8] = nanoseconds
 * from entry to the call to that moment (-1 = never). It is only observed: no
 * decision depends on it, so the search is unchanged.
 *
 * Built once per cluster tree by scripts/build_native.sh (plain gcc, no Python):
 *   cc -O2 -shared -fPIC -o src/native/build/libls_core.so src/native/ls_core.c
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct {
    int32_t n, m;
    const int32_t *lit_off, *lits;              /* clause c: lits[lit_off[c] .. lit_off[c+1]) */
    const uint8_t *is_hard;                      /* m */
    const int64_t *w;                            /* m, 0 for hard clauses */
    const int32_t *occ_off, *occ_ci, *occ_d;     /* var v: [occ_off[v], occ_off[v+1]), v in 1..n */
    const int32_t *cvd_off, *cvd_u, *cvd_d;      /* clause c: (u, d), u ascending */
    const int32_t *nb_off, *nb;                  /* var v: sorted neighbours; NULL = lean tables */
    int64_t total_soft;
    int32_t has_hard;
    const int32_t *aocc_off, *aocc_ci;           /* lean: var v: every clause containing it */
    const int32_t *cv_off, *cv_u;                /* lean: clause c: its distinct variables */
} Inst;

/* CC after flipping v (docs/current2/LONG_CLAUSE_RULE_DESIGN.md L1): every variable
 * sharing a clause with v becomes free, v itself blocked. Full tables walk nbrs; lean
 * ones walk v's clauses, which reaches the same set plus v, cleared last -- the same
 * conf state either way. */
static inline void cc_touch(const Inst *I, uint8_t *conf, int32_t v) {
    if (I->nb_off) {
        conf[v] = 0;
        for (int32_t k = I->nb_off[v]; k < I->nb_off[v + 1]; k++) conf[I->nb[k]] = 1;
    } else {
        for (int32_t k = I->aocc_off[v]; k < I->aocc_off[v + 1]; k++) {
            int32_t ci = I->aocc_ci[k];
            for (int32_t q = I->cv_off[ci]; q < I->cv_off[ci + 1]; q++) conf[I->cv_u[q]] = 1;
        }
        conf[v] = 0;
    }
}

/* ---------------------------------------------------------------- rng */
typedef struct { uint64_t s[4]; } Rng;

static uint64_t splitmix_next(uint64_t *x) {
    uint64_t z;
    *x += 0x9E3779B97F4A7C15ULL;
    z = *x;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
static void rng_seed(Rng *r, uint64_t seed) {
    uint64_t x = seed;
    for (int i = 0; i < 4; i++) r->s[i] = splitmix_next(&x);
}
static inline uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static inline uint64_t rng_next(Rng *r) {
    uint64_t *s = r->s;
    uint64_t result = rotl(s[1] * 5, 7) * 9;
    uint64_t t = s[1] << 17;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3];
    s[2] ^= t;
    s[3] = rotl(s[3], 45);
    return result;
}
static inline int64_t randbelow(Rng *r, int64_t n) { return (int64_t)((rng_next(r) >> 11) % (uint64_t)n); }
static inline double rnd(Rng *r) { return (double)(rng_next(r) >> 11) * (1.0 / 9007199254740992.0); }

/* exposed for the RNG equality test */
void rng_stream(uint64_t seed, int64_t count, uint64_t *out) {
    Rng r; rng_seed(&r, seed);
    for (int64_t i = 0; i < count; i++) out[i] = rng_next(&r);
}

static double now_s(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + 1e-9 * (double)ts.tv_nsec;
}

/* sorted int32 list (walksat: v2's bisect lists) */
static void sl_insert(int32_t *a, int32_t *len, int32_t x) {
    int32_t lo = 0, hi = *len;
    while (lo < hi) { int32_t mid = (lo + hi) >> 1; if (a[mid] < x) lo = mid + 1; else hi = mid; }
    memmove(a + lo + 1, a + lo, (size_t)(*len - lo) * sizeof(int32_t));
    a[lo] = x; (*len)++;
}
static void sl_delete(int32_t *a, int32_t *len, int32_t x) {
    int32_t lo = 0, hi = *len;
    while (lo < hi) { int32_t mid = (lo + hi) >> 1; if (a[mid] < x) lo = mid + 1; else hi = mid; }
    memmove(a + lo, a + lo + 1, (size_t)(*len - lo - 1) * sizeof(int32_t));
    (*len)--;
}

typedef struct { int32_t *a; int64_t len, cap; } Vec;
static void vec_push(Vec *v, int32_t x) {
    if (v->len == v->cap) { v->cap = v->cap ? 2 * v->cap : 1024; v->a = (int32_t *)realloc(v->a, (size_t)v->cap * sizeof(int32_t)); }
    v->a[v->len++] = x;
}

/* ============================================================ walksat_v3 */
/* out: [flips, applied, soft, hv, tabu_skips, tabu_aspirations, tabu_all_blocked] */
int ls_walksat(const Inst *I, uint8_t *A, uint64_t seed, int64_t max_flips, double tlim,
               double noise, int hard_safe, int noops, int tabu, int64_t tenure, int64_t tenure_rand,
               int64_t target_unsat, int64_t *out)
{
    const double t_in = now_s();
    const int32_t n = I->n, m = I->m;
    Rng R; rng_seed(&R, seed);
    int32_t *tc = (int32_t *)calloc((size_t)m + 1, sizeof(int32_t));
    int32_t *uh = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    int32_t *us = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    int64_t *last_flip = (int64_t *)malloc(((size_t)n + 1) * sizeof(int64_t));
    int64_t *tabu_until = (int64_t *)calloc((size_t)n + 1, sizeof(int64_t));
    uint8_t *conf = (uint8_t *)malloc((size_t)n + 1);
    int32_t maxlen = 1;
    for (int32_t c = 0; c < m; c++) { int32_t L = I->lit_off[c + 1] - I->lit_off[c]; if (L > maxlen) maxlen = L; }
    int32_t *cand = (int32_t *)malloc((size_t)maxlen * sizeof(int32_t));
    int32_t *allowed = (int32_t *)malloc((size_t)maxlen * sizeof(int32_t));
    if (!tc || !uh || !us || !last_flip || !tabu_until || !conf || !cand || !allowed) return -1;
    for (int32_t v = 0; v <= n; v++) { last_flip[v] = -1; conf[v] = 1; }
    int32_t nh = 0, ns = 0;
    int64_t usw = 0;
    for (int32_t c = 0; c < m; c++) {
        int32_t t = 0;
        for (int32_t k = I->lit_off[c]; k < I->lit_off[c + 1]; k++) {
            int32_t l = I->lits[k];
            if (l > 0) { if (A[l]) t++; } else if (!A[-l]) t++;
        }
        tc[c] = t;
        if (t == 0) { if (I->is_hard[c]) uh[nh++] = c; else { us[ns++] = c; usw += I->w[c]; } }
    }
    const int tabu_on = tabu != 0, use_cc = tabu == 2;
    int64_t skips = 0, asp = 0, alltabu = 0;
    int64_t best_hv = nh, best_soft = I->total_soft - usw;
    Vec trail = {0, 0, 0};
    int64_t applied = 0, num_flips = 0;
    int64_t hit = -1, hit_ns = -1;
#define HIT_CHECK(STEP, NH, USW) do { if (hit < 0 && target_unsat >= 0 && (NH) == 0 && (USW) <= target_unsat) { \
        hit = (STEP); hit_ns = (int64_t)((now_s() - t_in) * 1e9); } } while (0)
    HIT_CHECK(0, nh, usw);
    double t0 = now_s();

#define BLOCKED(v) (use_cc ? !conf[v] : (num_flips <= tabu_until[v]))
#define GAIN_SOFT(v, G) do { int sgn_ = A[v] ? -1 : 1; G = 0; \
        for (int32_t k_ = I->occ_off[v]; k_ < I->occ_off[(v) + 1]; k_++) { int32_t ci_ = I->occ_ci[k_]; \
            int32_t old_ = tc[ci_], nw_ = old_ + sgn_ * I->occ_d[k_]; \
            if (old_ > 0) { if (nw_ == 0) G -= I->w[ci_]; } else if (nw_ > 0) G += I->w[ci_]; } } while (0)
#define EFFECT(v, G, DH) do { int sgn_ = A[v] ? -1 : 1; G = 0; DH = 0; \
        for (int32_t k_ = I->occ_off[v]; k_ < I->occ_off[(v) + 1]; k_++) { int32_t ci_ = I->occ_ci[k_]; \
            int32_t old_ = tc[ci_], nw_ = old_ + sgn_ * I->occ_d[k_]; \
            if (I->is_hard[ci_]) { if (old_ > 0) { if (nw_ == 0) DH++; } else if (nw_ > 0) DH--; } \
            else if (old_ > 0) { if (nw_ == 0) G -= I->w[ci_]; } else if (nw_ > 0) G += I->w[ci_]; } } while (0)

    while ((noops ? num_flips : applied) < max_flips && !(tlim >= 0 && (now_s() - t0) >= tlim)) {
        num_flips++;
        int32_t target;
        if (nh) target = uh[randbelow(&R, nh)];
        else if (ns) target = us[randbelow(&R, ns)];
        else break;
        int32_t L = I->lit_off[target + 1] - I->lit_off[target];
        for (int32_t i = 0; i < L; i++) { int32_t l = I->lits[I->lit_off[target] + i]; cand[i] = l > 0 ? l : -l; }
        for (int32_t i = L - 1; i > 0; i--) { int32_t j = (int32_t)randbelow(&R, i + 1); int32_t x = cand[i]; cand[i] = cand[j]; cand[j] = x; }
        int explore = rnd(&R) < noise;
        int32_t chosen = 0;

        if (!I->has_hard) {
            if (!tabu_on) {
                if (explore) chosen = cand[0];
                else {
                    int have = 0; int64_t bg = 0;
                    for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; int64_t g; GAIN_SOFT(v, g);
                        if (!have || g > bg) { bg = g; chosen = v; have = 1; } }
                }
            } else {
                int64_t soft_now = I->total_soft - usw;
                if (explore) {
                    for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; if (BLOCKED(v)) { skips++; continue; } chosen = v; break; }
                } else {
                    int have = 0; int64_t bg = 0;
                    for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; int64_t g; GAIN_SOFT(v, g);
                        if (BLOCKED(v)) { if (best_hv == 0 && soft_now + g > best_soft) asp++; else { skips++; continue; } }
                        if (!have || g > bg) { bg = g; chosen = v; have = 1; } }
                }
                if (!chosen) { alltabu++; int32_t b = 0;
                    for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; if (!b || last_flip[v] < last_flip[b]) b = v; }
                    chosen = b; }
            }
        } else if (nh) {
            int have = 0; int64_t bdh = 0, bg = 0;
            for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; int64_t g, dh; EFFECT(v, g, dh);
                if (dh >= 0) continue;
                if (!have || dh < bdh || (dh == bdh && g > bg)) { bdh = dh; bg = g; chosen = v; have = 1; } }
            if (!chosen && explore && I->is_hard[target] && tc[target] == 0) {
                for (int32_t k = I->lit_off[target]; k < I->lit_off[target + 1]; k++) {
                    int32_t l = I->lits[k]; int32_t v = l > 0 ? l : -l;
                    int makes_true = (l > 0 && !A[v]) || (l < 0 && A[v]);
                    if (makes_true) { int64_t g, dh; EFFECT(v, g, dh); if (!hard_safe || dh < 0) { chosen = v; break; } }
                }
            }
        } else {
            if (!tabu_on) {
                if (explore) {
                    for (int32_t i = 0; i < L; i++) {
                        int32_t v = cand[i]; int64_t g, br; EFFECT(v, g, br);
                        if (hard_safe && br > 0) continue;
                        chosen = v;
                        break;
                    }
                } else {
                    int have = 0; int64_t bg = 0, bb = 0;
                    for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; int64_t g, br; EFFECT(v, g, br);
                        if (hard_safe && br > 0) continue;
                        if (!have || g > bg || (g == bg && br < bb)) { bg = g; bb = br; chosen = v; have = 1; } }
                }
            } else {
                int64_t soft_now = I->total_soft - usw;
                int32_t na = 0;
                if (explore) {
                    for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; int64_t g, br; EFFECT(v, g, br);
                        if (hard_safe && br > 0) continue;
                        allowed[na++] = v;
                        if (BLOCKED(v)) { skips++; continue; }
                        chosen = v; break; }
                } else {
                    int have = 0; int64_t bg = 0, bb = 0;
                    for (int32_t i = 0; i < L; i++) { int32_t v = cand[i]; int64_t g, br; EFFECT(v, g, br);
                        if (hard_safe && br > 0) continue;
                        allowed[na++] = v;
                        if (BLOCKED(v)) { if (br < best_hv || (br == best_hv && soft_now + g > best_soft)) asp++; else { skips++; continue; } }
                        if (!have || g > bg || (g == bg && br < bb)) { bg = g; bb = br; chosen = v; have = 1; } }
                }
                if (!chosen && na) { alltabu++; int32_t b = 0;
                    for (int32_t i = 0; i < na; i++) { int32_t v = allowed[i]; if (!b || last_flip[v] < last_flip[b]) b = v; }
                    chosen = b; }
            }
        }

        if (chosen) {
            int32_t v = chosen;
            A[v] = !A[v];
            int sgn = A[v] ? 1 : -1;
            for (int32_t k = I->occ_off[v]; k < I->occ_off[v + 1]; k++) {
                int32_t ci = I->occ_ci[k]; int32_t old = tc[ci], nw = old + sgn * I->occ_d[k];
                tc[ci] = nw;
                if (old == 0) { if (nw > 0) { if (I->is_hard[ci]) sl_delete(uh, &nh, ci); else { sl_delete(us, &ns, ci); usw -= I->w[ci]; } } }
                else if (nw == 0) { if (I->is_hard[ci]) sl_insert(uh, &nh, ci); else { sl_insert(us, &ns, ci); usw += I->w[ci]; } }
            }
            applied++;
            vec_push(&trail, v);
            if (tabu_on) {
                last_flip[v] = num_flips;
                if (use_cc) cc_touch(I, conf, v);
                else tabu_until[v] = num_flips + tenure + (tenure_rand > 0 ? randbelow(&R, tenure_rand + 1) : 0);
            }
        }
        int64_t hv = nh;
        if (hv <= best_hv) {
            int64_t soft_now = I->total_soft - usw;
            if (hv < best_hv || soft_now > best_soft) { best_hv = hv; best_soft = soft_now; trail.len = 0; }
        }
        HIT_CHECK(num_flips, nh, usw);
    }
    int64_t hv = nh, soft = I->total_soft - usw;
    if (best_hv == 0) { soft = best_soft; hv = 0; }
    if (best_hv <= hv) for (int64_t i = 0; i < trail.len; i++) A[trail.a[i]] = !A[trail.a[i]];
    out[0] = num_flips; out[1] = applied; out[2] = soft; out[3] = hv;
    out[4] = skips; out[5] = asp; out[6] = alltabu; out[7] = hit; out[8] = hit_ns;
    free(tc); free(uh); free(us); free(last_flip); free(tabu_until); free(conf); free(cand); free(allowed); free(trail.a);
    return 0;
#undef BLOCKED
#undef HIT_CHECK
#undef GAIN_SOFT
#undef EFFECT
}

/* ================================================================ dls_v3 */
typedef struct {
    const Inst *I;
    uint8_t *A;
    int32_t *tc;
    int64_t *dw, *score;
    int32_t *fh, *fs, *fpos; int32_t nfh, nfs;
    int32_t *D, *dpos; int32_t nD;
    int64_t usw;
} Dls;

static inline int ind(const Dls *S, int32_t ci, int32_t u, int32_t d) {
    int32_t old = S->tc[ci], nw = S->A[u] ? old - d : old + d;
    if (old == 0) return nw > 0 ? 1 : 0;
    return nw == 0 ? -1 : 0;
}
static void f_add(Dls *S, int32_t ci) {
    if (S->I->is_hard[ci]) { S->fpos[ci] = S->nfh; S->fh[S->nfh++] = ci; }
    else { S->fpos[ci] = S->nfs; S->fs[S->nfs++] = ci; }
}
static void f_del(Dls *S, int32_t ci) {
    int32_t *lst; int32_t *len;
    if (S->I->is_hard[ci]) { lst = S->fh; len = &S->nfh; } else { lst = S->fs; len = &S->nfs; }
    int32_t p = S->fpos[ci], last = lst[--(*len)];
    if (last != ci) { lst[p] = last; S->fpos[last] = p; }
    S->fpos[ci] = -1;
}
static void d_update(Dls *S, int32_t u) {
    int32_t p = S->dpos[u];
    if (S->score[u] > 0) { if (p < 0) { S->dpos[u] = S->nD; S->D[S->nD++] = u; } }
    else if (p >= 0) { int32_t last = S->D[--S->nD]; if (last != u) { S->D[p] = last; S->dpos[last] = p; } S->dpos[u] = -1; }
}
static void adjust(Dls *S, int32_t ci, int64_t delta) {
    const Inst *I = S->I;
    S->dw[ci] += delta;
    for (int32_t k = I->cvd_off[ci]; k < I->cvd_off[ci + 1]; k++) S->score[I->cvd_u[k]] += delta * ind(S, ci, I->cvd_u[k], I->cvd_d[k]);
    for (int32_t k = I->cvd_off[ci]; k < I->cvd_off[ci + 1]; k++) d_update(S, I->cvd_u[k]);
}

/* out: [steps, applied, best_hv, best_unsat, stuck, smooths, cc_blocked] */
int ls_dls(const Inst *I, uint8_t *A, uint64_t seed, int64_t max_flips, double tlim,
           int64_t t, double sp, int64_t zeta, int64_t h_inc, int64_t *dw_io, int cc,
           int64_t target_unsat, int64_t *out)
{
    const double t_in = now_s();
    const int32_t n = I->n, m = I->m;
    Rng R; rng_seed(&R, seed);
    Dls S; S.I = I; S.A = A;
    S.tc = (int32_t *)calloc((size_t)m + 1, sizeof(int32_t));
    int64_t *dw_own = NULL;
    if (dw_io) S.dw = dw_io;
    else { dw_own = (int64_t *)malloc(((size_t)m + 1) * sizeof(int64_t)); S.dw = dw_own;
        for (int32_t c = 0; c < m; c++) S.dw[c] = I->is_hard[c] ? 1 : I->w[c]; }
    S.score = (int64_t *)calloc((size_t)n + 1, sizeof(int64_t));
    S.fh = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    S.fs = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    S.fpos = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    S.D = (int32_t *)malloc(((size_t)n + 1) * sizeof(int32_t));
    S.dpos = (int32_t *)malloc(((size_t)n + 1) * sizeof(int32_t));
    int64_t *last_flip = (int64_t *)malloc(((size_t)n + 1) * sizeof(int64_t));
    uint8_t *conf = (uint8_t *)malloc((size_t)n + 1);
    if (!S.tc || !S.dw || !S.score || !S.fh || !S.fs || !S.fpos || !S.D || !S.dpos || !last_flip || !conf) return -1;
    S.nfh = S.nfs = S.nD = 0; S.usw = 0;
    for (int32_t v = 0; v <= n; v++) { S.dpos[v] = -1; last_flip[v] = -1; conf[v] = 1; }
    for (int32_t c = 0; c < m; c++) {
        int32_t k2 = 0;
        for (int32_t k = I->lit_off[c]; k < I->lit_off[c + 1]; k++) { int32_t l = I->lits[k]; if (l > 0) { if (A[l]) k2++; } else if (!A[-l]) k2++; }
        S.tc[c] = k2; S.fpos[c] = -1;
    }
    for (int32_t c = 0; c < m; c++) if (S.tc[c] == 0) { f_add(&S, c); if (!I->is_hard[c]) S.usw += I->w[c]; }
    for (int32_t c = 0; c < m; c++) { int64_t wc = S.dw[c];
        for (int32_t k = I->cvd_off[c]; k < I->cvd_off[c + 1]; k++) S.score[I->cvd_u[k]] += wc * ind(&S, c, I->cvd_u[k], I->cvd_d[k]); }
    for (int32_t v = 1; v <= n; v++) d_update(&S, v);

    int64_t stuck = 0, smooths = 0, ccb = 0;
    int64_t best_hv = S.nfh, best_unsat = S.usw;
    Vec trail = {0, 0, 0};
    int64_t applied = 0, steps = 0;
    int64_t hit = -1, hit_ns = -1;
#define HIT_CHECK(STEP, NH, USW) do { if (hit < 0 && target_unsat >= 0 && (NH) == 0 && (USW) <= target_unsat) { \
        hit = (STEP); hit_ns = (int64_t)((now_s() - t_in) * 1e9); } } while (0)
    HIT_CHECK(0, S.nfh, S.usw);
    double t0 = now_s();
#define BETTER(x, b) ((b) < 0 || S.score[x] > S.score[b] || (S.score[x] == S.score[b] && last_flip[x] < last_flip[b]))

    while (applied < max_flips && !(tlim >= 0 && (now_s() - t0) >= tlim)) {
        steps++;
        if (!S.nfh && !S.nfs) break;
        int32_t bv = -1;
        if (S.nD) {
            if (!cc) {
                for (int64_t i = 0; i < t; i++) { int32_t v = S.D[randbelow(&R, S.nD)]; if (BETTER(v, bv)) bv = v; }
            } else {
                int32_t ba = -1;
                for (int64_t i = 0; i < t; i++) { int32_t v = S.D[randbelow(&R, S.nD)];
                    if (BETTER(v, ba)) ba = v;
                    if (!conf[v]) { ccb++; continue; }
                    if (BETTER(v, bv)) bv = v; }
                if (bv < 0) bv = ba;
            }
        } else {
            stuck++;
            if (rnd(&R) < sp) {
                smooths++;
                for (int32_t ci = 0; ci < m; ci++) if (S.tc[ci] > 0 && S.dw[ci] > 1) adjust(&S, ci, -(I->is_hard[ci] ? h_inc : 1));
            } else {
                for (int32_t i = 0; i < S.nfh; i++) adjust(&S, S.fh[i], h_inc);
                for (int32_t i = 0; i < S.nfs; i++) { int32_t ci = S.fs[i]; if (S.dw[ci] < zeta) adjust(&S, ci, 1); }
            }
            int32_t ci = S.nfh ? S.fh[randbelow(&R, S.nfh)] : S.fs[randbelow(&R, S.nfs)];
            int32_t ba = -1;
            for (int32_t k = I->cvd_off[ci]; k < I->cvd_off[ci + 1]; k++) { int32_t u = I->cvd_u[k];
                if (BETTER(u, ba)) ba = u;
                if (cc && !conf[u]) continue;
                if (BETTER(u, bv)) bv = u; }
            if (bv < 0) bv = ba;
            if (bv < 0) break;
        }
        /* flip bv */
        {
            int32_t v = bv;
            for (int32_t k = I->occ_off[v]; k < I->occ_off[v + 1]; k++) { int32_t ci = I->occ_ci[k]; int64_t wc = S.dw[ci];
                for (int32_t q = I->cvd_off[ci]; q < I->cvd_off[ci + 1]; q++) S.score[I->cvd_u[q]] -= wc * ind(&S, ci, I->cvd_u[q], I->cvd_d[q]); }
            A[v] = !A[v];
            int sgn = A[v] ? 1 : -1;
            for (int32_t k = I->occ_off[v]; k < I->occ_off[v + 1]; k++) {
                int32_t ci = I->occ_ci[k]; int32_t old = S.tc[ci], nw = old + sgn * I->occ_d[k];
                S.tc[ci] = nw;
                if (old == 0 && nw > 0) { f_del(&S, ci); if (!I->is_hard[ci]) S.usw -= I->w[ci]; }
                else if (old > 0 && nw == 0) { f_add(&S, ci); if (!I->is_hard[ci]) S.usw += I->w[ci]; }
                int64_t wc = S.dw[ci];
                for (int32_t q = I->cvd_off[ci]; q < I->cvd_off[ci + 1]; q++) S.score[I->cvd_u[q]] += wc * ind(&S, ci, I->cvd_u[q], I->cvd_d[q]);
            }
            for (int32_t k = I->occ_off[v]; k < I->occ_off[v + 1]; k++) { int32_t ci = I->occ_ci[k];
                for (int32_t q = I->cvd_off[ci]; q < I->cvd_off[ci + 1]; q++) d_update(&S, I->cvd_u[q]); }
        }
        applied++;
        vec_push(&trail, bv);
        last_flip[bv] = steps;
        if (cc) cc_touch(I, conf, bv);
        int64_t hv = S.nfh;
        if (hv < best_hv || (hv == best_hv && S.usw < best_unsat)) { best_hv = hv; best_unsat = S.usw; trail.len = 0; }
        HIT_CHECK(steps, S.nfh, S.usw);
    }
#undef BETTER
#undef HIT_CHECK
    for (int64_t i = 0; i < trail.len; i++) A[trail.a[i]] = !A[trail.a[i]];
    out[0] = steps; out[1] = applied; out[2] = best_hv; out[3] = best_unsat;
    out[4] = stuck; out[5] = smooths; out[6] = ccb; out[7] = hit; out[8] = hit_ns;
    free(S.tc); free(dw_own); free(S.score); free(S.fh); free(S.fs); free(S.fpos); free(S.D); free(S.dpos);
    free(last_flip); free(conf); free(trail.a);
    return 0;
}


/* ======================================================= compact instance (C1)
 * docs/current2/COMPILED_MEMETIC_PLAN.md §4 C1 (2026-10-28). The instance as flat
 * arrays (CSR), parsed here instead of into Python Clause objects, and the polish
 * tables built here from them instead of from Python lists. Every rule and order is
 * the Python one (src/sat/cnf.py WCNF.parse_dimacs; src/sat/walksat_v2.py _Static;
 * src/sat/ls_v3.py _V3Static; src/native/native.py NativeCore); tests/test_compact.py
 * checks them element by element. Nothing here draws a random number. */

typedef struct {
    int32_t n, m;
    int64_t top;                 /* WCNF.hard_weight */
    int32_t is_wcnf, fmt;        /* fmt: 0 legacy (p line), 1 new (MSE 2022+) */
    int64_t nlits;
    int32_t *lit_off;            /* m + 1 */
    int32_t *lits;               /* nlits */
    int64_t *w;                  /* m: Clause.weight (new-format hard clauses: top) */
    uint8_t *hard;               /* m */
} CInst;

typedef struct { char *a; int64_t len, cap; size_t es; } GVec;
static int gv_need(GVec *v, int64_t need) {
    if (need <= v->cap) return 0;
    int64_t c = v->cap ? v->cap : 4096;
    while (c < need) c += c / 2 + 1;
    char *p = (char *)realloc(v->a, (size_t)c * v->es);
    if (!p) return -1;
    v->a = p; v->cap = c; return 0;
}
static void gv_shrink(GVec *v) {
    if (v->len > 0 && v->len < v->cap) { char *p = (char *)realloc(v->a, (size_t)v->len * v->es); if (p) { v->a = p; v->cap = v->len; } }
}

/* Python's str.strip()/split() whitespace, ASCII part */
static inline int is_ws(unsigned char ch) { return ch == ' ' || (ch >= 9 && ch <= 13) || (ch >= 28 && ch <= 31); }

/* int(token) for a plain token: optional sign, decimal digits. 0 = ok, -1 = not an
 * integer, -2 = outside int64 (Python would accept it; we refuse, plan §6). */
static int parse_i64(const char *s, const char *e, int64_t *out) {
    int neg = 0;
    if (s < e && (*s == '+' || *s == '-')) { neg = *s == '-'; s++; }
    if (s >= e) return -1;
    uint64_t v = 0;
    for (; s < e; s++) {
        if (*s < '0' || *s > '9') return -1;
        unsigned d = (unsigned)(*s - '0');
        if (v > (UINT64_C(9223372036854775808) - d) / 10) return -2;
        v = v * 10 + d;
    }
    if (!neg && v > (uint64_t)INT64_MAX) return -2;
    *out = neg ? (int64_t)(0 - v) : (int64_t)v;
    return 0;
}

typedef struct { const char **s; const char **e; int64_t n, cap; } Toks;
static int split_line(char *line, Toks *t) {
    t->n = 0;
    char *p = line;
    for (;;) {
        while (*p && is_ws((unsigned char)*p)) p++;
        if (!*p) break;
        char *q = p;
        while (*q && !is_ws((unsigned char)*q)) q++;
        if (t->n == t->cap) {
            int64_t c = t->cap ? 2 * t->cap : 256;
            const char **a = (const char **)realloc((void *)t->s, (size_t)c * sizeof(char *));
            const char **b = (const char **)realloc((void *)t->e, (size_t)c * sizeof(char *));
            if (!a || !b) return -1;
            t->s = a; t->e = b; t->cap = c;
        }
        t->s[t->n] = p; t->e[t->n] = q; t->n++;
        p = q;
    }
    return 0;
}
static inline int tok_is(const Toks *t, int64_t i, const char *lit) {
    size_t L = strlen(lit);
    return (size_t)(t->e[i] - t->s[i]) == L && memcmp(t->s[i], lit, L) == 0;
}
static inline const char *first_nonws(const char *p) { while (*p && is_ws((unsigned char)*p)) p++; return p; }

#define PERR(...) do { snprintf(err, (size_t)errlen, __VA_ARGS__); goto fail; } while (0)

/* WCNF.parse_dimacs: 0 = ok; else err holds the reason (ValueError text). */
int wcnf_parse(const char *path, CInst *out, char *err, int errlen) {
    memset(out, 0, sizeof(*out));
    FILE *f = fopen(path, "rb");
    if (!f) { snprintf(err, (size_t)errlen, "%s: cannot open", path); return 1; }
    char *line = NULL; size_t lcap = 0; ssize_t len;
    Toks T = {0, 0, 0, 0};
    GVec off = {0, 0, 0, sizeof(int32_t)}, L = {0, 0, 0, sizeof(int32_t)}, W = {0, 0, 0, sizeof(int64_t)},
         H = {0, 0, 0, sizeof(uint8_t)};
    int fmt = -1;
    while ((len = getline(&line, &lcap, f)) != -1) {        /* _detect_format */
        const char *p = first_nonws(line);
        if (!*p || *p == 'c' || *p == '%') continue;
        fmt = (*p == 'p') ? 0 : 1;
        break;
    }
    if (fmt < 0) PERR("%s: no problem line and no clauses -- empty instance", path);
    rewind(f);
    if (gv_need(&off, 1)) PERR("out of memory");
    ((int32_t *)off.a)[0] = 0; off.len = 1;
    int64_t lineno = 0, max_var = 0;
    /* legacy state */
    int have_n = 0, have_m = 0, is_wcnf = 0, top_set = 0;
    int64_t n_vars = 0, top = 0, soft_total = 0;
    while ((len = getline(&line, &lcap, f)) != -1) {
        lineno++;
        const char *p = first_nonws(line);
        if (!*p) continue;
        if (fmt == 1) {
            if (*p == 'c') continue;
            if (split_line(line, &T)) PERR("out of memory");
            if (!tok_is(&T, T.n - 1, "0")) PERR("%s:%lld: clause is not 0-terminated", path, (long long)lineno);
            int64_t nb = T.n - 1;
            if (nb == 0) PERR("%s:%lld: bare '0' line, not a clause", path, (long long)lineno);
            int hard; int64_t wt = 0;
            if (tok_is(&T, 0, "h")) hard = 1;
            else {
                hard = 0;
                int r = parse_i64(T.s[0], T.e[0], &wt);
                if (r == -1) PERR("%s:%lld: expected 'h' or an integer weight", path, (long long)lineno);
                if (r == -2) PERR("%s:%lld: weight outside int64", path, (long long)lineno);
                if (wt < 0) PERR("%s:%lld: negative soft weight %lld", path, (long long)lineno, (long long)wt);
                if (soft_total > INT64_MAX - 1 - wt) PERR("%s: total soft weight outside int64", path);
                soft_total += wt;
            }
            if (gv_need(&L, L.len + nb - 1)) PERR("out of memory");
            for (int64_t i = 1; i < nb; i++) {
                int64_t x;
                int r = parse_i64(T.s[i], T.e[i], &x);
                if (r) PERR("%s:%lld: non-integer literal", path, (long long)lineno);
                if (x == 0) PERR("%s:%lld: embedded 0 before end of clause", path, (long long)lineno);
                int64_t a = x < 0 ? -x : x;
                if (a > INT32_MAX) PERR("%s:%lld: variable index outside int32", path, (long long)lineno);
                if (a > max_var) max_var = a;
                ((int32_t *)L.a)[L.len++] = (int32_t)x;
            }
            if (L.len > INT32_MAX) PERR("%s: more than 2^31 literals (32-bit offsets)", path);
            if (gv_need(&off, off.len + 1) || gv_need(&W, W.len + 1) || gv_need(&H, H.len + 1)) PERR("out of memory");
            ((int32_t *)off.a)[off.len++] = (int32_t)L.len;
            ((int64_t *)W.a)[W.len++] = wt;
            ((uint8_t *)H.a)[H.len++] = (uint8_t)hard;
        } else {
            if (*p == 'c' || *p == '%' || *p == '0') continue;
            if (split_line(line, &T)) PERR("out of memory");
            if (*p == 'p') {
                if (T.n < 4) PERR("Bad problem line");
                size_t fl = (size_t)(T.e[1] - T.s[1]);
                char fm[8] = {0};
                if (fl < sizeof(fm)) for (size_t i = 0; i < fl; i++) { char ch = T.s[1][i]; fm[i] = (ch >= 'A' && ch <= 'Z') ? (char)(ch + 32) : ch; }
                int64_t a, b;
                if (parse_i64(T.s[2], T.e[2], &a) || parse_i64(T.s[3], T.e[3], &b)) PERR("Bad problem line");
                n_vars = a; have_n = 1; have_m = 1;
                if (fl < sizeof(fm) && strcmp(fm, "wcnf") == 0) {
                    is_wcnf = 1;
                    if (T.n >= 5) { if (parse_i64(T.s[4], T.e[4], &top)) PERR("Bad problem line"); }
                    else top = INT64_C(1000000000000000000);
                    top_set = 1;
                } else if (!(fl < sizeof(fm) && strcmp(fm, "cnf") == 0)) PERR("Unknown DIMACS format");
                continue;
            }
            int64_t wt, i0;
            int hard;
            if (is_wcnf) {
                if (parse_i64(T.s[0], T.e[0], &wt)) PERR("%s:%lld: bad weight", path, (long long)lineno);
                i0 = 1;
            } else {
                if (!top_set) { top = 1000000000; top_set = 1; }
                wt = 1; i0 = 0;
            }
            if (gv_need(&L, L.len + T.n)) PERR("out of memory");
            for (int64_t i = i0; i < T.n; i++) {
                if (tok_is(&T, i, "0")) continue;
                int64_t x;
                if (parse_i64(T.s[i], T.e[i], &x)) PERR("%s:%lld: non-integer literal", path, (long long)lineno);
                if (x == 0) PERR("%s:%lld: literal 0 (refused; plan §6)", path, (long long)lineno);
                int64_t a = x < 0 ? -x : x;
                if (a > INT32_MAX) PERR("%s:%lld: variable index outside int32", path, (long long)lineno);
                if (a > max_var) max_var = a;
                ((int32_t *)L.a)[L.len++] = (int32_t)x;
            }
            hard = is_wcnf ? (wt >= top) : 0;
            if (L.len > INT32_MAX) PERR("%s: more than 2^31 literals (32-bit offsets)", path);
            if (gv_need(&off, off.len + 1) || gv_need(&W, W.len + 1) || gv_need(&H, H.len + 1)) PERR("out of memory");
            ((int32_t *)off.a)[off.len++] = (int32_t)L.len;
            ((int64_t *)W.a)[W.len++] = wt;
            ((uint8_t *)H.a)[H.len++] = (uint8_t)hard;
        }
    }
    if (W.len > INT32_MAX) PERR("%s: more than 2^31 clauses", path);
    if (fmt == 1) {
        if (W.len == 0) PERR("%s: new-format WCNF with no clauses", path);
        top = soft_total + 1;
        for (int64_t c = 0; c < W.len; c++) if (((uint8_t *)H.a)[c]) ((int64_t *)W.a)[c] = top;
        n_vars = max_var; is_wcnf = 1;
    } else {
        if (!have_n || !have_m) PERR("Missing 'p' header");
        if (max_var > n_vars) PERR("%s: literal %lld above n_vars %lld", path, (long long)max_var, (long long)n_vars);
        if (n_vars > INT32_MAX || n_vars < 0) PERR("%s: n_vars outside int32", path);
        if (!top_set) top = 1000000000;
    }
    gv_shrink(&L); gv_shrink(&off); gv_shrink(&W); gv_shrink(&H);
    if (!L.a) { L.a = (char *)malloc(sizeof(int32_t)); }
    if (!W.a) { W.a = (char *)malloc(sizeof(int64_t)); H.a = (char *)malloc(1); }
    out->n = (int32_t)n_vars; out->m = (int32_t)W.len; out->top = top; out->is_wcnf = is_wcnf; out->fmt = fmt;
    out->nlits = L.len; out->lit_off = (int32_t *)off.a; out->lits = (int32_t *)L.a;
    out->w = (int64_t *)W.a; out->hard = (uint8_t *)H.a;
    free(line); free((void *)T.s); free((void *)T.e); fclose(f);
    return 0;
fail:
    free(line); free((void *)T.s); free((void *)T.e); fclose(f);
    free(off.a); free(L.a); free(W.a); free(H.a);
    memset(out, 0, sizeof(*out));
    return 1;
}
#undef PERR

void wcnf_free(CInst *c) {
    free(c->lit_off); free(c->lits); free(c->w); free(c->hard);
    memset(c, 0, sizeof(*c));
}

/* A CInst from arrays the caller filled (a kernel's WCNF): takes ownership of nothing;
 * copies. */
int wcnf_from_arrays(int32_t n, int32_t m, int64_t top, int32_t is_wcnf, const int32_t *lit_off,
                     const int32_t *lits, const int64_t *w, const uint8_t *hard, CInst *out) {
    memset(out, 0, sizeof(*out));
    int64_t nl = lit_off[m];
    out->lit_off = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    out->lits = (int32_t *)malloc((size_t)(nl ? nl : 1) * sizeof(int32_t));
    out->w = (int64_t *)malloc((size_t)(m ? m : 1) * sizeof(int64_t));
    out->hard = (uint8_t *)malloc((size_t)(m ? m : 1));
    if (!out->lit_off || !out->lits || !out->w || !out->hard) { wcnf_free(out); return 1; }
    memcpy(out->lit_off, lit_off, ((size_t)m + 1) * sizeof(int32_t));
    if (nl) memcpy(out->lits, lits, (size_t)nl * sizeof(int32_t));
    if (m) { memcpy(out->w, w, (size_t)m * sizeof(int64_t)); memcpy(out->hard, hard, (size_t)m); }
    out->n = n; out->m = m; out->top = top; out->is_wcnf = is_wcnf; out->fmt = -1; out->nlits = nl;
    return 0;
}

static int cmp_i32(const void *a, const void *b) { int32_t x = *(const int32_t *)a, y = *(const int32_t *)b; return (x > y) - (x < y); }
static void sort_i32(int32_t *a, int64_t k) {
    if (k <= 32) { for (int64_t i = 1; i < k; i++) { int32_t x = a[i]; int64_t j = i - 1; while (j >= 0 && a[j] > x) { a[j + 1] = a[j]; j--; } a[j + 1] = x; } }
    else qsort(a, (size_t)k, sizeof(int32_t), cmp_i32);
}

/* ls_v3.nbrs_plan's bound: sum over clauses of k(k-1), k = distinct variables. */
int inst_nbrs_bound(const CInst *c, int64_t *bound) {
    int32_t *stamp = (int32_t *)calloc((size_t)c->n + 1, sizeof(int32_t));
    if (!stamp) return 1;
    int64_t b = 0;
    for (int32_t ci = 0; ci < c->m; ci++) {
        int64_t k = 0;
        for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) {
            int32_t v = c->lits[q] < 0 ? -c->lits[q] : c->lits[q];
            if (stamp[v] != ci + 1) { stamp[v] = ci + 1; k++; }
        }
        b += k * (k - 1);
    }
    free(stamp); *bound = b; return 0;
}

/* The NativeCore tables (native.py NativeCore.__init__ from _Static + _V3Static),
 * built from the CSR arrays. lit_off / lits / is_hard point into c (not owned); every
 * other array is owned and freed by inst_tables_free. lean = 1: aocc/cv instead of
 * nbrs (ls_v3 _mode). Returns 0, 1 = out of memory, 2 = total soft weight overflow. */
int inst_tables(const CInst *c, int lean, Inst *I) {
    const int32_t n = c->n, m = c->m;
    memset(I, 0, sizeof(*I));
    I->n = n; I->m = m; I->lit_off = c->lit_off; I->lits = c->lits; I->is_hard = c->hard;
    int rc = 1;
    int64_t *w = (int64_t *)malloc(((size_t)m + 1) * sizeof(int64_t));
    int32_t *stamp = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    int32_t *pc = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    int32_t *nc = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    int32_t *cv_off = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    GVec CV = {0, 0, 0, sizeof(int32_t)}, CD = {0, 0, 0, sizeof(int32_t)}, HP = {0, 0, 0, 1};
    int32_t *occ_off = NULL, *occ_ci = NULL, *occ_d = NULL, *cvd_off = NULL, *cvd_u = NULL, *cvd_d = NULL;
    int32_t *aocc_off = NULL, *aocc_ci = NULL, *nb_off = NULL, *fill = NULL, *cnt_pos = NULL;
    Vec NB = {0, 0, 0};
    int32_t *gather = NULL; int64_t gcap = 0;
    if (!w || !stamp || !pc || !nc || !cv_off) goto done;
    int64_t tsoft = 0; int has_hard = 0;
    for (int32_t ci = 0; ci < m; ci++) {
        if (c->hard[ci]) { w[ci] = 0; has_hard = 1; }
        else {
            int64_t x = c->w[ci] ? c->w[ci] : 1;          /* _extract_clauses: int(cl.weight or 1) */
            w[ci] = x;
            if ((x > 0 && tsoft > INT64_MAX - x) || (x < 0 && tsoft < INT64_MIN - x)) { rc = 2; goto done; }
            tsoft += x;
        }
    }
    /* pass 1: per clause, distinct variables ascending, d = #pos - #neg, has-pos */
    cv_off[0] = 0;
    for (int32_t ci = 0; ci < m; ci++) {
        int64_t start = CV.len;
        for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) {
            int32_t l = c->lits[q], v = l < 0 ? -l : l;
            if (stamp[v] != ci + 1) {
                stamp[v] = ci + 1; pc[v] = nc[v] = 0;
                if (gv_need(&CV, CV.len + 1)) goto done;
                ((int32_t *)CV.a)[CV.len++] = v;
            }
            if (l > 0) pc[v]++; else nc[v]++;
        }
        int64_t k = CV.len - start;
        sort_i32((int32_t *)CV.a + start, k);
        if (gv_need(&CD, CV.len) || gv_need(&HP, CV.len)) goto done;
        for (int64_t i = start; i < CV.len; i++) {
            int32_t v = ((int32_t *)CV.a)[i];
            ((int32_t *)CD.a)[i] = pc[v] - nc[v];
            ((uint8_t *)HP.a)[i] = pc[v] > 0;
        }
        CD.len = HP.len = CV.len;
        if (CV.len > INT32_MAX) goto done;
        cv_off[ci + 1] = (int32_t)CV.len;
    }
    const int32_t *cv = (const int32_t *)CV.a, *cd = (const int32_t *)CD.a; const uint8_t *hp = (const uint8_t *)HP.a;
    const int64_t ne = CV.len;
    /* cvd: entries with d != 0, in clause order, variables ascending */
    cvd_off = (int32_t *)malloc(((size_t)m + 1) * sizeof(int32_t));
    int64_t nz = 0;
    for (int64_t i = 0; i < ne; i++) if (cd[i]) nz++;
    cvd_u = (int32_t *)malloc((size_t)(nz ? nz : 1) * sizeof(int32_t));
    cvd_d = (int32_t *)malloc((size_t)(nz ? nz : 1) * sizeof(int32_t));
    if (!cvd_off || !cvd_u || !cvd_d) goto done;
    { int64_t k = 0; cvd_off[0] = 0;
      for (int32_t ci = 0; ci < m; ci++) {
          for (int32_t i = cv_off[ci]; i < cv_off[ci + 1]; i++) if (cd[i]) { cvd_u[k] = cv[i]; cvd_d[k] = cd[i]; k++; }
          cvd_off[ci + 1] = (int32_t)k;
      } }
    /* occ[v]: clauses with +v (ascending), then clauses with only -v (ascending); d != 0 */
    occ_off = (int32_t *)calloc((size_t)n + 2, sizeof(int32_t));
    cnt_pos = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    fill = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    occ_ci = (int32_t *)malloc((size_t)(nz ? nz : 1) * sizeof(int32_t));
    occ_d = (int32_t *)malloc((size_t)(nz ? nz : 1) * sizeof(int32_t));
    if (!occ_off || !cnt_pos || !fill || !occ_ci || !occ_d) goto done;
    for (int64_t i = 0; i < ne; i++) if (cd[i]) { occ_off[cv[i] + 1]++; if (hp[i]) cnt_pos[cv[i]]++; }
    for (int32_t v = 1; v <= n; v++) occ_off[v + 1] += occ_off[v];
    memset(nc, 0, ((size_t)n + 1) * sizeof(int32_t));      /* nc: fill of the -v-only part */
    for (int32_t ci = 0; ci < m; ci++)
        for (int32_t i = cv_off[ci]; i < cv_off[ci + 1]; i++) {
            if (!cd[i]) continue;
            int32_t v = cv[i];
            int32_t pos = hp[i] ? occ_off[v] + fill[v]++ : occ_off[v] + cnt_pos[v] + nc[v]++;
            occ_ci[pos] = ci; occ_d[pos] = cd[i];
        }
    /* aocc[v]: every clause containing v, ascending (lean tables; nbrs builder) */
    aocc_off = (int32_t *)calloc((size_t)n + 2, sizeof(int32_t));
    aocc_ci = (int32_t *)malloc((size_t)(ne ? ne : 1) * sizeof(int32_t));
    if (!aocc_off || !aocc_ci) goto done;
    for (int64_t i = 0; i < ne; i++) aocc_off[cv[i] + 1]++;
    for (int32_t v = 1; v <= n; v++) aocc_off[v + 1] += aocc_off[v];
    memset(fill, 0, ((size_t)n + 1) * sizeof(int32_t));
    for (int32_t ci = 0; ci < m; ci++)
        for (int32_t i = cv_off[ci]; i < cv_off[ci + 1]; i++) { int32_t v = cv[i]; aocc_ci[aocc_off[v] + fill[v]++] = ci; }
    if (!lean) {
        nb_off = (int32_t *)calloc((size_t)n + 2, sizeof(int32_t));
        if (!nb_off) goto done;
        for (int32_t v = 1; v <= n; v++) {
            int64_t g = 0;
            for (int32_t k = aocc_off[v]; k < aocc_off[v + 1]; k++) {
                int32_t ci = aocc_ci[k];
                int64_t need = g + (cv_off[ci + 1] - cv_off[ci]);
                if (need > gcap) { int64_t nc2 = gcap ? gcap : 1024; while (nc2 < need) nc2 *= 2;
                    int32_t *p = (int32_t *)realloc(gather, (size_t)nc2 * sizeof(int32_t)); if (!p) goto done; gather = p; gcap = nc2; }
                for (int32_t i = cv_off[ci]; i < cv_off[ci + 1]; i++) if (cv[i] != v) gather[g++] = cv[i];
            }
            sort_i32(gather, g);
            int32_t last = 0;
            for (int64_t i = 0; i < g; i++) if (gather[i] != last) { vec_push(&NB, gather[i]); if (!NB.a) goto done; last = gather[i]; }
            if (NB.len > INT32_MAX) goto done;
            nb_off[v + 1] = (int32_t)NB.len;
        }
        if (!NB.a) { NB.a = (int32_t *)malloc(sizeof(int32_t)); if (!NB.a) goto done; }
        free(aocc_off); free(aocc_ci); aocc_off = aocc_ci = NULL;
        free(CV.a); CV.a = NULL; free(cv_off); cv_off = NULL;
    }
    I->w = w; I->total_soft = tsoft; I->has_hard = has_hard;
    I->occ_off = occ_off; I->occ_ci = occ_ci; I->occ_d = occ_d;
    I->cvd_off = cvd_off; I->cvd_u = cvd_u; I->cvd_d = cvd_d;
    I->nb_off = nb_off; I->nb = NB.a;
    I->aocc_off = aocc_off; I->aocc_ci = aocc_ci; I->cv_off = cv_off; I->cv_u = (const int32_t *)CV.a;
    w = NULL; occ_off = occ_ci = occ_d = cvd_off = cvd_u = cvd_d = nb_off = aocc_off = aocc_ci = cv_off = NULL;
    CV.a = NULL; NB.a = NULL;
    rc = 0;
done:
    free(w); free(stamp); free(pc); free(nc); free(cv_off); free(CV.a); free(CD.a); free(HP.a);
    free(occ_off); free(occ_ci); free(occ_d); free(cvd_off); free(cvd_u); free(cvd_d);
    free(aocc_off); free(aocc_ci); free(nb_off); free(NB.a); free(fill); free(cnt_pos); free(gather);
    if (rc) memset(I, 0, sizeof(*I));
    return rc;
}

void inst_tables_free(Inst *I) {
    free((void *)I->w); free((void *)I->occ_off); free((void *)I->occ_ci); free((void *)I->occ_d);
    free((void *)I->cvd_off); free((void *)I->cvd_u); free((void *)I->cvd_d);
    free((void *)I->nb_off); free((void *)I->nb);
    free((void *)I->aocc_off); free((void *)I->aocc_ci); free((void *)I->cv_off); free((void *)I->cv_u);
    memset(I, 0, sizeof(*I));
}

/* Once-per-run passes (plan C1.5). out: [0] n_hard, [1] n_soft, [2] soft weight sum
 * (raw Clause.weight), [3] 1 if [2] overflowed, [4] soft weight max (from 0),
 * [5] weighted (a soft weight != 1), [6] max clause length (literals). */
void inst_counts(const CInst *c, int64_t *out) {
    int64_t nh = 0, ns = 0, sw = 0, ovf = 0, wmax = 0, wtd = 0, ml = 0;
    for (int32_t ci = 0; ci < c->m; ci++) {
        int64_t L = c->lit_off[ci + 1] - c->lit_off[ci];
        if (L > ml) ml = L;
        if (c->hard[ci]) { nh++; continue; }
        int64_t x = c->w[ci];
        ns++;
        if ((x > 0 && sw > INT64_MAX - x) || (x < 0 && sw < INT64_MIN - x)) ovf = 1; else sw += x;
        if (x > wmax) wmax = x;
        if (x != 1) wtd = 1;
    }
    out[0] = nh; out[1] = ns; out[2] = sw; out[3] = ovf; out[4] = wmax; out[5] = wtd; out[6] = ml;
}

/* sum(float(cl.weight) for soft clauses), in clause order. */
double inst_soft_wsum_f(const CInst *c) {
    double s = 0.0;
    for (int32_t ci = 0; ci < c->m; ci++) if (!c->hard[ci]) s += (double)c->w[ci];
    return s;
}

/* kernel.screen_frac's counts: occurrences of v and -v with multiplicity. */
int inst_screen(const CInst *c, int64_t *out) {
    int64_t *pq = (int64_t *)calloc(2 * ((size_t)c->n + 1), sizeof(int64_t));
    if (!pq) return 1;
    for (int64_t q = 0; q < c->nlits; q++) { int32_t l = c->lits[q]; if (l > 0) pq[2 * l]++; else pq[2 * (-l) + 1]++; }
    int64_t hit = 0, occ = 0;
    for (int32_t v = 1; v <= c->n; v++) {
        int64_t p = pq[2 * v], qn = pq[2 * v + 1];
        if (p + qn == 0) continue;
        occ++;
        if (p == 0 || qn == 0 || (p == 1 && qn == 1)) hit++;
    }
    free(pq); out[0] = hit; out[1] = occ; return 0;
}

/* 2.0 ** (-k), exactly (halving a power of two is exact down to 2^-1074; then 0). */
static double pow2neg(int32_t k) {
    if (k > 1100) return 0.0;
    double r = 1.0;
    for (int32_t i = 0; i < k; i++) r *= 0.5;
    return r;
}

/* population.jw_priors: pri[0 .. n] (pri[0] = 0.5). */
int inst_jw(const CInst *c, double *pri) {
    double *pt = (double *)calloc((size_t)c->n + 1, sizeof(double)), *pf = (double *)calloc((size_t)c->n + 1, sizeof(double));
    if (!pt || !pf) { free(pt); free(pf); return 1; }
    for (int32_t ci = 0; ci < c->m; ci++) {
        if (c->hard[ci]) continue;
        int32_t L = c->lit_off[ci + 1] - c->lit_off[ci];
        double scale = (double)c->w[ci] * pow2neg(L > 1 ? L : 1);
        for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) {
            int32_t l = c->lits[q];
            if (l > 0) pt[l] += scale; else pf[-l] += scale;
        }
    }
    pri[0] = 0.5;
    for (int32_t v = 1; v <= c->n; v++) {
        double s = pt[v] + pf[v];
        double p = s > 0 ? pt[v] / s : 0.5;
        p = p > 0.05 ? p : 0.05;      /* max(0.05, p) */
        pri[v] = 0.95 < p ? 0.95 : p; /* min(0.95, .) */
    }
    free(pt); free(pf); return 0;
}

/* One pass for evaluate_assignment, score_assignment and the satisfied count.
 * A: 1-based, n + 1 bytes (0/1). fsat: sum(float(weight)) of satisfied soft clauses
 * in clause order. out: [0] hard violations, [1] unsatisfied soft weight (raw),
 * [2] unsatisfied soft count, [3] satisfied clauses, [4] 1 if [1] overflowed. */
void inst_eval(const CInst *c, const uint8_t *A, double *fsat, int64_t *out) {
    double s = 0.0; int64_t hv = 0, uw = 0, un = 0, sc = 0, ovf = 0;
    for (int32_t ci = 0; ci < c->m; ci++) {
        int sat = 0;
        for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) {
            int32_t l = c->lits[q];
            if (l > 0 ? A[l] : !A[-l]) { sat = 1; break; }
        }
        if (sat) { sc++; if (!c->hard[ci]) s += (double)c->w[ci]; }
        else if (c->hard[ci]) hv++;
        else { int64_t x = c->w[ci]; un++; if ((x > 0 && uw > INT64_MAX - x) || (x < 0 && uw < INT64_MIN - x)) ovf = 1; else uw += x; }
    }
    *fsat = s; out[0] = hv; out[1] = uw; out[2] = un; out[3] = sc; out[4] = ovf;
}

/* ===================================================== per-child functions (C2)
 * docs/current2/COMPILED_MEMETIC_PLAN.md §4 C2 (2026-10-28). Twins of src/evo/v3.py
 * partition_crossover / px_components, src/evo/impl_v2.py clause_aware_crossover1_v2,
 * src/evo/v3.py _guarded_flip with population.init_hard_satisfied. Assignments are
 * 1-based byte arrays (index 0 unused). No random draws. tests/test_compact.py. */

static int32_t uf_find(int32_t *parent, int32_t a) {
    while (parent[a] != a) { parent[a] = parent[parent[a]]; a = parent[a]; }
    return a;
}

/* partition_crossover: child = A, then B's values on every component where B is
 * strictly better on (hard violations, static soft cost) of the clauses first reached
 * through it, or equal and B is the fitter parent. out: [0] q, [1] took_a, [2] took_b.
 * 0 = ok, 1 = out of memory. */
int px_cross(const Inst *I, const uint8_t *A, const uint8_t *B, int fitter_is_b, uint8_t *child, int64_t *out) {
    const int32_t n = I->n, m = I->m;
    int rc = 1;
    uint8_t *indiff = (uint8_t *)calloc((size_t)n + 1, 1), *mark = NULL, *done = NULL;
    int32_t *parent = (int32_t *)malloc(((size_t)n + 1) * sizeof(int32_t));
    int32_t *comp_of = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    int32_t *cid_of_root = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    int32_t *coff = NULL, *cvars = NULL, *cfill = NULL;
    int64_t *ha = NULL, *hb = NULL, *sa = NULL, *sb = NULL;
    if (!indiff || !parent || !comp_of || !cid_of_root) goto done_;
    int64_t nd = 0;
    for (int32_t v = 0; v <= n; v++) { parent[v] = v; if (v && A[v] != B[v]) { indiff[v] = 1; nd++; } }
    if (I->nb_off) {          /* full tables: the BFS's edges, as union-find (same components) */
        for (int32_t v = 1; v <= n; v++) {
            if (!indiff[v]) continue;
            for (int32_t k = I->nb_off[v]; k < I->nb_off[v + 1]; k++) {
                int32_t u = I->nb[k];
                if (!indiff[u]) continue;
                int32_t r0 = uf_find(parent, v), ru = uf_find(parent, u);
                if (ru != r0) { if (ru < r0) { int32_t t = ru; ru = r0; r0 = t; } parent[ru] = r0; }
            }
        }
    } else {                  /* lean: _px_components_lean, line for line */
        done = (uint8_t *)calloc((size_t)m + 1, 1);
        if (!done) goto done_;
        for (int32_t v = 1; v <= n; v++) {
            if (!indiff[v]) continue;
            for (int32_t k = I->aocc_off[v]; k < I->aocc_off[v + 1]; k++) {
                int32_t ci = I->aocc_ci[k];
                if (done[ci]) continue;
                done[ci] = 1;
                int32_t r0 = uf_find(parent, v);
                for (int32_t q = I->cv_off[ci]; q < I->cv_off[ci + 1]; q++) {
                    int32_t u = I->cv_u[q];
                    if (!indiff[u]) continue;
                    int32_t ru = uf_find(parent, u);
                    if (ru != r0) { if (ru < r0) { int32_t t = ru; ru = r0; r0 = t; } parent[ru] = r0; }
                }
            }
        }
    }
    int32_t q = 0;
    for (int32_t v = 1; v <= n; v++) {          /* ids by smallest variable */
        if (!indiff[v]) continue;
        int32_t r = uf_find(parent, v);
        if (!cid_of_root[r]) cid_of_root[r] = ++q;
        comp_of[v] = cid_of_root[r];
    }
    coff = (int32_t *)calloc((size_t)q + 2, sizeof(int32_t));
    cvars = (int32_t *)malloc((size_t)(nd ? nd : 1) * sizeof(int32_t));
    cfill = (int32_t *)calloc((size_t)q + 1, sizeof(int32_t));
    ha = (int64_t *)calloc((size_t)q + 1, sizeof(int64_t)); hb = (int64_t *)calloc((size_t)q + 1, sizeof(int64_t));
    sa = (int64_t *)calloc((size_t)q + 1, sizeof(int64_t)); sb = (int64_t *)calloc((size_t)q + 1, sizeof(int64_t));
    mark = (uint8_t *)calloc((size_t)m + 1, 1);
    if (!coff || !cvars || !cfill || !ha || !hb || !sa || !sb || !mark) goto done_;
    for (int32_t v = 1; v <= n; v++) if (comp_of[v]) coff[comp_of[v] + 1]++;
    for (int32_t c = 1; c <= q; c++) coff[c + 1] += coff[c];
    for (int32_t v = 1; v <= n; v++) if (comp_of[v]) { int32_t c = comp_of[v]; cvars[coff[c] + cfill[c]++] = v; }
    for (int32_t c = 1; c <= q; c++)
        for (int32_t i = coff[c]; i < coff[c + 1]; i++) {
            int32_t v = cvars[i];
            for (int32_t k = I->occ_off[v]; k < I->occ_off[v + 1]; k++) {
                int32_t ci = I->occ_ci[k];
                if (mark[ci]) continue;
                mark[ci] = 1;
                int sat_a = 0, sat_b = 0;
                for (int32_t t = I->lit_off[ci]; t < I->lit_off[ci + 1]; t++) {
                    int32_t l = I->lits[t];
                    if (l > 0) { if (A[l]) sat_a = 1; if (B[l]) sat_b = 1; }
                    else { if (!A[-l]) sat_a = 1; if (!B[-l]) sat_b = 1; }
                }
                if (I->is_hard[ci]) { if (!sat_a) ha[c]++; if (!sat_b) hb[c]++; }
                else { if (!sat_a) sa[c] += I->w[ci]; if (!sat_b) sb[c] += I->w[ci]; }
            }
        }
    memcpy(child, A, (size_t)n + 1);
    int64_t took_a = 0, took_b = 0;
    for (int32_t c = 1; c <= q; c++) {
        int lt = hb[c] < ha[c] || (hb[c] == ha[c] && sb[c] < sa[c]);
        int eq = hb[c] == ha[c] && sb[c] == sa[c];
        if (lt || (eq && fitter_is_b)) {
            took_b++;
            for (int32_t i = coff[c]; i < coff[c + 1]; i++) child[cvars[i]] = B[cvars[i]];
        } else took_a++;
    }
    out[0] = q; out[1] = took_a; out[2] = took_b;
    rc = 0;
done_:
    free(indiff); free(mark); free(done); free(parent); free(comp_of); free(cid_of_root);
    free(coff); free(cvars); free(cfill); free(ha); free(hb); free(sa); free(sb);
    return rc;
}

/* clause_aware_crossover1_v2's instance tables (_XoStatic) and the hard-clause guard
 * tables (population.build_hard_occurs over the hard clauses in instance order). */
typedef struct {
    int32_t n, m_hard;
    double *s_true, *s_false;        /* n + 1: _soft_proxy_scores */
    int32_t *hc;                     /* m_hard: instance index of hard clause j */
    int32_t *unassigned0;            /* m_hard: len(lits) */
    int32_t *pos_off, *pos_ci, *neg_off, *neg_ci;   /* var v: hard clause ids per +v / -v occurrence */
    int32_t *hocc_off, *hocc;        /* var v: hard clause ids per occurrence of v (either sign) */
} HardTab;

int hard_build(const CInst *c, HardTab *H) {
    memset(H, 0, sizeof(*H));
    const int32_t n = c->n;
    H->n = n;
    int32_t mh = 0;
    for (int32_t ci = 0; ci < c->m; ci++) if (c->hard[ci]) mh++;
    H->m_hard = mh;
    H->s_true = (double *)calloc((size_t)n + 1, sizeof(double));
    H->s_false = (double *)calloc((size_t)n + 1, sizeof(double));
    H->hc = (int32_t *)malloc((size_t)(mh ? mh : 1) * sizeof(int32_t));
    H->unassigned0 = (int32_t *)malloc((size_t)(mh ? mh : 1) * sizeof(int32_t));
    H->pos_off = (int32_t *)calloc((size_t)n + 2, sizeof(int32_t));
    H->neg_off = (int32_t *)calloc((size_t)n + 2, sizeof(int32_t));
    H->hocc_off = (int32_t *)calloc((size_t)n + 2, sizeof(int32_t));
    if (!H->s_true || !H->s_false || !H->hc || !H->unassigned0 || !H->pos_off || !H->neg_off || !H->hocc_off) return 1;
    int32_t j = 0;
    for (int32_t ci = 0; ci < c->m; ci++) {
        if (c->hard[ci]) {
            H->hc[j] = ci; H->unassigned0[j] = c->lit_off[ci + 1] - c->lit_off[ci]; j++;
            for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) {
                int32_t l = c->lits[q], v = l < 0 ? -l : l;
                if (l > 0) H->pos_off[v + 1]++; else H->neg_off[v + 1]++;
                H->hocc_off[v + 1]++;
            }
        } else {
            double w = (double)c->w[ci];
            for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) {
                int32_t l = c->lits[q];
                if (l > 0) H->s_true[l] += w; else H->s_false[-l] += w;
            }
        }
    }
    for (int32_t v = 1; v <= n; v++) { H->pos_off[v + 1] += H->pos_off[v]; H->neg_off[v + 1] += H->neg_off[v]; H->hocc_off[v + 1] += H->hocc_off[v]; }
    int64_t np = H->pos_off[n + 1], nn = H->neg_off[n + 1], nh = H->hocc_off[n + 1];
    H->pos_ci = (int32_t *)malloc((size_t)(np ? np : 1) * sizeof(int32_t));
    H->neg_ci = (int32_t *)malloc((size_t)(nn ? nn : 1) * sizeof(int32_t));
    H->hocc = (int32_t *)malloc((size_t)(nh ? nh : 1) * sizeof(int32_t));
    int32_t *fp = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t)), *fn = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t)),
            *fh = (int32_t *)calloc((size_t)n + 1, sizeof(int32_t));
    if (!H->pos_ci || !H->neg_ci || !H->hocc || !fp || !fn || !fh) { free(fp); free(fn); free(fh); return 1; }
    for (int32_t k = 0; k < mh; k++) {
        int32_t ci = H->hc[k];
        for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) {
            int32_t l = c->lits[q], v = l < 0 ? -l : l;
            if (l > 0) H->pos_ci[H->pos_off[v] + fp[v]++] = k; else H->neg_ci[H->neg_off[v] + fn[v]++] = k;
            H->hocc[H->hocc_off[v] + fh[v]++] = k;
        }
    }
    free(fp); free(fn); free(fh);
    return 0;
}

void hard_free(HardTab *H) {
    free(H->s_true); free(H->s_false); free(H->hc); free(H->unassigned0);
    free(H->pos_off); free(H->pos_ci); free(H->neg_off); free(H->neg_ci); free(H->hocc_off); free(H->hocc);
    memset(H, 0, sizeof(*H));
}

/* clause_aware_crossover1_v2 (p1_better = p1.fitness >= p2.fitness). 0 / 1 = OOM. */
int xo_cross(const HardTab *H, const uint8_t *A, const uint8_t *B, int p1_better, uint8_t *child) {
    const int32_t n = H->n;
    const uint8_t *better = p1_better ? A : B;
    child[0] = 0;
    if (H->m_hard == 0) {
        for (int32_t v = 1; v <= n; v++) {
            uint8_t a = A[v] ? 1 : 0;
            if (a == (B[v] ? 1 : 0)) child[v] = a;
            else if (H->s_true[v] > H->s_false[v]) child[v] = 1;
            else if (H->s_false[v] > H->s_true[v]) child[v] = 0;
            else child[v] = better[v] ? 1 : 0;
        }
        return 0;
    }
    uint8_t *hs = (uint8_t *)calloc((size_t)H->m_hard, 1);
    int32_t *hu = (int32_t *)malloc((size_t)H->m_hard * sizeof(int32_t));
    if (!hs || !hu) { free(hs); free(hu); return 1; }
    memcpy(hu, H->unassigned0, (size_t)H->m_hard * sizeof(int32_t));
#define EVALC(v, val, DV, DS) do { DV = 0; DS = 0; \
        for (int32_t k_ = H->pos_off[v]; k_ < H->pos_off[(v) + 1]; k_++) { int32_t c_ = H->pos_ci[k_]; if (hs[c_]) continue; \
            if (val) DS++; else if (hu[c_] == 1) DV++; } \
        for (int32_t k_ = H->neg_off[v]; k_ < H->neg_off[(v) + 1]; k_++) { int32_t c_ = H->neg_ci[k_]; if (hs[c_]) continue; \
            if (!(val)) DS++; else if (hu[c_] == 1) DV++; } } while (0)
    for (int32_t v = 1; v <= n; v++) {
        uint8_t a = A[v] ? 1 : 0, b = B[v] ? 1 : 0, chosen;
        if (a == b) chosen = a;
        else {
            int64_t dva, dsa, dvb, dsb;
            EVALC(v, a, dva, dsa);
            EVALC(v, b, dvb, dsb);
            if (dva < dvb) chosen = a;
            else if (dvb < dva) chosen = b;
            else if (dsa > dsb) chosen = a;
            else if (dsb > dsa) chosen = b;
            else if (H->s_true[v] > H->s_false[v]) chosen = 1;
            else if (H->s_false[v] > H->s_true[v]) chosen = 0;
            else chosen = better[v] ? 1 : 0;   /* in {a, b}: the rng.choice branch is unreachable */
        }
        child[v] = chosen;                     /* commit */
        for (int32_t k = H->pos_off[v]; k < H->pos_off[v + 1]; k++) { int32_t c = H->pos_ci[k]; hu[c]--; if (chosen && !hs[c]) hs[c] = 1; }
        for (int32_t k = H->neg_off[v]; k < H->neg_off[v + 1]; k++) { int32_t c = H->neg_ci[k]; hu[c]--; if (!chosen && !hs[c]) hs[c] = 1; }
    }
#undef EVALC
    free(hs); free(hu);
    return 0;
}

static inline int hard_sat(const CInst *c, int32_t ci, const uint8_t *A) {
    for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) { int32_t l = c->lits[q]; if (l > 0 ? A[l] : !A[-l]) return 1; }
    return 0;
}

/* init_hard_satisfied: hsat[j] for hard clause j. */
void hard_sat_init(const CInst *c, const HardTab *H, const uint8_t *A, uint8_t *hsat) {
    for (int32_t j = 0; j < H->m_hard; j++) hsat[j] = (uint8_t)hard_sat(c, H->hc[j], A);
}

/* _guarded_flip: flip v unless it falsifies a satisfied hard clause; 1 = flipped. */
int hard_guarded_flip(const CInst *c, const HardTab *H, uint8_t *A, uint8_t *hsat, int32_t v) {
    A[v] = !A[v];
    for (int32_t k = H->hocc_off[v]; k < H->hocc_off[v + 1]; k++) {
        int32_t j = H->hocc[k];
        if (hsat[j] && !hard_sat(c, H->hc[j], A)) { A[v] = !A[v]; return 0; }
    }
    for (int32_t k = H->hocc_off[v]; k < H->hocc_off[v + 1]; k++) { int32_t j = H->hocc[k]; hsat[j] = (uint8_t)hard_sat(c, H->hc[j], A); }
    return 1;
}

/* ======================================================= hard-mode helpers (C3)
 * docs/current2/COMPILED_MEMETIC_PLAN.md §4 C3 (2026-10-28). Twins of src/evo/hard.py
 * SoftView (cost, unsat, the satisfied unit soft literals of the keep-sat moves) and
 * repair's Hamming distance. Soft clauses are numbered in instance order (SoftView's
 * index i). Weight sums stay in Python (sum() over the same floats, same order). */

/* Unsatisfied soft clauses under A: their soft indices, ascending; returns the count. */
int64_t soft_unsat(const CInst *c, const uint8_t *A, int32_t *out) {
    int64_t k = 0; int32_t j = 0;
    for (int32_t ci = 0; ci < c->m; ci++) {
        if (c->hard[ci]) continue;
        int sat = 0;
        for (int32_t q = c->lit_off[ci]; q < c->lit_off[ci + 1]; q++) { int32_t l = c->lits[q]; if (l > 0 ? A[l] : !A[-l]) { sat = 1; break; } }
        if (!sat) out[k++] = j;
        j++;
    }
    return k;
}

/* Soft index -> instance clause index (n_soft entries). */
void soft_index(const CInst *c, int32_t *out) {
    int32_t j = 0;
    for (int32_t ci = 0; ci < c->m; ci++) if (!c->hard[ci]) out[j++] = ci;
}

/* _keep_sat_move's `keep`: the literal of every unit soft clause it satisfies, in order. */
int64_t soft_unit_sat(const CInst *c, const uint8_t *A, int32_t *out) {
    int64_t k = 0;
    for (int32_t ci = 0; ci < c->m; ci++) {
        if (c->hard[ci] || c->lit_off[ci + 1] - c->lit_off[ci] != 1) continue;
        int32_t l = c->lits[c->lit_off[ci]];
        if (l > 0 ? A[l] : !A[-l]) out[k++] = l;
    }
    return k;
}

/* sum(1 for v in 1..n if x[v] != y[v]) */
int64_t u8_hamming(const uint8_t *x, const uint8_t *y, int64_t n_plus_1) {
    int64_t d = 0;
    for (int64_t v = 1; v < n_plus_1; v++) d += (x[v] != 0) != (y[v] != 0);
    return d;
}
