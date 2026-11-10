# Exact Variable Elimination in MaxSAT: 1/1, 1/2, and 2/2

Exact variable elimination removes a variable while preserving the minimum achievable cost. Some elimination rules produce a smaller, simpler formula; others introduce additional clauses or longer clauses.

According to the implementation description supplied in the conversation, only the 1/1 elimination rule is currently implemented. The 1/2 and 2/2 rules are possible extensions.

## 1. What the labels mean

The labels count the clauses containing the variable we want to eliminate:

| Case | Clauses containing x | Clauses containing ¬x |
|---|---:|---:|
| 1/1 | 1 | 1 |
| 1/2 | 1 | 2 |
| 2/2 | 2 | 2 |

These must account for all occurrences of x in the current formula.

In the Max-2-SAT examples below, A, A₁, A₂, B, B₁, and B₂ are individual literals on variables other than x. A literal can itself be a variable or its negation.

A soft clause's weight is the cost incurred when that clause is violated.

## 2. What exact elimination preserves

Suppose the clauses containing x are:

\[
(x\lor A_i,w_i),\qquad(\neg x\lor B_j,u_j).
\]

Fix the values of all variables except x.

- If x = 0, every clause containing ¬x is automatically satisfied. We pay for the positive-x clauses whose Aᵢ is false.
- If x = 1, every clause containing x is automatically satisfied. We pay for the negative-x clauses whose Bⱼ is false.

The best cost obtainable by choosing x is therefore:

\[
g=\min\left(
\sum_i w_i[A_i\text{ is false}],
\sum_j u_j[B_j\text{ is false}]
\right).
\]

The brackets denote an indicator: [P] is 1 if P is true and 0 otherwise.

The goal is to replace the clauses containing x with clauses that do not contain x and whose total cost is exactly g for every assignment to the remaining variables.

This preserves the best attainable cost over x for each remaining assignment. Combined with the unchanged clauses, it preserves the global optimum.

## 3. Why 1/1 is simple

Consider:

\[
(x\lor A,w_1),\qquad(\neg x\lor B,w_2).
\]

If at least one of A and B is true, we can choose x so that both clauses are satisfied.

If both are false, the clauses reduce to:

\[
(x,w_1),\qquad(\neg x,w_2).
\]

These requirements conflict. We must violate one clause, so we choose the cheaper one.

The exact replacement is consequently:

\[
\boxed{(A\lor B,\min(w_1,w_2))}.
\]

Two clauses become one, and x disappears.

For binary input clauses, the replacement remains binary or becomes shorter after simplification. For longer input clauses, A and B may be residual disjunctions, and their combined resolvent can be longer than either original clause.

## 4. Why 1/2 requires compensation

Consider three clauses, all with weight 1:

\[
(x\lor A),\qquad
(\neg x\lor B_1),\qquad
(\neg x\lor B_2).
\]

Suppose A, B₁, and B₂ are all false.

- Choosing x = 0 violates only the first clause: cost 1.
- Choosing x = 1 violates the other two clauses: cost 2.

The correct projected cost is therefore 1.

Simply replacing the original clauses with the two ordinary resolvents

\[
(A\lor B_1),\qquad(A\lor B_2)
\]

would be incorrect: both would be violated, producing cost 2.

An exact replacement is:

\[
(A\lor B_2),\qquad(A\lor B_1\lor\neg B_2).
\]

When B₂ is false, the first clause already charges for false A. The second clause is then satisfied by ¬B₂, preventing double counting.

When B₂ is true, the first clause is satisfied, and the second reduces to A ∨ B₁, charging precisely when both A and B₁ are false.

The compensation literal preserves the cost, but it creates a clause of length 3.

### Weighted 1/2

For:

\[
(x\lor A,w),\qquad
(\neg x\lor B_1,u_1),\qquad
(\neg x\lor B_2,u_2),
\]

define:

\[
a=\min(w,u_1),\qquad b=\min(w,u_2),
\]

\[
d=a+b-\min(w,u_1+u_2).
\]

The exact replacement is:

\[
(A\lor B_1,a-d),
\]

\[
(A\lor B_1\lor\neg B_2,d),
\]

\[
(A\lor B_2,b).
\]

Clauses with weight zero can be omitted.

The quantity d corrects the excess charge that would otherwise arise when both B literals are false.

For nonnegative input weights, \(0\le d\le\min(a,b)\), so the replacement weights are nonnegative.

If A is true, the projected cost and all replacement costs are zero. If A is false, the cases are:

| B₁ | B₂ | Correct projected cost | Replacement cost |
|---|---|---|---|
| True | True | 0 | 0 |
| False | True | min(w, u₁) = a | (a − d) + d = a |
| True | False | min(w, u₂) = b | b |
| False | False | min(w, u₁ + u₂) | a − d + b |

When all weights are 1, a = b = d = 1, giving the two-clause replacement above.

If:

\[
w\ge u_1+u_2,
\]

then d = 0, and the replacement consists of two binary clauses:

\[
(A\lor B_1,u_1),\qquad(A\lor B_2,u_2).
\]

In this weight regime, no compensation clause is needed.

## 5. Understanding unit-weight 2/2

Start with four clauses, all with weight 1:

\[
(x\lor A_1),\quad(x\lor A_2),\quad
(\neg x\lor B_1),\quad(\neg x\lor B_2).
\]

If x = 0, the B clauses are automatically satisfied. The cost is the number of false A literals.

If x = 1, the A clauses are automatically satisfied. The cost is the number of false B literals.

Let p be the number of false A literals and q the number of false B literals. Then:

\[
g=\min(p,q).
\]

| p: false A literals | q = 0 | q = 1 | q = 2 |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 |
| 1 | 0 | 1 | 1 |
| 2 | 0 | 1 | 2 |

The key observation is:

\[
\min(p,q)
=
[p\ge1\land q\ge1]
+
[p=2\land q=2].
\]

In words:

1. Charge one unit if there is at least one false A literal and at least one false B literal.
2. Charge one additional unit if all four literals are false.

## 6. Deriving the five clauses for 2/2

To charge the first unit exactly once, identify the first false literal on each side, using the order A₁, A₂ and B₁, B₂.

On the A side, the two possibilities are:

- A₁ is false.
- A₁ is true and A₂ is false.

On the B side, the two possibilities are:

- B₁ is false.
- B₁ is true and B₂ is false.

Combining these possibilities gives four mutually exclusive cases. For each case, construct a clause that is violated exactly in that case:

| Condition for charging one unit | Clause violated under that condition |
|---|---|
| A₁ = 0, B₁ = 0 | A₁ ∨ B₁ |
| A₁ = 0, B₁ = 1, B₂ = 0 | A₁ ∨ ¬B₁ ∨ B₂ |
| A₁ = 1, A₂ = 0, B₁ = 0 | ¬A₁ ∨ A₂ ∨ B₁ |
| A₁ = 1, A₂ = 0, B₁ = 1, B₂ = 0 | ¬A₁ ∨ A₂ ∨ ¬B₁ ∨ B₂ |

Whenever each side contains a false literal, exactly one of these four clauses is violated. Otherwise, none is violated.

These clauses therefore charge exactly the first unit.

To charge the additional unit when all four literals are false, add:

\[
(A_1\lor A_2\lor B_1\lor B_2).
\]

This fifth clause is violated precisely when all four are false.

Thus the complete replacement, with every weight equal to 1, is:

\[
(A_1\lor B_1),
\]

\[
(A_1\lor\neg B_1\lor B_2),
\]

\[
(\neg A_1\lor A_2\lor B_1),
\]

\[
(\neg A_1\lor A_2\lor\neg B_1\lor B_2),
\]

\[
(A_1\lor A_2\lor B_1\lor B_2).
\]

### Example: all four literals are false

In the original formula, either value of x violates two clauses, so the minimum cost is 2.

In the replacement:

- The first clause is violated.
- The next three clauses are satisfied by ¬A₁ or ¬B₁.
- The fifth clause is violated.

The total cost is exactly 2.

This construction eliminates x but replaces four binary clauses with five clauses of length up to 4.

## 7. Why this differs from SAT

In SAT, elimination must preserve whether the remaining assignment can be extended to satisfy all the original clauses.

In MaxSAT, elimination must also preserve the numerical cost of the best extension.

Ordinary SAT elimination produces the pairwise resolvents:

\[
(A_i\lor B_j).
\]

For 2/2, this gives four resolvents. If all four A and B literals are false, all four resolvents are violated.

Treating them as unit-weight soft clauses would charge 4, whereas the correct projected MaxSAT cost is:

\[
\min(2,2)=2.
\]

The compensation literals prevent this overcounting.

If every clause containing x is hard, ordinary SAT variable elimination applies: the resolvents remain hard. With binary input clauses, these resolvents have at most two literals.

## 8. Reconstructing the eliminated variable

After finding an assignment to the reduced formula, reconstruct x by evaluating its two local costs in the original clauses:

\[
x=
\begin{cases}
1,&\text{if cost}(x=1)\le\text{cost}(x=0),\\
0,&\text{otherwise}.
\end{cases}
\]

This reconstruction is called lifting.

It chooses the value of x that achieves the projected cost for the current assignment to the remaining variables.

If several variables were eliminated, reconstruct them in reverse elimination order.

## 9. Implications for the solver

Fewer variables do not necessarily make a problem easier. Elimination can introduce more clauses or longer clauses.

According to the supplied description, the current acceptance gate rejects a reduced formula if it contains a clause longer than the longest original clause.

For Max-2-SAT, general soft 1/2 can create clauses of length 3, and the displayed soft 2/2 construction can create clauses of length 4. These constructions can therefore fail that gate.

Hard-only elimination and the weighted 1/2 case with:

\[
w\ge u_1+u_2
\]

preserve binary clause lengths in the cases described here.

These are relatively simple extensions, but any runtime benefit remains an empirical question. General soft elimination also requires accounting for longer clauses and retaining the information needed for lifting.
