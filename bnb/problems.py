import random


def demo_problem(name: str) -> dict:
    if name == "balanced_fractions":
        return {
            "name": "Balanced Fractions Demo",
            "display": "3 coupled capacity constraints create several fractional LP values at the root",
            "var_names": ["x1", "x2", "x3", "x4", "x5"],
            "objective": {"x1": 9, "x2": 8, "x3": 8, "x4": 7, "x5": 6},
            "constraints": [
                {"coeffs": {"x1": 2, "x2": 2, "x3": 3, "x4": 1, "x5": 2}, "sense": "<=", "rhs": 7},
                {"coeffs": {"x1": 1, "x2": 3, "x3": 2, "x4": 2, "x5": 1}, "sense": "<=", "rhs": 6},
                {"coeffs": {"x1": 3, "x2": 1, "x3": 2, "x4": 2, "x5": 2}, "sense": "<=", "rhs": 7},
            ],
            "sense": "max",
            "integer_vars": ["x1", "x2", "x3", "x4", "x5"],
            "var_bounds": {v: (0, 1) for v in ["x1", "x2", "x3", "x4", "x5"]},
        }
    if name == "cover_mix":
        return {
            "name": "Cover Mix Demo",
            "display": "Set-packing style constraints with overlapping covers and multiple fractional candidates",
            "var_names": ["x1", "x2", "x3", "x4", "x5", "x6"],
            "objective": {"x1": 10, "x2": 9, "x3": 8, "x4": 8, "x5": 7, "x6": 6},
            "constraints": [
                {"coeffs": {"x1": 1, "x2": 1, "x3": 1, "x4": 0, "x5": 1, "x6": 0}, "sense": "<=", "rhs": 2},
                {"coeffs": {"x1": 0, "x2": 1, "x3": 1, "x4": 1, "x5": 0, "x6": 1}, "sense": "<=", "rhs": 2},
                {"coeffs": {"x1": 1, "x2": 0, "x3": 1, "x4": 1, "x5": 1, "x6": 0}, "sense": "<=", "rhs": 2},
                {"coeffs": {"x1": 1, "x2": 1, "x3": 0, "x4": 0, "x5": 0, "x6": 1}, "sense": "<=", "rhs": 1},
            ],
            "sense": "max",
            "integer_vars": ["x1", "x2", "x3", "x4", "x5", "x6"],
            "var_bounds": {v: (0, 1) for v in ["x1", "x2", "x3", "x4", "x5", "x6"]},
        }
    if name == "knapsack_triads":
        return {
            "name": "Knapsack Triads Demo",
            "display": "Two linked knapsack constraints yield several tied fractional branching candidates",
            "var_names": ["x1", "x2", "x3", "x4", "x5", "x6"],
            "objective": {"x1": 14, "x2": 13, "x3": 12, "x4": 11, "x5": 9, "x6": 8},
            "constraints": [
                {"coeffs": {"x1": 5, "x2": 4, "x3": 4, "x4": 3, "x5": 2, "x6": 2}, "sense": "<=", "rhs": 10},
                {"coeffs": {"x1": 2, "x2": 3, "x3": 4, "x4": 4, "x5": 3, "x6": 2}, "sense": "<=", "rhs": 9},
                {"coeffs": {"x1": 1, "x2": 1, "x3": 0, "x4": 1, "x5": 1, "x6": 1}, "sense": "<=", "rhs": 3},
            ],
            "sense": "max",
            "integer_vars": ["x1", "x2", "x3", "x4", "x5", "x6"],
            "var_bounds": {v: (0, 1) for v in ["x1", "x2", "x3", "x4", "x5", "x6"]},
        }
    raise ValueError(f"Unknown demo problem: {name}")


def generate_problem(n_vars: int, seed: int) -> dict:
    rng = random.Random(seed)
    var_names = [f"x{i + 1}" for i in range(n_vars)]
    objective = {v: rng.randint(1, 9) for v in var_names}
    constraints = []

    for _ in range(max(3, n_vars)):
        coeffs = {v: rng.randint(1, 8) for v in var_names}
        rhs = rng.randint(max(6, n_vars * 2), max(10, n_vars * 5))
        constraints.append({"coeffs": coeffs, "sense": "<=", "rhs": rhs})

    return {
        "name": f"Random IP ({n_vars} vars)",
        "display": f"Maximize sum of {n_vars} variables with random constraints",
        "var_names": var_names,
        "objective": objective,
        "constraints": constraints,
        "sense": "max",
        "integer_vars": var_names,
        "var_bounds": {v: (0, None) for v in var_names},
    }


def load_problem(problem_family: str, problem_name: str, n_vars: int, seed: int) -> dict:
    if problem_family == "demo":
        return demo_problem(problem_name)
    if problem_family == "random":
        return generate_problem(n_vars, seed)
    raise ValueError(f"Unknown problem family: {problem_family}")
