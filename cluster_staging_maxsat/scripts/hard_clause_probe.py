"""Workstation probe (NOT a measurement): does the UNCHANGED staging memetic
reach / keep / improve hard-feasible assignments on small generated partial
instances? Record: docs/current/CORPUS_FREEZE_PREP.md §8 (repo).

    cd cluster_staging_maxsat
    python3 scripts/hard_clause_probe.py <scratch dir for instances> \
        | grep -v DEBUG > results/hard_clause_probe/probe_<date>.txt

Two seeds x 20 s budgets per instance, 3.5 s polish calls: it can show that a
mechanism fails; it cannot show what a 900 s run would reach.

Separates three difficulties:
  (i)   finding feasibility from the solver's own JW init (run_memetic, 20 s)
  (ii)  preserving it: crossover1 / mutate1 (correct hard_satisfied) / polish
        applied to pairs of hard-feasible Glucose models
  (iii) improving the soft objective from a feasible start (polish only)
"""
import random, sys, time, os, statistics
from pysat.solvers import Glucose4
from pysat.formula import WCNF as PWCNF
from pysat.examples.rc2 import RC2

sys.path.insert(0, "src"); sys.path.insert(0, "..")
from sat.cnf import WCNF
from evo.memetic import run_memetic
from evo.population import Individual, evaluate_assignment, init_hard_satisfied, build_hard_occurs
from evo.operators import clause_aware_crossover1, mutate1, short_polish
from instancegen.generate import GenParams
from instancegen.feasible import generate_feasible
from instancegen.wcnf_io import write_wcnf

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)


def ksat_partial(n, hr, sr, seed):
    p = GenParams(n_vars=n, k=3, soft_ratio=sr, hard_ratio=hr, w_max=1, seed=seed)
    inst, _w = generate_feasible(p)
    path = os.path.join(OUT, f"ksat_n{n}_hr{hr}_sr{sr}_s{seed}.wcnf")
    write_wcnf(inst, path, dialect="old")
    return path


def clique(nv, p, seed):
    rng = random.Random(seed)
    edges = {(u, v) for u in range(1, nv + 1) for v in range(u + 1, nv + 1) if rng.random() < p}
    non = [(u, v) for u in range(1, nv + 1) for v in range(u + 1, nv + 1) if (u, v) not in edges]
    top = nv + 1
    path = os.path.join(OUT, f"clique_n{nv}_p{p}_s{seed}.wcnf")
    with open(path, "w") as f:
        f.write(f"p wcnf {nv} {nv + len(non)} {top}\n")
        for v in range(1, nv + 1):
            f.write(f"1 {v} 0\n")
        for u, v in non:
            f.write(f"{top} -{u} -{v} 0\n")
    return path


def rc2_opt(path):
    w = PWCNF(from_file=path)
    t = time.time()
    with RC2(w, solver="g3") as r:
        r.compute()
        return r.cost, time.time() - t


def glucose_models(path, k, seed):
    w = WCNF.parse_dimacs(path)
    hard = [list(c.lits) for c in w.clauses if c.is_hard]
    rng = random.Random(seed)
    out = []
    for _ in range(k):
        with Glucose4(bootstrap_with=hard) as s:
            s.set_phases([v if rng.random() < 0.5 else -v for v in range(1, w.n_vars + 1)])
            assert s.solve()
            m = s.get_model()
        a = [False] * (w.n_vars + 1)
        for lit in m:
            if abs(lit) <= w.n_vars:
                a[abs(lit)] = lit > 0
        out.append(a)
    return w, out


CFG = {"ea": {"enabled": True, "pop_size": 40, "tournament_k": 3, "pmutate": 0.02,
              "elitism": True, "max_gens": 1000000, "deadline_mode": "clip"},
       "ls": {"ls_polish_flips": 12500, "time_limit_s": 3.5, "flip_budget": 12500}}


def probe(path, budget=20.0):
    w = WCNF.parse_dimacs(path)
    nh = sum(c.is_hard for c in w.clauses); ns = len(w.clauses) - nh
    tot = sum(c.weight for c in w.clauses if not c.is_hard)
    opt, t_rc2 = rc2_opt(path)
    print(f"\n== {os.path.basename(path)}  vars={w.n_vars} hard={nh} soft={ns}  RC2 c*={opt} ({t_rc2:.2f}s)")
    # (i) own init
    for seed in (1, 2):
        cfg = dict(CFG, time_limit_s=budget)
        t = time.time()
        r = run_memetic(w, cfg, rng_seed=seed, target_cost=opt)
        print(f"  (i) memetic seed {seed}: stop={r['stop_reason']} hv={r['hard_violations']} "
              f"cost={tot - r['best_soft_weight'] if r['hard_violations'] == 0 else 'infeasible'} "
              f"gens={r['meta']['ea_generations']} children={r['meta']['children']} wall={time.time()-t:.1f}s")
    # init population feasibility
    rng = random.Random(1)
    from evo.population import Population
    pop = Population(w.n_vars, 40, rng); pop.init_seeds(w, CFG)
    hvs = [pop.evaluate(w, ind).hard_violations for ind in pop.members]
    print(f"  JW init (40 members): feasible {sum(h == 0 for h in hvs)}/40, median hv {statistics.median(hvs)}")
    # (ii)/(iii) from Glucose models
    w, models = glucose_models(path, 12, seed=7)
    hard = [c for c in w.clauses if c.is_hard]
    occ = build_hard_occurs(hard, w.n_vars)
    inds = []
    for a in models:
        s, hv = evaluate_assignment(w, a)
        assert hv == 0
        inds.append(Individual(assign01=a, fitness=s, hard_violations=0, hard_satisfied=init_hard_satisfied(hard, a)))
    start_costs = [tot - i.fitness for i in inds]
    rng = random.Random(3)
    x_feas = m_feas = p_feas = 0; pol_costs = []; N = 20; hx = []; hp = []; tw = []
    for _ in range(N):
        p1, p2 = rng.sample(inds, 2)
        child = clause_aware_crossover1(p1, p2, w, rng)
        _, hv = evaluate_assignment(w, child); x_feas += hv == 0; hx.append(hv)
        hs = init_hard_satisfied(hard, child)
        mutate1(child, 0.02, rng, hard, occ, hs)
        _, hv = evaluate_assignment(w, child); m_feas += hv == 0
        t0 = time.time(); pol, _f = short_polish(child, w, CFG["ls"], rng_seed=rng.randrange(1 << 30)); tw.append(time.time() - t0)
        s, hv = evaluate_assignment(w, pol); p_feas += hv == 0; hp.append(hv)
        if hv == 0: pol_costs.append(tot - s)
    print(f"  (ii) Glucose parents: child feasible after crossover {x_feas}/{N}, after mutate1 {m_feas}/{N}, after polish {p_feas}/{N}")
    print(f"       hv after crossover median {statistics.median(hx)} range {min(hx)}-{max(hx)}; after polish median {statistics.median(hp)} range {min(hp)}-{max(hp)}; polish wall/call median {statistics.median(tw):.2f}s")
    # (iii) polish straight from a feasible model
    gains = []
    for i in inds[:6]:
        pol, _f = short_polish(i.assign01, w, CFG["ls"], rng_seed=11)
        s, hv = evaluate_assignment(w, pol)
        gains.append((tot - i.fitness, tot - s if hv == 0 else None))
    print(f"  Glucose model costs: {sorted(start_costs)}")
    print(f"  (iii) polish from feasible model, cost before->after: {gains}")
    print(f"  polished-child costs (feasible ones): {sorted(pol_costs)}")


if __name__ == "__main__":
    probe(ksat_partial(150, 2.0, 2.0, 1))
    probe(ksat_partial(150, 3.0, 2.0, 1))
    probe(ksat_partial(150, 4.0, 2.0, 1))
    probe(clique(60, 0.5, 1))
