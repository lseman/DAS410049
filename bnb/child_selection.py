from abc import ABC, abstractmethod


class ChildSelector(ABC):
    @abstractmethod
    def choose(self, var, value, node, ctx):
        raise NotImplementedError


class DownwardsChildSelector(ChildSelector):
    def choose(self, var, value, node, ctx):
        return "down", _info("downwards", "down", "always choose down branch first", var, value, ctx)


class UpwardsChildSelector(ChildSelector):
    def choose(self, var, value, node, ctx):
        return "up", _info("upwards", "up", "always choose up branch first", var, value, ctx)


class PseudocostChildSelector(ChildSelector):
    def choose(self, var, value, node, ctx):
        frac_down = value - int(value)
        frac_up = (int(value) + 1) - value
        pc = ctx["pseudocosts"][var]
        down_est = pc["down_score"] * frac_down
        up_est = pc["up_score"] * frac_up
        preferred = "down" if down_est <= up_est else "up"
        return preferred, _info("pseudocost", preferred, f"smaller pseudocost deterioration: down={down_est:.4f}, up={up_est:.4f}", var, value, ctx)


class LPValueChildSelector(ChildSelector):
    def choose(self, var, value, node, ctx):
        frac_down = value - int(value)
        frac_up = (int(value) + 1) - value
        preferred = "down" if frac_down <= 0.5 else "up"
        return preferred, _info("lp_value", preferred, f"branch toward nearest integer: f-={frac_down:.4f}, f+={frac_up:.4f}", var, value, ctx)


class RootLPValueChildSelector(ChildSelector):
    def choose(self, var, value, node, ctx):
        root_val = ctx["root_lp_sol"].get(var, value)
        preferred = "down" if value <= root_val else "up"
        return preferred, _info("root_lp_value", preferred, f"follow movement from root LP value {root_val:.4f}", var, value, ctx)


class InferenceChildSelector(ChildSelector):
    def choose(self, var, value, node, ctx):
        infh = ctx["inference_history"][var]
        preferred = "down" if infh["down_score"] >= infh["up_score"] else "up"
        return preferred, _info("inference", preferred, f"larger inference history: down={infh['down_score']:.4f}, up={infh['up_score']:.4f}", var, value, ctx)


class HybridInferenceRootLPChildSelector(ChildSelector):
    def choose(self, var, value, node, ctx):
        infh = ctx["inference_history"][var]
        root_val = ctx["root_lp_sol"].get(var, value)
        eps_dir = 1e-6
        down_weight = (infh["down_score"] + eps_dir) * (root_val - value + 1)
        up_weight = (infh["up_score"] + eps_dir) * (value - root_val + 1)
        preferred = "down" if down_weight >= up_weight else "up"
        return preferred, _info("hybrid_inference_root_lp", preferred, f"hybrid score: down={down_weight:.4f}, up={up_weight:.4f}", var, value, ctx)


def create_child_selector(name: str) -> ChildSelector:
    selectors = {
        "downwards": DownwardsChildSelector(),
        "upwards": UpwardsChildSelector(),
        "pseudocost": PseudocostChildSelector(),
        "lp_value": LPValueChildSelector(),
        "root_lp_value": RootLPValueChildSelector(),
        "inference": InferenceChildSelector(),
        "hybrid_inference_root_lp": HybridInferenceRootLPChildSelector(),
    }
    if name not in selectors:
        raise ValueError(f"Unknown child selection rule: {name}")
    return selectors[name]


def _info(rule, preferred, reason, var, value, ctx):
    frac_down = value - int(value)
    frac_up = (int(value) + 1) - value
    pc = ctx["pseudocosts"][var]
    infh = ctx["inference_history"][var]
    root_val = ctx["root_lp_sol"].get(var, value)
    return {
        "rule": rule,
        "reason": reason,
        "preferred": preferred,
        "down_estimate": round(pc["down_score"] * frac_down, 8),
        "up_estimate": round(pc["up_score"] * frac_up, 8),
        "down_inference": infh["down_score"],
        "up_inference": infh["up_score"],
        "root_value": round(root_val, 8),
    }
