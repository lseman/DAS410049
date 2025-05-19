# SOS1 and SOS2 branching

---

## 📚 Table of Contents

1. [Introduction to Degradation](#what-is-degradation)
2. [General Formulation](#general-form-of-degradation)
2. [Pseudo-Shadow Prices](#pseudo-shadow-price)

   * [Motivation and Definition](#what-is-a-pseudo-shadow-price)
   * [How They Are Used](#how-they-are-used)
   * [Beale & Forrest Assignment Rules](#rules-from-beale--forrest-section-3)
   * [Why Pseudo-Shadow Prices Matter](#why-it-matters)
3. [Degradation for SOS1](#sos1-specific-formulation)

   * [Degradation Formula for SOS1](#sos1-specific-formulation)
   * [Numerical Example: SOS1 with Reference Row](#numerical-example-sos1-degradation-estimation-with-reference-row)
4. [Degradation for SOS2](#sos2-degradation)

   * [Numerical Example: SOS2 with Piecewise Linearization](#numerical-example-sos2-degradation-estimation-with-piecewise-constraints)
5. [How Degradation Guides Branching](#how-is-degradation-used-for-branching)

   * [Selecting the Set to Branch On](#step-2-select-the-most-degrading-set)
   * [Choosing the Branch Point](#step-3-determine-where-to-branch-within-the-set)
6. [Summary Tables](#summary)

   * [Full Derivations or Additional Figures](#appendix)

---

# Degradation

## What Is Degradation?

In the context of branch-and-bound algorithms using **Special Ordered Sets (SOS1 or SOS2)**, the term **degradation** refers to the estimated **reduction in the objective value** (or increase in infeasibility) that would result from enforcing the integrality or SOS constraints on a variable set that is currently **fractionally assigned** in the LP relaxation.

It quantifies how much “worse” the LP solution might get if we force it to be **feasible with respect to the SOS structure**.

---

### General Form of Degradation

Let:

* $a_{Ak}$: actual contribution of the infeasible LP solution (vector-valued if more than one constraint)
* $a_{Ck}$: corrected contribution from a feasible (SOS1/SOS2-respecting) point
* $\pi_i$: shadow price of constraint $i$
* $p_i^+, p_i^-$: pseudo-shadow prices

Then, Beale & Forrest define the **general degradation score** for a set $k$ as:

$$
D_{Ak} = \sum_i \max \left\{
p_i^+ \cdot (a_{Cik} - a_{Aik}),\ 
- p_i^- \cdot (a_{Cik} - a_{Aik}),\ 
\pi_i \cdot (a_{Cik} - a_{Aik})
\right\}
\tag{12}
$$

This expression accounts for:

* the true marginal value of constraint violations via $\pi_i$,
* and surrogate values when $\pi_i = 0$ (e.g., non-binding constraints), using the pseudo prices $p_i^+, p_i^-$.

---

### SOS1-Specific Formulation

In the case of an **SOS1** set, Beale & Forrest use **two possible corrected contributions** (at the interval endpoints) and take the minimum degradation:

$$
D_{Ak} = \min(D_{Ak}^-, D_{Ak}^+) \tag{13}
$$

with

$$
D_{Ak}^- = \sum_i \max \left\{
p_i^+ (a_{Cik}^- - a_{Aik}),
- p_i^- (a_{Cik}^- - a_{Aik}),
\pi_i (a_{Cik}^- - a_{Aik})
\right\}
$$

$$
D_{Ak}^+ = \sum_i \max \left\{
p_i^+ (a_{Cik}^+ - a_{Aik}),
- p_i^- (a_{Cik}^+ - a_{Aik}),
\pi_i (a_{Cik}^+ - a_{Aik})
\right\}
$$

These two evaluations simulate what would happen if the current fractional LP solution were replaced by one of the two feasible (SOS1-valid) single-variable assignments.

---

## How Is Degradation Used for Branching?

The goal of a branch-and-bound algorithm is to eliminate infeasibility by branching on the **most promising set**, i.e., the one whose correction would result in the largest impact (worsening) on the LP objective.

Thus, the branching strategy proceeds as follows:

---

### Step 1: Compute Degradation for Each Candidate Set

For each SOS set $k$, compute its degradation score $D_{Ak}$ as shown above.

---

### Step 2: Select the Most Degrading Set

Select the set $k^*$ with the **largest degradation**:

$$
k^* = \arg\max_k D_{Ak} \tag{14}
$$

This identifies the SOS set most responsible for the LP solution being overly optimistic (violating integrality/SOS structure), and where enforcing feasibility could most significantly correct the estimate.

---

### Step 3: Determine Where to Branch Within the Set

Once $k^*$ is chosen, we must decide **where** to branch. Beale & Forrest propose:

* **For SOS1**: choose which interval endpoint to favor
* **For SOS2**: compute the **discrepancy function**:

$$
D_{Ik}(t) = \sum_i \max\left\{
p_i^+ (a_i(t) - \tilde{a}_i(t)),
- p_i^- (a_i(t) - \tilde{a}_i(t)),
\pi_i (a_i(t) - \tilde{a}_i(t))
\right\} \tag{15}
$$

where $\tilde{a}_i(t)$ is the linear interpolation of coefficients at $t$, and $a_i(t)$ is the true coefficient function.

The value of $t$ maximizing $D_{Ik}(t)$ is selected as the **branch point**.

---

## Summary

| Component                | Formula                                                       | Purpose                                        |
| ------------------------ | ------------------------------------------------------------- | ---------------------------------------------- |
| General degradation      | $D_{Ak} = \sum_i \max\{p_i^+, -p_i^-, \pi_i\} \cdot \Delta a$ | Quantify loss when enforcing feasibility       |
| SOS1 degradation         | $D_{Ak} = \min(D_{Ak}^-, D_{Ak}^+)$                           | Pick best among two feasible endpoints         |
| Best set to branch on    | $k^* = \arg\max_k D_{Ak}$                                     | Choose set contributing most to error          |
| Branch point (SOS2 only) | $t^* = \arg\max_t D_{Ik}(t)$                                  | Identify location where approximation is worst |

This approach ensures that branching focuses effort on the most critical errors in the LP relaxation, while remaining computationally efficient due to local evaluations (no need to re-solve LPs for every branching possibility).

---

# Pseudo-Shadow Price
---

## What Is a Pseudo-Shadow Price?

In linear programming, the **shadow price** $\pi_i$ of a constraint measures how much the objective value would improve if the right-hand side $b_i$ of constraint $i$ were increased by one unit — **but only if the constraint is binding**.

However, when solving the LP relaxation of a MIP with **SOS1/SOS2 constraints**, many of the constraints are **non-binding** at the current solution. For example:

* A constraint might have positive slack, meaning it's not tight at the solution.
* The associated shadow price $\pi_i = 0$, giving no useful signal for branching.

This creates a problem for estimating degradation:

* If we use only $\pi_i$, we **underestimate** the impact of correcting the solution.
* This can cause the algorithm to ignore important sets during branching.

---

## The Pseudo-Shadow Price

Beale & Forrest introduce two additional parameters:

$$
p_i^+ \geq 0,\quad p_i^- \geq 0
$$

These are called **pseudo-shadow prices**, and they are designed to:

* Assign **a small but positive value** to constraint violations,
* Even when the true shadow price $\pi_i = 0$.

These are not derived from the LP dual but are **heuristically assigned constants**, typically small:

$$
p_i^+ = p_i^- = 10^{-4}
$$

They represent a “default cost” of deviating from feasibility, ensuring that even constraints with zero shadow price exert **some influence** on the degradation estimate.

---

## How They Are Used

In degradation formulas (e.g., for SOS1):

$$
D_{Ak}^- = \sum_i \max \left\{
p_i^+ (a_{Cik}^- - a_{Aik}),
- p_i^- (a_{Cik}^- - a_{Aik}),
\pi_i (a_{Cik}^- - a_{Aik})
\right\}
$$

Here:

* $\pi_i \cdot \Delta a_i$ is used if the shadow price is informative.
* Otherwise, the pseudo-shadow prices ensure we **still get a nonzero degradation** for rows where $\Delta a_i \neq 0$, even if $\pi_i = 0$.

---

## Rules from Beale & Forrest (Section 3)

They propose rules for assigning pseudo-shadow prices:

* **Objective row**:

  * $p_i^+ = p_i^- = 0$ (since degradation is computed *toward* improving objective).
* **Constraint row with negative slack**:

  * $p_i^+ = 0$, $p_i^- > 0$
* **Constraint row with positive slack**:

  * $p_i^- = 0$, $p_i^+ > 0$
* **Otherwise**:

  * Both pseudo-prices are strictly positive (e.g., $10^{-4}$).

This enforces **directional sensitivity**:

* We only penalize worsening the slack direction.
* This helps guide the branching to correct errors without over-penalizing neutral directions.

---

## Why It Matters

* Prevents branching logic from **ignoring important but non-binding constraints**.
* Acts as a **fallback** when LP dual information is weak.
* Analogous to **pseudo-costs** in modern MIP solvers, which accumulate cost estimates from past branching decisions.

---

## Summary

| Term              | Meaning                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| $\pi_i$           | Dual shadow price from LP (0 if constraint is non-binding)                                            |
| $p_i^+, p_i^-$    | Manually defined pseudo-shadow prices for estimating degradation                                      |
| Role in branching | Ensure that all sets can be evaluated for importance, even if LP solution doesn’t show immediate cost |
| Common values     | $10^{-4}$, or adaptive small positive constants                                                       |

Together with the actual contributions and corrected values, **pseudo-shadow prices** provide the algorithm with the robustness needed to make informed branching choices even in early or degenerate LP relaxations.

---

# SOS1 Degradation

## Numerical Example: SOS1 Degradation Estimation with Reference Row

We define a Special Ordered Set of type 1 (SOS1) over breakpoints:

$$
t_j \in \{0, 1, 2, 3\}, \quad j = 0,1,2,3
$$

Let the SOS1 variables be $x_0, x_1, x_2, x_3$, associated with each $t_j$, and used to model a discrete input $t$ as a convex representation:

---

### 1. **Constraints**

#### Convexity (SOS1):

$$
\sum_{j=0}^{3} x_j = 1 \tag{1}
$$

#### Reference Row:

$$
\sum_{j=0}^{3} t_j \cdot x_j = t \tag{2}
$$

This implies:

$$
t = 0 \cdot x_0 + 1 \cdot x_1 + 2 \cdot x_2 + 3 \cdot x_3 \tag{3}
$$

Note: Under SOS1 feasibility, only one $x_j = 1$, so $t \in \{0,1,2,3\}$. But in LP relaxation, $t$ may take fractional values.

---

### 2. **Row Coefficients**

Let the coefficient row be derived from a function $a(t)$, with:

| $t_j$ | $a(t_j)$ |
| ----- | -------- |
| 0     | 2        |
| 1     | 3        |
| 2     | 4        |
| 3     | 7        |

Let this define the coefficients in some constraint or objective row:

$$
\text{Row: } a(t) = [2, 3, 4, 7] \tag{4}
$$

---

### 3. **Infeasible LP Relaxation**

Assume the LP gives:

$$
x_0 = 0.1,\quad x_1 = 0.3,\quad x_2 = 0.6,\quad x_3 = 0 \tag{5}
$$

This violates SOS1 (more than one $x_j > 0$).

---

### 4. **Compute Reference Value $\bar{t}$**

From the reference row:

$$
\bar{t} = \sum_j t_j x_j = 0.1 \cdot 0 + 0.3 \cdot 1 + 0.6 \cdot 2 = 1.5 \tag{6}
$$

---

### 5. **Actual Contribution $a_{Ak}$**

$$
a_{Ak} = - \sum_j x_j \cdot a(t_j)
= - (0.1 \cdot 2 + 0.3 \cdot 3 + 0.6 \cdot 4) = - (0.2 + 0.9 + 2.4) = -3.5 \tag{7}
$$

---

### 6. **Determine Endpoints of the Interval Containing $\bar{t}$**

From $\bar{t} = 1.5$, endpoints are:

* $t_k^- = 1$, with $a(1) = 3$
* $t_k^+ = 2$, with $a(2) = 4$

---

### 7. **Corrected Contributions**

We follow Beale & Forrest’s formula (3.6) for SOS1:

$$
a_{Ck}^- = (1.0 - 0) \cdot a(t_k^-) = 3 \\
a_{Ck}^+ = (1.0 - 0) \cdot a(t_k^+) = 4 \tag{8}
$$

---

### 8. **Compute Differences**

$$
a_{Ck}^- - a_{Ak} = 3 - (-3.5) = 6.5 \\
a_{Ck}^+ - a_{Ak} = 4 - (-3.5) = 7.5 \tag{9}
$$

---

### 9. **Degradation Estimation**

Assume:

* Shadow price $\pi = 1.3$
* Pseudo shadow prices $p^+ = p^- = 0.0001$

We compute:

$$
D_{Ak}^- = \max\{0.0001 \cdot 6.5,\ -0.0001 \cdot 6.5,\ 1.3 \cdot 6.5\} = \max\{0.00065,\ -0.00065,\ 8.45\} = 8.45 \\
D_{Ak}^+ = \max\{0.0001 \cdot 7.5,\ -0.0001 \cdot 7.5,\ 1.3 \cdot 7.5\} = \max\{0.00075,\ -0.00075,\ 9.75\} = 9.75 \tag{10}
$$

So the final degradation is:

$$
D_{Ak} = \min(D_{Ak}^-, D_{Ak}^+) = \min(8.45,\ 9.75) = \boxed{8.45} \tag{11}
$$

---

# SOS2 Degradation

## Numerical Example: SOS2 Degradation Estimation with Piecewise Constraints

We aim to approximate a nonlinear function $a(t) = t^2$ using **piecewise linear interpolation** over breakpoints $t = 0, 1, 2, 3$ with SOS2 structure.

### Step 0: Define the SOS2 Structure

Let the variables $\lambda_0, \lambda_1, \lambda_2, \lambda_3$ represent the weights at breakpoints $T_0 = 0, T_1 = 1, T_2 = 2, T_3 = 3$.

---

### 1. **Constraints**

#### 1.1 Convexity Constraint:

$$
\lambda_0 + \lambda_1 + \lambda_2 + \lambda_3 = 1 \tag{1}
$$

#### 1.2 Reference Constraint (a.k.a. Reference Row):

$$
0 \cdot \lambda_0 + 1 \cdot \lambda_1 + 2 \cdot \lambda_2 + 3 \cdot \lambda_3 = t \tag{2}
$$

#### 1.3 SOS2 Constraint:

At most two $\lambda_j$ can be nonzero, and they must be adjacent.

---

### 2. **Coefficient Function**

Let the function $a(t) = t^2$ have corresponding **row coefficients**:

| $t_j$ | $a(t_j)$  |
| ----- | --------- |
| 0     | $a_0 = 0$ |
| 1     | $a_1 = 1$ |
| 2     | $a_2 = 4$ |
| 3     | $a_3 = 9$ |

Assume the coefficient row in the LP is:

$$
a(t) = [0,\ 1,\ 4,\ 9] \tag{3}
$$

---

### 3. **Infeasible LP Solution (violating SOS2)**

Suppose we get an LP relaxation solution:

$$
\lambda_0 = 0.3,\quad \lambda_1 = 0,\quad \lambda_2 = 0.7,\quad \lambda_3 = 0 \tag{4}
$$

This violates SOS2 feasibility (nonzero values at non-adjacent positions: $\lambda_0$ and $\lambda_2$).

We now compute the **actual contribution**, **corrected contribution**, and estimate degradation as in Beale & Forrest’s approach.

---

### 4. **Actual Contribution**

Using equation (3.3) from Beale & Forrest:

$$
a_{Ak} = -\sum_j \lambda_j \cdot a(t_j)
= - (0.3 \cdot 0 + 0 \cdot 1 + 0.7 \cdot 4 + 0 \cdot 9)
= -2.8 \tag{5}
$$

---

### 5. **Compute Reference Value $\bar{t}$**

This is computed using the reference constraint:

$$
\bar{t} = \sum_j T_j \cdot \lambda_j = 0.3 \cdot 0 + 0 \cdot 1 + 0.7 \cdot 2 = 1.4 \tag{6}
$$

---

### 6. **Interpolated Coefficient at $\bar{t} = 1.4$**

We interpolate $a(1.4)$ between $a(1) = 1$ and $a(2) = 4$:

$$
a(1.4) = (1 - 0.4) \cdot 1 + 0.4 \cdot 4 = 0.6 \cdot 1 + 0.4 \cdot 4 = 0.6 + 1.6 = 2.2 \tag{7}
$$

---

### 7. **Corrected Contribution**

From equation (3.3) in the paper:

$$
a_{Ck} = (1.0 - 0) \cdot a(\bar{t}) = 2.2 \tag{8}
$$

---

### 8. **Degradation Estimation**

Now compute:

$$
a_{Ck} - a_{Ak} = 2.2 - (-2.8) = 5.0 \tag{9}
$$

Assume:

* Shadow price $\pi_i = 1.5$
* Pseudo shadow prices $p_i^+ = p_i^- = 0.0001$

Then from Beale & Forrest’s degradation formula for SOS2 sets:

$$
D_{Ak} = \max\left\{
0.0001 \cdot 5.0,\ -0.0001 \cdot 5.0,\ 1.5 \cdot 5.0
\right\} = \max\{0.0005,\ -0.0005,\ 7.5\} = 7.5 \tag{10}
$$

---

## Result

$$
\boxed{\text{Estimated degradation } D_{Ak} = 7.5}
$$

This is the predicted reduction in the objective if we enforce SOS2 feasibility (i.e., restrict to adjacent non-zero $\lambda_j$).
