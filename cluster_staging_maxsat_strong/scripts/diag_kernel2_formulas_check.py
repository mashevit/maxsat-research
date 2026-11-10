"""DIAGNOSTIC ONLY (2026-11-10): brute-force check of the hand formulas in
docs/current2/KERNEL2_LOW_DEGREE_ELIMINATION_PLAN.md §2 and
docs/current2/EXACT_VARIABLE_ELIMINATION_EXPLAINED.md:
weighted 1/2 (2,000 random weight triples 1-9, all 8 assignments each),
unit 2/2 (all 16 assignments), unit 1/3 (all 16 assignments).
Expected output: 0 mismatches on every line.
"""
import itertools, random

def viol(c, a):  # 1 if clause c is violated under assignment a
    return 0 if any(a[abs(l)] == (l > 0) for l in c) else 1

random.seed(0)
bad = 0
for _ in range(2000):  # 1/2: (x v A, w), (-x v B1, u1), (-x v B2, u2); A=1, B1=2, B2=3
    w, u1, u2 = [random.randint(1, 9) for _ in range(3)]
    a, b = min(w, u1), min(w, u2); d = a + b - min(w, u1 + u2)
    assert 0 <= d <= min(a, b)
    rep = [((1, 2), a - d), ((1, 2, -3), d), ((1, 3), b)]
    for bits in itertools.product((0, 1), repeat=3):
        asg = dict(zip((1, 2, 3), bits))
        g = min(w * (1 - asg[1]), u1 * (1 - asg[2]) + u2 * (1 - asg[3]))
        bad += g != sum(wt * viol(c, asg) for c, wt in rep)
print("weighted 1/2: 2000 weight triples, mismatches", bad)

rep = [(1, 3), (1, -3, 4), (-1, 2, 3), (-1, 2, -3, 4), (1, 2, 3, 4)]  # 2/2: A1=1 A2=2 B1=3 B2=4
bad = 0
for bits in itertools.product((0, 1), repeat=4):
    asg = dict(zip((1, 2, 3, 4), bits))
    bad += min(2 - asg[1] - asg[2], 2 - asg[3] - asg[4]) != sum(viol(c, asg) for c in rep)
print("unit 2/2: 16 assignments, mismatches", bad)

rep = [(1, 2), (1, -2, 3), (1, -2, -3, 4)]  # 1/3: A=1, B1..B3=2..4
bad = 0
for bits in itertools.product((0, 1), repeat=4):
    asg = dict(zip((1, 2, 3, 4), bits))
    bad += min(1 - asg[1], 3 - asg[2] - asg[3] - asg[4]) != sum(viol(c, asg) for c in rep)
print("unit 1/3: 16 assignments, mismatches", bad)
