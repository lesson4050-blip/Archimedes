# app/agents/mcts.py
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class PlanNode:
    """One node in the search tree. action is the step taken to reach
    this node from its parent; None only for the root.
    """

    action: str | None
    parent: PlanNode | None
    depth: int
    children: list[PlanNode] = field(default_factory=list)
    visit_count: int = 0
    total_value: float = 0.0
    is_terminal: bool = False

    def ucb1_score(self, exploration_constant: float = 1.41421356) -> float:
        """Upper Confidence Bound. Unvisited nodes MUST be selected first —
        return infinity, not zero, or they'll never be explored.
        """
        if self.visit_count == 0:
            return float("inf")
        assert self.parent is not None
        exploitation = self.total_value / self.visit_count
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visit_count) / self.visit_count
        )
        return exploitation + exploration

    def best_child(self) -> PlanNode:
        """Select child with highest UCB1 score. Caller must ensure children exist."""
        return max(self.children, key=lambda c: c.ucb1_score())

    def most_visited_child(self) -> PlanNode:
        """Final selection after search completes — use visit_count, not
        UCB1 score, since UCB1 is for exploration during search, not for
        the final answer. The most-visited path is the most-confirmed one.
        """
        return max(self.children, key=lambda c: c.visit_count)
