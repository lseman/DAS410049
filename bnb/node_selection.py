from abc import ABC, abstractmethod


STRATEGY_ALIASES = {
    "dfs": "depth_first_search",
    "bfs": "breadth_first_search",
    "best": "best_first_search",
    "best_estimate": "best_estimate_search",
    "best_plunging": "best_first_search_with_plunging",
    "interleaved_best_estimate_best": "interleaved_best_estimate_best_first_search",
    "hybrid_best_estimate_best": "hybrid_best_estimate_best_first_search",
}


def canonicalize_strategy_name(name: str) -> str:
    return STRATEGY_ALIASES.get(name, name)


class NodeSelector(ABC):
    @abstractmethod
    def next_node(self, queue, nodes, ctx):
        raise NotImplementedError

    def after_branch(self, queue, ordered_child_ids, ctx):
        return queue


class DFSSelector(NodeSelector):
    def next_node(self, queue, nodes, ctx):
        return queue.pop(0) if queue else None

    def after_branch(self, queue, ordered_child_ids, ctx):
        return list(ordered_child_ids) + queue


class BFSSelector(NodeSelector):
    def next_node(self, queue, nodes, ctx):
        return queue.pop(0) if queue else None

    def after_branch(self, queue, ordered_child_ids, ctx):
        return queue + list(ordered_child_ids)


class BestBoundSelector(NodeSelector):
    def next_node(self, queue, nodes, ctx):
        if not queue:
            return None
        index = max(range(len(queue)), key=lambda i: nodes[queue[i]].lp_val)
        return queue.pop(index)

    def after_branch(self, queue, ordered_child_ids, ctx):
        return queue + list(ordered_child_ids)


class BestEstimateSelector(NodeSelector):
    def next_node(self, queue, nodes, ctx):
        if not queue:
            return None
        index = max(range(len(queue)), key=lambda i: ctx["best_estimate_value"](nodes[queue[i]]))
        return queue.pop(index)

    def after_branch(self, queue, ordered_child_ids, ctx):
        return queue + list(ordered_child_ids)


class InterleavedBestEstimateBestSelector(NodeSelector):
    def next_node(self, queue, nodes, ctx):
        plunge_stack = ctx["plunge_stack"]
        while plunge_stack:
            nid = plunge_stack.pop(0)
            if nid in queue:
                queue.remove(nid)
                return nid
        if not queue:
            return None
        plunge_count = ctx["interleave_plunge_count"]
        ctx["interleave_plunge_count"] += 1
        if plunge_count % max(1, ctx["interleave_best_freq"]) == 0:
            index = max(range(len(queue)), key=lambda i: nodes[queue[i]].lp_val)
        else:
            index = max(
                range(len(queue)),
                key=lambda i: ctx["best_estimate_value"](nodes[queue[i]]),
            )
        return queue.pop(index)

    def after_branch(self, queue, ordered_child_ids, ctx):
        plunge_stack = ctx["plunge_stack"]
        child_set = set(ordered_child_ids)
        ctx["plunge_stack"] = list(ordered_child_ids) + [pid for pid in plunge_stack if pid not in child_set]
        return queue + list(ordered_child_ids)


class HybridBestEstimateBestSelector(NodeSelector):
    def next_node(self, queue, nodes, ctx):
        plunge_stack = ctx["plunge_stack"]
        while plunge_stack:
            nid = plunge_stack.pop(0)
            if nid in queue:
                queue.remove(nid)
                return nid
        if not queue:
            return None
        weight = ctx["hybrid_best_weight"]
        index = max(
            range(len(queue)),
            key=lambda i: (
                weight * ctx["best_estimate_value"](nodes[queue[i]])
                + (1 - weight) * nodes[queue[i]].lp_val
            ),
        )
        return queue.pop(index)

    def after_branch(self, queue, ordered_child_ids, ctx):
        plunge_stack = ctx["plunge_stack"]
        child_set = set(ordered_child_ids)
        ctx["plunge_stack"] = list(ordered_child_ids) + [pid for pid in plunge_stack if pid not in child_set]
        return queue + list(ordered_child_ids)


class BestPlungingSelector(NodeSelector):
    def next_node(self, queue, nodes, ctx):
        plunge_stack = ctx["plunge_stack"]
        while plunge_stack:
            nid = plunge_stack.pop(0)
            if nid in queue:
                queue.remove(nid)
                return nid
        if not queue:
            return None
        index = max(range(len(queue)), key=lambda i: nodes[queue[i]].lp_val)
        return queue.pop(index)

    def after_branch(self, queue, ordered_child_ids, ctx):
        plunge_stack = ctx["plunge_stack"]
        child_set = set(ordered_child_ids)
        ctx["plunge_stack"] = list(ordered_child_ids) + [pid for pid in plunge_stack if pid not in child_set]
        return queue + list(ordered_child_ids)


def create_node_selector(name: str) -> NodeSelector:
    canonical = canonicalize_strategy_name(name)
    selectors = {
        "depth_first_search": DFSSelector(),
        "breadth_first_search": BFSSelector(),
        "best_first_search": BestBoundSelector(),
        "best_estimate_search": BestEstimateSelector(),
        "interleaved_best_estimate_best_first_search": InterleavedBestEstimateBestSelector(),
        "hybrid_best_estimate_best_first_search": HybridBestEstimateBestSelector(),
        "best_first_search_with_plunging": BestPlungingSelector(),
    }
    if canonical not in selectors:
        raise ValueError(f"Unknown node selection strategy: {name}")
    return selectors[canonical]
