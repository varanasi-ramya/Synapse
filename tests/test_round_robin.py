"""Unit tests for the Synapse round-robin backend selection algorithm.

These tests isolate the selection *algorithm* from the asyncio socket layer, the
HTTP parsing and the connection pool that make up the full load balancer. The
``RoundRobin`` helper below mirrors the contract implemented in
``loadbalancer/lb.py`` so that the balancing logic can be verified in
milliseconds without standing up Docker containers.

If the implementation in ``loadbalancer/lb.py`` changes its behaviour, update
this module in lockstep: the two are intentionally kept as parallel
definitions of the same algorithm.
"""

from __future__ import annotations

from typing import List, Sequence

import pytest


class RoundRobin:
    """Cycle through a fixed list of backends in order.

    The helper keeps an index into ``backends`` and advances it by one on every
    call to :meth:`next_backend`, wrapping back to the first entry once the end
    of the list is reached.

    Args:
        backends: Ordered sequence of backend identifiers. The order defines
            the round-robin cycle and must not be empty.
    """

    def __init__(self, backends: Sequence[str]) -> None:
        """Store the backend list and position the cursor before the first entry.

        Raises:
            ValueError: If ``backends`` is empty, since there is nothing to
                balance across.
        """
        if not backends:
            raise ValueError("RoundRobin requires at least one backend")
        self._backends: List[str] = list(backends)
        self._index: int = 0

    def next_backend(self) -> str:
        """Return the next backend in the cycle.

        Returns:
            str: The identifier of the backend at the current cursor position,
                after advancing the cursor for the following call.
        """
        backend = self._backends[self._index]
        self._index = (self._index + 1) % len(self._backends)
        return backend


class TestRoundRobin:
    """Behavioural tests for the round-robin selection algorithm."""

    def test_cycles_through_backends_in_order(self) -> None:
        """Six selections across three backends produce two full cycles."""
        balancer = RoundRobin(["b1", "b2", "b3"])

        selected = [balancer.next_backend() for _ in range(6)]

        assert selected == ["b1", "b2", "b3", "b1", "b2", "b3"]

    def test_single_backend_always_selected(self) -> None:
        """With one backend every selection returns that backend."""
        balancer = RoundRobin(["only"])

        selected = [balancer.next_backend() for _ in range(4)]

        assert selected == ["only", "only", "only", "only"]

    def test_empty_backend_list_raises_value_error(self) -> None:
        """Constructing a balancer with no backends fails loudly."""
        with pytest.raises(ValueError, match="at least one backend"):
            RoundRobin([])

    def test_cursor_wraps_around_indefinitely(self) -> None:
        """The cursor returns to the first backend after a full cycle."""
        balancer = RoundRobin(["b1", "b2"])

        assert balancer.next_backend() == "b1"
        assert balancer.next_backend() == "b2"
        assert balancer.next_backend() == "b1"

    def test_backend_list_is_copied_not_aliased(self) -> None:
        """Mutating the caller's list does not change the balancer's cycle."""
        backends = ["b1", "b2"]
        balancer = RoundRobin(backends)

        backends.append("b3")

        assert balancer.next_backend() == "b1"
        assert balancer.next_backend() == "b2"
        assert balancer.next_backend() == "b1"