"""
Branch and Bound Problem Generator

Configure the problem and strategy at the top of this file.
Run this script to generate and solve a random integer programming problem.
"""

# ==== CONFIGURATION ====
PROBLEM_FAMILY = "random"  # Options: "demo", "random"
PROBLEM_NAME = "balanced_fractions"  # Demo options: "balanced_fractions", "cover_mix", "knapsack_triads"
N_VARS = 20  # Used for random problems
STRATEGY = "depth_first_search"  # Options: "depth_first_search", "best_first_search", "best_first_search_with_plunging", "best_estimate_search", "interleaved_best_estimate_best_first_search", "hybrid_best_estimate_best_first_search", "breadth_first_search"
COMPARE_STRATEGIES = ["depth_first_search", "best_first_search"]
BRANCHING_RULE = "reliability"  # Options: "most_fractional", "pseudocost", "strong", "hybrid_strong_pseudocost", "pseudocost_strong_init", "reliability"
CHILD_SELECTION = "upwards"  # Options: "downwards", "upwards", "pseudocost", "lp_value", "root_lp_value", "inference", "hybrid_inference_root_lp"
EXPERIMENTAL_MULTI_BRANCH_WIDTH = 1  # 1 keeps exact binary branching; values >1 enqueue multiple branch pairs from the same parent and are not exact branch-and-bound
SEED = 42  # Random seed for reproducibility

# =======================

import json

from bnb_core import queue_policy_label, run_bnb, summarize_run
from problems import load_problem

if __name__ == "__main__":
    problem = load_problem(PROBLEM_FAMILY, PROBLEM_NAME, N_VARS, SEED)
    print(f"Problem: {problem['name']}")
    print(f"Objective: {problem['objective']}")
    print(f"Constraints: {len(problem['constraints'])}")
    print(f"\nBranching rule: {BRANCHING_RULE}")
    print(f"Child selection: {CHILD_SELECTION}")
    print(f"Experimental multi-branch width: {EXPERIMENTAL_MULTI_BRANCH_WIDTH}")

    strategy_runs = []
    for strategy_name in COMPARE_STRATEGIES:
        opt_val, opt_sol, frames, problem = run_bnb(
            problem,
            strategy_name,
            BRANCHING_RULE,
            CHILD_SELECTION,
            EXPERIMENTAL_MULTI_BRANCH_WIDTH,
        )
        strategy_runs.append(
            {
                "strategy": strategy_name,
                "frames": [f.__dict__ for f in frames],
                "summary": summarize_run(
                    strategy_name, frames, opt_val, opt_sol, CHILD_SELECTION
                ),
            }
        )
        print(f"\nStrategy: {strategy_name.upper()}")
        print(f"Optimal value: {opt_val}")
        print(f"Optimal solution: {opt_sol}")

    with open("viewer_template.html", "r", encoding="utf-8") as f:
        template = f.read()

    default_run = next(
        (run for run in strategy_runs if run["strategy"] == STRATEGY), strategy_runs[0]
    )
    trace = {
        "problem": problem,
        "strategy": default_run["strategy"],
        "branching_rule": BRANCHING_RULE,
        "config": {
            "problem_family": PROBLEM_FAMILY,
            "problem_name": PROBLEM_NAME if PROBLEM_FAMILY == "demo" else "random",
            "n_vars": N_VARS,
            "strategy": default_run["strategy"],
            "compare_strategies": COMPARE_STRATEGIES,
            "branching_rule": BRANCHING_RULE,
            "child_selection": CHILD_SELECTION,
            "experimental_multi_branch_width": EXPERIMENTAL_MULTI_BRANCH_WIDTH,
            "experimental_multi_branching_enabled": EXPERIMENTAL_MULTI_BRANCH_WIDTH > 1,
            "exact_branch_and_bound": EXPERIMENTAL_MULTI_BRANCH_WIDTH == 1,
            "seed": SEED,
            "queue_policy": queue_policy_label(default_run["strategy"]),
        },
        "comparison": {
            "runs": [
                {"strategy": run["strategy"], "summary": run["summary"]}
                for run in strategy_runs
            ],
        },
        "runs": strategy_runs,
        "frames": default_run["frames"],
    }
    html = template.replace("__TRACE__", json.dumps(trace))
    with open("bnb_trace.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("\nHTML trace written to bnb_trace.html")
