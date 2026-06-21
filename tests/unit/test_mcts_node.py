# tests/unit/test_mcts_node.py
from __future__ import annotations

import math
import pytest

from app.agents.mcts import PlanNode


def test_unvisited_node_has_infinite_ucb1_score() -> None:
    parent = PlanNode(action=None, parent=None, depth=0, visit_count=10)
    child = PlanNode(action="step1", parent=parent, depth=1, visit_count=0)
    assert child.ucb1_score() == float("inf")


def test_visited_node_ucb1_score_is_finite_and_computed_correctly() -> None:
    parent = PlanNode(action=None, parent=None, depth=0, visit_count=10)
    child = PlanNode(action="step1", parent=parent, depth=1, visit_count=2, total_value=1.5)

    # Let's calculate expected score:
    # exploitation = 1.5 / 2 = 0.75
    # exploration = 1.41421356 * math.sqrt(math.log(10) / 2)
    #             = 1.41421356 * math.sqrt(2.302585092994046 / 2)
    #             = 1.41421356 * math.sqrt(1.151292546497023)
    #             = 1.41421356 * 1.0729830131446704
    #             = 1.5174272186711585
    # expected_ucb1 = 0.75 + 1.5174272186711585 = 2.2674272186711585
    expected_ucb1 = 0.75 + 1.41421356 * math.sqrt(math.log(10) / 2)
    assert child.ucb1_score() == pytest.approx(expected_ucb1)


def test_best_child_selects_highest_ucb1() -> None:
    root = PlanNode(action=None, parent=None, depth=0, visit_count=10)
    child1 = PlanNode(action="step1", parent=root, depth=1, visit_count=5, total_value=2.0)
    child2 = PlanNode(action="step2", parent=root, depth=1, visit_count=3, total_value=2.5)

    root.children = [child1, child2]

    # Let's calculate:
    # child1: 2.0 / 5 + 1.41421356 * math.sqrt(math.log(10) / 5) = 0.4 + 1.41421356 * 0.6786 = 0.4 + 0.9597 = 1.3597
    # child2: 2.5 / 3 + 1.41421356 * math.sqrt(math.log(10) / 3) = 0.8333 + 1.41421356 * 0.8761 = 0.8333 + 1.2390 = 2.0723
    assert root.best_child() == child2


def test_most_visited_child_selects_highest_visit_count_not_highest_ucb1() -> None:
    root = PlanNode(action=None, parent=None, depth=0, visit_count=20)

    # child1 has high UCB1 score (e.g. unvisited or high value, but lower visits)
    child1 = PlanNode(action="step1", parent=root, depth=1, visit_count=5, total_value=4.0)

    # child2 has lower UCB1 score but has been visited more times
    child2 = PlanNode(action="step2", parent=root, depth=1, visit_count=15, total_value=3.0)

    root.children = [child1, child2]

    # child1 ucb1: 4.0 / 5 + 1.41421356 * sqrt(log(20) / 5) = 0.8 + 1.41421356 * 0.774 = 1.89
    # child2 ucb1: 3.0 / 15 + 1.41421356 * sqrt(log(20) / 15) = 0.2 + 1.41421356 * 0.447 = 0.83
    # child1 has higher UCB1 score:
    assert root.best_child() == child1

    # But child2 is the most visited one:
    assert root.most_visited_child() == child2
