# Branch-and-Bound Teaching Sandbox

This project is a compact branch-and-bound sandbox for integer programming. It is designed for teaching:

- how a branch-and-bound tree is built,
- how different branching and node-selection policies change the search,
- how incumbents and bounds interact,
- how design choices in a solver affect both theory and observed behavior.

The code is intentionally small enough to read in class, but rich enough to compare several classical ideas from integer programming.

## What This Code Does

Given an integer linear optimization problem,

$$
\begin{aligned}
\max \quad & c^\top x \\
\text{s.t.} \quad & Ax \le b, \\
& x \in \mathbb{Z}^n,
\end{aligned}
$$

the solver:

1. solves the LP relaxation at a node,
2. checks whether the LP solution is already integral,
3. branches on a fractional variable if needed,
4. chooses which node to process next,
5. updates the incumbent and pruning decisions,
6. records a detailed trace for visualization in `bnb_trace.html`.

The implementation is split into modules:

- [`bnb_basic.py`](./bnb_basic.py): experiment configuration and trace generation
- [`bnb_core.py`](./bnb_core.py): branch-and-bound loop, LP solves, trace assembly
- [`branching.py`](./branching.py): branching-variable rules
- [`node_selection.py`](./node_selection.py): node selection rules
- [`child_selection.py`](./child_selection.py): child ordering rules
- [`problems.py`](./problems.py): random and demo instances

## Quick Start

Edit the configuration at the top of [`bnb_basic.py`](./bnb_basic.py):

```python
PROBLEM_FAMILY = "demo"
PROBLEM_NAME = "balanced_fractions"
STRATEGY = "best_estimate_search"
COMPARE_STRATEGIES = ["depth_first_search", "best_first_search", "best_estimate_search", "interleaved_best_estimate_best_first_search", "hybrid_best_estimate_best_first_search", "best_first_search_with_plunging", "breadth_first_search"]
BRANCHING_RULE = "reliability"
CHILD_SELECTION = "pseudocost"
SEED = 42
```

Then run:

```bash
python3 bnb_basic.py
```

This generates `bnb_trace.html`, an interactive visualization of the search tree and comparison statistics.

## Core Mathematical Ideas

### LP Relaxation

At each node $Q$, the solver enforces local bounds

$$
\ell^Q \le x \le u^Q
$$

and solves the LP relaxation

$$
\begin{aligned}
\max \quad & c^\top x \\
\text{s.t.} \quad & Ax \le b, \\
& \ell^Q \le x \le u^Q, \\
& x \in \mathbb{R}^n.
\end{aligned}
$$

Its optimal value is the node's LP bound, denoted here by $\bar c_Q$.

For a maximization problem:

- if the LP is infeasible, the node is pruned,
- if the LP solution is integral, we have a feasible integer solution,
- if $\bar c_Q$ is not better than the incumbent value $\hat c$, the node is pruned by bound,
- otherwise we branch.

### Fractionality

For a variable value $\bar x_j$, define its distances to the nearest integers by

$$
f^-_j = \bar x_j - \lfloor \bar x_j \rfloor,
\qquad
f^+_j = \lceil \bar x_j \rceil - \bar x_j.
$$

The scalar fractionality measure used often in branching is

$$
\phi(\bar x_j) = \min(f^-_j, f^+_j).
$$

The closer $\phi(\bar x_j)$ is to $\tfrac12$, the “more fractional” the variable is.

## Branching Rules

Branching rules decide which fractional variable to split on.

If we branch on variable $x_j$ at value $\bar x_j$, the two children are:

$$
x_j \le \lfloor \bar x_j \rfloor
\qquad\text{and}\qquad
x_j \ge \lceil \bar x_j \rceil.
$$

### 1. Most Fractional

Config value: `most_fractional`

Choose the variable maximizing

$$
\phi(\bar x_j)=\min(f^-_j,f^+_j).
$$

Pedagogical idea:

- branch on the variable farthest from integrality,
- often creates a visually intuitive tree,
- cheap to compute.

### 2. Pseudocost Branching

Config value: `pseudocost`

For each variable, the code stores directional pseudocosts:

$$
\Psi^-_j,\qquad \Psi^+_j
$$

which estimate the deterioration in the LP objective per unit of rounding downward or upward.

The implementation summarizes them into a ranking score, while preserving separate down/up values internally.

Pedagogical idea:

- learn from previous branches,
- use historical information instead of solving probe LPs every time.

### 3. Strong Branching

Config value: `strong`

For each candidate variable $x_j$, temporarily solve both child LPs and score the branch using the observed deterioration.

If the current LP bound is $\bar c_Q$ and the child LP values are $\bar c^-_j$ and $\bar c^+_j$, then for maximization the observed loss is

$$
(\bar c_Q - \bar c^-_j) + (\bar c_Q - \bar c^+_j).
$$

Pedagogical idea:

- expensive but informative,
- often chooses very strong branching variables,
- good for demonstrating why “thinking harder now” may reduce the tree later.

### 4. Hybrid Strong/Pseudocost

Config value: `hybrid_strong_pseudocost`

Use strong branching while the pseudocost history is still sparse, then switch to pseudocost branching.

Pedagogical idea:

- warm-start the learning process with real probes,
- then exploit cheaper historical estimates.

### 5. Pseudocost with Strong Initialization

Config value: `pseudocost_strong_init`

Run strong probing at the beginning to initialize pseudocosts, then use pseudocost branching afterwards.

Pedagogical idea:

- separates “initial training” from “fast production mode”.

### 6. Reliability Branching

Config value: `reliability`

If the pseudocost history of a variable is not reliable enough, use a strong probe; otherwise use pseudocost estimates.

In the implementation, reliability is tied to the number of directional samples already collected.

Pedagogical idea:

- combine the robustness of strong branching with the efficiency of pseudocosts,
- ideal for discussing exploration vs exploitation.

## Node Selection Rules

Node selection decides which open subproblem to process next.

### 1. Depth-First Search

Config value: `depth_first_search`

Process the most recently created eligible node first.

Pedagogical interpretation:

- usually finds feasible solutions early,
- uses little memory,
- may wander into poor parts of the tree.

### 2. Breadth-First Search

Config value: `breadth_first_search`

Process nodes in first-in, first-out order.

Pedagogical interpretation:

- explores the tree level by level,
- visually easy to explain,
- often slower to find incumbents.

### 3. Best-Bound Search

Config value: `best_first_search`

For maximization, choose the open node with largest LP bound:

$$
Q^* \in \arg\max_{Q \in \mathcal{L}} \bar c_Q
$$

where $\mathcal{L}$ is the set of open leaves.

Pedagogical interpretation:

- tends to process fewer nodes,
- focuses on promising dual bounds,
- may stay far from integer-feasible regions.

### 4. Best Estimate Search

Config value: `best_estimate_search`

This project implements a pseudocost-based best estimate rule.

For a node $Q$ with LP solution $\bar x$, the estimate is:

$$
e_Q = \bar c_Q - \sum_{j \in I_f} \min\{\Psi^-_j f^-_j,\; \Psi^+_j f^+_j\}
$$

for maximization, where:

- $I_f$ is the set of fractional integer variables,
- $\Psi^-_j,\Psi^+_j$ are directional pseudocosts,
- $f^-_j,f^+_j$ are distances to the nearest integers.

Intuition:

- best-bound only asks “how good is the LP bound?”,
- best-estimate asks “how good might an integer solution in this subtree be after rounding pressure is paid?”.

This is often a more “primal-aware” choice than plain best-bound selection.

### 5. Best-First Search with Plunging

Config value: `best_first_search_with_plunging`

This mixes:

- a global best-bound restart,
- local DFS-style movement through children/siblings.

In this code:

- when no plunge is active, choose the best-bound open node,
- once branching occurs, prefer continuing down the selected local direction,
- when that plunge exhausts itself, jump back to the globally best open leaf.

Pedagogical interpretation:

- a nice compromise between aggressive global ranking and local solution hunting.

### 6. Interleaved Best Estimate / Best First Search

Config value: `interleaved_best_estimate_best_first_search`

This rule combines:

- best-estimate ranking,
- periodic best-bound correction,
- plunging.

In the implementation, plunging is still local as above, but when a new global restart is needed the selector chooses:

- the best-bound node every `bestfreq` restarts,
- the best-estimate node otherwise.

The default in the code is

$$
\texttt{bestfreq} = 10.
$$

So the global choice alternates between:

$$
Q^* \in \arg\max_{Q \in \mathcal{L}} \bar c_Q
\qquad\text{and}\qquad
Q^* \in \arg\max_{Q \in \mathcal{L}} e_Q.
$$

Pedagogical interpretation:

- keeps the primal-awareness of best estimate,
- but revisits the global dual bound often enough that students can see dual progress,
- useful for discussing anytime behavior and quality guarantees.

### 7. Hybrid Best Estimate / Best First Search

Config value: `hybrid_best_estimate_best_first_search`

This rule also uses plunging, but scores each open node with a convex combination of its best-estimate value and its LP bound.

For maximization, the implementation uses

$$
s_Q = \omega e_Q + (1-\omega)\bar c_Q,
$$

and selects

$$
Q^* \in \arg\max_{Q \in \mathcal{L}} s_Q.
$$

The default in the code is

$$
\omega = 0.1.
$$

Hence the dual bound receives most of the weight, while the estimate mainly breaks ties among nodes with similar LP bounds.

Pedagogical interpretation:

- smoother than hard interleaving,
- easy to discuss as a weighted tradeoff between dual-bound focus and primal promise,
- a nice example of heuristic blending in modern solvers.

## Child Selection Rules

When branching on a variable, child selection decides which of the two children should be explored first. This matters especially for:

- `depth_first_search`
- `best_first_search_with_plunging`

because these strategies actually follow a local direction.

### 1. Downwards Selection

Config value: `downwards`

Always visit

$$
x_j \le \lfloor \bar x_j \rfloor
$$

first.

### 2. Upwards Selection

Config value: `upwards`

Always visit

$$
x_j \ge \lceil \bar x_j \rceil
$$

first.

### 3. Pseudocost Child Selection

Config value: `pseudocost`

Prefer the direction with smaller predicted deterioration:

$$
\Psi^-_j f^-_j
\quad\text{vs}\quad
\Psi^+_j f^+_j.
$$

### 4. LP Value Selection

Config value: `lp_value`

Go toward the nearest integer:

$$
\text{choose down if } f^-_j \le \tfrac12,
\qquad
\text{otherwise choose up.}
$$

### 5. Root LP Value Selection

Config value: `root_lp_value`

Compare the current value $\bar x_j$ to its root LP value $(\bar x^R)_j$:

$$
\text{choose down if } \bar x_j \le (\bar x^R)_j,
\qquad
\text{otherwise choose up.}
$$

This tries to continue the variable's movement relative to the root relaxation.

### 6. Inference Selection

Config value: `inference`

The code keeps directional inference-history proxies

$$
\Phi^-_j,\qquad \Phi^+_j
$$

based on how many integral/fixed effects appear after probing. The preferred direction is the larger one.

Pedagogical interpretation:

- choose the branch expected to create stronger propagation or simplification.

### 7. Hybrid Inference / Root-LP Selection

Config value: `hybrid_inference_root_lp`

The implemented score mirrors the qualitative form

$$
(\Phi^-_j + \varepsilon)\big((\bar x^R)_j - \bar x_j + 1\big)
\quad\text{vs}\quad
(\Phi^+_j + \varepsilon)\big(\bar x_j - (\bar x^R)_j + 1\big),
$$

and chooses the larger side.

Pedagogical interpretation:

- combine a “move like the root trend” idea with a “prefer stronger inference” idea.

## Comparison Mode

One of the nicest features for teaching is that the same instance can be run under multiple node-selection strategies.

In [`bnb_basic.py`](./bnb_basic.py), set:

```python
COMPARE_STRATEGIES = ["depth_first_search", "best_first_search", "best_estimate_search", "best_first_search_with_plunging", "breadth_first_search"]
```

The generated viewer shows:

- one comparison card per strategy,
- total nodes and total steps,
- first incumbent step,
- full incumbent history in order,
- the detailed trace for the currently selected strategy.

This is especially useful for classroom questions like:

- Why does DFS often find incumbents earlier?
- Why can best-bound process fewer nodes but still feel less “solution-oriented”?
- When does best-estimate outperform pure best-bound?
- How does plunging change the rhythm of the search?

## Suggested Classroom Experiments

### Experiment 1: DFS vs Best-Bound

Keep the same branching and child rules, compare:

```python
COMPARE_STRATEGIES = ["depth_first_search", "best_first_search"]
```

Ask students to observe:

- which method finds the first incumbent earlier,
- which method closes the tree with fewer processed nodes,
- whether a better dual strategy automatically means better primal progress.

### Experiment 2: Best-Bound vs Best-Estimate

Use:

```python
COMPARE_STRATEGIES = ["best_first_search", "best_estimate_search"]
```

Ask:

- how integrality information changes the search,
- whether the estimate gives a more “primal-minded” trajectory.

### Experiment 3: Effect of Child Selection

Fix the node selector to `depth_first_search` or `best_first_search_with_plunging`, then vary:

- `downwards`
- `upwards`
- `pseudocost`
- `root_lp_value`

Ask:

- does the solver enter good incumbent regions earlier?
- how sensitive is the plunge direction to child ordering?

### Experiment 4: Strong vs Reliability

Fix node selection and compare branching:

- `strong`
- `reliability`
- `pseudocost`

Ask:

- when is spending more work at a node worth it?
- how much “learning” is enough before we trust pseudocosts?

## A Note on Scientific Interpretation

This code is a teaching implementation, not a production MIP solver. That matters:

- the ideas are mathematically meaningful,
- the instrumentation is pedagogically useful,
- but some solver statistics here are simplified proxies of what industrial solvers compute more carefully.

That is a strength for teaching. Students can:

- understand the concepts,
- read the implementation,
- modify the policy rules,
- and immediately see how mathematical modeling choices affect search behavior.

## Good Student Questions

Some questions that usually lead to productive discussion:

1. Why can a node with the best LP bound still be poor for finding an integer solution?
2. Why do we need separate “branching variable”, “next node”, and “child direction” decisions?
3. What information is local to a node, and what information is global across the tree?
4. When should a solver spend time probing versus using learned statistics?
5. Which policy is most “primal”, which is most “dual”, and which tries to balance both?

## Summary

This project separates three decisions in branch-and-bound:

1. Which variable should we branch on?
2. Which open node should we process next?
3. Which child should we inspect first?

That separation is exactly what makes it such a useful teaching tool. Students can see that branch-and-bound is not a single algorithmic choice, but a family of interacting strategies grounded in optimization, estimation, and search design.
