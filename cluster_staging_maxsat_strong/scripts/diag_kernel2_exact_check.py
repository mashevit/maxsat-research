"""DIAGNOSTIC ONLY (2026-11-10): brute-force check that the simulated elimination
in diag_kernel2_elim.py preserves the optimum (n 12, unit and weights 1-5).
Expected output: "optimum mismatches 0".   python3 scripts/diag_kernel2_exact_check.py
"""
import sys, random, itertools
import os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here); sys.path.insert(0, os.path.join(_here, ".."))
from diag_kernel2_elim import simulate
from src.sat.kernel import kernelize
def opt(C, n):
    best = None
    for bits in itertools.product((0,1), repeat=n):
        c = sum(w for k, w in C.items() if not any((bits[abs(l)-1]==1)==(l>0) for l in k))
        best = c if best is None or c < best else best
    return best
bad = runs = elim = 0
for seed in range(120):
    r = random.Random(seed); n = 12; m = r.choice([14, 18, 24, 30])
    cl = []
    for _ in range(m):
        a, b = r.sample(range(1, n+1), 2)
        w = 1 if seed % 2 == 0 else r.randint(1, 5)
        cl.append((w, [a if r.random()<.5 else -a, b if r.random()<.5 else -b]))
    Corig = {}
    for w, l in cl:
        k = tuple(sorted(set(l))); Corig[k] = Corig.get(k, 0) + w
    o = opt(Corig, n)
    C, const, _ = kernelize(cl, n)
    for L, d, g in [(3,3,0), (4,4,0), (6,6,2)]:
        nv, mm, c2, lens, el = simulate(C, L, d, g); C2, c2 = simulate.last
        elim += sum(el.values()); runs += 1
        if opt(C2, n) + c2 + const != o: bad += 1
print(f"runs {runs}, eliminations {elim}, optimum mismatches {bad}")
