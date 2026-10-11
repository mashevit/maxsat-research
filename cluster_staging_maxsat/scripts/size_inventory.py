#!/usr/bin/env python3
"""Size inventory of every .cnf/.wcnf under data/: n, m, hard, weighted, clause lengths.

Run from cluster_staging_maxsat/: python3 scripts/size_inventory.py results/size_inventory.csv
docs/current/HYPERPARAMETER_CALIBRATION_PLAN.md §1 (repo).
"""
import os, sys, json, csv
def scan(path):
    n = m = hard = 0; top = None; weights = set(); kmax = 0; kmin = 10**9; newfmt = None; ptype = None
    with open(path, 'rb') as f:
        for raw in f:
            s = raw.strip()
            if not s or s[:1] == b'c': continue
            if s[:1] == b'p':
                t = s.split(); ptype = t[1].decode()
                if ptype == 'wcnf' and len(t) >= 5: top = int(t[4])
                newfmt = False; continue
            if newfmt is None: newfmt = True
            t = s.split()
            if newfmt:
                if t[0] == b'h': hard += 1; lits = t[1:-1]
                else: weights.add(int(t[0])); lits = t[1:-1]
            elif ptype == 'wcnf':
                w = int(t[0]); lits = t[1:-1]
                if top is not None and w >= top: hard += 1
                else: weights.add(w)
            else:
                lits = t[:-1]; weights.add(1)
            m += 1; k = len(lits); kmax = max(kmax, k); kmin = min(kmin, k)
            for l in lits:
                v = abs(int(l)); n = max(n, v)
    return dict(n=n, m=m, hard=hard, soft=m - hard, weighted=len(weights) > 1, kmin=kmin if m else 0, kmax=kmax)
rows = []
for root, _, files in os.walk('data'):
    for fn in files:
        if fn.endswith(('.cnf', '.wcnf')):
            p = os.path.join(root, fn)
            parts = p.split(os.sep)
            group = '/'.join(parts[1:3]) if parts[1] in ('generated', 'raw') else parts[1]
            if parts[1] == 'raw' and 'mse_2024' in p: group = 'raw/mse_2024/' + parts[3]
            try: r = scan(p)
            except Exception as e: r = dict(error=str(e))
            rows.append(dict(group=group, path=p, **r))
w = csv.DictWriter(open(sys.argv[1], 'w', newline=''), fieldnames=['group','path','n','m','hard','soft','weighted','kmin','kmax','error'])
w.writeheader(); w.writerows(rows)
print(len(rows))
