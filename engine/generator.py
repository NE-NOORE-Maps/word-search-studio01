"""Word-search grid generation & word placement (plan §5).

Algorithm (plan §5.1):
  1. Sort words longest-first.
  2. For each word, shuffle candidate directions & positions; place with
     backtracking-style retry.
  3. If a word can't be placed after N attempts -> retry the whole grid
     (up to R retries) -> if still failing, report the word and continue.
     Never crash.
  4. Fill remaining cells with random letters (smart fill optional).
  5. Seedable RNG -> reproducible books.

The output object is a ``Puzzle`` (grid + placements + theme + words).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .models import DIRECTION_VECTORS, PuzzleConfig
from .wordlist import build_blacklist

EMPTY = ""  # marker for an unfilled cell during placement


@dataclass
class Placement:
    """Where a word was placed, for the solutions renderer."""

    word: str
    start: tuple[int, int]  # (row, col)
    direction: str  # key into DIRECTION_VECTORS

    def cells(self) -> list[tuple[int, int]]:
        """The (row, col) cells the word occupies, in order."""
        dr, dc = DIRECTION_VECTORS[self.direction]
        r, c = self.start
        return [(r + dr * i, c + dc * i) for i in range(len(self.word))]

    @property
    def end(self) -> tuple[int, int]:
        return self.cells()[-1]


@dataclass
class Puzzle:
    """A generated puzzle."""

    grid: list[list[str]]
    placements: list[Placement]
    theme: str
    words: list[str]
    skipped: list[str] = field(default_factory=list)

    @property
    def rows(self) -> int:
        return len(self.grid)

    @property
    def cols(self) -> int:
        return len(self.grid[0]) if self.grid else 0


class GenerationError(Exception):
    """Raised only for programmer errors (never for unplaceable words)."""


def _normalize_words(raw: list[str]) -> list[str]:
    """Uppercase, strip whitespace, drop empties, de-duplicate (keep order)."""
    seen: set[str] = set()
    out: list[str] = []
    for w in raw:
        w2 = (w or "").strip().upper()
        if not w2 or w2 in seen:
            continue
        seen.add(w2)
        out.append(w2)
    return out


def _can_place(
    grid: list[list[str]],
    word: str,
    start: tuple[int, int],
    direction: str,
    allow_overlap: bool,
) -> bool:
    dr, dc = DIRECTION_VECTORS[direction]
    r0, c0 = start
    rows, cols = len(grid), len(grid[0])
    for i, ch in enumerate(word):
        r, c = r0 + dr * i, c0 + dc * i
        if not (0 <= r < rows and 0 <= c < cols):
            return False
        cur = grid[r][c]
        if cur == EMPTY:
            continue
        if cur != ch:
            return False  # conflicting letter
        if not allow_overlap:
            return False  # occupied cell, overlaps disallowed
    return True


def _write(grid: list[list[str]], word: str, start: tuple[int, int], direction: str) -> None:
    dr, dc = DIRECTION_VECTORS[direction]
    r0, c0 = start
    for i, ch in enumerate(word):
        grid[r0 + dr * i][c0 + dc * i] = ch


def _place_word(
    grid: list[list[str]],
    word: str,
    directions: list[str],
    allow_overlap: bool,
    rng: random.Random,
    max_attempts: int,
) -> Optional[Placement]:
    """Try to place a single word; return its Placement or None."""
    rows, cols = len(grid), len(grid[0])

    # Build a shuffled candidate list of (start, direction) so retries explore
    # different spots. Cap the number of attempts.
    dir_pool = list(directions)
    rng.shuffle(dir_pool)

    attempts = 0
    while attempts < max_attempts:
        direction = dir_pool[attempts % len(dir_pool)]
        r = rng.randrange(rows)
        c = rng.randrange(cols)
        attempts += 1
        if _can_place(grid, word, (r, c), direction, allow_overlap):
            _write(grid, word, (r, c), direction)
            return Placement(word=word, start=(r, c), direction=direction)
    return None


def _fill_empties(
    grid: list[list[str]],
    placed_words: list[str],
    cfg: PuzzleConfig,
    rng: random.Random,
) -> None:
    if cfg.smart_fill:
        pool = sorted({ch for w in placed_words for ch in w})
        if not pool:  # no placed words -> fall back to full alphabet
            pool = list(cfg.fill_alphabet)
    else:
        pool = list(cfg.fill_alphabet)
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == EMPTY:
                grid[r][c] = rng.choice(pool)


def _grid_lines(rows: int, cols: int) -> list[list[tuple[int, int]]]:
    """All maximal straight lines (H, V, both diagonals) as coordinate lists."""
    lines: list[list[tuple[int, int]]] = []
    # Horizontal.
    for r in range(rows):
        lines.append([(r, c) for c in range(cols)])
    # Vertical.
    for c in range(cols):
        lines.append([(r, c) for r in range(rows)])
    # Diagonals down-right (constant r-c).
    for start in range(-(rows - 1), cols):
        line = [(r, r - start) for r in range(rows) if 0 <= r - start < cols]
        if len(line) >= 3:
            lines.append(line)
    # Diagonals down-left (constant r+c).
    for s in range(rows + cols - 1):
        line = [(r, s - r) for r in range(rows) if 0 <= s - r < cols]
        if len(line) >= 3:
            lines.append(line)
    return lines


def _scrub_bad_words(
    grid: list[list[str]],
    protected: set[tuple[int, int]],
    blacklist: frozenset[str],
    rng: random.Random,
    max_passes: int = 8,
) -> int:
    """Re-roll fill letters that accidentally spell blacklisted words.

    Only cells not part of a real placement are changed. Returns the number of
    substitutions made. Matches wholly inside placements are left alone (those
    are intended words).
    """
    if not blacklist:
        return 0
    max_len = max(len(w) for w in blacklist)
    lines = _grid_lines(len(grid), len(grid[0]))
    changes = 0
    for _ in range(max_passes):
        dirty = False
        for line in lines:
            s = "".join(grid[r][c] for (r, c) in line)
            for forward in (s, s[::-1]):
                coords = line if forward is s else line[::-1]
                lo = forward.upper()
                for wlen in range(3, max_len + 1):
                    for i in range(0, len(lo) - wlen + 1):
                        if lo[i : i + wlen] in blacklist:
                            window = coords[i : i + wlen]
                            editable = [rc for rc in window if rc not in protected]
                            if not editable:
                                continue  # all letters are intended placements
                            r, c = rng.choice(editable)
                            cur = grid[r][c]
                            choices = [ch for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if ch != cur]
                            grid[r][c] = rng.choice(choices)
                            changes += 1
                            dirty = True
        if not dirty:
            break
    return changes


def _scrub_duplicate_words(
    grid: list[list[str]],
    placements: list["Placement"],
    rng: random.Random,
    max_passes: int = 8,
) -> int:
    """Ensure each placed word appears in the grid only at its own placement.

    Scans every line (8 directions). If a listed word is spelled anywhere other
    than its intended cell path (an accidental duplicate created by the random
    fill), one fill cell in that occurrence is re-rolled to break it. Cells that
    belong to a real placement are never changed. Returns substitutions made.
    """
    if not placements:
        return 0
    protected = {rc for p in placements for rc in p.cells()}
    # Legit coordinate paths per word (forward + reverse of its placement).
    legit: dict[str, set[tuple]] = {}
    for p in placements:
        cells = tuple(p.cells())
        legit.setdefault(p.word, set()).update({cells, cells[::-1]})
    words = list(legit.keys())
    lines = _grid_lines(len(grid), len(grid[0]))

    changes = 0
    for _ in range(max_passes):
        dirty = False
        for line in lines:
            for coords in (line, line[::-1]):
                s = "".join(grid[r][c] for (r, c) in coords)
                for w in words:
                    start = 0
                    while True:
                        idx = s.find(w, start)
                        if idx < 0:
                            break
                        window = tuple(coords[idx : idx + len(w)])
                        if window not in legit[w]:
                            editable = [rc for rc in window if rc not in protected]
                            if editable:
                                r, c = rng.choice(editable)
                                cur = grid[r][c]
                                grid[r][c] = rng.choice(
                                    [ch for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if ch != cur]
                                )
                                changes += 1
                                dirty = True
                                s = "".join(grid[r2][c2] for (r2, c2) in coords)
                        start = idx + 1
        if not dirty:
            break
    return changes


def generate_puzzle(
    words: list[str],
    cfg: PuzzleConfig,
    theme: str = "",
) -> Puzzle:
    """Generate one puzzle. Never raises for unplaceable words — they are
    collected in ``Puzzle.skipped`` instead.
    """
    rows, cols = cfg.grid_rows, cfg.grid_cols
    if not rows or not cols or rows < 1 or cols < 1:
        raise GenerationError("grid_rows and grid_cols must be >= 1")

    directions = cfg.resolved_directions()
    if not directions:
        raise GenerationError("no directions available for placement")

    rng = random.Random(cfg.seed)

    cleaned = _normalize_words(words)
    max_dim = max(rows, cols)
    # Words that cannot possibly fit are skipped up-front (plan §4.4 / §5.1).
    too_long = [w for w in cleaned if len(w) > max_dim]
    candidates = [w for w in cleaned if len(w) <= max_dim]

    # Longest-first placement (plan §5.1 step 1).
    ordered = sorted(candidates, key=len, reverse=True)

    best_grid: Optional[list[list[str]]] = None
    best_placements: list[Placement] = []
    best_unplaced: list[str] = list(ordered)

    for _ in range(max(1, cfg.max_grid_retries)):
        grid = [[EMPTY for _ in range(cols)] for _ in range(rows)]
        placements: list[Placement] = []
        unplaced: list[str] = []
        for w in ordered:
            p = _place_word(
                grid, w, directions, cfg.allow_overlap, rng, cfg.max_word_attempts
            )
            if p is None:
                unplaced.append(w)
            else:
                placements.append(p)

        if best_grid is None or len(unplaced) < len(best_unplaced):
            best_grid, best_placements, best_unplaced = grid, placements, unplaced
        if not unplaced:
            break  # perfect grid, stop retrying

    assert best_grid is not None  # at least one retry always runs
    _fill_empties(best_grid, [p.word for p in best_placements], cfg, rng)

    if cfg.avoid_bad_words:
        protected = {rc for p in best_placements for rc in p.cells()}
        blacklist = build_blacklist(cfg.extra_blacklist)
        _scrub_bad_words(best_grid, protected, blacklist, rng)

    if cfg.avoid_duplicate_words:
        _scrub_duplicate_words(best_grid, best_placements, rng)

    skipped = too_long + best_unplaced
    return Puzzle(
        grid=best_grid,
        placements=best_placements,
        theme=theme,
        words=[p.word for p in best_placements],
        skipped=skipped,
    )


def word_at(grid: list[list[str]], placement: Placement) -> str:
    """Read the letters out of the grid along a placement (for verification)."""
    return "".join(grid[r][c] for (r, c) in placement.cells())
