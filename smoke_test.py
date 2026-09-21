import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT) not in sys.path:
    sys.path.insert(1, str(ROOT))

try:
    from engine.generator import generate_puzzle
    from engine.models import Difficulty, PuzzleConfig
    from core.grid_raster import render_grid_image, render_solution_image
except ModuleNotFoundError:
    from modules.word_search.generator import generate_puzzle
    from modules.word_search.models import Difficulty, PuzzleConfig
    from core.grid_raster import render_grid_image, render_solution_image

# 1. Test standard medium puzzle (13x13)
cfg = PuzzleConfig(difficulty=Difficulty.medium, words_per_page=6, seed=42)
puzzle = generate_puzzle(["APPLE", "BANANA", "CHERRY", "ORANGE", "PEAR", "MELON"], cfg, theme="Fruit")
assert puzzle.rows == 13 and puzzle.cols == 13
assert len(puzzle.words) == 6
assert all(len(row) == puzzle.cols for row in puzzle.grid)
print(f"ok standard pageshape={puzzle.rows}x{puzzle.cols} words={len(puzzle.words)}")

# 2. Test dynamic 10x10 (Kids preset)
cfg_kids = PuzzleConfig(difficulty=Difficulty.easy, grid_rows=10, grid_cols=10, words_per_page=5, seed=101)
p_kids = generate_puzzle(["CAT", "DOG", "BIRD", "FISH", "FROG"], cfg_kids, theme="Animals")
assert p_kids.rows == 10 and p_kids.cols == 10
assert len(p_kids.grid) == 10 and len(p_kids.grid[0]) == 10
print(f"ok dynamic 10x10 pageshape={p_kids.rows}x{p_kids.cols}")

# 3. Test dynamic 12x10 (Activity book rectangular layout)
cfg_rect = PuzzleConfig(difficulty=Difficulty.medium, grid_rows=12, grid_cols=10, words_per_page=6, seed=202)
p_rect = generate_puzzle(["SUMMER", "WINTER", "SPRING", "AUTUMN", "SEASON", "WEATHER"], cfg_rect, theme="Seasons")
assert p_rect.rows == 12 and p_rect.cols == 10
assert len(p_rect.grid) == 12 and len(p_rect.grid[0]) == 10
print(f"ok dynamic 12x10 pageshape={p_rect.rows}x{p_rect.cols}")

# 4. Test rendering with different styles and line removal
# 4a. Kids style (rounded boxes, 76% font scale, 0.8mm line)
style_kids = SimpleNamespace(
    cell_style="rounded_boxes",
    grid_line_width=0.8,
    grid_line_color="#516d61",
    font_scale=0.76,
    letter_font="DejaVu Sans Bold",
    letter_color="#172721",
    solution_style="capsule",
    solution_color="#172721",
)
img_kids = render_grid_image(p_kids, style_kids, cell_mm=12.5, dpi=150)
assert img_kids.size[0] > 0 and img_kids.size[1] > 0
sol_kids = render_solution_image(p_kids, style_kids, cell_mm=12.5, dpi=150)
assert sol_kids.size == img_kids.size

# 4b. Senior / Large print (bold grid, 82% font scale, 1.2mm line)
style_senior = SimpleNamespace(
    cell_style="grid",
    grid_line_width=1.2,
    grid_line_color="#111815",
    font_scale=0.82,
    letter_font="DejaVu Sans Bold",
    letter_color="#000000",
    solution_style="bold",
    solution_color="#000000",
)
img_senior = render_grid_image(p_rect, style_senior, cell_mm=12.5, dpi=150)
assert img_senior.size[0] > 0 and img_senior.size[1] > 0
sol_senior = render_solution_image(p_rect, style_senior, cell_mm=12.5, dpi=150)
assert sol_senior.size == img_senior.size

# 4c. Minimalist / No Lines (cell_style="none", grid_line_width=0.0)
style_none = SimpleNamespace(
    cell_style="none",
    grid_line_width=0.0,
    grid_line_color="#9da49f",
    font_scale=0.70,
    letter_font="DejaVu Sans",
    letter_color="#1c2621",
    solution_style="capsule",
    solution_color="#1c2621",
)
img_none = render_grid_image(p_rect, style_none, cell_mm=12.5, dpi=150)
sol_none = render_solution_image(p_rect, style_none, cell_mm=12.5, dpi=150)
assert img_none.size == sol_none.size

# 4d. Outer border only
style_outer = SimpleNamespace(
    cell_style="outer_border",
    grid_line_width=0.8,
    grid_line_color="#202a26",
    font_scale=0.62,
    letter_font="DejaVu Sans",
    letter_color="#202a26",
    solution_style="box",
    solution_color="#202a26",
)
img_outer = render_grid_image(p_rect, style_outer, cell_mm=12.5, dpi=150)
sol_outer = render_solution_image(p_rect, style_outer, cell_mm=12.5, dpi=150)
assert img_outer.size == sol_outer.size

import xlsxwriter

# 5. Multilingual Puzzle Generation & Rendering Tests
# 5a. German Puzzle (Ä, Ö, Ü, ß -> SS)
cfg_de = PuzzleConfig(
    difficulty=Difficulty.medium,
    grid_rows=12,
    grid_cols=12,
    words_per_page=5,
    seed=303,
    fill_alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ",
)
words_de = ["LÖWE", "BÄR", "KÄFER", "VÖGEL", "FÜCHSE"]
p_de = generate_puzzle(words_de, cfg_de, theme="Deutsche Tiere")
assert p_de.rows == 12 and p_de.cols == 12
assert len(p_de.words) == 5
assert any("Ä" in row or "Ö" in row or "Ü" in row for row in p_de.grid)
img_de = render_grid_image(p_de, style_kids, cell_mm=12.5, dpi=150)
sol_de = render_solution_image(p_de, style_kids, cell_mm=12.5, dpi=150)
assert img_de.size == sol_de.size
print(f"ok German puzzle generation and rendering: {p_de.rows}x{p_de.cols}")

# 5b. Spanish Puzzle (Ñ letter support in Sopa de Letras)
cfg_es = PuzzleConfig(
    difficulty=Difficulty.medium,
    grid_rows=11,
    grid_cols=11,
    words_per_page=5,
    seed=404,
    fill_alphabet="ABCDEFGHIJKLMNÑOPQRSTUVWXYZ",
)
words_es = ["ESPAÑA", "MONTAÑA", "PIÑA", "SUEÑO", "OTOÑO"]
p_es = generate_puzzle(words_es, cfg_es, theme="Sopa de Letras")
assert p_es.rows == 11 and p_es.cols == 11
assert len(p_es.words) == 5
assert any("Ñ" in row for row in p_es.grid)
img_es = render_grid_image(p_es, style_senior, cell_mm=12.5, dpi=150)
sol_es = render_solution_image(p_es, style_senior, cell_mm=12.5, dpi=150)
assert img_es.size == sol_es.size
print(f"ok Spanish puzzle generation and rendering: {p_es.rows}x{p_es.cols}")

# 5c. Word normalization & language cleaning logic
import unicodedata

def clean_word_for_language(raw_word: str, language: str, accent_mode: str = "Standard Book Mode") -> str:
    w = (raw_word or "").strip().upper()
    if not w:
        return ""
    w = w.replace("ß", "SS").replace("ẞ", "SS")
    if accent_mode == "Preserve Exact Accents":
        return "".join(ch for ch in w if ch.isalpha())
    if accent_mode == "Strip All Accents (A-Z)":
        nfkd = unicodedata.normalize("NFKD", w)
        return "".join(ch for ch in nfkd if "A" <= ch <= "Z")
    if "Spanish" in language:
        out = []
        for ch in w:
            if ch == "Ñ":
                out.append("Ñ")
            else:
                nfkd = unicodedata.normalize("NFKD", ch)
                letters = [c for c in nfkd if "A" <= c <= "Z"]
                if letters:
                    out.append(letters[0])
        return "".join(out)
    elif "German" in language:
        out = []
        for ch in w:
            if ch in ("Ä", "Ö", "Ü"):
                out.append(ch)
            else:
                nfkd = unicodedata.normalize("NFKD", ch)
                letters = [c for c in nfkd if "A" <= c <= "Z"]
                if letters:
                    out.append(letters[0])
        return "".join(out)
    else:
        nfkd = unicodedata.normalize("NFKD", w)
        return "".join(ch for ch in nfkd if "A" <= ch <= "Z")

# Test clean_word_for_language across all supported languages
assert clean_word_for_language("schloß", "German") == "SCHLOSS"
assert clean_word_for_language("löwe", "German") == "LÖWE"
assert clean_word_for_language("españa", "Spanish") == "ESPAÑA"
assert clean_word_for_language("león", "Spanish") == "LEON"
assert clean_word_for_language("éléphant", "French") == "ELEPHANT"
assert clean_word_for_language("éléphant", "French", "Preserve Exact Accents") == "ÉLÉPHANT"
assert clean_word_for_language("città", "Italian") == "CITTA"
assert clean_word_for_language("españa", "Spanish", "Strip All Accents (A-Z)") == "ESPANA"
print("ok clean_word_for_language passed all language scenarios")

print("ALL SMOKE TESTS PASSED SUCCESSFULLY!")

