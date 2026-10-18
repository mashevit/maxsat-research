"""
New-format (MaxSAT Evaluation 2022+) WCNF parsing.

These two instances were excluded from tier 2 because `parse_dimacs` could not
read them: they carry no `p` line, so the parser fell through to its CNF branch
and raised `ValueError: invalid literal for int(): 'h'` on the first hard
clause. See `cluster_staging_maxsat/DIVERGENCE.md`.

The expected numbers below are derived from the instance files themselves --
recomputed line by line in `derive_stats`, independently of `WCNF` -- and are
additionally cross-checked against the JSON metadata each file carries in its
own `c` comment header (`"nvars"`, `"ncls"`, `"nhards"`, `"nsofts"`).
"""
import json
import os
import re

import pytest

from src.sat.cnf import WCNF

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MSE_DIR = os.path.join(REPO, "data", "raw", "mse_2024", "mse23-uw-small")

INSTANCES = {
    "00000293": {
        "path": os.path.join(
            MSE_DIR,
            "judgment-aggregation-ja-maxham-preflib-00049-00000293.wcnf",
        ),
        "n_vars": 18508,
        "n_hard": 134142,
        "n_soft": 78,
        "soft_weight_total": 78,
        "sha256": "98c63c04fb54b305f554e99e56ffeafe11b89d8230127a9ed78858a5bd7370d2",
    },
    "00000385": {
        "path": os.path.join(
            MSE_DIR,
            "judgment-aggregation-ja-maxham-preflib-00049-00000385.wcnf",
        ),
        "n_vars": 6604,
        "n_hard": 48294,
        "n_soft": 78,
        "soft_weight_total": 78,
        "sha256": "438a8e13ef95dfdc6004aa0367a15829290a690543c13b235b3f4fe7b7465ca4",
    },
}


def derive_stats(path):
    """Recompute the instance statistics without going through WCNF."""
    n_hard = n_soft = soft_weight_total = max_var = 0
    for raw in open(path):
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        toks = line.split()
        assert toks[-1] == "0", f"clause not 0-terminated: {line[:60]!r}"
        body = toks[:-1]
        if body[0] == "h":
            n_hard += 1
            lits = [int(x) for x in body[1:]]
        else:
            n_soft += 1
            soft_weight_total += int(body[0])
            lits = [int(x) for x in body[1:]]
        for lit in lits:
            max_var = max(max_var, abs(lit))
    return {
        "n_vars": max_var,
        "n_hard": n_hard,
        "n_soft": n_soft,
        "soft_weight_total": soft_weight_total,
    }


def header_metadata(path):
    """The JSON block the standardizer writes into the `c` comment header."""
    body = []
    for raw in open(path):
        if not raw.startswith("c"):
            break
        body.append(raw[1:].rstrip("\n"))
    text = "\n".join(body)
    start, end = text.index("{"), text.rindex("}")
    blob = text[start : end + 1]
    # The header ends with a `c---...` rule and contains nested stat objects;
    # strip trailing commas so it is strict JSON.
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", blob))


@pytest.mark.parametrize("key", sorted(INSTANCES))
def test_new_format_instance_parses_with_expected_stats(key):
    spec = INSTANCES[key]
    path = spec["path"]
    if not os.path.exists(path):
        pytest.skip(f"instance not present: {path}")

    inst = WCNF.parse_dimacs(path)

    hard = [cl for cl in inst.clauses if cl.is_hard]
    soft = [cl for cl in inst.clauses if not cl.is_hard]

    assert inst.n_vars == spec["n_vars"]
    assert len(hard) == spec["n_hard"]
    assert len(soft) == spec["n_soft"]
    assert sum(cl.weight for cl in soft) == spec["soft_weight_total"]

    # The format is weighted-with-hards, and `top` must strictly exceed the
    # total soft weight or a hard clause would be cheaper to break than the
    # soft clauses are to satisfy.
    assert inst.is_wcnf is True
    assert inst.hard_weight == spec["soft_weight_total"] + 1
    assert all(cl.weight == inst.hard_weight for cl in hard)

    # No clause may reference a variable outside the declared range, or the
    # occurrence lists would be silently truncated.
    assert all(1 <= abs(lit) <= inst.n_vars for cl in inst.clauses for lit in cl.lits)


@pytest.mark.parametrize("key", sorted(INSTANCES))
def test_expected_stats_match_file_derivation(key):
    """The constants above are the file's, not ours."""
    spec = INSTANCES[key]
    if not os.path.exists(spec["path"]):
        pytest.skip("instance not present")
    derived = derive_stats(spec["path"])
    for field, value in derived.items():
        assert value == spec[field], field


@pytest.mark.parametrize("key", sorted(INSTANCES))
def test_expected_stats_match_embedded_header(key):
    """Third source: the metadata the file carries in its own comments."""
    spec = INSTANCES[key]
    if not os.path.exists(spec["path"]):
        pytest.skip("instance not present")
    meta = header_metadata(spec["path"])
    assert meta["nvars"] == spec["n_vars"]
    assert meta["nhards"] == spec["n_hard"]
    assert meta["nsofts"] == spec["n_soft"]
    assert meta["ncls"] == spec["n_hard"] + spec["n_soft"]


@pytest.mark.parametrize("key", sorted(INSTANCES))
def test_occurrence_lists_are_complete(key):
    spec = INSTANCES[key]
    if not os.path.exists(spec["path"]):
        pytest.skip("instance not present")
    inst = WCNF.parse_dimacs(spec["path"])
    occurrences = sum(len(inst.pos_adj[v]) + len(inst.neg_adj[v])
                      for v in range(inst.n_vars + 1))
    assert occurrences == sum(len(cl.lits) for cl in inst.clauses)


# --------------------------------------------------------------------------
# Format detection and loud failure. A malformed instance must raise, never
# parse into a plausible-looking wrong answer.
# --------------------------------------------------------------------------

def test_legacy_formats_still_take_the_legacy_path(tmp_path):
    p = tmp_path / "legacy.wcnf"
    p.write_text("c legacy\np wcnf 3 3 100\n100 1 -2 0\n5 -1 3 0\n7 2 0\n")
    inst = WCNF.parse_dimacs(str(p))
    assert inst.n_vars == 3 and inst.hard_weight == 100
    assert [cl.is_hard for cl in inst.clauses] == [True, False, False]


def test_large_weights_survive(tmp_path):
    """Python ints are unbounded; make sure nothing narrows them."""
    p = tmp_path / "big.wcnf"
    p.write_text("h 1 -2 0\n1000000000000000000 -1 3 0\n999999999999999999 2 0\n")
    inst = WCNF.parse_dimacs(str(p))
    soft = [cl for cl in inst.clauses if not cl.is_hard]
    assert sum(cl.weight for cl in soft) == 1999999999999999999
    assert inst.hard_weight == 2000000000000000000


def test_new_format_hard_only_instance(tmp_path):
    """No soft clauses: `top` is 1, and nothing divides by zero."""
    p = tmp_path / "hardonly.wcnf"
    p.write_text("c hards only\nh 1 -2 0\nh 2 0\n")
    inst = WCNF.parse_dimacs(str(p))
    assert all(cl.is_hard for cl in inst.clauses)
    assert inst.hard_weight == 1


def test_unterminated_clause_raises(tmp_path):
    p = tmp_path / "bad.wcnf"
    p.write_text("h 1 -2 0\n1 -1 3\n")
    with pytest.raises(ValueError, match="not 0-terminated"):
        WCNF.parse_dimacs(str(p))


def test_bad_weight_token_raises(tmp_path):
    p = tmp_path / "bad.wcnf"
    p.write_text("h 1 -2 0\nx -1 3 0\n")
    with pytest.raises(ValueError, match="expected 'h' or an integer weight"):
        WCNF.parse_dimacs(str(p))


def test_non_integer_literal_raises(tmp_path):
    p = tmp_path / "bad.wcnf"
    p.write_text("h 1 -2 0\n1 -1 three 0\n")
    with pytest.raises(ValueError, match="non-integer literal"):
        WCNF.parse_dimacs(str(p))


def test_embedded_zero_raises(tmp_path):
    p = tmp_path / "bad.wcnf"
    p.write_text("h 1 0 -2 0\n")
    with pytest.raises(ValueError, match="embedded 0"):
        WCNF.parse_dimacs(str(p))


def test_negative_weight_raises(tmp_path):
    p = tmp_path / "bad.wcnf"
    p.write_text("-5 1 -2 0\n")
    with pytest.raises(ValueError, match="negative soft weight"):
        WCNF.parse_dimacs(str(p))


def test_empty_file_raises(tmp_path):
    p = tmp_path / "empty.wcnf"
    p.write_text("c nothing here\n")
    with pytest.raises(ValueError, match="empty instance"):
        WCNF.parse_dimacs(str(p))


def test_soft_only_new_format_is_not_silently_misread(tmp_path):
    """
    The regression that made the old failure dangerous: a new-format file with
    no `h` lines never hit the `int('h')` crash. It parsed through the CNF
    branch with each weight absorbed as a phantom literal -- no error at all.
    """
    p = tmp_path / "softonly.wcnf"
    p.write_text("c soft only\n3 -11 0\n4 -12 0\n")
    inst = WCNF.parse_dimacs(str(p))
    assert inst.n_vars == 12                      # not 12-with-a-phantom-var-3/4
    assert [cl.lits for cl in inst.clauses] == [[-11], [-12]]
    assert [cl.weight for cl in inst.clauses] == [3, 4]
