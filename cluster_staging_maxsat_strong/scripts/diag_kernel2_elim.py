"""DIAGNOSTIC ONLY (2026-11-10), not solver code: docs/current2/KERNEL2_LOW_DEGREE_ELIMINATION_PLAN.md §3.
Profiles the current exact kernel (src/sat/kernel.py) and simulates exact
min-elimination (bucket elimination) of low-degree variables (1/2, 2/2, 1/3, ...)
under a clause-length bound L, an occurrence bound and a clause-count bound.

    python3 scripts/diag_kernel2_elim.py <instance.wcnf> ...
"""
import sys, itertools
from collections import Counter, defaultdict
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from src.sat.kernel import kernelize

def read_wcnf(path):
    cl = []
    for line in open(path):
        if not line.strip() or line[0] in "cp": continue
        t = list(map(int, line.split())); cl.append((t[0], t[1:-1]))
    return cl

def g_table(xcl, x, nbrs):
    """g(rest)=min over x of cost of the x-clauses; table over nbr assignments."""
    idx = {v: i for i, v in enumerate(nbrs)}
    tab = {}
    for bits in itertools.product((0, 1), repeat=len(nbrs)):
        c = [0, 0]
        for lits, w in xcl:
            rest_sat = any((bits[idx[abs(l)]] == 1) == (l > 0) for l in lits if abs(l) != x)
            if rest_sat: continue
            xs = x in lits   # clause needs x=1
            c[0 if xs else 1] += w  # violated when x=0 if x positive in it
        tab[bits] = min(c)
    return tab

def encode(tab, nbrs):
    """Greedy exact decomposition of a nonneg table into weighted clauses
    (each clause = violated on one subcube). Largest subcubes first."""
    k = len(nbrs); tab = dict(tab); out = []
    cubes = []
    for pat in itertools.product((None, 0, 1), repeat=k):
        cubes.append(pat)
    cubes.sort(key=lambda p: sum(z is not None for z in p))
    def members(p):
        return [b for b in tab if all(z is None or b[i] == z for i, z in enumerate(p))]
    for p in cubes:
        ms = members(p)
        m = min(tab[b] for b in ms)
        if m > 0:
            for b in ms: tab[b] -= m
            # clause violated exactly on subcube p: literal v if p=0 (v false violates), -v if p=1
            lits = tuple(sorted((nbrs[i] if z == 0 else -nbrs[i]) for i, z in enumerate(p) if z is not None))
            out.append((lits, m))
    assert all(v == 0 for v in tab.values())
    return out

def simulate(C, L, maxdeg, growth):
    """Repeatedly eliminate a variable (lowest degree first) whose exact
    replacement has max length <= L and clause count <= removed + growth."""
    C = dict(C); const = 0
    occ = defaultdict(set)
    for k in C:
        for l in k: occ[abs(l)].add(k)
    changed = True; elim = Counter()
    while changed:
        changed = False
        for x in sorted(list(occ), key=lambda v: len(occ[v])):
            ks = list(occ[x])
            if not ks or len(ks) > maxdeg: continue
            xcl = [(k, C[k]) for k in ks]
            nbrs = sorted({abs(l) for k in ks for l in k if abs(l) != x})
            if len(nbrs) > 6: continue
            tab = g_table(xcl, x, nbrs)
            new = encode(tab, nbrs)
            if any(len(l) > L for l, _ in new): continue
            n_new = sum(1 for l, _ in new if l and l not in C)
            if n_new > len(ks) + growth: continue
            p = sum(1 for k in ks if x in k); q = len(ks) - p
            for k in ks:
                C.pop(k)
                for l in k: occ[abs(l)].discard(k)
            for l, w in new:
                if not l: const += w; continue
                C[l] = C.get(l, 0) + w
                for z in l: occ[abs(z)].add(l)
            elim[f"{min(p,q)}/{max(p,q)}"] += 1
            changed = True
    nv = sum(1 for v in occ if occ[v])
    simulate.last = (C, const)
    return nv, len(C), const, Counter(len(k) for k in C), elim

def main():
  for path in sys.argv[1:]:
      cl = read_wcnf(path)
      C, const, rec = kernelize(cl)
      occ = defaultdict(lambda: [0, 0])
      for k in C:
          for l in k: occ[abs(l)][0 if l > 0 else 1] += 1
      pq = Counter(f"{min(a,b)}/{max(a,b)}" for a, b in occ.values())
      name = path.rsplit("/", 1)[-1]
      print(f"== {name}: kernel n={len(occ)} m={len(C)} const={const} "
            f"weights={dict(Counter(C.values()))} lens={dict(Counter(len(k) for k in C))}")
      tot = len(occ)
      print("   degree p/q:", ", ".join(f"{k}:{v} ({100*v/tot:.0f}%)" for k, v in sorted(pq.items(), key=lambda t: -t[1])[:8]))
      for L, maxdeg, growth in [(2, 4, 0), (3, 3, 0), (3, 4, 0), (4, 4, 0), (4, 4, 1)]:
          nv, m, c2, lens, elim = simulate(C, L, maxdeg, growth)
          print(f"   L<={L} deg<={maxdeg} growth<={growth}: n {tot}->{nv} ({100*(tot-nv)/tot:.0f}% less), m {len(C)}->{m}, const+{c2}, lens {dict(sorted(lens.items()))}, elim {dict(elim)}")

if __name__ == '__main__':
    main()
