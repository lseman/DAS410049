# Presolve Techniques in Mixed Integer Programming

## Introduction

This tutorial explains key presolve techniques based on the work of Achterberg et al. (2016) in "Presolve Reductions in Mixed Integer Programming". We'll provide detailed mathematical explanations, derivations, and implementation insights for each method.

## Problem Definition and Notation

We define a Mixed Integer Programming problem as:

$$
\begin{align}
\min \quad & c^T x \\
\text{s.t.} \quad & Ax \circ b \\
& \ell \leq x \leq u \\
& x_j \in \mathbb{Z} \quad \text{for all } j \in I
\end{align}
$$

Where:
- $A \in \mathbb{R}^{m \times n}$ is the constraint coefficient matrix
- $c \in \mathbb{R}^n$ is the objective coefficient vector
- $b \in \mathbb{R}^m$ is the right-hand side vector
- $\ell, u \in (\mathbb{R} \cup \{-\infty, \infty\})^n$ are the lower and upper bounds
- $I \subseteq N = \{1, \ldots, n\}$ is the set of integer variables
- The relation $\circ_i \in \{=, \leq, \geq\}$ specifies the constraint type for each row $i \in M = \{1, \ldots, m\}$

### Activity Bounds: A Key Concept

A fundamental concept in presolve is the **activity** of a constraint - the value of the left-hand side expression under a given variable assignment. For each row $i$, we define:

**Minimal activity**: The smallest possible value of the left-hand side:
$$\inf\{A_{i\cdot}x\} := \sum_{j \in N, a_{ij} > 0} a_{ij}\ell_j + \sum_{j \in N, a_{ij} < 0} a_{ij}u_j$$

**Maximal activity**: The largest possible value of the left-hand side:
$$\sup\{A_{i\cdot}x\} := \sum_{j \in N, a_{ij} > 0} a_{ij}u_j + \sum_{j \in N, a_{ij} < 0} a_{ij}\ell_j$$

These formulas account for how each coefficient's sign affects the activity:
- For positive coefficients, the minimal activity occurs at the variable's lower bound, and the maximal at its upper bound
- For negative coefficients, the minimal activity occurs at the variable's upper bound, and the maximal at its lower bound

We can similarly define activities for subsets of variables, which is critical for many presolve techniques.

## 1. Single-Row Reductions

### 1.1 Bound Strengthening (Domain Propagation)

Bound strengthening uses a single constraint to derive tighter bounds on variables. For a constraint:

$$A_{iS}x_S + a_{ik}x_k \leq b_i$$

Where $S = \text{supp}(A_{i\cdot}) \setminus \{k\}$ (all variables in the constraint except $x_k$) and $a_{ik} \neq 0$, we want to calculate how the bounds on other variables constrain $x_k$.

**Step 1**: Calculate a lower bound on the activity of the other terms:
$$\ell_{iS} \leq A_{iS}x_S \text{ for all } x \in P_{MIP}$$

In practice, for single-row bound strengthening, we use $\ell_{iS} = \inf\{A_{iS}x_S\}$ calculated using the formula for minimal activity.

**Step 2**: Derive new bounds for $x_k$ based on $\ell_{iS}$. Since $A_{iS}x_S \geq \ell_{iS}$, we have:
$$A_{iS}x_S + a_{ik}x_k \leq b_i \implies a_{ik}x_k \leq b_i - A_{iS}x_S \leq b_i - \ell_{iS}$$

For $a_{ik} > 0$, this gives an upper bound:
$$x_k \leq \min\Big(u_k,\frac{b_i - \ell_{iS}}{a_{ik}}\Big)$$

For $a_{ik} < 0$, this gives a lower bound:
$$x_k \geq \max\Big(l_k,\frac{b_i - \ell_{iS}}{a_{ik}})$$

**Step 3**: For integer variables ($k \in I$), we can strengthen these bounds further by rounding:
- For upper bounds: $x_k \leq \lfloor(b_i - \ell_{iS})/a_{ik}\rfloor$ when $a_{ik} > 0$
- For lower bounds: $x_k \geq \lceil(b_i - \ell_{iS})/a_{ik}\rceil$ when $a_{ik} < 0$

**Example**:
Consider the constraint $2x_1 + 3x_2 - 4x_3 \leq 10$ with bounds $0 \leq x_1, x_2, x_3 \leq 5$.

For $x_1$:
- Calculate $\ell_{iS} = \inf\{3x_2 - 4x_3\} = 3 \cdot 0 - 4 \cdot 5 = -20$
- Derive new bound: $x_1 \leq \frac{10 - (-20)}{2} = 15$
- This is not tighter than the existing bound $x_1 \leq 5$

For $x_3$:
- Calculate $\ell_{iS} = \inf\{2x_1 + 3x_2\} = 2 \cdot 0 + 3 \cdot 0 = 0$
- Derive new bound: $x_3 \geq \frac{0 - 10}{-4} = 2.5$
- This is tighter than the existing bound $x_3 \geq 0$, so update $x_3 \geq 2.5$

**Implementation Pseudocode**:
```
function BoundStrengthening(constraint, variables):
    for each variable x_k in constraint:
        # Calculate lower bound on other terms
        ℓ_iS = calculate_min_activity(constraint without x_k)
        
        coef = coefficient of x_k in constraint
        if coef > 0:  # Derive upper bound
            new_ub = (RHS - ℓ_iS) / coef
            if x_k is integer:
                new_ub = floor(new_ub)
            if new_ub < current_upper_bound(x_k):
                update_upper_bound(x_k, new_ub)
                
        elif coef < 0:  # Derive lower bound
            new_lb = (RHS - ℓ_iS) / coef
            if x_k is integer:
                new_lb = ceiling(new_lb)
            if new_lb > current_lower_bound(x_k):
                update_lower_bound(x_k, new_lb)
```

---

### 1.2 Coefficient Strengthening

Coefficient strengthening modifies coefficients of integer variables to tighten the LP relaxation while preserving all integer feasible solutions. This technique exploits the integrality of variables to create constraints that are equivalent for integer solutions but stronger for continuous relaxations.

Consider an inequality constraint:
$$A_{iS}x_S + a_{ik}x_k \leq b_i$$

where $x_k \in \mathbb{Z}$ is an integer variable with $\ell_k \leq x_k \leq u_k$.

The key insight behind coefficient strengthening is that when variables are restricted to integer values, there exists "slack" in the constraint that can be exploited to tighten the LP relaxation without affecting the integer feasible region.

**Notice:** A constraint $a'x \leq b'$ dominates another constraint $ax \leq b$ if:
$$\{x \in \mathbb{R}^n | \ell \leq x \leq u, ax \leq b\} \subset \{x \in \mathbb{R}^n | \ell \leq x \leq u, a'x \leq b'\}$$

Our goal is to find a dominating constraint that is equivalent for all integer solutions.

**Step 1**: Calculate the Activity Bound

First, calculate $u_{iS}$, the upper bound on the activity of other terms:
$$u_{iS} = \sup\{A_{iS}x_S\}$$

This represents the maximum value that the sum of all terms except for $a_{ik}x_k$ can achieve across all integer feasible solutions. This bound is crucial for determining how much we can tighten the constraint.

**Step 2**: Positive Coefficient Case

For a positive coefficient $a_{ik} > 0$ with finite upper bound $u_k$, we calculate the strengthening factor:
$$d = b_i - u_{iS} - a_{ik}(u_k - 1)$$

The intuition for this formula:
- $b_i - a_{ik}(u_k - 1)$ represents the right-hand side limit for $A_{iS}x_S$ when $x_k = u_k - 1$
- Subtracting $u_{iS}$ gives us the "slack" available for strengthening
- If this slack is positive ($d > 0$), we can tighten the constraint

If $d > 0$, we can strengthen the constraint to:
$$A_{iS}x_S + (a_{ik} - d)x_k \leq b_i - du_k$$

This transformation reduces the coefficient of $x_k$ while adjusting the right-hand side to maintain equivalence for integer solutions.

To understand why this works, let's verify the constraint at critical integer values:

**For $x_k = u_k$ (upper bound):**
- Original: $A_{iS}x_S + a_{ik}u_k \leq b_i$
- Strengthened: $A_{iS}x_S + (a_{ik} - d)u_k \leq b_i - du_k$
- Expanding: $A_{iS}x_S + a_{ik}u_k - du_k \leq b_i - du_k$
- Simplified: $A_{iS}x_S + a_{ik}u_k \leq b_i$ (identical)

**For $x_k = u_k - 1$ (one below upper bound):**
- Original: $A_{iS}x_S + a_{ik}(u_k - 1) \leq b_i$
- Strengthened: $A_{iS}x_S + (a_{ik} - d)(u_k - 1) \leq b_i - du_k$
- Expanding: $A_{iS}x_S + a_{ik}(u_k - 1) - d(u_k - 1) \leq b_i - du_k$
- Simplified: $A_{iS}x_S + a_{ik}(u_k - 1) \leq b_i - d(u_k - (u_k - 1))$
- Further: $A_{iS}x_S + a_{ik}(u_k - 1) \leq b_i - d$ (tighter by exactly $d$ units)

Since $A_{iS}x_S \leq u_{iS}$ by definition, and:
$$u_{iS} + a_{ik}(u_k - 1) \leq b_i$$

We can confirm that the strengthened constraint remains valid for all integer solutions but is tighter for the LP relaxation.

**Step 3**: Negative Coefficient Case

For a negative coefficient $a_{ik} < 0$ with finite lower bound $\ell_k$, we calculate:
$$d' = b_i - u_{iS} - a_{ik}(\ell_k + 1)$$

If $d' > 0$, we can strengthen the constraint to:
$$A_{iS}x_S + (a_{ik} + d')x_k \leq b_i + d'\ell_k$$

The reasoning is symmetric to the positive coefficient case, but we focus on the lower bound $\ell_k$ instead of the upper bound $u_k$.

#### Geometric Interpretation

Geometrically, coefficient strengthening "rotates" the constraint hyperplane around the integer feasible points, making it steeper and cutting off portions of the LP relaxation that don't contain integer solutions.

For a 2D example with $x_k$ on the horizontal axis, the strengthened constraint creates a steeper line that:
1. Passes through the same point at $x_k = u_k$
2. Is strictly tighter at $x_k = u_k - 1$
3. Creates a tighter approximation of the integer hull

function CoefficientStrengthening(constraint, variables):
    for each integer variable x_k in constraint:
        coef = coefficient of x_k in constraint
        
        # Calculate upper bound on other terms
        u_iS = calculate_max_activity(constraint without x_k)
        
        if coef > 0 and x_k has finite upper bound u_k:
            # Calculate strengthening factor for positive coefficient
            d = RHS - u_iS - coef * (u_k - 1)
            
            if d > 0:
                # Strengthen coefficient and RHS
                new_coef = coef - d
                new_rhs = RHS - d * u_k
                update_coefficient(constraint, x_k, new_coef)
                update_rhs(constraint, new_rhs)
                
        elif coef < 0 and x_k has finite lower bound ℓ_k:
            # Calculate strengthening factor for negative coefficient
            d_prime = RHS - u_iS - coef * (ℓ_k + 1)
            
            if d_prime > 0:
                # Strengthen coefficient and RHS
                new_coef = coef + d_prime
                new_rhs = RHS + d_prime * ℓ_k
                update_coefficient(constraint, x_k, new_coef)
                update_rhs(constraint, new_rhs)
                
    return constraint  # Return the strengthened constraint
---

### 1.3 GCD Coefficient Reduction

For equations with integer variables, we can divide by the greatest common divisor (GCD) of the coefficients to simplify the constraint and potentially detect infeasibility.

Consider a constraint:
$$\sum_{j=1}^{n} a_{ij}x_j \circ_i b_i$$

where all variables are integer: $\text{supp}(A_{i\cdot}) \subseteq I$.

**Step 1**: Calculate the GCD of all coefficients:
$$d = \text{gcd}(a_{i1}, \ldots, a_{in})$$

**Step 2**: Divide the constraint by $d$:
$$\sum_{j=1}^{n} \frac{a_{ij}}{d} x_j \circ_i \left\lfloor\frac{b_i}{d}\right\rfloor$$

**Step 3**: If $\circ_i = "="$ and $b_i/d \notin \mathbb{Z}$, the problem is infeasible (no integer solution exists).

**Example**:
Consider the constraint $6x_1 + 9x_2 + 15x_3 = 12$ with integer variables.

- GCD of coefficients: $\text{gcd}(6, 9, 15) = 3$
- Divide by GCD: $2x_1 + 3x_2 + 5x_3 = 4$
- Since $12/3 = 4$ is an integer, the equation is valid

If the right side were 11 instead of 12:
- $6x_1 + 9x_2 + 15x_3 = 11$
- Divide by GCD: $2x_1 + 3x_2 + 5x_3 = 11/3$
- Since $11/3$ is not an integer, the problem is infeasible

**Implementation Pseudocode**:
```
function GCDCoefficientReduction(constraint, variables):
    # Only apply to constraints with all integer variables
    if not all variables in constraint are integer:
        return false
        
    # Calculate GCD of coefficients
    d = gcd(all non-zero coefficients)
    
    if d > 1:
        # Divide coefficients and RHS by GCD
        for each coefficient in constraint:
            coefficient = coefficient / d
            
        RHS = RHS / d
        
        # Check for infeasibility
        if constraint is equality and RHS is not integer:
            mark problem as infeasible
            
        return true
    
    return false
```

## 2. Single-Column Reductions

### 2.1 Implied Free Variable Substitution

An implied free variable is one whose bounds are already implied by the constraints. Such variables can be substituted out of the problem by expressing them in terms of other variables.

For a variable $x_j$ and its bounds $\ell_j$ and $u_j$, let $\bar{\ell}_j$ and $\bar{u}_j$ be the tightest implied bounds that can be discovered using bound strengthening without exploiting the explicit bounds of $x_j$. If $[\bar{\ell}_j, \bar{u}_j] \subseteq [\ell_j, u_j]$, then $x_j$ is an implied free variable.

**Step 1**: Identify an implied free continuous variable $x_j$ that appears in an equality constraint:
$$A_{iS}x_S + a_{ij}x_j = b_i$$

**Step 2**: Solve for $x_j$:
$$x_j = \frac{b_i - A_{iS}x_S}{a_{ij}}$$

**Step 3**: Substitute this expression throughout the problem:
- Replace $x_j$ in all other constraints
- Adjust the objective function
- Remove the equality constraint used for substitution

**Numerical Considerations**: To avoid numerical issues, Gurobi applies safeguards:
- The pivot element $|a_{ij}|$ should be sufficiently large relative to other coefficients
- The estimated fill-in (increase in non-zeros) should be below a threshold

**Example**:
Consider the constraints:
```
x1 - x2 ≤ 0      (1)
x1 - x3 ≥ 0      (2)
0 ≤ x1 ≤ 1       (3)
0 ≤ x2 ≤ 1       (4)
0 ≤ x3 ≤ 1       (5)
```

Constraint (1) implies $x_1 \leq x_2 \leq 1$, and constraint (2) implies $x_1 \geq x_3 \geq 0$. These implied bounds $0 \leq x_1 \leq 1$ match the explicit bounds in constraint (3), making $x_1$ an implied free variable.

If we had another constraint:
```
x1 + 2x4 = 5     (6)
```

We could substitute $x_1 = 5 - 2x_4$ throughout the problem.

**Implementation Pseudocode**:
```
function ImpliedFreeVariableSubstitution(problem):
    for each equality constraint in problem:
        for each variable x_j in constraint:
            # Check if variable is implied free
            if is_implied_free(x_j) and not too_much_fill_in(x_j):
                # Express x_j in terms of other variables
                expr = solve_for_variable(constraint, x_j)
                
                # Substitute throughout problem
                substitute_expression(problem, x_j, expr)
                
                # Remove the equality constraint
                remove_constraint(constraint)
                
                return true
    
    return false
```

---

### 2.2 Dual Fixing

Dual fixing exploits the relationship between objective coefficients and constraint coefficients to fix variables or determine unboundedness.

Consider a variable $x_j$ that appears only in inequality constraints (not in equalities).

**Case 1**: If $c_j \geq 0$ and $a_{ij} \geq 0$ for all constraints $i$, then:
- If $u_j$ is finite, we can fix $x_j := u_j$
- If $u_j = \infty$ and $c_j < 0$, the problem is unbounded (or infeasible)

**Case 2**: If $c_j \leq 0$ and $a_{ij} \leq 0$ for all constraints $i$, then:
- If $\ell_j$ is finite, we can fix $x_j := \ell_j$
- If $\ell_j = -\infty$ and $c_j > 0$, the problem is unbounded (or infeasible)

**Intuition**:
- In Case 1, increasing $x_j$ would only make the objective worse and constraints tighter
- In Case 2, decreasing $x_j$ would only make the objective worse and constraints tighter

**Example**:
Consider the problem:
```
min x1 + x2 + x3
2x1 + 4x2 - 3x3 ≤ 8   (1)
-x2 - x3 ≤ -4        (2)
-2x1 - 2x2 + x3 ≤ 6   (3)
0 ≤ x1, x2, x3 ≤ 10
```

For $x_3$, we have $c_3 = 1 > 0$, but the coefficients $a_{13} = -3 < 0$, $a_{23} = -1 < 0$, and $a_{33} = 1 > 0$ have mixed signs, so dual fixing doesn't apply.

**Implementation Pseudocode**:
```
function DualFixing(problem):
    for each variable x_j in problem:
        # Skip variables that appear in equalities
        if x_j appears in any equality constraint:
            continue
            
        # Check Case 1: c_j ≥ 0 and all a_ij ≥ 0
        if objective_coefficient(x_j) ≥ 0 and all_coefficients_non_negative(x_j):
            if lower_bound(x_j) is finite:
                fix_variable(x_j, lower_bound(x_j))
                return true
            elif objective_coefficient(x_j) > 0:
                mark problem as unbounded
                return true
                
        # Check Case 2: c_j ≤ 0 and all a_ij ≤ 0
        if objective_coefficient(x_j) ≤ 0 and all_coefficients_non_positive(x_j):
            if upper_bound(x_j) is finite:
                fix_variable(x_j, upper_bound(x_j))
                return true
            elif objective_coefficient(x_j) < 0:
                mark problem as unbounded
                return true
    
    return false
```

## 3. Multi-Row and Advanced Techniques

### 3.1 Probing

Probing is one of the most powerful presolve techniques, especially for MIPs with binary variables. It involves temporarily fixing binary variables to 0 or 1 and analyzing the implications through domain propagation.

**Basic Steps**:

1. **Select a binary variable** $x_k$ for probing
2. **Try setting $x_k = 0$**:
   - Propagate this assignment through all constraints
   - Record any implied bounds on other variables
   - Check if this assignment leads to infeasibility
3. **Try setting $x_k = 1$**:
   - Repeat the propagation process
   - Record implied bounds
   - Check for infeasibility
4. **Analyze results**:
   - If both $x_k = 0$ and $x_k = 1$ lead to infeasibility, the problem is infeasible
   - If one setting leads to infeasibility, fix $x_k$ to the other value
   - If both settings are feasible, identify common implications and clique relationships

**Lifting**: If setting $x_k = 1$ implies a minimum slack $d > 0$ in a constraint $ax \leq b$, we can strengthen the constraint to $ax + dx_k \leq b$.

**Full Propagation Process**:
When a binary variable is fixed, we propagate through constraints systematically:

1. For a constraint $Ax \leq b$, calculate the minimal and maximal activities excluding variables that have been fixed
2. Use these activities to derive bounds on unfixed variables
3. If new bounds are derived, add those variables to a queue for further propagation
4. Continue until no more bounds can be tightened

**Implementation Pseudocode**:
```
function Probing(problem):
    for each binary variable x_k in problem:
        # Try setting x_k = 0
        implications_0 = probe_setting(problem, x_k, 0)
        
        # Try setting x_k = 1
        implications_1 = probe_setting(problem, x_k, 1)
        
        # Check results
        if implications_0 is null and implications_1 is null:
            mark problem as infeasible
            return true
            
        if implications_0 is null:
            # x_k = 0 is infeasible, so fix x_k = 1
            fix_variable(x_k, 1)
            return true
            
        if implications_1 is null:
            # x_k = 1 is infeasible, so fix x_k = 0
            fix_variable(x_k, 0)
            return true
            
        # Find global implications (bounds that change in both cases)
        apply_global_implications(implications_0, implications_1)
        
        # Perform lifting
        for each constraint in problem:
            if constraint can be lifted using implications:
                perform_lifting(constraint, x_k, implications_1)
                
    return false
```

### 3.2 Parallel Row Detection

Parallel row detection identifies constraints that are scalar multiples of each other and either removes redundant constraints or detects infeasibility.

**Basic Steps**:

1. For each pair of rows $q, r \in M$, check if $A_{q\cdot} = sA_{r\cdot}$ for some $s \neq 0$
2. If the rows are parallel, analyze the conditions:
   - For equations: If $b_q = sb_r$, row $r$ is redundant; if $b_q \neq sb_r$, the problem is infeasible
   - For inequalities: Rules depend on the signs of $s$ and the constraint senses

**Implementation Considerations**:
- Use hashing to efficiently identify potential parallel rows
- Normalize rows by dividing by the maximum absolute coefficient
- Special handling for nearly-parallel rows with singleton columns

**Implementation Pseudocode**:
```
function ParallelRowDetection(problem):
    # Create a hash for each row
    row_hashes = create_row_hashes(problem)
    
    # Group rows by hash
    hash_groups = group_rows_by_hash(row_hashes)
    
    for each group in hash_groups:
        if group.size > 1:
            # Check each pair of rows in the group
            for each pair (q, r) in group:
                if are_parallel(row_q, row_r):
                    s = compute_scaling_factor(row_q, row_r)
                    
                    if both_are_equalities:
                        if b_q == s * b_r:
                            remove_constraint(r)  # Redundant
                            return true
                        else:
                            mark problem as infeasible
                            return true
                    
                    # Handle other cases based on constraint types
                    # ...
    
    return false
```
