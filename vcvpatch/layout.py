"""
Pure layout values for explicit VCV Rack module placement.

The core builder API is agent-first: placement is part of the plan, not a
hidden cursor inside PatchBuilder. Layout objects therefore describe space and
yield positions, but they do not add modules or mutate global state.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """Exact Rack placement expressed in HP column and row index."""
    hp: int
    row: int

    def as_list(self) -> list[int]:
        return [self.hp, self.row]


@dataclass(frozen=True)
class Row:
    """A spatial row descriptor. Rows yield positions; they do not own modules."""
    index: int

    def at(self, hp: int) -> Position:
        return Position(hp=hp, row=self.index)


class RackLayout:
    """Namespace for pure layout helpers."""

    def row(self, index: int) -> Row:
        return Row(index=index)

    def at(self, hp: int, row: int) -> Position:
        return Position(hp=hp, row=row)


def position(hp: int, row: int) -> Position:
    """Convenience constructor for an explicit position value."""
    return Position(hp=hp, row=row)
