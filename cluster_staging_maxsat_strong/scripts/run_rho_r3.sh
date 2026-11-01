#!/bin/bash
# Third ρ readout (MSE26_RHO_RESULTS_3.md): both columns, then exploratory subsets and complementarity.
set -u
cd "$(dirname "$0")/.."
P=~/miniforge3/envs/maxsat/bin/python
$P scripts/mse26_rho_errors.py --errors fail    --outdir results/mse26_memetic/tasks --out results/mse26_rho_r3_fail    > results/mse26_rho_r3_fail.log 2>&1 & a=$!
$P scripts/mse26_rho_errors.py --errors exclude --outdir results/mse26_memetic/tasks --out results/mse26_rho_r3_exclude > results/mse26_rho_r3_exclude.log 2>&1 & b=$!
wait $a; ra=$?; wait $b; rb=$?
echo "rho fail exit=$ra exclude exit=$rb"
MSE26_RHO_TAG=r3_ $P scripts/mse26_rho_explore.py > results/mse26_rho_r3_explore.log 2>&1; echo "explore exit=$?"
MSE26_RHO_TAG=r3_ $P scripts/mse26_complementarity.py > results/mse26_rho_r3_complementarity.txt 2>&1; echo "complementarity exit=$?"
tail -n 2 results/mse26_rho_r3_fail.log results/mse26_rho_r3_exclude.log
echo R3_DONE
