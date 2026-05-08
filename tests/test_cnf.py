from src.sat.cnf import WCNF

def test_parse_mini_wcnf():
    inst = WCNF.parse_dimacs("data/toy/mini.wcnf")
    assert inst.n_vars == 3
    assert len(inst.clauses) == 5
    assert inst.hard_weight == 10
    assert inst.is_wcnf is True
    hard = [cl for cl in inst.clauses if cl.is_hard]
    soft = [cl for cl in inst.clauses if not cl.is_hard]
    assert len(hard) == 2
    assert len(soft) == 3


def test_parse_wcnf_without_top(tmp_path):
    # Old-style WCNF header omits `top`. Convention: every clause is soft.
    p = tmp_path / "no_top.wcnf"
    p.write_text("c old-style\np wcnf 3 3\n10 1 -2 0\n3 -1 2 0\n7 2 3 0\n")
    inst = WCNF.parse_dimacs(str(p))
    assert inst.n_vars == 3
    assert len(inst.clauses) == 3
    assert inst.is_wcnf is True
    assert all(not cl.is_hard for cl in inst.clauses)
    assert [cl.weight for cl in inst.clauses] == [10, 3, 7]


def test_parse_cnf_marks_format(tmp_path):
    p = tmp_path / "tiny.cnf"
    p.write_text("p cnf 2 2\n1 -2 0\n-1 2 0\n")
    inst = WCNF.parse_dimacs(str(p))
    assert inst.is_wcnf is False
    assert all(not cl.is_hard for cl in inst.clauses)
