import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from modules.word_search.generator import generate_puzzle
    from modules.word_search.models import Difficulty, PuzzleConfig
except ModuleNotFoundError:
    from engine.generator import generate_puzzle
    from engine.models import Difficulty, PuzzleConfig

cfg = PuzzleConfig(difficulty=Difficulty.medium, words_per_page=6, seed=42)
puzzle = generate_puzzle(["APPLE", "BANANA", "CHERRY", "ORANGE", "PEAR", "MELON"], cfg, theme="Fruit")
assert puzzle.rows == 13 and puzzle.cols == 13
assert len(puzzle.words) == 6
assert all(len(row) == puzzle.cols for row in puzzle.grid)
import xlsxwriter
print(f"ok pageshape={puzzle.rows}x{puzzle.cols} words={len(puzzle.words)}")
