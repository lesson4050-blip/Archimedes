# app/agents/mcts.py
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from app.models.base import ModelAdapter


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


_EXPAND_SYSTEM_PROMPT = (
    "You are a planning assistant. Given a task and a list of steps already planned, "
    "propose 2 to 3 alternative next steps that make progress toward completing the task. "
    "Make sure each step description is completely self-contained and concrete, "
    "explicitly including all target URLs, file paths, parameters, or details from the task "
    "so that a worker executing only that step knows exactly what to act on.\n"
    "For each next step, decide if that step would fully complete the task (is_terminal).\n"
    "Format each candidate on a new line exactly as:\n"
    "STEP: <description> | TERMINAL: <YES/NO>\n"
    "Do not output any introductory or concluding text."
)

_SIMULATE_SYSTEM_PROMPT = (
    "You are a plan evaluator. You are given a target task and a proposed sequence of steps. "
    "Evaluate how close the proposed plan is to solving the task.\n"
    "Respond with a single float score between 0.0 and 1.0 (where 1.0 means the plan fully solves the task, "
    "and 0.0 means it does not make progress or is completely wrong).\n"
    "Output ONLY the float number, with no other text, punctuation, or explanation."
)


class MCTSPlanner:
    """Runs MCTS to decompose a complex task into a step plan.

    Hard limits are non-negotiable: without max_iterations and max_depth,
    a pathological task can spin the tree forever. This is the same class
    of bug as the April 2026 ExecutorAgent that returned after every tool
    call instead of only on results — uncapped loops are how agents hang.
    """

    def __init__(
        self,
        adapter: ModelAdapter,
        max_depth: int = 5,
        max_iterations: int = 20,
        exploration_constant: float = 1.41421356,
    ) -> None:
        self.adapter = adapter
        self.max_depth = max_depth
        self.max_iterations = max_iterations
        self.exploration_constant = exploration_constant

    async def search(self, task: str) -> list[str]:
        """Run MCTS and return the best plan as an ordered list of step descriptions.

        Each iteration of the search loop makes at most 2 adapter.stream calls:
        - _select: 0 calls (pure tree traversal)
        - _expand: exactly 1 call (proposes 2-3 candidate steps)
        - _simulate: exactly 1 call (scores the plan represented by the node)

        If the selected node is terminal or at max depth, _expand is skipped, making
        exactly 1 call (simulate only). Thus, the total number of calls satisfies:
        adapter.call_count <= max_iterations * 2.

        Returns an empty list if no viable plan was found within max_iterations.
        """
        root = PlanNode(action=None, parent=None, depth=0)

        # Each iteration of this loop makes at most 2 LLM calls:
        # - _select makes 0 calls (pure tree traversal, no LLM)
        # - _expand makes exactly 1 call (if the selected node is not terminal and depth < max_depth)
        # - _simulate makes exactly 1 call (regardless of whether the node is terminal or not)
        # This keeps the number of calls per iteration deterministic and bounded by 2.
        for _ in range(self.max_iterations):
            node = self._select(root)
            if not node.is_terminal and node.depth < self.max_depth:
                children = await self._expand(node, task)
                node.children.extend(children)
                if children:
                    node = children[0]
            value = await self._simulate(node, task)
            self._backpropagate(node, value)

        return self._extract_best_plan(root)

    def _select(self, node: PlanNode) -> PlanNode:
        """Traverse via UCB1 until reaching a leaf (no children) or a
        terminal/max-depth node.
        """
        while node.children and not node.is_terminal and node.depth < self.max_depth:
            node = node.best_child()
        return node

    async def _expand(self, node: PlanNode, task: str) -> list[PlanNode]:
        """Ask the model for candidate next steps.

        Makes exactly 1 LLM call to propose 2-3 steps.
        """
        plan_steps: list[str] = []
        curr: PlanNode | None = node
        while curr is not None:
            if curr.action is not None:
                plan_steps.append(curr.action)
            curr = curr.parent
        plan_steps.reverse()

        plan_str = "\n".join(f"- {step}" for step in plan_steps) if plan_steps else "None"
        user_content = (
            f"Task: {task}\n"
            f"Steps planned so far:\n{plan_str}\n\n"
            "Propose 2-3 candidate next steps."
        )

        messages = [
            {"role": "system", "content": _EXPAND_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            chunks: list[str] = []
            async for delta in self.adapter.stream(
                messages, max_tokens=500, temperature=0.7, think=False
            ):
                chunks.append(delta)
            raw = "".join(chunks).strip()
        except Exception:
            return []

        children: list[PlanNode] = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "|" not in line or "STEP:" not in line:
                continue
            parts = line.split("|", 1)
            step_part = parts[0].replace("STEP:", "").strip()
            term_part = parts[1].replace("TERMINAL:", "").strip().upper()
            if not step_part:
                continue
            is_terminal = "YES" in term_part or "TRUE" in term_part
            children.append(PlanNode(
                action=step_part,
                parent=node,
                depth=node.depth + 1,
                is_terminal=is_terminal,
            ))
        return children

    async def _simulate(self, node: PlanNode, task: str) -> float:
        """Estimate how promising the plan up to this node is.

        Makes exactly 1 LLM call.
        """
        plan_steps: list[str] = []
        curr: PlanNode | None = node
        while curr is not None:
            if curr.action is not None:
                plan_steps.append(curr.action)
            curr = curr.parent
        plan_steps.reverse()

        plan_str = "\n".join(f"- {step}" for step in plan_steps) if plan_steps else "None"
        user_content = (
            f"Task: {task}\n"
            f"Proposed Plan:\n{plan_str}"
        )

        messages = [
            {"role": "system", "content": _SIMULATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            chunks: list[str] = []
            async for delta in self.adapter.stream(
                messages, max_tokens=10, temperature=0.0, think=False
            ):
                chunks.append(delta)
            raw = "".join(chunks).strip()

            # Defensive float parsing using regular expression
            match = re.search(r"\d+(?:\.\d+)?", raw)
            if match:
                score = float(match.group(0))
                return max(0.0, min(1.0, score))
            return 0.0
        except Exception:
            return 0.0

    def _backpropagate(self, node: PlanNode, value: float) -> None:
        """Walk up to root, incrementing visit_count and total_value on
        every ancestor — not just the leaf. This is the step most often
        forgotten; skipping it makes UCB1 scores at the root meaningless.
        """
        current: PlanNode | None = node
        while current is not None:
            current.visit_count += 1
            current.total_value += value
            current = current.parent

    def _extract_best_plan(self, root: PlanNode) -> list[str]:
        """Walk most_visited_child from root to a leaf, collecting actions.

        If root.children is empty (no successful expansion ever happened
        within budget), the while-loop body never executes and the function
        returns [] naturally. Do not add any explicit early-return check.
        """
        plan: list[str] = []
        node = root
        while node.children:
            node = node.most_visited_child()
            if node.action:
                plan.append(node.action)
        return plan
