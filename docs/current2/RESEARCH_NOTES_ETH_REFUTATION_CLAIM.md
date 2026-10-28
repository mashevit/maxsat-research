# Research note: OpenAI's claimed refutation of ETH, and what it could mean for our MaxSAT work

**Created:** 2026-10-28. **Status:** documentation only. Nothing was
implemented, no solver was changed, no experiment was run.
**Index entry:** `docs/current/RESEARCH_NOTES.md` §1 and N-2026-10-28-a.

**This is a claim under independent examination.** It is not an
established result. Everything in §2–§4 records what the sources say,
not that the sources are correct. Our own reasoning is labelled
[inference] or [speculation].

Status labels as in `RESEARCH_NOTES.md`: [verified] = read off the source
file named; [quote] = verbatim text; [inference] = follows from verified
facts by a stated argument; [speculation] = a possible application, not
checked.

---

## 0. Why this note exists

> "Shlomi Dolev sent me OpenAI's claimed refutation of the Exponential Time
> Hypothesis and suggested that we might be able to use the results in our
> MaxSAT research." (user, 2026-10-28)

The user asked for: the algorithm and its time/space bounds (manuscript
vs Lean scope); the Max-k-SAT corollary; which implementation artifacts
exist; relevance to the memetic solver and to the RC2/EvalMaxSAT
comparisons, including weighted instances and hard clauses; whether a
practical implementation looks feasible; and what to investigate first.

## 1. Sources, as read on 2026-10-28

| source | URL | read? |
|---|---|---|
| Announcement | https://openai.com/index/building-scientific-understanding-with-academic-communities/ | **No.** The direct fetch returned HTTP 403, and a web search did not find the page. Nothing in this note comes from it. The repo's `history.md` entry (§1.1) is used in its place. |
| Paper (PDF) | https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/paper.pdf | Downloaded (sha256 `5b1612dc…8123`). It could not be rendered on the workstation (no poppler), so the text was read from the LaTeX. |
| LaTeX source | https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/main_full_version.tex | **Read** (4,829 lines, sha256 `b2e6159d…6aa`). Dated "17 October 2026, revised 25 October 2026". Author: "OpenAI". |
| Lean formalization | https://github.com/openai/math/tree/main/lean/OAI/Algorithms/SubexponentialSAT | Listed (≥ 3,977 `.lean` files, 35.5 MB; the GitHub tree listing was truncated). `Algorithm.lean` header read. **Not built or checked by us.** |
| Formalization scope | https://github.com/openai/math/blob/main/lean/docs/378.md | **Read** in full (17 lines). |
| Comparator statement | https://github.com/openai/math/blob/main/lean/ComparatorChallenges/SubexponentialSAT.lean (+ `.json`) | **Read** in full. |
| Repo README, `history.md`, `lean/formalization.yaml` | https://github.com/openai/math | Relevant parts read. |

Repo state when read: `openai/math` main at commit `7ef5c0cc5ca4b0e072b7a050fca09ab24bc6fa3a`
(2026-10-26T21:18:03Z). The files are **not** copied into this repo. To
re-check a later version, compare against the hashes above.

**Section numbers.** Theorem and section numbers below were derived from
the LaTeX (amsart numbering, counted by script), not from the rendered
PDF. Each is given with its LaTeX `\label`, so it can be found with
grep.

### 1.1 Provenance and verification status [quote]

Repo `README.md`:

> "This repository contains mathematical manuscripts and supporting proof
> artifacts produced by an unnamed internal OpenAI model."

> "This collection includes results at different stages of verification.
> Not all have accompanying Lean formalizations. […] Some of the
> unformalized results could have issues."

> "In our view, these manuscripts are best understood as a form of raw
> research data, rather than polished academic papers."

`history.md`, entry "October 26, 2026":

> "*The Exponential Time Hypothesis is False.* The paper gives a
> deterministic algorithm that exactly counts satisfying assignments of
> fixed-width CNF formulas in subexponential time and polynomial space.
> The case of 3-SAT refutes the Exponential Time Hypothesis. An
> independent working group of computer scientists led by Russell
> Impagliazzo, Ramamohan Paturi, and Ryan Williams will examine and
> explain the proof. At the group's request, we are making the materials
> public immediately so others can examine them as well."

**Follow-up:** the outcome of that working group's examination is the
first thing to check before this note is used anywhere (§6, item 1).

---

## 2. The claimed algorithm and its bounds

### 2.1 What the manuscript claims [verified: LaTeX]

**Theorem 1.1** (`thm:main`, LaTeX lines 73–87):

> "For each fixed $k\ge2$, there exists a deterministic algorithm that,
> given a $k$-CNF $F$ on $n\ge20$ declared variables with $m$ clauses,
> computes $\#F$ […] in
> $(n+m)^{O_k(1)}2^{O_k(n\log\log n/\sqrt{\log n})}$
> bit operations and $(n+m)^{O_k(1)}$ bits of space.
> For each fixed $D>0$, its running time on inputs with $m\le Dn$ is
> $(n+m)^{O_{k,D}(1)}2^{O_{k,D}(n/\sqrt{\log n})}$."

- **Problem:** exact **counting** (#k-SAT). Deciding SAT is the test
  #F > 0. A satisfying assignment is found by the standard self-reduction
  (§1, after Theorem 1.1).
- **Deterministic.** The space is polynomial.
- **k must be fixed.** All constants hidden in O_k(·) depend on k. §1.1.3
  (`subsec:related-consequences`) states that the result does not cover
  CNF-SAT with width growing with n.
- **The abstract** gives the time as $(n+m)^{O_k(1)}2^{n/(\log n)^{1/2+o(1)}}$.

**The weaker bound that the main text proves** (Proposition 6.4,
`prop:interpolation-bound`): $(n+m)^{O_k(1)}2^{O_k(\rho(n))}$ time and
$(n+m)^{O_k(1)}$ space, where
$\rho(n)=n(\log\log n)^2/\sqrt{\log n}$ (natural logs).

**Discrepancy, to be followed up** [verified]. Lines 93–94 say:

> "Appendix~\ref{app:quantitative} proves both bounds in
> Theorem~\ref{thm:main} by tensor contraction."

`main_full_version.tex` has **no** `\label{app:quantitative}` and no
section on tensor contraction. Its appendices are A (`app:sparsify`),
B (`app:arithmetic`) and C (`app:consequences`). So in this source file:
- the sharper bounds of Theorem 1.1 (n·log log n/√log n, and n/√log n
  when m ≤ Dn) are **stated but not proved**;
- what is proved is the ρ(n) bound of Proposition 6.4.

The PDF may contain more. Its streams are compressed, so a plain string
search for "tensor" in it is inconclusive. Check the rendered PDF.

### 2.2 How it works, in brief [verified: LaTeX §2]

From the technique overview (§2, `sec:technical-overview`):

1. **Sparsify.** Disjoint, count-preserving sparsification splits F into
   leaves on the same n variables (Lemma 6.3, `lem:sparsify`; Appendix
   A). Each variable occurs at most B = (log n)^{O_k(1)} times in a leaf.
2. **Turn each leaf into sparse F₂ equations on the original n
   variables.**
   - First, parity checks from an expander (Tanner) code.
   - Then extra parity tests, chosen greedily by exact counts (method of
     conditional expectations).
   - The common zeros of the system are exactly the leaf's satisfying
     assignments (§6, `sec:hashes`; Lemmas 6.1–6.2).
3. **Count the common zeros** (Theorem 2.2,
   `thm:overview-sparse-polynomials`; §3–§5).
   - Write the count as a sum over $\{0,1\}^n$ of a product of
     polynomial factors. Parity is encoded by a complemented Beigel–Tarui
     polynomial modulo $2^{n+1}$ (Lemma 5.1, `lem:rational-idempotent`).
   - Replace each variable occurrence by a "replacement linear form"
     $\langle\vec P(T),\vec X\rangle$. It equals the original variable at
     T = 0.
   - At T = 1..Q, the variables split into r small groups that interact
     only through a few integer "measurements". Fixing the measurements
     lets each group be summed separately.
   - H(0) = #F is recovered by interpolating Taylor coefficients at
     T = 1..Q.
4. **The cost is a product of three terms** (§2.6,
   `subsec:preview-parameters`):
   - Taylor data, $\sum_{j\le q}2^j\binom nj$;
   - measurements, $(2D+1)^{2\tau n}$;
   - one group, $2^{2n/r}$.

   The parameter choice (Lemma 4.8, `lem:incidence-parameters`) makes all
   three exponents $o(n)$.

A simpler, weaker route (§2.8, `subsec:preview-general-sat`) gives
$2^{O_k(n(\log\log n)^{k+1}/(\log n)^{1/(2k)})}$. It sparsifies, reduces
to 3-CNF with each variable occurring at most 3 times (Tovey copies),
and counts.

### 2.3 What the Lean formalization covers [verified: `378.md`, comparator files]

`lean/docs/378.md`, §"Scope", verbatim:

> "For fixed $k\ge2$, Lean proves that a deterministic machine exactly
> counts satisfying assignments of a canonically encoded $k$-CNF on $n$
> variables in time
> $(L+1)^{O_k(1)}2^{O_k(n(\log\log n)^2/\sqrt{\log n})}$, where $L$ is
> the encoding's bit length. At every step, the machine has visited at
> most $(L+1)^{O_k(1)}$ tape cells in total."

> "For $m$ clauses, the October 25 manuscript gives the sharper time
> bound $(n+m)^{O_k(1)}2^{O_k(n\log\log n/\sqrt{\log n})}$. When
> $m\le Dn$ for fixed $D>0$, this improves to
> $(n+m)^{O_{k,D}(1)}2^{O_{k,D}(n/\sqrt{\log n})}$."

The difference between the manuscript and the formal statement:

| aspect | manuscript (Theorem 1.1) | Lean (per `378.md` and the comparator statement) |
|---|---|---|
| time exponent | $O_k(n\log\log n/\sqrt{\log n})$; $O_{k,D}(n/\sqrt{\log n})$ when $m\le Dn$ | $O_k(\rho(n))=O_k(n(\log\log n)^2/\sqrt{\log n})$ only. The sharper bounds are attributed to the manuscript, **not formalized**. |
| polynomial factor | $(n+m)^{O_k(1)}$ | $(L+1)^{O_k(1)}$, L = bit length of a canonical encoding |
| space | $(n+m)^{O_k(1)}$ bits | visited tape cells ≤ $(L+1)^{O_k(1)}$ at every step |
| model | bit operations | a multi-tape `PrimitiveMachine` (TM-style transitions over `Option Bool`) |
| output | #F | #F on a count tape, plus a SAT/UNSAT bit |

The formal theorem is
`OAI.Algorithms.SubexponentialSAT.SqrtLogSpace.exact_count_and_sat`:
- comparator statement: `lean/ComparatorChallenges/SubexponentialSAT.lean`;
- solution file per `lean/formalization.yaml`: `OAI/Algorithms/SubexponentialSAT/SqrtLogSpace/Final.lean`;
- permitted axioms: `propext`, `Quot.sound`, `Classical.choice`.

What it asserts [verified, by reading the statement]:
- *there exist* a machine and constants C, A, S > 0 and d, e > 0, such
  that for every n and every width-k CNF on `Fin n`, the machine halts
  with the count, within C·(L+1)^d·2^{A·runtimeScale(n)} steps;
- `runtimeScale n = n·(log log (n+16))² / √log (n+16)`.

The constants are **existential and not given**. The formal statement
therefore says nothing about the size of n at which the bound beats
anything.

- In the challenge file the theorem ends in `sorry`. This is the
  comparator challenge format; the proof is in the solution module.
- Minor inconsistency, worth noting at follow-up: the `.json` names the
  solution module `OAI.Algorithms.SubexponentialSAT.Main`, while
  `formalization.yaml` names `…/SqrtLogSpace/Final.lean`.

**We have not built the Lean project or run the comparator.** Every
statement that "Lean proves X" in this note is the repo's own claim.

---

## 3. The Max-k-SAT approximation corollary

### 3.1 The statement [verified: LaTeX lines 101–147]

The context sentence before it:

> "The theorem also yields arbitrarily accurate subexponential-time
> approximation algorithms for Max-$k$-SAT. The Unique Games
> Theorem~[OpenAIUGC26, Section 8.1] implies NP-hardness bounds for
> Max-$k$-SAT that match, up to arbitrarily small error in the
> approximation ratio, the guarantees of the semidefinite-programming
> algorithm of~[Rag08]."

[OpenAIUGC26] is another model-produced preprint in the same repo ("The
Unique Games Theorem", September 23, 2026). It is a second unexamined
claim. [Rag08] is Raghavendra, STOC 2008.

**Corollary 1.2** (`cor:max-sat-approximation`):

> "For every fixed $k\ge2$ and $\varepsilon>0$, there exists a randomized
> algorithm that, given a $k$-CNF $F$ on $n\ge20$ variables with $m$
> clauses, finds an assignment satisfying at least
> $\operatorname{OPT}(F)-\varepsilon m$ clauses with probability
> $1-2^{-\Omega(n)}$, in
> $(n+m)^{O_{k,\varepsilon}(1)}2^{O_{k,\varepsilon}(\rho(n))}$ time and
> $(n+m)^{O_{k,\varepsilon}(1)}$ space."

Here $\operatorname{OPT}(F)$ is "the maximum number of clauses of $F$
simultaneously satisfied by an assignment".

### 3.2 The proof, in steps [verified: LaTeX]

1. Sample $O(n/\varepsilon^2)$ clauses uniformly with replacement.
   Hoeffding plus a union bound over all $2^n$ assignments give
   $|\hat f(x)-f(x)|\le\varepsilon/2$ for every x, with probability
   $1-2^{-\Omega(n)}$.
2. For a threshold b, a fan-in-2 circuit of size $O_{k,\varepsilon}(n)$
   tests "x satisfies ≥ b sampled clauses". The circuit-to-3-CNF
   reduction turns it into a formula with $O_{k,\varepsilon}(n)$
   variables and clauses.
3. Theorem 1.1, binary search on b, and self-reduction find an exact
   optimiser of the **sample**.

### 3.3 What the corollary is and is not [inference]

- **The guarantee is an additive εm, in unweighted clause counts.** It
  does not find an optimum. It does not bound the number of falsified
  clauses relative to c\*.
  - Our corpus has c\* between 1 and about 50, with m from 48 to 276,705
    (`HYPERPARAMETER_CALIBRATION_PLAN.md`).
  - Any ε useful for us would have to satisfy εm < 1, i.e. ε < 1/m.
  - The corollary treats ε as **fixed**: the constants in
    $O_{k,\varepsilon}(\cdot)$ depend on ε, and the sample is
    $O(n/\varepsilon^2)$.
  - So it says nothing about the regime we measure: "reach c\* exactly".
- **The sampling step is why ρ(n) is in terms of n alone.** The threshold
  circuit is over $O(n/\varepsilon^2)$ sampled clauses, so the SAT
  instance has $O_{k,\varepsilon}(n)$ variables.
  - An **exact** Max-k-SAT decision ("cost ≤ b") over all m clauses needs
    a counter over all m clause outputs. That adds $\Theta(m)$ auxiliary
    variables, so Theorem 1.1 would give $2^{o(n+m)}$, not $2^{o(n)}$.
  - When m ≤ Dn (all our random Max-2/3-SAT grids), $2^{o(n+m)}$ is still
    $2^{o(n)}$ asymptotically. The paper states no exact-MaxSAT corollary.
- **The result is randomized.** Theorem 1.1 is deterministic; the
  corollary is randomized because of the sampling.

---

## 4. What implementation artifacts exist [verified]

| artifact | what it is | runnable as a SAT/MaxSAT solver? |
|---|---|---|
| `paper.pdf`, `main_full_version.tex` | manuscript and source | no |
| `lean/OAI/Algorithms/SubexponentialSAT/` (≥ 3,977 `.lean` files) | machine-checked proof that a `PrimitiveMachine` with the stated time/space bounds **exists**, plus the formal infrastructure: bit programs, arithmetic kernels with instruction-count traces, branch trees, binomial interpolation, … | **No.** It is a proof development. Some definitions are executable Lean (`Algorithm.lean` header: "Executable separated arithmetic kernels … Its instruction counts are proved by actual transition traces"), but the same header says "refining the supplied coefficient operations to the [primitive bit-machine instructions] remains a separate obligation". There is no CLI, no DIMACS/WCNF reader, no build target for a solver. |
| `ComparatorChallenges/SubexponentialSAT.{lean,json}` | the formal statement for independent checking | no; it is for proof checking |
| other code (Python/C/C++/Rust/…) for this result | **none found** in the (truncated) tree listing | — |

[inference] In principle, a Lean definition of the machine could be
extracted and run by `#eval`. In practice this would be a Turing-machine
simulation of exhaustive search at every n we could ever give it (§5.1).
It is not a candidate solver.

---

## 5. Is a practical implementation feasible?

### 5.1 Where the paper's own parameter choices take effect [inference, computed]

The manuscript defines explicit parameters, and when a check fails it
falls back to exhaustive search. Two places matter.

**(a) The sparsification parameter** (Proposition 6.4 proof, lines
3583–3591):
- $s=\lfloor\sqrt{\lambda}/\nu^2\rfloor$ with $\lambda=\lceil\log_2 n\rceil$
  and $\nu=\lceil\log_2\lambda\rceil$;
- "If $s<2$, we use exhaustive search".

**(b) The counting parameters** (Lemma 4.8, eq. `eq:parameter-QR`, used
in §5.5 lines 3147–3194):
- $r=\lfloor\sqrt\lambda/\nu^2\rfloor$, $Q=\lfloor\lambda/(128\nu)\rfloor$,
  $R=(\beta+3)\lceil\sqrt\lambda\rceil$, $\beta\ge1$;
- it requires r ≥ 2, R ≥ 32 and 6R ≤ Q, among other checks;
- otherwise: "If any check fails, the algorithm abandons the branched
  computation and checks the original equations directly on all $2^n$
  assignments."

We evaluated these integer formulas exactly (Python, workstation,
2026-10-28; script below):

| condition | smallest λ = ⌈log₂ n⌉ | i.e. n ≥ |
|---|---|---|
| s ≥ 2 (sparsification used at all) | 521,284 | $2^{521{,}283}$ (≈ $10^{156{,}922}$) |
| r ≥ 2, R ≥ 32, 6R ≤ Q (counting construction used; β = 1, the most favourable) | ≈ 1.09 × 10¹⁰ | ≈ $2^{1.09\times10^{10}}$ (≈ $10^{3.28\times10^{9}}$) |

So, **as parameterised in the manuscript, the algorithm runs exhaustive
search for every instance that can physically exist.** This is
consistent with the asymptotic claim, because only finitely many n fall
back (§5.5 says so). But it settles the practical question for the
algorithm as written.

The computation, for reproducibility (no repo script was added; the
note is documentation only):

```python
import math
ceil_log2 = lambda x: (x - 1).bit_length()
r_of = lambda lam: math.isqrt(lam // ceil_log2(lam)**4)  # largest r with r^2 nu^4 <= lam
lam = 2
while r_of(lam) < 2: lam += 1                            # -> 521284
def ok(lam, beta=1):
    nu = ceil_log2(lam); Q = lam // (128 * nu)
    R = (beta + 3) * math.ceil(math.sqrt(lam))
    return r_of(lam) >= 2 and R >= 32 and 6 * R <= Q    # first True near 1.09e10 (bisection)
```

### 5.2 Even with retuned constants [inference]

The constants 128, β+3, etc. are proof conveniences. A practical version
would retune them. Even ignoring every hidden constant, though, the
**shape** of the bound is unfavourable at our sizes (n ≤ 64,000; MSE
instances larger):

- **The one-group factor** $2^{2n/r}$, with $r\sim\sqrt{\log_2 n}$ even
  without the $\nu^2$ divisor, is about $2^{0.5n}$ at n = 10⁴ and about
  $2^{0.45n}$ at n = 10⁶.
  - That alone is worse than Schöning (3-SAT: $2^{0.415n}$) and PPSZ
    ($1.307^n\approx2^{0.386n}$), which the paper cites in §1.1.1.
  - It is multiplied by the other two costs.
- **ρ(n)/n** = $(\ln\ln n)^2/\sqrt{\ln n}$ is 1.42, 1.62, 1.76 and 1.85
  at n = 10³, 10⁴, 10⁵ and 10⁶.
  - It is greater than 1 until roughly ln n ≈ 10⁴.
  - The sharper Theorem 1.1 shape $\ln\ln n/\sqrt{\ln n}$ is about 0.7
    over the same range, before its unknown constant.
- **Worst case vs instance case.** The bound is a worst-case bound for
  **counting**. Practical SAT/MaxSAT solvers (CDCL; core-guided RC2,
  EvalMaxSAT; our local search) are not measured against worst-case
  bounds. On our corpus they already solve n = 64,000 instances (kernel
  route, `KERNEL_MEMETIC_RUN.md`) and MSE instances far beyond what any
  $2^{cn}$-type algorithm with c ≥ 0.01 could touch.
- **Deterministic subroutines that are themselves heavy.**
  - Expander and local codes are found "by deterministic exhaustive
    searches" (§1.1.6, Lemma 6.1).
  - The greedy test selection makes $2^{(\log n)^{O_k(1)}}$ counting
    calls per leaf (§2.9).
  - Exact rational arithmetic is done with $(n+1)$-bit moduli
    (Appendix B).

### 5.3 What to investigate before attempting anything

In order:
1. **The outcome of the independent examination** (Impagliazzo / Paturi /
   Williams working group, per `history.md`). Check the repo's
   `history.md` and README files for corrections or a withdrawal.
2. **The missing "quantitative" appendix** (§2.1): does the rendered PDF
   or a later revision contain the proof of the sharper bounds?
3. **Independent Lean check:** build the project, run the comparator on
   `exact_count_and_sat`, and confirm the permitted-axiom list. This is
   a large build (≥ 3,977 files plus Mathlib). It is not for the
   workstation under the WSL memory limits
   (`workstation-wsl-memory-limits` memory).
4. **A concrete-constants analysis:** for n in 10³–10⁶, is there **any**
   setting of (r, Q, R, τ, D, σ) that satisfies the construction's
   constraints (Lemma 4.8, Lemma `lem:layout`) **and** makes the
   three-cost product (eq. `eq:overview-three-costs`) smaller than
   $2^{0.386n}$? This is pen-and-paper plus a small script. If the
   answer is no, implementation is moot.
5. Only then: whether any **component** is useful by itself (§6.2).

---

## 6. Relevance to our memetic solver and to the RC2 / EvalMaxSAT comparisons

### 6.1 What it does not change [inference]

- **The ρ / orthogonality study is empirical**: per-instance anytime time
  to the optimum vs exact proof time. A worst-case asymptotic bound for
  #k-SAT does not predict per-instance times, so no measured result or
  pre-registered rule changes.
- **RC2 and EvalMaxSAT stay the exact references.** The paper offers no
  exact MaxSAT algorithm. Corollary 1.2 is additive-ε approximation for
  unweighted Max-k-SAT.
- **Weighted instances** (MSE 2024 is weighted; see `POPSIZE_RUN.md`):
  - the corollary is stated for clause counts;
  - a weighted version by weight-proportional sampling looks plausible
    [speculation], but the paper does not state one;
  - the error would be εW (W = total soft weight), which is even coarser
    for the large weight ranges in MSE.
- **Hard clauses** (MSE 2023/2024, `UNDER30_HARDMSE_RUN.md`):
  - Corollary 1.2 has no notion of hard clauses. An εm-optimal
    assignment of the sample may be infeasible.
  - An exact decision version could conjoin the hard clauses with the
    threshold formula [inference]: they are ordinary CNF clauses, and
    Theorem 1.1 handles any fixed-width CNF.
  - But that is the exact route of §3.3, with Θ(m) counter variables. It
    is not the corollary.
- **Fixed k:**
  - Our random grids are k = 2, 3 (fine).
  - MSE instances have long clauses. The setcover rail has
    Σk(k−1) > 50M (`LONG_CLAUSE_RULE_DESIGN.md`).
  - Reducing to 3-CNF (Tseitin/OR-gates, §2.8) adds a variable per gate,
    so n grows to about the total literal count. The $2^{o(n)}$ is then
    in that larger n.
- **The memetic solver.** Nothing in the algorithm is a local-search
  operator. It is an algebraic exact counter, with no anytime behaviour
  and no incumbent.

### 6.2 Possible uses, all speculative [speculation]

- **Related work / framing.** If the claim survives examination, the
  write-up's motivation should not lean on "ETH ⇒ exact MaxSAT needs
  2^{Ω(n)}".
  - [verified] No document in this repo mentions ETH or SETH: a grep of
    all `.md` and `.tex` files on 2026-10-28 found no matches.
  - The practical argument for anytime solvers does not depend on ETH.
    It rests on measured solver behaviour, which this result does not
    touch (§5.2).
- **Clause subsampling as a surrogate fitness** for very large
  instances.
  - The idea in Corollary 1.2's proof (Hoeffding over $O(n/\varepsilon^2)$
    clauses) is classical, and independent of the ETH machinery.
  - It could in principle screen children cheaply.
  - Its additive error is far above our c\* gaps, so it would at most
    rank candidates, never certify. Not proposed; recorded only because
    it is the one piece that touches MaxSAT directly.
- **Exact model counting / uniform sampling** of satisfying assignments
  (self-reduction with counts, JVV86) is not a need in our pipeline.

### 6.3 Bottom line (2026-10-28)

[inference] There is nothing to implement now:
- the result is an unexamined claim;
- its MaxSAT corollary is additive-ε and unweighted;
- as written, the algorithm is exhaustive search below n ≈ 2^{1.09·10¹⁰}.

Revisit only after items 1–4 of §5.3.

## 7. Follow-up checklist (links kept)

- [ ] Working-group outcome: https://github.com/openai/math/blob/main/history.md
- [ ] Announcement text (403 on 2026-10-28): https://openai.com/index/building-scientific-understanding-with-academic-communities/
- [ ] `app:quantitative` missing from https://github.com/openai/math/blob/main/preprints/The-Exponential-Time-Hypothesis-is-False-October-25-2026/build/main_full_version.tex (lines 93–94): check the PDF / later revision
- [ ] Lean build + comparator: https://github.com/openai/math/tree/main/lean/OAI/Algorithms/SubexponentialSAT, https://github.com/openai/math/blob/main/lean/ComparatorChallenges/SubexponentialSAT.lean, scope https://github.com/openai/math/blob/main/lean/docs/378.md
- [ ] UGC preprint cited for the Max-k-SAT hardness remark: https://github.com/openai/math/blob/main/preprints/The-Unique-Games-Theorem-September-23-2026/paper.pdf
- [ ] Concrete-constants analysis (§5.3 item 4)
