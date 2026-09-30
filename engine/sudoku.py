"""Sudoku puzzle generator and solver engine for KDP Activity Studio.

Supports:
- Classic 9x9 Sudoku
- Kids Mini 4x4 Sudoku
- Junior 6x6 Sudoku
- Wordoku / Alphabet 9x9 (uses 9 distinct letters from a keyword)
- Sudoku X (Diagonal Sudoku with main diagonals)
- Windoku (Hyper Sudoku with 4 inner shaded 3x3 windows)
- Symmetric clue removal (180° rotation) for authentic print-quality puzzles
- Unique solution verification using MRV backtracking
"""
from __future__ import annotations

import random
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field


class SudokuType(str, Enum):
    CLASSIC_9X9 = "classic_9x9"
    MINI_4X4 = "mini_4x4"
    JUNIOR_6X6 = "junior_6x6"
    WORDOKU_9X9 = "wordoku_9x9"
    SUDOKU_X = "sudoku_x"
    WINDOKU = "windoku"


class SudokuDifficulty(str, Enum):
    VERY_EASY = "very_easy"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


# Recommended target clue counts for each size and difficulty
TARGET_CLUES: Dict[str, Dict[SudokuDifficulty, int]] = {
    "4x4": {
        SudokuDifficulty.VERY_EASY: 9,
        SudokuDifficulty.EASY: 8,
        SudokuDifficulty.MEDIUM: 6,
        SudokuDifficulty.HARD: 5,
        SudokuDifficulty.EXPERT: 4,
    },
    "6x6": {
        SudokuDifficulty.VERY_EASY: 20,
        SudokuDifficulty.EASY: 17,
        SudokuDifficulty.MEDIUM: 14,
        SudokuDifficulty.HARD: 12,
        SudokuDifficulty.EXPERT: 10,
    },
    "9x9": {
        SudokuDifficulty.VERY_EASY: 46,
        SudokuDifficulty.EASY: 38,
        SudokuDifficulty.MEDIUM: 32,
        SudokuDifficulty.HARD: 27,
        SudokuDifficulty.EXPERT: 24,
    },
}

DIFFICULTY_STARS: Dict[SudokuDifficulty, str] = {
    SudokuDifficulty.VERY_EASY: "★☆☆☆☆",
    SudokuDifficulty.EASY: "★★☆☆☆",
    SudokuDifficulty.MEDIUM: "★★★☆☆",
    SudokuDifficulty.HARD: "★★★★☆",
    SudokuDifficulty.EXPERT: "★★★★★",
}

DIFFICULTY_LABELS: Dict[SudokuDifficulty, str] = {
    SudokuDifficulty.VERY_EASY: "Very Easy",
    SudokuDifficulty.EASY: "Easy",
    SudokuDifficulty.MEDIUM: "Medium",
    SudokuDifficulty.HARD: "Hard",
    SudokuDifficulty.EXPERT: "Expert",
}

TYPE_LABELS: Dict[SudokuType, str] = {
    SudokuType.CLASSIC_9X9: "Classic 9×9",
    SudokuType.MINI_4X4: "Kids Mini 4×4",
    SudokuType.JUNIOR_6X6: "Junior 6×6",
    SudokuType.WORDOKU_9X9: "Wordoku (Letter 9×9)",
    SudokuType.SUDOKU_X: "Sudoku X (Diagonal)",
    SudokuType.WINDOKU: "Windoku (Hyper 4-Window)",
}

DEFAULT_WORDOKU_WORDS = [
    "PUBLISHER",
    "ALGORITHM",
    "AUTHORING",
    "CHEMISTRY",
    "DANGEROUS",
    "DISCOVERY",
    "BLUEPRINT",
    "CHILDRENS",
    "WONDERFUL",
    "CAMPGROUN",
    "EDUCATION",
    "NOTEBOOKS", # Cleaned to 9 unique in fallback
]


class SudokuConfig(BaseModel):
    puzzle_type: SudokuType = SudokuType.CLASSIC_9X9
    difficulty: SudokuDifficulty = SudokuDifficulty.MEDIUM
    target_clues: Optional[int] = None
    seed: Optional[int] = 42
    symmetric: bool = True
    wordoku_word: Optional[str] = "PUBLISHER"
    title_template: str = "Sudoku #{num}"


class SudokuPuzzle(BaseModel):
    puzzle_id: int
    puzzle_type: SudokuType
    size: int
    box_rows: int
    box_cols: int
    difficulty: SudokuDifficulty
    difficulty_label: str
    difficulty_stars: str
    clues_grid: List[List[str]] # Empty cells are ""
    solution_grid: List[List[str]]
    clues_count: int
    title: str
    symbols: List[str]
    wordoku_word: Optional[str] = None
    is_x: bool = False
    is_windoku: bool = False


def clean_wordoku_letters(raw_word: str) -> List[str]:
    """Extract exactly 9 distinct uppercase letters from a word or fallback to default."""
    cleaned = []
    seen = set()
    for ch in (raw_word or "").upper():
        if "A" <= ch <= "Z" and ch not in seen:
            seen.add(ch)
            cleaned.append(ch)
            if len(cleaned) == 9:
                break
    if len(cleaned) < 9:
        for ch in "PUBLISHER":
            if ch not in seen:
                seen.add(ch)
                cleaned.append(ch)
                if len(cleaned) == 9:
                    break
    return cleaned[:9]


def get_grid_dimensions(p_type: SudokuType) -> Tuple[int, int, int]:
    """Return (size, box_rows, box_cols)."""
    if p_type == SudokuType.MINI_4X4:
        return 4, 2, 2
    if p_type == SudokuType.JUNIOR_6X6:
        return 6, 2, 3
    return 9, 3, 3


def get_default_clues(size: int, difficulty: SudokuDifficulty) -> int:
    category = f"{size}x{size}"
    if category not in TARGET_CLUES:
        category = "9x9"
    return TARGET_CLUES[category].get(difficulty, 32)


def solve_sudoku_board(
    grid: List[List[int]],
    size: int,
    box_r: int,
    box_c: int,
    is_x: bool = False,
    is_windoku: bool = False,
    count_only: bool = False,
    max_count: int = 2,
    rng: Optional[random.Random] = None,
) -> int | bool:
    """MRV backtracking solver. Returns True/False for search, or solution count if count_only."""
    if rng is None:
        rng = random

    min_candidates = None
    min_cell = None
    all_filled = True

    windows = [(1, 1), (1, 5), (5, 1), (5, 5)] if is_windoku and size == 9 else []

    for r in range(size):
        row_vals = set(grid[r])
        for c in range(size):
            if grid[r][c] == 0:
                all_filled = False
                cands = []
                for v in range(1, size + 1):
                    if v in row_vals:
                        continue
                    if any(grid[i][c] == v for i in range(size)):
                        continue
                    br = (r // box_r) * box_r
                    bc = (c // box_c) * box_c
                    if any(grid[i][j] == v for i in range(br, br + box_r) for j in range(bc, bc + box_c)):
                        continue
                    if is_x:
                        if r == c and any(grid[i][i] == v for i in range(size)):
                            continue
                        if r + c == size - 1 and any(grid[i][size - 1 - i] == v for i in range(size)):
                            continue
                    if is_windoku:
                        failed_win = False
                        for wr, wc in windows:
                            if wr <= r < wr + 3 and wc <= c < wc + 3:
                                if any(grid[i][j] == v for i in range(wr, wr + 3) for j in range(wc, wc + 3)):
                                    failed_win = True
                                    break
                        if failed_win:
                            continue
                    cands.append(v)

                if len(cands) == 0:
                    return 0 if count_only else False
                if min_candidates is None or len(cands) < len(min_candidates):
                    min_candidates = cands
                    min_cell = (r, c)
                    if len(cands) == 1:
                        break
        if min_candidates and len(min_candidates) == 1:
            break

    if all_filled:
        return 1 if count_only else True

    r, c = min_cell
    cands_copy = list(min_candidates)
    rng.shuffle(cands_copy)
    sol_count = 0

    for v in cands_copy:
        grid[r][c] = v
        if count_only:
            sub = solve_sudoku_board(
                grid, size, box_r, box_c, is_x, is_windoku, count_only=True, max_count=max_count, rng=rng
            )
            sol_count += sub
            if sol_count >= max_count:
                grid[r][c] = 0
                return sol_count
        else:
            if solve_sudoku_board(grid, size, box_r, box_c, is_x, is_windoku, count_only=False, rng=rng):
                return True
        grid[r][c] = 0

    return sol_count if count_only else False


def generate_sudoku_puzzle(
    puzzle_id: int,
    config: SudokuConfig,
) -> SudokuPuzzle:
    """Generate a single verified Sudoku puzzle according to config."""
    rng = random.Random((config.seed or 100) + puzzle_id * 17 + 3)

    size, box_r, box_c = get_grid_dimensions(config.puzzle_type)
    is_x = config.puzzle_type == SudokuType.SUDOKU_X
    is_windoku = config.puzzle_type == SudokuType.WINDOKU

    target_clues = config.target_clues or get_default_clues(size, config.difficulty)

    # 1. Generate full solved board
    board = [[0] * size for _ in range(size)]
    solve_sudoku_board(board, size, box_r, box_c, is_x=is_x, is_windoku=is_windoku, rng=rng)
    solution_numeric = [row[:] for row in board]

    # 2. Clue removal with rotational symmetry (if requested)
    current_clues = size * size
    puzzle_numeric = [row[:] for row in board]

    if config.symmetric:
        pairs = []
        seen = set()
        for r in range(size):
            for c in range(size):
                if (r, c) not in seen:
                    sr, sc = size - 1 - r, size - 1 - c
                    seen.add((r, c))
                    seen.add((sr, sc))
                    if (r, c) == (sr, sc):
                        pairs.append([(r, c)])
                    else:
                        pairs.append([(r, c), (sr, sc)])
        rng.shuffle(pairs)

        for p in pairs:
            if current_clues <= target_clues:
                break
            removed_vals = [(r, c, puzzle_numeric[r][c]) for r, c in p]
            for r, c, _ in removed_vals:
                puzzle_numeric[r][c] = 0

            test_board = [row[:] for row in puzzle_numeric]
            sols = solve_sudoku_board(
                test_board, size, box_r, box_c, is_x=is_x, is_windoku=is_windoku, count_only=True, max_count=2, rng=rng
            )
            if sols != 1:
                # Put them back
                for r, c, val in removed_vals:
                    puzzle_numeric[r][c] = val
            else:
                current_clues -= len(removed_vals)

    # 3. Asymmetric pass if more clues need to be removed or symmetric was False
    if current_clues > target_clues:
        active_cells = [(r, c) for r in range(size) for c in range(size) if puzzle_numeric[r][c] != 0]
        rng.shuffle(active_cells)
        for r, c in active_cells:
            if current_clues <= target_clues:
                break
            val = puzzle_numeric[r][c]
            puzzle_numeric[r][c] = 0
            test_board = [row[:] for row in puzzle_numeric]
            sols = solve_sudoku_board(
                test_board, size, box_r, box_c, is_x=is_x, is_windoku=is_windoku, count_only=True, max_count=2, rng=rng
            )
            if sols != 1:
                puzzle_numeric[r][c] = val
            else:
                current_clues -= 1

    # 4. Symbol mapping (Digits 1-N or Letters for Wordoku)
    wordoku_letters = None
    if config.puzzle_type == SudokuType.WORDOKU_9X9:
        wordoku_letters = clean_wordoku_letters(config.wordoku_word or "PUBLISHER")
        # Map 1-9 to the 9 distinct letters
        symbol_map = {i + 1: wordoku_letters[i] for i in range(9)}
        symbols = wordoku_letters
    else:
        symbol_map = {i + 1: str(i + 1) for i in range(size)}
        symbols = [str(i + 1) for i in range(size)]

    clues_grid = [
        [symbol_map[puzzle_numeric[r][c]] if puzzle_numeric[r][c] != 0 else "" for c in range(size)]
        for r in range(size)
    ]
    solution_grid = [
        [symbol_map[solution_numeric[r][c]] for c in range(size)]
        for r in range(size)
    ]

    title = config.title_template.replace("{num}", str(puzzle_id)).replace(
        "{diff}", DIFFICULTY_LABELS.get(config.difficulty, "Medium")
    ).replace("{type}", TYPE_LABELS.get(config.puzzle_type, "Sudoku"))

    return SudokuPuzzle(
        puzzle_id=puzzle_id,
        puzzle_type=config.puzzle_type,
        size=size,
        box_rows=box_r,
        box_cols=box_c,
        difficulty=config.difficulty,
        difficulty_label=DIFFICULTY_LABELS[config.difficulty],
        difficulty_stars=DIFFICULTY_STARS[config.difficulty],
        clues_grid=clues_grid,
        solution_grid=solution_grid,
        clues_count=current_clues,
        title=title,
        symbols=symbols,
        wordoku_word="".join(wordoku_letters) if wordoku_letters else None,
        is_x=is_x,
        is_windoku=is_windoku,
    )
