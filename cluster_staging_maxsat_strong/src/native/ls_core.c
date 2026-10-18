/* C twin of the v3 polish cores (src/sat/ls_v3.py): walksat_v3 and dls_v3.
 *
 * docs/current2/STRONGER_MEMETIC_DESIGN.md §7 (repo). Every decision, random
 * draw and data-structure order follows the Python code line by line, with the
 * portable RNG of src/sat/rng.py (xoshiro256** seeded by splitmix64). So, for
 * the same instance, start, seed and flip budget (no time limit), this core and
 * the Python core run with PortableRng return the same assignment and counters;
 * tests/test_native.py checks it. B5 changes speed, nothing else.
 *
 * Built once per cluster tree by scripts/build_native.sh (plain gcc, no Python):
 *   cc -O2 -shared -fPIC -o src/native/build/libls_core.so src/native/ls_core.c
 */
#include <stdint.h>
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
    const int32_t *nb_off, *nb;                  /* var v: sorted neighbours */
    int64_t total_soft;
    int32_t has_hard;
} Inst;

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
               int64_t *out)
{
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
                if (use_cc) { conf[v] = 0; for (int32_t k = I->nb_off[v]; k < I->nb_off[v + 1]; k++) conf[I->nb[k]] = 1; }
                else tabu_until[v] = num_flips + tenure + (tenure_rand > 0 ? randbelow(&R, tenure_rand + 1) : 0);
            }
        }
        int64_t hv = nh;
        if (hv <= best_hv) {
            int64_t soft_now = I->total_soft - usw;
            if (hv < best_hv || soft_now > best_soft) { best_hv = hv; best_soft = soft_now; trail.len = 0; }
        }
    }
    int64_t hv = nh, soft = I->total_soft - usw;
    if (best_hv == 0) { soft = best_soft; hv = 0; }
    if (best_hv <= hv) for (int64_t i = 0; i < trail.len; i++) A[trail.a[i]] = !A[trail.a[i]];
    out[0] = num_flips; out[1] = applied; out[2] = soft; out[3] = hv;
    out[4] = skips; out[5] = asp; out[6] = alltabu;
    free(tc); free(uh); free(us); free(last_flip); free(tabu_until); free(conf); free(cand); free(allowed); free(trail.a);
    return 0;
#undef BLOCKED
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
           int64_t t, double sp, int64_t zeta, int64_t h_inc, int64_t *dw_io, int cc, int64_t *out)
{
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
        if (cc) { conf[bv] = 0; for (int32_t k = I->nb_off[bv]; k < I->nb_off[bv + 1]; k++) conf[I->nb[k]] = 1; }
        int64_t hv = S.nfh;
        if (hv < best_hv || (hv == best_hv && S.usw < best_unsat)) { best_hv = hv; best_unsat = S.usw; trail.len = 0; }
    }
#undef BETTER
    for (int64_t i = 0; i < trail.len; i++) A[trail.a[i]] = !A[trail.a[i]];
    out[0] = steps; out[1] = applied; out[2] = best_hv; out[3] = best_unsat;
    out[4] = stuck; out[5] = smooths; out[6] = ccb;
    free(S.tc); free(dw_own); free(S.score); free(S.fh); free(S.fs); free(S.fpos); free(S.D); free(S.dpos);
    free(last_flip); free(conf); free(trail.a);
    return 0;
}
