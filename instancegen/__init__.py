"""Parametric weighted MaxSAT instance generation.

Plan of record: docs/INSTANCEGEN_PLAN.md. Steps 1-2 of that doc's §13 are
implemented here (generate.py, wcnf_io.py, feasible.py); tiers.py, calibrate.py
and cli.py are still plan-only.

Standalone in the same sense as maxsat_new/: this package does not import from
src/, so it survives src/'s deletion (PORT_NOTES §10 step 8). It may import
maxsat_new.cnf (one-way edge, INSTANCEGEN_PLAN §7).
"""

GENERATOR_NAME = "weighted_ksat"
GENERATOR_VERSION = "0.1.0"
