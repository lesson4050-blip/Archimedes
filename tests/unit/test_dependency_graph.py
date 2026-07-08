"""Unit tests for the DependencyGraph topological sorting and cycle detection."""

from __future__ import annotations
import pytest
from app.agents.hydra import DependencyGraph


def test_no_deps_returns_single_batch_with_all_steps() -> None:
    """If there are no dependencies, all steps should run in a single batch."""
    graph = DependencyGraph(["Step A", "Step B", "Step C"])
    batches = graph.topological_batches()
    assert batches == [[0, 1, 2]]


def test_linear_chain_returns_sequential_batches() -> None:
    """If each step depends on the previous, they must run sequentially in order."""
    graph = DependencyGraph(["Step A", "Step B", "Step C"])
    graph.add_dependency(1, 0)  # B depends on A
    graph.add_dependency(2, 1)  # C depends on B
    batches = graph.topological_batches()
    assert batches == [[0], [1], [2]]


def test_diamond_dependency_returns_correct_batches() -> None:
    """Verify topological batches with a diamond dependency graph.

    A -> B -> D
    A -> C -> D
    Expected batches: [[0], [1, 2], [3]]
    """
    graph = DependencyGraph(["A", "B", "C", "D"])
    graph.add_dependency(1, 0)  # B depends on A
    graph.add_dependency(2, 0)  # C depends on A
    graph.add_dependency(3, 1)  # D depends on B
    graph.add_dependency(3, 2)  # D depends on C
    batches = graph.topological_batches()
    assert batches == [[0], [1, 2], [3]]


def test_cycle_detection_raises_value_error() -> None:
    """Verify that a cycle in the dependency graph raises a ValueError."""
    graph = DependencyGraph(["A", "B"])
    graph.add_dependency(0, 1)  # A depends on B
    graph.add_dependency(1, 0)  # B depends on A
    with pytest.raises(ValueError, match="Dependency cycle detected"):
        graph.topological_batches()
