"""PuzzleConfig — pydantic model for word-search generation options (plan §5).

All generator behaviour is driven by this config; nothing is hardcoded in the
algorithm. Difficulty presets expand into concrete direction/grid settings.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# Canonical direction vectors as (d_row, d_col). Row increases downward.
DIRECTION_VECTORS: dict[str, tuple[int, int]] = {
    "E": (0, 1),
    "W": (0, -1),
    "S": (1, 0),
    "N": (-1, 0),
    "SE": (1, 1),
    "NW": (-1, -1),
    "NE": (-1, 1),
    "SW": (1, -1),
}

ALL_DIRECTIONS = list(DIRECTION_VECTORS.keys())
# "Forward" directions (used before reverse ones are added in).
FORWARD_DIRECTIONS = ["E", "S", "SE", "NE"]
REVERSE_OF = {"E": "W", "S": "N", "SE": "NW", "NE": "SW"}


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"
    custom = "custom"


# Preset table (plan §5.2): directions, reverse, grid size.
_PRESETS: dict[Difficulty, dict] = {
    Difficulty.easy: {
        "directions": ["E", "S"],
        "allow_reverse": False,
        "grid_rows": 10,
        "grid_cols": 10,
    },
    Difficulty.medium: {
        "directions": ["E", "S", "SE", "NE"],
        "allow_reverse": False,
        "grid_rows": 13,
        "grid_cols": 13,
    },
    Difficulty.hard: {
        "directions": ALL_DIRECTIONS,
        "allow_reverse": True,
        "grid_rows": 16,
        "grid_cols": 16,
    },
}


def max_words_for_grid(rows: int, cols: int) -> int:
    """Word capacity of a grid: ~45% of cells filled by word letters at an
    average word length of 6. 10x10 -> 8, 13x13 -> 13, 16x16 -> 19."""
    return max(4, round(rows * cols * 0.45 / 6))


class PuzzleConfig(BaseModel):
    """Word-search generation options."""

    difficulty: Difficulty = Difficulty.medium

    # Grid — None means "take from the difficulty preset".
    grid_rows: Optional[int] = None
    grid_cols: Optional[int] = None

    # Direction control — None means "take from the difficulty preset".
    directions: Optional[list[str]] = None
    allow_reverse: Optional[bool] = None
    allow_overlap: bool = True

    # None => derived from grid capacity via max_words_for_grid().
    words_per_page: Optional[int] = None

    # Fill behaviour (plan §5.1).
    smart_fill: bool = False  # True => fill only from letters used in words
    fill_alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    avoid_bad_words: bool = True  # scrub accidental blacklisted words in fill
    extra_blacklist: list[str] = Field(default_factory=list)
    avoid_duplicate_words: bool = True  # ensure each listed word appears once

    # Placement effort knobs.
    max_word_attempts: int = 200  # per-word placement attempts
    max_grid_retries: int = 20  # whole-grid retries before giving up on a word

    seed: Optional[int] = None

    @model_validator(mode="after")
    def _apply_preset(self) -> "PuzzleConfig":
        """Fill unset fields from the difficulty preset (custom => keep given)."""
        preset = _PRESETS.get(self.difficulty)
        if preset is not None:
            if self.directions is None:
                self.directions = list(preset["directions"])
            if self.allow_reverse is None:
                self.allow_reverse = preset["allow_reverse"]
            if self.grid_rows is None:
                self.grid_rows = preset["grid_rows"]
            if self.grid_cols is None:
                self.grid_cols = preset["grid_cols"]


        # Custom with nothing supplied => sensible defaults.
        if self.directions is None:
            self.directions = list(FORWARD_DIRECTIONS)
        if self.allow_reverse is None:
            self.allow_reverse = False
        if self.grid_rows is None:
            self.grid_rows = 13
        if self.grid_cols is None:
            self.grid_cols = 13
        if self.words_per_page is None:
            # Linked to grid capacity (see max_words_for_grid).
            self.words_per_page = max_words_for_grid(self.grid_rows, self.grid_cols)
        return self

    def resolved_directions(self) -> list[str]:
        """Effective direction list, adding reverses when allow_reverse is set."""
        dirs = list(self.directions or [])
        if self.allow_reverse:
            for d in list(dirs):
                rev = REVERSE_OF.get(d)
                if rev and rev not in dirs:
                    dirs.append(rev)
        # De-duplicate while preserving order.
        seen: set[str] = set()
        out: list[str] = []
        for d in dirs:
            if d in DIRECTION_VECTORS and d not in seen:
                seen.add(d)
                out.append(d)
        return out
