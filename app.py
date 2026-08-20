from __future__ import annotations

import csv
import io
import os
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    # Reuse the main studio implementation when running inside the repository.
    from modules.word_search.generator import generate_puzzle
    from modules.word_search.models import Difficulty, PuzzleConfig
    from core.grid_raster import render_grid_image, render_solution_image
except ModuleNotFoundError:
    # Fall back to the bundled copies when this folder is deployed by itself.
    from engine.generator import generate_puzzle
    from engine.models import Difficulty, PuzzleConfig
    from core.grid_raster import render_grid_image, render_solution_image

st.set_page_config(page_title="Word Search Studio", page_icon="", layout="wide", initial_sidebar_state="collapsed")

THEMED_CSV = """theme,word
Big Cats,LION
Big Cats,TIGER
Big Cats,LEOPARD
Farm Animals,COW
Farm Animals,SHEEP
Farm Animals,HORSE
Ocean,WHALE
Ocean,SHARK
Ocean,DOLPHIN
"""
SIMPLE_CSV = """word
LION
TIGER
LEOPARD
ZEBRA
GIRAFFE
ELEPHANT
MONKEY
"""
GOOGLE_ADSENSE_CLIENT = os.getenv("GOOGLE_ADSENSE_CLIENT", "")
GOOGLE_ADSENSE_SLOT = os.getenv("GOOGLE_ADSENSE_SLOT", "")


def render_square_ad():
    """Render a 300x250 AdSense unit or a clear placeholder before setup."""
    if GOOGLE_ADSENSE_CLIENT and GOOGLE_ADSENSE_SLOT:
        components.html(f"""
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={GOOGLE_ADSENSE_CLIENT}" crossorigin="anonymous"></script>
        <ins class="adsbygoogle" style="display:inline-block;width:300px;height:250px"
             data-ad-client="{GOOGLE_ADSENSE_CLIENT}" data-ad-slot="{GOOGLE_ADSENSE_SLOT}"></ins>
        <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        """, height=265, scrolling=False)
    else:
        st.markdown('''<div class="ad-placeholder"><div class="ad-label">ADVERTISEMENT</div><div class="ad-square">300 × 250<br><span>Add your Google AdSense details after hosting</span></div></div>''', unsafe_allow_html=True)


PROMPTS = {
    "Themed CSV": """Create a themed word-search CSV for a children's activity book.\nReturn CSV only with exactly two columns: theme,word.\nCreate 10 themes with 12 unique uppercase words per theme.\nTheme: [INSERT THEME]\nDifficulty: [easy, medium, or hard]\nUse only family-friendly words, 3-12 letters, letters only, no spaces or punctuation.\nDo not add explanations or markdown.""",
    "Simple CSV": """Create a simple word-search CSV for a children's activity book.\nReturn CSV only with exactly one column: word.\nCreate [INSERT NUMBER] unique uppercase words about: [INSERT TOPIC]\nDifficulty: [easy, medium, or hard]\nUse only family-friendly words, 3-12 letters, letters only, no spaces or punctuation.\nDo not add explanations or markdown.""",
    "Pasted word list": """Create a clean word list for a word-search puzzle.\nReturn one uppercase word per line and nothing else.\nTopic: [INSERT TOPIC]\nNumber of words: [INSERT NUMBER]\nUse family-friendly words, 3-12 letters, letters only, no spaces or punctuation.\nDo not add numbering, bullets, explanations, or markdown.""",
}

st.markdown("""
<style>
:root { --ink:#14251f; --muted:#64746d; --cream:#f7f4ee; }
.stApp { background:var(--cream); color:var(--ink); }
[data-testid="stHeader"] { visibility: hidden !important; }
.block-container { max-width:1500px; padding:0.7rem 1.25rem 1.5rem; }
.hero { background:linear-gradient(135deg,#17352b,#285b4a); color:white; border-radius:16px; padding:14px 22px; margin-bottom:9px; }
.hero h1 { margin:0; font-size:2rem; letter-spacing:-.04em; }
.hero p { margin:.35rem 0 0; color:#d9ebe1; font-size:.95rem; }
.card { background:white; border:1px solid #e6e1d7; border-radius:16px; padding:15px 17px; box-shadow:0 6px 18px rgba(20,37,31,.05); }
.smallcaps { color:var(--muted); font-size:.68rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
.section-title { font-size:1rem; font-weight:800; margin:0 0 .35rem; }
div[data-testid="stMetricValue"] { color:var(--ink); font-size:1.08rem; line-height:1.05; }
div[data-testid="stMetricLabel"] { font-size:.68rem; margin-bottom:0; }
div[data-testid="stMetric"] { padding:.1rem 0; }
.stButton > button, .stDownloadButton > button { border-radius:9px; font-weight:700; }
.ad-placeholder { width:300px; height:250px; border:1px dashed #c8cec8; background:#f2f3f0; border-radius:10px; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#7b857f; margin:.5rem auto 0; }
.ad-label { font-size:.58rem; letter-spacing:.14em; font-weight:800; margin-bottom:.45rem; }
.ad-square { text-align:center; font-size:.9rem; font-weight:700; line-height:1.5; }
.ad-square span { font-size:.68rem; font-weight:500; }
.word-bank-title { color:#315e4d; font-size:.72rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; margin:.35rem 0 .2rem; }
.word-bank-item { color:#315e4d; font-size:.78rem; line-height:1.3; padding:.08rem 0; }
[data-testid="stImage"] img { max-height:66vh; width:auto !important; max-width:100%; object-fit:contain; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><div class="smallcaps">Standalone puzzle production tool</div><h1>Word Search Studio</h1><p>Import words, tune the puzzle, preview the complete page, and export a Canva Bulk Create workbook.</p></div>', unsafe_allow_html=True)


def parse_input(uploaded, mode, raw_text, default_theme):
    groups = defaultdict(list)
    if mode == "Paste a word list":
        words = [x.strip() for x in raw_text.replace(";", "\n").splitlines() if x.strip()]
        groups[default_theme.strip() or "Word Search"] = words
        return groups
    if not uploaded:
        # Load the built-in sample immediately so the preview is useful on first launch.
        sample_words = [x.strip() for x in raw_text.replace(";", "\n").splitlines() if x.strip()]
        groups[default_theme.strip() or "My Theme"] = sample_words
        return groups
    rows = list(csv.reader(io.StringIO(uploaded.getvalue().decode("utf-8-sig", errors="replace"))))
    if not rows:
        return groups
    header = [c.strip().lower() for c in rows[0]]
    if "theme" in header and "word" in header:
        ti, wi = header.index("theme"), header.index("word")
        for row in rows[1:]:
            if len(row) > max(ti, wi) and row[wi].strip():
                groups[row[ti].strip() or default_theme].append(row[wi].strip())
    else:
        start = 1 if rows[0] and rows[0][0].strip().lower() in {"word", "words"} else 0
        for row in rows[start:]:
            if row and row[0].strip():
                groups[default_theme.strip() or "Word Search"].append(row[0].strip())
    return groups


def generate_reliably(words, cfg, theme):
    """Try several deterministic seeds and keep the puzzle with fewest skips."""
    best = None
    for attempt in range(5):
        candidate_cfg = cfg.model_copy(deep=True)
        candidate_cfg.seed = (cfg.seed or 0) + attempt
        candidate = generate_puzzle(words, candidate_cfg, theme=theme)
        if best is None or len(candidate.skipped) < len(best.skipped):
            best = candidate
        if not candidate.skipped:
            return candidate
    return best


def make_font(size, bold=False):
    candidates = ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_png(puzzle, bank_columns=2, show_bank=True, solution=False, compact=False):
    """Use the main studio raster renderer so letters stay large and crisp.

    The word bank is intentionally not baked into this image. It remains a
    separate text field in the Canva workbook and a separate UI block in the
    preview, matching the main studio behavior.
    """
    style = SimpleNamespace(
        cell_style="boxes",
        grid_line_width=0.6,
        grid_line_color="#9da49f",
        letter_color="#202a26",
        letter_font="DejaVu Sans",
        letter_size_pt=None,
        solution_style="capsule",
        solution_color="#202a26",
    )
    dpi = 170 if compact else 300
    cell_mm = 12.5 if compact else 15.0
    if solution:
        return render_solution_image(puzzle, style, cell_mm=cell_mm, dpi=dpi)
    return render_grid_image(puzzle, style, cell_mm=cell_mm, dpi=dpi)


def render_word_bank(words, columns=2):
    """Show the word bank as separate UI text, never inside the grid image."""
    if not words:
        return
    st.markdown('<div class="word-bank-title">Word bank</div>', unsafe_allow_html=True)
    bank_cols = st.columns(max(1, min(5, columns)), gap="small")
    for index, word in enumerate(sorted(words)):
        bank_cols[index % len(bank_cols)].markdown(f'<div class="word-bank-item">{word}</div>', unsafe_allow_html=True)


def build_workbooks(puzzles, out_dir, show_bank, bank_columns, solutions_per_page, progress_bar=None):
    import xlsxwriter
    from core.canva_bulk import write_bulk_excel

    os.makedirs(out_dir, exist_ok=True)
    grid_paths, sol_paths = [], []
    total = len(puzzles)
    for i, puzzle in enumerate(puzzles, 1):
        gp = os.path.join(out_dir, f"page_{i:03d}_grid.png")
        sp = os.path.join(out_dir, f"page_{i:03d}_solution.png")
        # The grid image contains only the grid and letters. The word bank stays
        # in separate Excel text columns, matching the main studio.
        render_png(puzzle, bank_columns, False, False).save(gp)
        render_png(puzzle, bank_columns, False, True).save(sp)
        grid_paths.append(gp); sol_paths.append(sp)
        
        if progress_bar:
            progress_bar.progress(int((i / total) * 75), text=f"Rendering images: page {i} of {total}...")

    if progress_bar:
        progress_bar.progress(80, text="Building Canva workbook...")
    max_words = max((len(p.words) for p in puzzles), default=0)
    text_columns = ["page", "title"] + [f"word_{i}" for i in range(1, max_words + 1)]
    rows = []
    for i, puzzle in enumerate(puzzles, 1):
        row = {"page": i, "title": puzzle.theme, "grid_image": grid_paths[i - 1]}
        for j, word in enumerate(sorted(puzzle.words), 1):
            row[f"word_{j}"] = word
        rows.append(row)
    canva_path = os.path.join(out_dir, "word_search_canva_bulk.xlsx")
    canva_files = write_bulk_excel(canva_path, rows, text_columns, ["grid_image"], max_rows=0)
    canva_path = canva_files[0]

    if progress_bar:
        progress_bar.progress(90, text="Building solutions workbook...")
    solutions_path = os.path.join(out_dir, "word_search_solutions.xlsx")
    wb = xlsxwriter.Workbook(solutions_path); ws = wb.add_worksheet("Solutions")
    solution_headers = ["solution_page"] + [f"solution_{i}" for i in range(1, solutions_per_page + 1)]
    for c, header in enumerate(solution_headers): ws.write(0, c, header)
    ws.set_column(1, solutions_per_page, 30)
    for page_start in range(0, len(puzzles), solutions_per_page):
        row = page_start // solutions_per_page + 1
        ws.write(row, 0, row); ws.set_row(row, 160)
        for offset in range(solutions_per_page):
            index = page_start + offset
            if index >= len(sol_paths):
                break
            ws.insert_image(row, 1 + offset, sol_paths[index], {"x_scale": .09, "y_scale": .09, "x_offset": 5, "y_offset": 5, "positioning": 1})
    wb.close()

    if progress_bar:
        progress_bar.progress(95, text="Creating ZIP bundle...")
    zip_path = os.path.join(out_dir, "word_search_canva_export.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(canva_path, os.path.basename(canva_path))
        z.write(solutions_path, os.path.basename(solutions_path))
        for p in grid_paths + sol_paths: z.write(p, os.path.basename(p))
    return canva_path, solutions_path, zip_path


# Main workspace: controls are split into two compact columns instead of a long sidebar.
controls, preview_area = st.columns([0.92, 1.55], gap="medium")
with controls:
    left_settings, right_settings = st.columns(2, gap="small")
    with left_settings:
        st.markdown('<div class="section-title">1. Import</div>', unsafe_allow_html=True)
        mode = st.radio("Source", ["Import CSV", "Paste a word list"], label_visibility="collapsed")
        default_theme = st.text_input("Theme / title", "My Theme")
        uploaded = st.file_uploader("CSV file", type=["csv"], disabled=mode != "Import CSV")
        raw_text = st.text_area("Words", "APPLE\nBANANA\nCHERRY\nORANGE\nPEAR\nSTRAWBERRY", height=105, disabled=mode != "Paste a word list")
    with right_settings:
        st.markdown('<div class="section-title">2. Settings</div>', unsafe_allow_html=True)
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
        words_per_page = st.slider("Words / page", 4, 20, 10)
        seed = st.number_input("Seed", min_value=0, value=42, step=1)
        show_bank = st.toggle("Display word bank", True)
        bank_columns = st.selectbox("Bank columns", [1, 2, 3, 4, 5], index=1)
        solutions_per_page = st.selectbox("Solutions per page", [1, 2, 3, 4, 5], index=3, help="Controls how many solution images are placed on each row/page in the separate solutions workbook.")

    st.markdown('<div class="section-title" style="margin-top:.55rem">CSV examples & prompts</div>', unsafe_allow_html=True)
    ex1, ex2 = st.columns(2, gap="small")
    with ex1:
        st.download_button("Download themed CSV", THEMED_CSV, "themed_word_search_example.csv", "text/csv", use_container_width=True)
    with ex2:
        st.download_button("Download simple CSV", SIMPLE_CSV, "simple_word_search_example.csv", "text/csv", use_container_width=True)
    with st.expander("Prompt templates — click to open and copy", expanded=False):
        prompt_type = st.selectbox("Prompt template", list(PROMPTS), label_visibility="collapsed")
        st.code(PROMPTS[prompt_type], language="text")

    groups = parse_input(uploaded, mode, raw_text, default_theme)
    all_count = sum(len(v) for v in groups.values())
    sample_note = " · Built-in sample" if not uploaded and mode == "Import CSV" else ""
    st.markdown(f'<div class="card"><div class="smallcaps">Ready to generate</div><b>{len(groups)} theme(s) · {all_count} word(s)</b><span style="color:#64746d;font-size:.8rem">{sample_note}</span></div>', unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def get_puzzles(groups_dict, diff_str, words_per_page, seed_val):
    cfg = PuzzleConfig(difficulty=Difficulty(diff_str), words_per_page=words_per_page, seed=int(seed_val))
    result = []
    for theme, words in groups_dict.items():
        cleaned = [w for w in words if len("".join(ch for ch in w.upper() if ch.isalpha())) >= 3]
        for start in range(0, len(cleaned), words_per_page):
            chunk = cleaned[start:start + words_per_page]
            if chunk:
                local = cfg.model_copy(deep=True); local.seed = int(seed_val) + len(result)
                result.append(generate_reliably(chunk, local, theme))
    return result

with preview_area:
    if groups:
        puzzles = get_puzzles(dict(groups), difficulty, words_per_page, seed)
        
        # Clear old export files if the puzzle inputs have changed
        current_hash = hash(str(dict(groups)) + difficulty + str(words_per_page) + str(seed))
        if st.session_state.get("last_puzzles_hash") != current_hash:
            st.session_state["last_puzzles_hash"] = current_hash
            for k in ["canva_bytes", "solutions_bytes", "zip_bytes"]:
                st.session_state.pop(k, None)

        if puzzles:
            # Compact metrics strip: useful status without consuming the preview height.
            c1, c2, c3 = st.columns(3, gap="small")
            c1.metric("Pages", len(puzzles), label_visibility="visible")
            c2.metric("Level", difficulty.title(), label_visibility="visible")
            c3.metric("Grid", f"{puzzles[0].rows} × {puzzles[0].cols}", label_visibility="visible")

            preview_col, export_col = st.columns([1.55, .72], gap="small")
            with preview_col:
                selected = st.selectbox("Preview page", range(1, len(puzzles) + 1), format_func=lambda x: f"Page {x}: {puzzles[x-1].theme}")
                st.image(render_png(puzzles[selected - 1], bank_columns, False, compact=True), use_container_width=True)
                if show_bank:
                    render_word_bank(puzzles[selected - 1].words, bank_columns)
                if puzzles[selected - 1].skipped:
                    st.warning("Some words could not be placed: " + ", ".join(puzzles[selected - 1].skipped))
            with export_col:
                st.markdown('<div class="section-title">Export</div>', unsafe_allow_html=True)
                st.caption(f"Solutions: {solutions_per_page} per page")
                if st.button("Generate Export Bundle", type="primary", use_container_width=True):
                    progress_bar = st.progress(0, text="Starting generation...")
                    out_dir = tempfile.mkdtemp(prefix="word_search_studio_")
                    canva_path, solutions_path, zip_path = build_workbooks(puzzles, out_dir, show_bank, bank_columns, solutions_per_page, progress_bar=progress_bar)
                    
                    if progress_bar:
                        progress_bar.progress(100, text="Export bundle ready!")
                    
                    st.session_state["canva_bytes"] = Path(canva_path).read_bytes()
                    st.session_state["solutions_bytes"] = Path(solutions_path).read_bytes()
                    st.session_state["zip_bytes"] = Path(zip_path).read_bytes()
                    st.success("Export ready.")
                if "canva_bytes" in st.session_state:
                    st.download_button("Canva Excel", st.session_state["canva_bytes"], "word_search_canva_bulk.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    st.download_button("Solutions Excel", st.session_state["solutions_bytes"], "word_search_solutions.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    st.download_button("Canva ZIP", st.session_state["zip_bytes"], "word_search_canva_export.zip", "application/zip", use_container_width=True)
                st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
                render_square_ad()
        else:
            st.info("Add at least one valid word of three or more letters.")
    else:
        st.info("Import a CSV or paste words to begin.")
