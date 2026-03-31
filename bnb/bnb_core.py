import copy
import math
from dataclasses import dataclass, field
from typing import Optional

import pulp

from branching import create_branching_rule
from child_selection import create_child_selector
from node_selection import canonicalize_strategy_name, create_node_selector

EPS = 1e-6


@dataclass
class NodeResult:
    status: str
    lp_val: Optional[float]
    lp_sol: dict
    is_integer: bool
    frac_vars: list


@dataclass
class BnBNode:
    id: int
    parent_id: Optional[int]
    depth: int
    lb: dict
    ub: dict
    branch_desc: str = ""
    status: str = "open"
    lp_val: Optional[float] = None
    lp_sol: dict = field(default_factory=dict)
    frac_vars: list = field(default_factory=list)
    prune_reason: str = ""
    children: list = field(default_factory=list)


@dataclass
class Frame:
    step: int
    event: str
    current_id: Optional[int]
    nodes: dict
    queue: list
    best_val: Optional[float]
    best_sol: dict
    info: dict


def solve_lp(problem: dict, node: BnBNode) -> NodeResult:
    vnames = problem["var_names"]
    iv = set(problem.get("integer_vars", []))
    db = problem.get("var_bounds", {})
    lp = pulp.LpProblem("n", pulp.LpMaximize if problem["sense"] == "max" else pulp.LpMinimize)
    vars_ = {}
    for v in vnames:
        lo, hi = db.get(v, (0, None))
        lo = max(lo, node.lb.get(v, lo))
        hi_nd = node.ub.get(v, hi)
        hi = hi_nd if hi is None else (min(hi, hi_nd) if hi_nd is not None else hi)
        if v in iv:
            lo = math.ceil(lo - EPS)
            if hi is not None:
                hi = math.floor(hi + EPS)
        vars_[v] = pulp.LpVariable(v, lowBound=lo, upBound=hi, cat="Continuous")
    lp += pulp.lpSum(problem["objective"].get(v, 0) * vars_[v] for v in vnames)
    for i, c in enumerate(problem["constraints"]):
        expr = pulp.lpSum(c["coeffs"].get(v, 0) * vars_[v] for v in vnames)
        if c["sense"] == "<=":
            lp += expr <= c["rhs"], "c" + str(i)
        elif c["sense"] == ">=":
            lp += expr >= c["rhs"], "c" + str(i)
        else:
            lp += expr == c["rhs"], "c" + str(i)
    lp.solve(pulp.PULP_CBC_CMD(msg=0))
    smap = {1: "optimal", 0: "infeasible", -1: "infeasible", -2: "unbounded", -3: "infeasible"}
    st = smap.get(lp.status, "infeasible")
    if st != "optimal":
        return NodeResult(status=st, lp_val=None, lp_sol={}, is_integer=False, frac_vars=[])
    sol = {v: round(pulp.value(vars_[v]) or 0, 8) for v in vnames}
    lp_val = round(pulp.value(lp.objective), 8)
    frac = [(v, sol[v]) for v in iv if abs(sol[v] - round(sol[v])) > EPS]
    frac.sort(key=lambda p: -min(p[1] - math.floor(p[1]), math.ceil(p[1]) - p[1]))
    return NodeResult(status="optimal", lp_val=lp_val, lp_sol=sol, is_integer=len(frac) == 0, frac_vars=frac)


def queue_policy_label(strategy: str) -> str:
    strategy = canonicalize_strategy_name(strategy)
    labels = {
        "depth_first_search": "LIFO queue (depth-first)",
        "breadth_first_search": "FIFO queue (breadth-first)",
        "best_first_search": "Best LP bound first",
        "best_estimate_search": "Best estimate first",
        "interleaved_best_estimate_best_first_search": "Interleaved best-estimate / best-bound with plunging",
        "hybrid_best_estimate_best_first_search": "Hybrid best-estimate / best-bound with plunging",
        "best_first_search_with_plunging": "Best-bound restart with DFS plunges",
    }
    return labels.get(strategy, strategy)


def run_bnb(
    problem: dict,
    strategy: str,
    branching_rule: str,
    child_selection: str,
    experimental_multi_branch_width: int = 1,
):
    strategy = canonicalize_strategy_name(strategy)
    vb = problem.get("var_bounds", {v: (0, None) for v in problem["var_names"]})
    nodes = {}
    ctr = [0]
    queue = []
    best_val = [None]
    best_sol = [{}]
    frames = []
    step = [0]
    pseudocosts = {
        v: {"down_score": 1.0, "down_count": 0, "up_score": 1.0, "up_count": 0}
        for v in problem["var_names"]
    }
    inference_history = {
        v: {"down_score": 1.0, "down_count": 0, "up_score": 1.0, "up_count": 0}
        for v in problem["var_names"]
    }
    reliability_threshold = 2
    hybrid_strong_rounds = 4
    strong_init_done = [False]
    plunge_stack = []
    root_lp_sol = [{}]
    interleave_best_freq = 10
    hybrid_best_weight = 0.1
    lp_stats = {
        "total_lp_solves": 0,
        "node_lp_solves": 0,
        "probe_lp_solves": 0,
    }

    branching = create_branching_rule(branching_rule)
    child_selector = create_child_selector(child_selection)
    node_selector = create_node_selector(strategy)

    def new_node(pid, depth, lb, ub, branch_desc=""):
        ctr[0] += 1
        nid = ctr[0]
        nodes[nid] = BnBNode(id=nid, parent_id=pid, depth=depth, lb=copy.deepcopy(lb), ub=copy.deepcopy(ub), branch_desc=branch_desc)
        return nid

    def snap(ev, cur, info=None):
        def node_dict(nd):
            return {
                "id": nd.id,
                "parent_id": nd.parent_id,
                "depth": nd.depth,
                "lb": dict(nd.lb),
                "ub": dict(nd.ub),
                "branch_desc": nd.branch_desc,
                "status": nd.status,
                "lp_val": nd.lp_val,
                "lp_sol": dict(nd.lp_sol),
                "frac_vars": list(nd.frac_vars),
                "prune_reason": nd.prune_reason,
                "children": list(nd.children),
            }
        snap_info = dict(info or {})
        snap_info["pseudocosts"] = {
            var: {
                "down_score": stats["down_score"],
                "up_score": stats["up_score"],
                "down_count": stats["down_count"],
                "up_count": stats["up_count"],
            }
            for var, stats in pseudocosts.items()
        }
        snap_info["inference_history"] = {
            var: {
                "down_score": stats["down_score"],
                "up_score": stats["up_score"],
                "down_count": stats["down_count"],
                "up_count": stats["up_count"],
            }
            for var, stats in inference_history.items()
        }
        snap_info["lp_stats"] = dict(lp_stats)
        frames.append(Frame(step=step[0], event=ev, current_id=cur, nodes={k: node_dict(v) for k, v in nodes.items()}, queue=list(queue), best_val=best_val[0], best_sol=dict(best_sol[0]), info=snap_info))

    def solve_lp_tracked(node, kind="node"):
        result = solve_lp(problem, node)
        lp_stats["total_lp_solves"] += 1
        if kind == "probe":
            lp_stats["probe_lp_solves"] += 1
        else:
            lp_stats["node_lp_solves"] += 1
        return result

    def update_directional_score(prev_score, prev_count, sample):
        new_count = prev_count + 1
        return round((prev_score * prev_count + sample) / new_count, 8), new_count

    def inference_proxy(result, child_bounds):
        if result.status != "optimal":
            return float(len(problem["integer_vars"]) + 2)
        integral_count = sum(1 for v in problem["integer_vars"] if abs(result.lp_sol.get(v, 0) - round(result.lp_sol.get(v, 0))) <= EPS)
        fixed_count = sum(1 for v in problem["integer_vars"] if child_bounds["lb"].get(v) == child_bounds["ub"].get(v))
        return float(integral_count + fixed_count)

    def probe_branch(var, value, nd):
        lb_l = copy.deepcopy(nd.lb)
        ub_l = copy.deepcopy(nd.ub)
        lo_b = math.floor(value)
        ub_l[var] = lo_b if ub_l.get(var) is None else min(lo_b, ub_l[var])
        left_res = solve_lp_tracked(BnBNode(id=-1, parent_id=nd.id, depth=nd.depth + 1, lb=lb_l, ub=ub_l), kind="probe")
        lb_r = copy.deepcopy(nd.lb)
        ub_r = copy.deepcopy(nd.ub)
        hi_b = math.ceil(value)
        lb_r[var] = max(hi_b, lb_r.get(var, 0))
        right_res = solve_lp_tracked(BnBNode(id=-1, parent_id=nd.id, depth=nd.depth + 1, lb=lb_r, ub=ub_r), kind="probe")
        if problem["sense"] == "max":
            left_gain = 0.0 if left_res.lp_val is None else max(0.0, nd.lp_val - left_res.lp_val)
            right_gain = 0.0 if right_res.lp_val is None else max(0.0, nd.lp_val - right_res.lp_val)
        else:
            left_gain = 0.0 if left_res.lp_val is None else max(0.0, left_res.lp_val - nd.lp_val)
            right_gain = 0.0 if right_res.lp_val is None else max(0.0, right_res.lp_val - nd.lp_val)
        strong_score = max(left_gain, EPS) * max(right_gain, EPS)
        return {
            "left_lp": left_res.lp_val,
            "right_lp": right_res.lp_val,
            "left_gain": round(left_gain, 8),
            "right_gain": round(right_gain, 8),
            "score": round(strong_score, 8),
            "left_inference": round(inference_proxy(left_res, {"lb": lb_l, "ub": ub_l}), 8),
            "right_inference": round(inference_proxy(right_res, {"lb": lb_r, "ub": ub_r}), 8),
        }

    def update_pseudocost(var, value, nd, probe):
        frac_down = value - math.floor(value)
        frac_up = math.ceil(value) - value
        stats = pseudocosts[var]
        if problem["sense"] == "max":
            if probe["left_lp"] is not None:
                sample = max(0.0, nd.lp_val - probe["left_lp"]) / max(frac_down, EPS)
                stats["down_score"], stats["down_count"] = update_directional_score(stats["down_score"], stats["down_count"], sample)
            if probe["right_lp"] is not None:
                sample = max(0.0, nd.lp_val - probe["right_lp"]) / max(frac_up, EPS)
                stats["up_score"], stats["up_count"] = update_directional_score(stats["up_score"], stats["up_count"], sample)
        else:
            if probe["left_lp"] is not None:
                sample = max(0.0, probe["left_lp"] - nd.lp_val) / max(frac_down, EPS)
                stats["down_score"], stats["down_count"] = update_directional_score(stats["down_score"], stats["down_count"], sample)
            if probe["right_lp"] is not None:
                sample = max(0.0, probe["right_lp"] - nd.lp_val) / max(frac_up, EPS)
                stats["up_score"], stats["up_count"] = update_directional_score(stats["up_score"], stats["up_count"], sample)
        _update_directional_history(inference_history, "down", var, probe["left_inference"])
        _update_directional_history(inference_history, "up", var, probe["right_inference"])

    def pseudocost_summary(var):
        stats = pseudocosts[var]
        total_count = stats["down_count"] + stats["up_count"]
        avg_score = (stats["down_score"] * max(stats["down_count"], 1) + stats["up_score"] * max(stats["up_count"], 1)) / max(max(stats["down_count"], 1) + max(stats["up_count"], 1), 1)
        return round(avg_score, 8), total_count

    def best_estimate_value(nd):
        if nd.lp_val is None:
            return -float("inf") if problem["sense"] == "max" else float("inf")
        estimate = nd.lp_val
        for var, value in nd.frac_vars:
            stats = pseudocosts[var]
            frac_down = value - math.floor(value)
            frac_up = math.ceil(value) - value
            penalty = min(stats["down_score"] * frac_down, stats["up_score"] * frac_up)
            estimate = estimate - penalty if problem["sense"] == "max" else estimate + penalty
        return round(estimate, 8)

    def ensure_strong_initialization(frac_vars, nd):
        if strong_init_done[0]:
            return
        for var, value in frac_vars:
            probe = probe_branch(var, value, nd)
            update_pseudocost(var, value, nd, probe)
        strong_init_done[0] = True

    strategy_ctx = {
        "pseudocosts": pseudocosts,
        "inference_history": inference_history,
        "root_lp_sol": root_lp_sol[0],
        "probe_branch": probe_branch,
        "update_pseudocost": update_pseudocost,
        "pseudocost_summary": pseudocost_summary,
        "ensure_strong_initialization": ensure_strong_initialization,
        "hybrid_strong_rounds": hybrid_strong_rounds,
        "reliability_threshold": reliability_threshold,
        "best_estimate_value": best_estimate_value,
        "plunge_stack": plunge_stack,
        "interleave_best_freq": interleave_best_freq,
        "interleave_plunge_count": 0,
        "hybrid_best_weight": hybrid_best_weight,
        "experimental_multi_branch_width": max(1, int(experimental_multi_branch_width or 1)),
    }

    lb0 = {v: vb.get(v, (0, None))[0] for v in problem["var_names"]}
    ub0 = {v: vb.get(v, (0, None))[1] for v in problem["var_names"]}
    root_id = new_node(None, 0, lb0, ub0)
    queue = [root_id]
    snap("start", root_id, {"strategy": strategy, "branching_rule": branching_rule, "child_selection": child_selection, "queue_policy": queue_policy_label(strategy)})

    def evaluate_node(nid):
        nd = nodes[nid]
        step[0] += 1
        result = solve_lp_tracked(nd, kind="node")
        nd.lp_val = result.lp_val
        nd.lp_sol = result.lp_sol
        nd.frac_vars = result.frac_vars
        if nid == root_id and result.status == "optimal":
            root_lp_sol[0] = dict(result.lp_sol)
            strategy_ctx["root_lp_sol"] = root_lp_sol[0]
        if result.status == "infeasible":
            nd.status = "pruned_inf"
            nd.prune_reason = "infeasible LP relaxation"
            snap("prune_inf", nid, {"reason": "infeasible"})
            return False
        nd.status = "lp_solved"
        snap("lp_solved", nid, {"lp_val": result.lp_val, "lp_sol": result.lp_sol, "frac_vars": result.frac_vars})
        if best_val[0] is not None and result.lp_val <= best_val[0] + EPS:
            nd.status = "pruned_bound"
            nd.prune_reason = "LP bound cannot beat incumbent"
            snap("prune_bound", nid, {"lp_val": result.lp_val, "best_val": best_val[0]})
            return False
        if result.is_integer:
            nd.status = "integer"
            step[0] += 1
            is_new = best_val[0] is None or result.lp_val > best_val[0] + EPS
            if is_new:
                best_val[0] = round(result.lp_val, 8)
                best_sol[0] = {v: round(result.lp_sol[v]) for v in problem["var_names"]}
            snap("integer", nid, {"lp_val": result.lp_val, "lp_sol": result.lp_sol, "is_new_best": is_new})
            return False
        return True

    def refresh_best_queue():
        for qid in list(queue):
            qn = nodes[qid]
            if qn.status == "open" and qn.lp_val is None:
                if not evaluate_node(qid):
                    queue.remove(qid)
                    if qid in strategy_ctx["plunge_stack"]:
                        strategy_ctx["plunge_stack"][:] = [pid for pid in strategy_ctx["plunge_stack"] if pid != qid]
                    continue
            if best_val[0] is not None and qn.lp_val is not None and qn.lp_val <= best_val[0] + EPS:
                qn.status = "pruned_bound"
                qn.prune_reason = "LP bound cannot beat incumbent"
                step[0] += 1
                snap("prune_bound", qid, {"lp_val": qn.lp_val, "best_val": best_val[0]})
                queue.remove(qid)
                if qid in strategy_ctx["plunge_stack"]:
                    strategy_ctx["plunge_stack"][:] = [pid for pid in strategy_ctx["plunge_stack"] if pid != qid]

    while queue:
        if strategy in {
            "best_first_search",
            "best_estimate_search",
            "best_first_search_with_plunging",
            "interleaved_best_estimate_best_first_search",
            "hybrid_best_estimate_best_first_search",
        }:
            refresh_best_queue()
            if not queue:
                continue
            nid = node_selector.next_node(queue, nodes, strategy_ctx)
            if nid is None:
                continue
            nd = nodes[nid]
        else:
            nid = node_selector.next_node(queue, nodes, strategy_ctx)
            if nid is None:
                continue
            if not evaluate_node(nid):
                continue
            nd = nodes[nid]

        candidate_details = branching.rank_candidates(nd.frac_vars, nd, strategy_ctx)
        branch_width = min(
            strategy_ctx["experimental_multi_branch_width"],
            len(candidate_details),
        )
        selected_candidates = candidate_details[:branch_width]
        branch_groups = []
        ordered_child_ids = []
        all_children = []
        for selected in selected_candidates:
            bvar, bval = selected["var"], selected["value"]
            lo_b, hi_b = math.floor(bval), math.ceil(bval)

            lb_l = copy.deepcopy(nd.lb)
            ub_l = copy.deepcopy(nd.ub)
            ub_l[bvar] = lo_b if ub_l.get(bvar) is None else min(lo_b, ub_l[bvar])
            left_id = new_node(nid, nd.depth + 1, lb_l, ub_l, f"{bvar}<={lo_b}")

            lb_r = copy.deepcopy(nd.lb)
            ub_r = copy.deepcopy(nd.ub)
            lb_r[bvar] = max(hi_b, lb_r.get(bvar, 0))
            right_id = new_node(nid, nd.depth + 1, lb_r, ub_r, f"{bvar}>={hi_b}")

            preferred_child, child_info = child_selector.choose(bvar, bval, nd, strategy_ctx)
            group_order = [left_id, right_id] if preferred_child == "down" else [right_id, left_id]
            ordered_child_ids.extend(group_order)
            all_children.extend([left_id, right_id])
            branch_groups.append(
                {
                    "rank": selected.get("rank"),
                    "var": bvar,
                    "value": bval,
                    "lo": lo_b,
                    "hi": hi_b,
                    "left_id": left_id,
                    "right_id": right_id,
                    "preferred_child": preferred_child,
                    "first_child_id": group_order[0],
                    "second_child_id": group_order[1],
                    "child_selection": child_info,
                    "candidate": selected,
                }
            )

        primary_group = branch_groups[0]
        nd.status = "branched"
        nd.children = all_children
        queue[:] = node_selector.after_branch(queue, ordered_child_ids, strategy_ctx)
        step[0] += 1
        snap(
            "branch",
            nid,
            {
                "bvar": primary_group["var"],
                "bval": primary_group["value"],
                "candidate_details": candidate_details,
                "selected_candidates": selected_candidates,
                "branch_groups": branch_groups,
                "branching_rule": branching_rule,
                "child_selection": primary_group["child_selection"],
                "queue_policy": queue_policy_label(strategy),
                "lo": primary_group["lo"],
                "hi": primary_group["hi"],
                "left_id": primary_group["left_id"],
                "right_id": primary_group["right_id"],
                "first_child_id": primary_group["first_child_id"],
                "second_child_id": primary_group["second_child_id"],
                "ordered_child_ids": ordered_child_ids,
                "experimental_multi_branch_width": strategy_ctx["experimental_multi_branch_width"],
                "experimental_multi_branch_active": len(branch_groups) > 1,
            },
        )

    step[0] += 1
    snap("done", None, {"best_val": best_val[0], "best_sol": best_sol[0], "total_nodes": len(nodes), "strategy": strategy, "queue_policy": queue_policy_label(strategy)})
    return best_val[0], best_sol[0], frames, problem


def summarize_run(strategy: str, frames: list, opt_val, opt_sol, child_selection: str) -> dict:
    last = frames[-1].info if frames else {}
    integer_steps = [{"step": frame.step, "value": frame.info.get("lp_val"), "is_new_best": frame.info.get("is_new_best", False), "solution": frame.info.get("lp_sol", {}), "node_id": frame.current_id} for frame in frames if frame.event == "integer"]
    incumbents = [{"step": item["step"], "value": item["value"], "solution": item["solution"], "node_id": item["node_id"]} for item in integer_steps if item["is_new_best"]]
    first_incumbent = next((item["step"] for item in incumbents), None)
    return {
        "strategy": strategy,
        "best_val": opt_val,
        "best_sol": opt_sol,
        "total_nodes": last.get("total_nodes", len(frames)),
        "total_steps": frames[-1].step if frames else 0,
        "first_incumbent_step": first_incumbent,
        "integer_events": len(integer_steps),
        "incumbents": incumbents,
        "queue_policy": queue_policy_label(strategy),
        "child_selection": child_selection,
        "experimental_multi_branch_events": sum(
            1
            for frame in frames
            if frame.event == "branch"
            and frame.info.get("experimental_multi_branch_active")
        ),
    }


def _update_directional_history(store, direction, var, sample):
    if sample is None:
        return
    score_key = f"{direction}_score"
    count_key = f"{direction}_count"
    stats = store[var]
    new_count = stats[count_key] + 1
    stats[score_key] = round((stats[score_key] * stats[count_key] + sample) / new_count, 8)
    stats[count_key] = new_count
