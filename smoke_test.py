import os
import sys
import zipfile
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

# 6. Sudoku Engine & Generator Tests
from engine.sudoku import (
    SudokuConfig,
    SudokuType,
    SudokuDifficulty,
    generate_sudoku_puzzle,
    clean_wordoku_letters,
)
from core.sudoku_raster import render_sudoku_image, render_sudoku_solution_image, SUDOKU_PRESETS
from core.sudoku_pdf import build_sudoku_pdf
from core.sudoku_export import build_sudoku_workbooks

# 6a. Classic 9x9 Sudoku
cfg_s9 = SudokuConfig(puzzle_type=SudokuType.CLASSIC_9X9, difficulty=SudokuDifficulty.MEDIUM, seed=10)
p_s9 = generate_sudoku_puzzle(1, cfg_s9)
assert p_s9.size == 9 and p_s9.box_rows == 3 and p_s9.box_cols == 3
assert len(p_s9.clues_grid) == 9 and len(p_s9.solution_grid) == 9
assert 20 <= p_s9.clues_count <= 40
print(f"ok Sudoku Classic 9x9 generated with {p_s9.clues_count} clues")

# 6b. Kids Mini 4x4 Sudoku
cfg_s4 = SudokuConfig(puzzle_type=SudokuType.MINI_4X4, difficulty=SudokuDifficulty.EASY, seed=20)
p_s4 = generate_sudoku_puzzle(2, cfg_s4)
assert p_s4.size == 4 and p_s4.box_rows == 2 and p_s4.box_cols == 2
assert 4 <= p_s4.clues_count <= 10
print(f"ok Sudoku Mini 4x4 generated with {p_s4.clues_count} clues")

# 6c. Junior 6x6 Sudoku
cfg_s6 = SudokuConfig(puzzle_type=SudokuType.JUNIOR_6X6, difficulty=SudokuDifficulty.MEDIUM, seed=30)
p_s6 = generate_sudoku_puzzle(3, cfg_s6)
assert p_s6.size == 6 and p_s6.box_rows == 2 and p_s6.box_cols == 3
assert 10 <= p_s6.clues_count <= 18
print(f"ok Sudoku Junior 6x6 generated with {p_s6.clues_count} clues")

# 6d. Wordoku 9x9 (Letter Sudoku)
letters = clean_wordoku_letters("CHEMISTRY")
assert len(letters) == 9 and len(set(letters)) == 9
cfg_sw = SudokuConfig(puzzle_type=SudokuType.WORDOKU_9X9, wordoku_word="CHEMISTRY", seed=40)
p_sw = generate_sudoku_puzzle(4, cfg_sw)
assert p_sw.wordoku_word == "CHEMISTRY"
assert all(any(c in letters for c in row if c) for row in p_sw.clues_grid)
print("ok Wordoku generated with keyword CHEMISTRY and 9 unique letters")

# 6e. Sudoku X and Windoku
cfg_sx = SudokuConfig(puzzle_type=SudokuType.SUDOKU_X, seed=50)
p_sx = generate_sudoku_puzzle(5, cfg_sx)
assert p_sx.is_x is True
print("ok Sudoku X generated with diagonal constraints")

cfg_win = SudokuConfig(puzzle_type=SudokuType.WINDOKU, seed=60)
p_win = generate_sudoku_puzzle(6, cfg_win)
assert p_win.is_windoku is True
print("ok Windoku generated with hyper-window constraints")

# 6f. Raster rendering tests
style_s_classic = SimpleNamespace(**SUDOKU_PRESETS["👔 Adult Classic"])
img_s = render_sudoku_image(p_s9, style_s_classic, cell_mm=10.0, dpi=150)
sol_s = render_sudoku_solution_image(p_s9, style_s_classic, cell_mm=10.0, dpi=150)
assert img_s.size == sol_s.size and img_s.size[0] > 0
print("ok Sudoku raster rendering test passed")

# 6g. PDF Interior Book generation test
pdf_bytes = build_sudoku_pdf([p_s9, p_s4], style_s_classic, solutions_per_page=2)
assert len(pdf_bytes) > 5000
print("ok Sudoku KDP PDF book generator test passed")

# 7. Composite Solution Page Preview Tests
from core.grid_raster import render_word_search_solution_page_image
from core.sudoku_raster import render_sudoku_solution_page_image

ws_sol_page = render_word_search_solution_page_image([p_kids, p_rect], style_kids, solutions_per_page=2, page_num=1, total_pages=1, dpi=120)
assert ws_sol_page.size[0] > 0 and ws_sol_page.size[1] > 0
print("ok Word Search composite solution page preview test passed")

sdk_sol_page = render_sudoku_solution_page_image([p_s9, p_s4], style_s_classic, solutions_per_page=2, page_num=1, total_pages=1, dpi=120)
assert sdk_sol_page.size[0] > 0 and sdk_sol_page.size[1] > 0
print("ok Sudoku composite solution page preview test passed")

# 8. Sudoku Workbook Export with same vs separate Excel
import tempfile
out_sdk_same = tempfile.mkdtemp(prefix="sdk_same_test_")
canva_same, sol_same, zip_same, pdf_same = build_sudoku_workbooks([p_s9], out_sdk_same, include_solution_in_same_excel=True)
assert os.path.exists(canva_same)
assert sol_same is None
assert os.path.exists(zip_same)
assert len(pdf_same) > 0
print("ok Sudoku workbook export with solution in same excel passed")

out_sdk_sep = tempfile.mkdtemp(prefix="sdk_sep_test_")
canva_sep, sol_sep, zip_sep, pdf_sep = build_sudoku_workbooks([p_s9], out_sdk_sep, include_solution_in_same_excel=False)
assert os.path.exists(canva_sep)
assert sol_sep is not None and os.path.exists(sol_sep)
assert os.path.exists(zip_sep)
print("ok Sudoku workbook export with separate solutions excel passed")

# 9. Sudoku Multi-Game Per Page Tests (1, 2, 4, 6 games per page)
from core.sudoku_raster import render_sudoku_puzzle_page_image

test_puzzles = [p_s9, p_s4, p_s6, p_sw, p_sx, p_win]

# 9a. Test book interior page rendering for 1, 2, 4, 6
for g_per_page in [1, 2, 4, 6]:
    puz_page_img = render_sudoku_puzzle_page_image(
        test_puzzles[:g_per_page],
        style_s_classic,
        puzzles_per_page=g_per_page,
        page_num=1,
        total_pages=2,
        dpi=120,
        include_instructions=True,
    )
    assert puz_page_img.size[0] > 0 and puz_page_img.size[1] > 0
    print(f"ok Sudoku interior book page with {g_per_page} game(s)/page rendered successfully")

# 9b. Test PDF with 4 games per page
pdf_multi = build_sudoku_pdf(test_puzzles, style_s_classic, puzzles_per_page=4, solutions_per_page=6)
assert len(pdf_multi) > 10000
print("ok Sudoku KDP PDF book generator with 4 games/page passed")

# 9c. Test Workbook Export with 4 games per page
out_sdk_multi = tempfile.mkdtemp(prefix="sdk_multi_test_")
canva_multi, sol_multi, zip_multi, pdf_multi_exp = build_sudoku_workbooks(
    test_puzzles,
    out_sdk_multi,
    puzzles_per_page=4,
    solutions_per_page=6,
    include_solution_in_same_excel=True,
)
assert os.path.exists(canva_multi)
assert os.path.exists(zip_multi)
assert len(pdf_multi_exp) > 0
print("ok Sudoku workbook & Canva export with 4 games/page passed")

# 10. Sudoku Date & Calendar Integration Tests
from core.calendar_builder import (
    DATE_FORMAT_PRESETS,
    format_puzzle_date,
    get_puzzle_date_info,
    render_mini_month_calendar,
    CALENDAR_THEMES,
)
import datetime

# 10a. Date formatting presets verification
sample_dt = datetime.date(2026, 9, 27)
f_27_sep = format_puzzle_date(sample_dt, "27-September")
assert f_27_sep == "27-September", f"Expected '27-September', got '{f_27_sep}'"

f_27_sep_yr = format_puzzle_date(sample_dt, "27-sept-2026")
assert f_27_sep_yr == "27-sept-2026", f"Expected '27-sept-2026', got '{f_27_sep_yr}'"

f_us = format_puzzle_date(sample_dt, "9-27-2026")
assert f_us == "9-27-2026", f"Expected '9-27-2026', got '{f_us}'"

# Test all presets execute without error
for preset in DATE_FORMAT_PRESETS:
    formatted = format_puzzle_date(sample_dt, preset)
    assert len(formatted) > 0
print("ok All date format presets verified")

# 10b. Date info calculation (daily 365 and monthly progression)
start_d = datetime.date(2026, 1, 1)
# Day 1
d_info_0 = get_puzzle_date_info(0, start_d, "daily", "27-September")
assert d_info_0["day"] == 1 and d_info_0["month"] == 1 and d_info_0["year"] == 2026
# Day 365 (Dec 31, 2026)
d_info_364 = get_puzzle_date_info(364, start_d, "daily", "27-September")
assert d_info_364["day"] == 31 and d_info_364["month"] == 12 and d_info_364["year"] == 2026
print("ok 365-day progression calculation verified")

# Monthly progression
d_info_m5 = get_puzzle_date_info(5, start_d, "monthly", "27-September")
assert d_info_m5["month"] == 6  # June
print("ok Monthly progression calculation verified")

# 10c. Mini month calendar image rendering
for theme_name in CALENDAR_THEMES:
    cal_img = render_mini_month_calendar(
        year=2026,
        month=9,
        highlight_day=27,
        theme=theme_name,
        width=600,
        height=420,
    )
    assert cal_img.size == (600, 420)
print("ok Mini month calendar card rendering in all themes verified")

# 10d. Multi-game page rendering with date strings and calendar images
cal_img_test = render_mini_month_calendar(2026, 9, 27, theme="Modern Emerald", width=400, height=280)
for g_per_page in [1, 2, 4, 6]:
    d_strs = [f"Day {i+1} - Sep 2{i}" for i in range(g_per_page)]
    c_imgs = [cal_img_test] * g_per_page
    puz_page_with_date = render_sudoku_puzzle_page_image(
        test_puzzles[:g_per_page],
        style_s_classic,
        puzzles_per_page=g_per_page,
        page_num=1,
        total_pages=2,
        dpi=120,
        date_strings=d_strs,
        calendar_images=c_imgs,
    )
    assert puz_page_with_date.size[0] > 0
    print(f"ok Sudoku page with {g_per_page} game(s)/page + date headers & calendars rendered successfully")

# 10e. PDF generation with date text and mini calendars
pdf_cal_bytes = build_sudoku_pdf(
    test_puzzles[:4],
    style_s_classic,
    puzzles_per_page=2,
    solutions_per_page=4,
    date_strings=["27-September", "28-September", "29-September", "30-September"],
    calendar_images=[cal_img_test] * 4,
)
assert len(pdf_cal_bytes) > 10000
print("ok Sudoku PDF book with date headers and mini calendars passed")

# 10f. Workbook & Canva export with date text config
date_cfg_text = {
    "enabled": True,
    "mode": "date_text",
    "start_date": datetime.date(2026, 1, 1),
    "date_format": "27-September",
    "progression": "daily",
    "cal_theme": "Modern Emerald",
    "monday_first": False,
}
out_sdk_date_text = tempfile.mkdtemp(prefix="sdk_date_text_test_")
canva_dt, sol_dt, zip_dt, pdf_dt = build_sudoku_workbooks(
    test_puzzles[:4],
    out_sdk_date_text,
    puzzles_per_page=2,
    solutions_per_page=4,
    date_config=date_cfg_text,
)
assert os.path.exists(canva_dt)
assert os.path.exists(zip_dt)
print("ok Sudoku workbook & Canva export with date text mode passed")

# 10g. Workbook & Canva export with calendar image mode
date_cfg_img = {
    "enabled": True,
    "mode": "calendar_image",
    "start_date": datetime.date(2026, 9, 27),
    "date_format": "27-sept-2026",
    "progression": "daily",
    "cal_theme": "Minimalist Slate",
    "monday_first": True,
    "show_year": False,
    "show_card_border": True,
}
out_sdk_date_img = tempfile.mkdtemp(prefix="sdk_date_img_test_")
canva_di, sol_di, zip_di, pdf_di = build_sudoku_workbooks(
    test_puzzles[:4],
    out_sdk_date_img,
    puzzles_per_page=2,
    solutions_per_page=4,
    date_config=date_cfg_img,
)
assert os.path.exists(canva_di)
assert os.path.exists(zip_di)
print("ok Sudoku workbook & Canva export with mini calendar image mode (show_year=False) passed")

# 10h. Calendar show_year toggle and date preset September 27 verification
cal_yr_true = render_mini_month_calendar(2026, 9, highlight_day=27, show_year=True)
cal_yr_false = render_mini_month_calendar(2026, 9, highlight_day=27, show_year=False)
assert cal_yr_true.size == cal_yr_false.size
assert format_puzzle_date(datetime.date(2026, 9, 27), "September 27") == "September 27"
print("ok Calendar show/hide year rendering & September 27 date format verified")

# 11. Large Volume 1460-Puzzle Verification (4 puzzles/day = 365 pages)
total_1460_puzzles = 1460
puz_per_page = 4
total_pages = (total_1460_puzzles + puz_per_page - 1) // puz_per_page
assert total_pages == 365, f"Expected 365 pages for 1460 puzzles at 4/page, got {total_pages}"
d1459 = get_puzzle_date_info(1459, datetime.date(2026, 1, 1), progression="daily")
assert d1459["year"] == 2029
print(f"ok 1460-puzzle volume calculation verified: 1460 puzzles / 4 per page = {total_pages} pages")

# 12. Canva Bulk Batch Splitting Verification (Split into ordered ZIP)
out_sdk_batch = tempfile.mkdtemp(prefix="sdk_batch_test_")
canva_batch_p, _, _, _ = build_sudoku_workbooks(
    test_puzzles[:6],
    out_sdk_batch,
    puzzles_per_page=1,
    canva_batch_size=2,
)
assert canva_batch_p.endswith(".zip"), f"Expected .zip, got {canva_batch_p}"
with zipfile.ZipFile(canva_batch_p) as z:
    batch_names = z.namelist()
    assert "CANVA_BULK_CREATE_INSTRUCTIONS.txt" in batch_names
    assert any("batch_01" in n for n in batch_names)
    assert any("batch_02" in n for n in batch_names)
    assert any("batch_03" in n for n in batch_names)
# 13. Word Search: 14 Words Input with 12 Words Per Page & 12 Target Puzzles Verification
from app import get_base_word_chunks, select_puzzle_words
fourteen_words = [f"ANIMAL_{i:02d}" for i in range(1, 15)]
ws_chunks = get_base_word_chunks({"Animals": fourteen_words}, 12)
assert len(ws_chunks) == 1, f"Expected 1 base chunk (not orphan 2-word chunk), got {len(ws_chunks)}"
all_sampled_words = set()
for p_idx in range(12):
    p_words = select_puzzle_words(ws_chunks[0][1], ws_chunks[0][2], p_idx, 12)
    assert len(p_words) == 12, f"Expected 12 words on puzzle {p_idx+1}, got {len(p_words)}"
    all_sampled_words.update(p_words)
assert len(all_sampled_words) == 14, f"Expected all 14 words to be utilized across 12 puzzles, got {len(all_sampled_words)}"
# 14. Word Search: Themed Page Title Verification (title of page is title of theme)
from app import get_ws_puzzle_title, get_puzzles
assert get_ws_puzzle_title("Animals", 1, 12) == "Animals"
assert get_ws_puzzle_title("Animals", 7, 12) == "Animals"
assert get_ws_puzzle_title("Big Cats", 2, 50) == "Big Cats"
assert get_ws_puzzle_title("Ocean", 1, 1) == "Ocean"

# Multi-theme verification
multi_puzzles = get_puzzles(
    {"Big Cats": ["LION", "TIGER", "LEOPARD", "JAGUAR"], "Ocean": ["WHALE", "SHARK", "DOLPHIN", "OCTOPUS"]},
    "medium",
    4,
    42,
    grid_rows=10,
    grid_cols=10,
    target_count=2,
)
assert len(multi_puzzles) == 2
assert multi_puzzles[0].theme == "Big Cats", f"Expected 'Big Cats', got {multi_puzzles[0].theme}"
assert multi_puzzles[1].theme == "Ocean", f"Expected 'Ocean', got {multi_puzzles[1].theme}"

# Single theme with target_count > 1 verification
single_themed_12 = get_puzzles(
    {"Animals": fourteen_words},
    "medium",
    12,
    42,
    grid_rows=12,
    grid_cols=10,
    target_count=12,
)
assert len(single_themed_12) == 12
for p in single_themed_12:
    assert p.theme == "Animals", f"Expected theme 'Animals', got '{p.theme}'"
print("ok Themed Word Search page titles equal theme title verified across single & multi-theme books")

print("ALL SMOKE TESTS PASSED SUCCESSFULLY!")





