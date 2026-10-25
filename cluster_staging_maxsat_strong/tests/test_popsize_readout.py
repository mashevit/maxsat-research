"""Batch POP readout (scripts/popsize_readout.py): the pre-registered rule.

- per instance: arrivals first, then median cost, then TTT by >= 1.25x when both
  arms reach the target in >= 2 runs; else a tie;
- the exact sign test;
- W1 (sign test) alone does not make a winner: the arrival gate W2 and the fitness
  gate W3 must hold too;
- the outcome: class winner, else overall winner, else pop 10.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import popsize_readout as pr  # noqa: E402

INF = math.inf


def st(S, C, T=INF):
    return {"S": S, "C": C, "T": T}


def row(a, b, weighted="0"):
    return {"pop10": a, "pop40": b, "weighted": weighted}


def test_arm_stats_counts_misses_as_infinite():
    runs = [{"success": True, "cost": 5, "ttt": 10.0}, {"success": False, "cost": 7, "ttt": None},
            {"success": True, "cost": 5, "ttt": 30.0}]
    assert pr.arm_stats(runs) == {"S": 2, "C": 5, "T": 30.0}
    assert pr.arm_stats(runs[1:2] * 3)["T"] == INF


def test_verdict_order():
    assert pr.verdict(st(2, 9), st(1, 5)) == ("a", "arrival")          # arrival beats cost
    assert pr.verdict(st(0, 9), st(0, 8)) == ("b", "fitness")
    assert pr.verdict(st(3, 5, 10.0), st(3, 5, 12.4)) == ("tie", "")    # < 1.25x
    assert pr.verdict(st(3, 5, 10.0), st(3, 5, 12.5)) == ("a", "speed")
    assert pr.verdict(st(1, 6, INF), st(1, 6, INF)) == ("tie", "")      # TTT only with >= 2 arrivals


def test_sign_test():
    assert pr.sign_test(0, 0) == 1.0
    assert math.isclose(pr.sign_test(9, 1), 22 / 1024)
    assert pr.sign_test(5, 5) == 1.0


def test_winner_needs_all_three_gates():
    win = [row(st(0, 8), st(0, 9))] * 20 + [row(st(0, 9), st(0, 8))] * 4
    d = pr.decide(win, 0.05)
    assert d["winner"] == "pop10" and d["better_pop10"] == 20 and d["fitness_pop10"] == 20
    # same sign-test majority, but pop40 gets more arrivals: W2 fails, no winner
    arr = [row(st(0, 8), st(0, 9))] * 20 + [row(st(0, 9), st(3, 1))] * 4
    d = pr.decide(arr, 0.05)
    assert d["gates_pop10"] == {"W1": True, "W2": False, "W3": True} and d["winner"] is None
    # majority by speed only, while pop40 wins more on cost: W3 fails
    spd = [row(st(3, 1, 1.0), st(3, 1, 9.0))] * 20 + [row(st(0, 9), st(0, 8))] * 6
    d = pr.decide(spd, 0.05)
    assert d["gates_pop10"]["W1"] and not d["gates_pop10"]["W3"] and d["winner"] is None


def test_outcome():
    none = {"winner": None}
    assert pr.outcome(none, {"unweighted": none, "weighted": none})["pops"] == {"unweighted": 10, "weighted": 10}
    o = pr.outcome({"winner": "pop40"}, {"unweighted": none, "weighted": {"winner": "pop10"}})
    assert o["pops"] == {"unweighted": 40, "weighted": 10} and "by class" in o["text"]
    o = pr.outcome({"winner": "pop40"}, {"unweighted": none, "weighted": none})
    assert o["pops"] == {"unweighted": 40, "weighted": 40} and "every hard instance" in o["text"]
    assert "confirmed" in pr.outcome({"winner": "pop10"}, {"unweighted": none, "weighted": none})["text"]
