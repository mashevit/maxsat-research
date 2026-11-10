"""DIAGNOSTIC ONLY (2026-11-10): docs/current2/KERNEL2_LOW_DEGREE_ELIMINATION_PLAN.md §2.1.
How much of today's kernel (src/sat/kernel.py) comes from the first round
(variables pure or 1/1 in the input) and how much only from cascades; checks the
fixpoint (no pure / 1/1 variable and no complementary unit pair left).
Run from cluster_staging_maxsat_strong/:  python3 scripts/diag_kernel_cascade.py <wcnf> ...
"""
import os
import sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from src.sat.kernel import kernelize
from scripts.diag_kernel2_elim import read_wcnf
print("instance | occurring | start pure or 1/1 | removed only via cascade (by a rule / left with no clauses) | kernel")
for path in sys.argv[1:]:
    cl = read_wcnf(path)
    occ = defaultdict(lambda: [0, 0])
    for w, lits in cl:
        for l in set(lits): occ[abs(l)][0 if l > 0 else 1] += 1
    start = {v for v, (p, q) in occ.items() if p == 0 or q == 0 or (p == 1 and q == 1)}
    C, const, rec = kernelize(cl)
    kern = {abs(l) for k in C for l in k}
    recv = {v for _, v, _ in rec}
    casc_rule = len(recv - start); casc_free = len(set(occ) - start - recv - kern)
    n = len(occ)
    pc = lambda x: f"{x:,} ({100*x/n:.1f} %)"
    ko = defaultdict(lambda: [0, 0])
    for k in C:
        for l in k: ko[abs(l)][0 if l > 0 else 1] += 1
    left = sum(1 for p, q in ko.values() if p == 0 or q == 0 or (p == 1 and q == 1))
    units = sum(1 for k in C if len(k) == 1 and (-k[0],) in C)
    print(f"   fixpoint check: pure or 1/1 left {left}, complementary unit pairs {units}")
    print(f"{path.rsplit('/',1)[-1].split('_s')[-1][:-5]} | {n:,} | {pc(len(start))} | {pc(casc_rule+casc_free)} ({casc_rule:,} / {casc_free:,}) | {pc(len(kern))} | start-set in kernel: {len(start & kern)}")
