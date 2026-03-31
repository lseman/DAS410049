from abc import ABC, abstractmethod


class BranchingRule(ABC):
    @abstractmethod
    def rank_candidates(self, frac_vars, node, ctx):
        raise NotImplementedError


class MostFractionalRule(BranchingRule):
    def rank_candidates(self, frac_vars, node, ctx):
        details = []
        for var, value in frac_vars:
            frac_part = value - int(value)
            score = round(min(frac_part, 1 - frac_part), 8)
            details.append(
                {
                    "var": var,
                    "value": value,
                    "score": score,
                    "score_label": "fractionality",
                    "detail": f"min({frac_part:.4f}, {1 - frac_part:.4f})",
                }
            )
        details.sort(key=lambda item: (-item["score"], item["var"]))
        return _with_ranks(details)


class PseudocostRule(BranchingRule):
    def rank_candidates(self, frac_vars, node, ctx):
        details = []
        for var, value in frac_vars:
            avg_score, total_count = ctx["pseudocost_summary"](var)
            stats = ctx["pseudocosts"][var]
            details.append(
                {
                    "var": var,
                    "value": value,
                    "score": avg_score,
                    "score_label": "pseudocost",
                    "down_score": stats["down_score"],
                    "up_score": stats["up_score"],
                    "down_count": stats["down_count"],
                    "up_count": stats["up_count"],
                    "detail": f"down={stats['down_score']:.4f}, up={stats['up_score']:.4f}, samples={total_count}",
                }
            )
        details.sort(key=lambda item: (-item["score"], item["var"]))
        return _with_ranks(details)


class StrongRule(BranchingRule):
    def rank_candidates(self, frac_vars, node, ctx):
        details = []
        for var, value in frac_vars:
            probe = ctx["probe_branch"](var, value, node)
            ctx["update_pseudocost"](var, value, node, probe)
            details.append(
                {
                    "var": var,
                    "value": value,
                    "score": probe["score"],
                    "score_label": "strong score",
                    "left_gain": probe["left_gain"],
                    "right_gain": probe["right_gain"],
                    "detail": f"left LP={probe['left_lp'] if probe['left_lp'] is not None else 'inf'} right LP={probe['right_lp'] if probe['right_lp'] is not None else 'inf'} left gain={probe['left_gain']:.4f} right gain={probe['right_gain']:.4f}",
                }
            )
        details.sort(key=lambda item: (-item["score"], item["var"]))
        return _with_ranks(details)


class HybridStrongPseudocostRule(BranchingRule):
    def rank_candidates(self, frac_vars, node, ctx):
        total_samples = sum(
            stats["down_count"] + stats["up_count"] for stats in ctx["pseudocosts"].values()
        )
        if total_samples < ctx["hybrid_strong_rounds"]:
            return StrongRule().rank_candidates(frac_vars, node, ctx)
        return PseudocostRule().rank_candidates(frac_vars, node, ctx)


class PseudocostStrongInitRule(BranchingRule):
    def rank_candidates(self, frac_vars, node, ctx):
        ctx["ensure_strong_initialization"](frac_vars, node)
        return PseudocostRule().rank_candidates(frac_vars, node, ctx)


class ReliabilityRule(BranchingRule):
    def rank_candidates(self, frac_vars, node, ctx):
        details = []
        for var, value in frac_vars:
            stats = ctx["pseudocosts"][var]
            sample_count = stats["down_count"] + stats["up_count"]
            if sample_count < ctx["reliability_threshold"]:
                probe = ctx["probe_branch"](var, value, node)
                ctx["update_pseudocost"](var, value, node, probe)
                details.append(
                    {
                        "var": var,
                        "value": value,
                        "score": probe["score"],
                        "score_label": "reliability score",
                        "left_gain": probe["left_gain"],
                        "right_gain": probe["right_gain"],
                        "detail": f"strong probe used because samples={sample_count} < {ctx['reliability_threshold']}; left LP={probe['left_lp'] if probe['left_lp'] is not None else 'inf'} right LP={probe['right_lp'] if probe['right_lp'] is not None else 'inf'} left gain={probe['left_gain']:.4f} right gain={probe['right_gain']:.4f}",
                    }
                )
            else:
                avg_score, _ = ctx["pseudocost_summary"](var)
                details.append(
                    {
                        "var": var,
                        "value": value,
                        "score": avg_score,
                        "score_label": "reliable pseudocost",
                        "down_score": stats["down_score"],
                        "up_score": stats["up_score"],
                        "down_count": stats["down_count"],
                        "up_count": stats["up_count"],
                        "detail": f"used pseudocost estimate with samples={sample_count}; down={stats['down_score']:.4f}, up={stats['up_score']:.4f}",
                    }
                )
        details.sort(key=lambda item: (-item["score"], item["var"]))
        return _with_ranks(details)


def create_branching_rule(name: str) -> BranchingRule:
    rules = {
        "most_fractional": MostFractionalRule(),
        "pseudocost": PseudocostRule(),
        "strong": StrongRule(),
        "hybrid_strong_pseudocost": HybridStrongPseudocostRule(),
        "pseudocost_strong_init": PseudocostStrongInitRule(),
        "reliability": ReliabilityRule(),
    }
    if name not in rules:
        raise ValueError(f"Unknown branching rule: {name}")
    return rules[name]


def _with_ranks(details):
    for rank, item in enumerate(details, start=1):
        item["rank"] = rank
    return details
