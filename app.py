from __future__ import annotations

import csv
import io
import os
import sys
import tempfile
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

# Ensure local word_search_studio modules take precedence
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT) not in sys.path:
    sys.path.insert(1, str(ROOT))

try:
    from engine.generator import generate_puzzle
    from engine.models import Difficulty, PuzzleConfig, max_words_for_grid
    from core.grid_raster import render_grid_image, render_solution_image
except ModuleNotFoundError:
    from modules.word_search.generator import generate_puzzle
    from modules.word_search.models import Difficulty, PuzzleConfig, max_words_for_grid
    from core.grid_raster import render_grid_image, render_solution_image

st.set_page_config(page_title="Word Search Studio", page_icon="🧩", layout="wide", initial_sidebar_state="collapsed")

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


LANGUAGE_CONFIGS = {
    "English": {
        "flag": "🇬🇧",
        "label": "🇬🇧 English",
        "default_theme": "Animals",
        "word_bank_title": "Word bank",
        "fill_alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "badge_info": "Standard Latin alphabet (A–Z).",
        "sample_words": "LION\nTIGER\nLEOPARD\nELEPHANT\nGIRAFFE\nMONKEY\nZEBRA\nKANGAROO\nPANDA\nDOLPHIN\nBEAR\nWOLF",
        "themed_csv": """theme,word
Big Cats,LION
Big Cats,TIGER
Big Cats,LEOPARD
Farm Animals,COW
Farm Animals,SHEEP
Farm Animals,HORSE
Ocean,WHALE
Ocean,SHARK
Ocean,DOLPHIN
""",
        "simple_csv": """word
LION
TIGER
LEOPARD
ZEBRA
GIRAFFE
ELEPHANT
MONKEY
BEAR
""",
        "prompts": {
            "Themed CSV": """Create a themed word-search CSV for a children's activity book.\nReturn CSV only with exactly two columns: theme,word.\nCreate 10 themes with 12 unique uppercase words per theme.\nTheme: [INSERT THEME]\nDifficulty: [easy, medium, or hard]\nUse only family-friendly words, 3-12 letters, letters only, no spaces or punctuation.\nDo not add explanations or markdown.""",
            "Simple CSV": """Create a simple word-search CSV for a children's activity book.\nReturn CSV only with exactly one column: word.\nCreate [INSERT NUMBER] unique uppercase words about: [INSERT TOPIC]\nDifficulty: [easy, medium, or hard]\nUse only family-friendly words, 3-12 letters, letters only, no spaces or punctuation.\nDo not add explanations or markdown.""",
            "Pasted word list": """Create a clean word list for a word-search puzzle.\nReturn one uppercase word per line and nothing else.\nTopic: [INSERT TOPIC]\nNumber of words: [INSERT NUMBER]\nUse family-friendly words, 3-12 letters, letters only, no spaces or punctuation.\nDo not add numbering, bullets, explanations, or markdown.""",
        },
    },
    "German (Deutsch)": {
        "flag": "🇩🇪",
        "label": "🇩🇪 German (Deutsch)",
        "default_theme": "Tiere",
        "word_bank_title": "Wortliste",
        "fill_alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ",
        "badge_info": "Umlaute Ä, Ö, Ü unterstützt · ß wird automatisch als SS geschrieben.",
        "sample_words": "LÖWE\nTIGER\nLEOPARD\nELEFANT\nGIRAFFE\nAFFE\nZEBRA\nBÄR\nWOLF\nSCHLANGE\nHIRSCH\nFUCHS",
        "themed_csv": """theme,word
Raubkatzen,LÖWE
Raubkatzen,TIGER
Raubkatzen,LEOPARD
Bauernhof,KUH
Bauernhof,SCHAF
Bauernhof,PFERD
Waldtiere,BÄR
Waldtiere,WOLF
Waldtiere,HIRSCH
""",
        "simple_csv": """word
LÖWE
TIGER
LEOPARD
ZEBRA
GIRAFFE
ELEFANT
BÄR
FUCHS
""",
        "prompts": {
            "Themed CSV": """Erstelle eine Wortsuch-CSV (Buchstabensalat) für ein deutsches Rätselbuch.\nGib nur CSV mit genau zwei Spalten zurück: theme,word.\nErstelle 10 Themen mit je 12 einzigartigen Wörtern in Großbuchstaben pro Thema.\nThema: [THEMA HIER EINFÜGEN]\nSchwierigkeitsgrad: [easy, medium, oder hard]\nVerwende deutsche Wörter, 3-12 Buchstaben, nur Buchstaben (Ä, Ö, Ü erlaubt, ß als SS).\nKeine Erklärungen oder Markdown hinzufügen.""",
            "Simple CSV": """Erstelle eine einfache Wortsuch-CSV für ein deutsches Rätselbuch.\nGib nur CSV mit genau einer Spalte zurück: word.\nErstelle [ANZAHL] einzigartige Wörter in Großbuchstaben über: [THEMA]\nSchwierigkeitsgrad: [easy, medium, oder hard]\nVerwende familienfreundliche Wörter, 3-12 Buchstaben (Ä, Ö, Ü erlaubt, ß als SS).\nKeine Erklärungen oder Markdown hinzufügen.""",
            "Pasted word list": """Erstelle eine saubere Wortliste für ein deutsches Suchsel (Wortsuchspiel).\nGib genau ein deutsches Wort in Großbuchstaben pro Zeile zurück und sonst nichts.\nThema: [THEMA]\nAnzahl der Wörter: [ANZAHL]\nVerwende Wörter mit 3-12 Buchstaben (Ä, Ö, Ü erlaubt, ß als SS).\nKeine Nummerierung, Aufzählungspunkte oder Erklärungen hinzufügen.""",
        },
    },
    "Spanish (Español)": {
        "flag": "🇪🇸",
        "label": "🇪🇸 Spanish (Español)",
        "default_theme": "Animales",
        "word_bank_title": "Lista de palabras",
        "fill_alphabet": "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ",
        "badge_info": "Letra oficial Ñ incluida en alfabeto y relleno · Acentos adaptados.",
        "sample_words": "LEÓN\nTIGRE\nLEOPARDO\nELEFANTE\nJIRAFA\nMONO\nCEBRA\nOSO\nLOBO\nSERPIENTE\nDELFÍN\nBALLENA",
        "themed_csv": """theme,word
Grandes Felinos,LEÓN
Grandes Felinos,TIGRE
Grandes Felinos,LEOPARDO
Granja,VACA
Granja,OVEJA
Granja,CABALLO
Océano,BALLENA
Océano,TIBURÓN
Océano,DELFÍN
""",
        "simple_csv": """word
LEÓN
TIGRE
LEOPARDO
CEBRA
JIRAFA
ELEFANTE
MONO
OSO
""",
        "prompts": {
            "Themed CSV": """Crea un archivo CSV de sopa de letras para un libro de pasatiempos en español.\nDevuelve solo el CSV con exactamente dos columnas: theme,word.\nCrea 10 temas con 12 palabras únicas en mayúsculas por tema.\nTema: [INSERTAR TEMA]\nDificultad: [easy, medium, o hard]\nUsa palabras en español familiares, de 3 a 12 letras (la letra Ñ está permitida).\nSin explicaciones ni formato markdown.""",
            "Simple CSV": """Crea un archivo CSV simple de sopa de letras para un libro de pasatiempos en español.\nDevuelve solo el CSV con exactamente una columna: word.\nCrea [INSERTAR NÚMERO] palabras únicas en mayúsculas sobre: [INSERTAR TEMA]\nDificultad: [easy, medium, o hard]\nUsa palabras familiares de 3 a 12 letras (la letra Ñ está permitida).\nSin explicaciones ni formato markdown.""",
            "Pasted word list": """Crea una lista de palabras para una sopa de letras en español.\nDevuelve una palabra en mayúsculas por línea y nada más.\nTema: [INSERTAR TEMA]\nNúmero de palabras: [INSERTAR NÚMERO]\nPalabras en español de 3 a 12 letras (la letra Ñ está permitida).\nSin números, viñetas ni explicaciones.""",
        },
    },
    "French (Français)": {
        "flag": "🇫🇷",
        "label": "🇫🇷 French (Français)",
        "default_theme": "Animaux",
        "word_bank_title": "Liste de mots",
        "fill_alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "badge_info": "Mots mêlés en français · Supporte les accents ou normalisation A–Z.",
        "sample_words": "LION\nTIGRE\nLÉOPARD\nÉLÉPHANT\nGIRAFE\nSINGE\nZÈBRE\nOURS\nLOUP\nSERPENT\nDAUPHIN\nBALEINE",
        "themed_csv": """theme,word
Félins,LION
Félins,TIGRE
Félins,LÉOPARD
Ferme,VACHE
Ferme,MOUTON
Ferme,CHEVAL
Océan,BALEINE
Océan,REQUIN
Océan,DAUPHIN
""",
        "simple_csv": """word
LION
TIGRE
LÉOPARD
ZÈBRE
GIRAFE
ÉLÉPHANT
SINGE
OURS
""",
        "prompts": {
            "Themed CSV": """Créez un fichier CSV de mots mêlés pour un livre d'activités en français.\nRetournez uniquement le CSV avec exactement deux colonnes : theme,word.\nCréez 10 thèmes avec 12 mots uniques en majuscules par thème.\nThème : [INSÉRER LE THÈME]\nDifficulté : [easy, medium, ou hard]\nUtilisez des mots français adaptés aux familles, 3 à 12 lettres, sans espaces ni ponctuation.\nPas d'explications ni de balisage markdown.""",
            "Simple CSV": """Créez un simple fichier CSV de mots mêlés pour un livre d'activités en français.\nRetournez uniquement le CSV avec exactement une colonne : word.\nCréez [INSÉRER LE NOMBRE] mots uniques en majuscules sur : [INSÉRER LE SUJET]\nDifficulté : [easy, medium, ou hard]\nUtilisez des mots français de 3 à 12 lettres.\nPas d'explications ni de balisage markdown.""",
            "Pasted word list": """Créez une liste de mots pour un jeu de mots mêlés en français.\nRetournez un mot en majuscules par ligne et rien d'autre.\nSujet : [INSÉRER LE SUJET]\nNombre de mots : [INSÉRER LE NOMBRE]\nMots français de 3 à 12 lettres, uniquement des lettres.\nPas de numérotation, puces ni explications.""",
        },
    },
    "Italian (Italiano)": {
        "flag": "🇮🇹",
        "label": "🇮🇹 Italian (Italiano)",
        "default_theme": "Animali",
        "word_bank_title": "Elenco parole",
        "fill_alphabet": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "badge_info": "Crucipuzzle in italiano · Lettere A–Z con accenti adattati.",
        "sample_words": "LEONE\nTIGRE\nLEOPARDO\nELEFANTE\nGIRAFFA\nSCIMMIA\nZEBRA\nORSO\nLUPO\nSERPENTE\nDELFINO\nBALENA",
        "themed_csv": """theme,word
Grandi Felini,LEONE
Grandi Felini,TIGRE
Grandi Felini,LEOPARDO
Fattoria,MUCCA
Fattoria,PECORA
Fattoria,CAVALLO
Oceano,BALENA
Oceano,SQUALO
Oceano,DELFINO
""",
        "simple_csv": """word
LEONE
TIGRE
LEOPARDO
ZEBRA
GIRAFFA
ELEFANTE
SCIMMIA
ORSO
""",
        "prompts": {
            "Themed CSV": """Crea un file CSV per crucipuzzle (cerca parole) per un libro di enigmistica in italiano.\nRestituisci solo il CSV con esattamente due colonne: theme,word.\nCrea 10 temi con 12 parole uniche in maiuscolo per tema.\nTema: [INSERISCI TEMA]\nDifficoltà: [easy, medium, o hard]\nUsa parole in italiano per famiglie, 3-12 lettere, solo lettere, senza spazi o punteggiatura.\nNessuna spiegazione né markdown.""",
            "Simple CSV": """Crea un semplice file CSV per crucipuzzle in italiano.\nRestituisci solo il CSV con esattamente una colonna: word.\nCrea [INSERISCI NUMERO] parole uniche in maiuscolo su: [INSERISCI ARGOMENTO]\nDifficoltà: [easy, medium, o hard]\nUsa parole in italiano di 3-12 lettere.\nNessuna spiegazione né markdown.""",
            "Pasted word list": """Crea un elenco pulito di parole per un crucipuzzle in italiano.\nRestituisci una parola in maiuscolo per riga e nient'altro.\nArgomento: [INSERISCI ARGOMENTO]\nNumero di parole: [INSERISCI NUMERO]\nParole in italiano di 3-12 lettere, solo lettere.\nNessuna numerazione, elenchi puntati o spiegazioni.""",
        },
    },
}

THEME_PRESETS = {
    "🎈 Kids Fun": {
        "cell_style": "rounded_boxes",
        "grid_line_width": 0.8,
        "grid_line_color": "#516d61",
        "font_scale": 76,
        "letter_font": "DejaVu Sans Bold",
        "letter_color": "#172721",
        "solution_style": "capsule",
        "description": "Playful rounded tiles, softer slate-green border, large punchy letters. Perfect for children's activity books.",
    },
    "👔 Adult Classic": {
        "cell_style": "grid",
        "grid_line_width": 0.5,
        "grid_line_color": "#9da49f",
        "font_scale": 62,
        "letter_font": "DejaVu Sans",
        "letter_color": "#202a26",
        "solution_style": "capsule",
        "description": "Crisp traditional grid lines, balanced font proportion, neutral tones. Standard for adult puzzle books.",
    },
    "👓 Senior / Large Print": {
        "cell_style": "grid",
        "grid_line_width": 1.2,
        "grid_line_color": "#111815",
        "font_scale": 82,
        "letter_font": "DejaVu Sans Bold",
        "letter_color": "#000000",
        "solution_style": "bold",
        "description": "Bold high-contrast borders and giant 82% font for effortless readability and vision comfort.",
    },
    "📄 Minimalist (No Lines)": {
        "cell_style": "none",
        "grid_line_width": 0.0,
        "grid_line_color": "#9da49f",
        "font_scale": 70,
        "letter_font": "DejaVu Sans",
        "letter_color": "#1c2621",
        "solution_style": "capsule",
        "description": "Clean borderless design without grid lines. Floating letters for modern, airy aesthetic.",
    },
    "⚙️ Custom": {
        "cell_style": "boxes",
        "grid_line_width": 0.6,
        "grid_line_color": "#9da49f",
        "font_scale": 62,
        "letter_font": "DejaVu Sans",
        "letter_color": "#202a26",
        "solution_style": "capsule",
        "description": "Full manual control over every slider, color, and line option.",
    },
}

st.markdown("""
<style>
:root { --ink:#14251f; --muted:#64746d; --cream:#f7f4ee; --primary:#17352b; }
.stApp { background:var(--cream); color:var(--ink); }
[data-testid="stHeader"] { visibility: hidden !important; }
.block-container { max-width:1560px; padding:0.65rem 1.25rem 1.5rem; }
.hero { background:linear-gradient(135deg,#17352b,#285b4a); color:white; border-radius:14px; padding:12px 20px; margin-bottom:10px; }
.hero h1 { margin:0; font-size:1.9rem; letter-spacing:-.04em; }
.hero p { margin:.25rem 0 0; color:#d9ebe1; font-size:.9rem; }

/* Control Panel container & cards */
.ctrl-card { background:white; border:1px solid #e3ded5; border-radius:12px; padding:12px 14px; margin-bottom:10px; box-shadow:0 3px 10px rgba(20,37,31,.03); }
.lang-badge { background:#e7efe9; border:1px solid #c7dcce; color:#184534; border-radius:8px; padding:6px 10px; font-size:.78rem; font-weight:600; line-height:1.35; margin:.35rem 0 .5rem; }
.panel-step { color:#285b4a; font-size:.72rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:3px; }
.smallcaps { color:var(--muted); font-size:.66rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
.section-title { font-size:.95rem; font-weight:800; margin:0 0 .3rem; color:#14251f; }

div[data-testid="stMetricValue"] { color:var(--ink); font-size:1.02rem; line-height:1.05; font-weight:800; }
div[data-testid="stMetricLabel"] { font-size:.64rem; margin-bottom:0; font-weight:700; color:var(--muted); text-transform:uppercase; }
div[data-testid="stMetric"] { background:white; border:1px solid #e7e2d9; border-radius:10px; padding:.32rem .6rem; }
.stButton > button, .stDownloadButton > button { border-radius:8px; font-weight:700; }
.ad-placeholder { width:300px; height:250px; border:1px dashed #c8cec8; background:#f2f3f0; border-radius:10px; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#7b857f; margin:.5rem auto 0; }
.ad-label { font-size:.58rem; letter-spacing:.14em; font-weight:800; margin-bottom:.45rem; }
.ad-square { text-align:center; font-size:.9rem; font-weight:700; line-height:1.5; }
.ad-square span { font-size:.68rem; font-weight:500; }
.word-bank-title { color:#315e4d; font-size:.72rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase; margin:.35rem 0 .2rem; }
.word-bank-item { color:#315e4d; font-size:.78rem; line-height:1.3; padding:.08rem 0; }
[data-testid="stImage"] img { max-height:64vh; width:auto !important; max-width:100%; object-fit:contain; border-radius:8px; }
.theme-badge { background:#e8f0eb; border:1px solid #c9ded3; color:#1f4d3c; border-radius:8px; padding:6px 10px; font-size:.8rem; margin-bottom:.45rem; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; margin-bottom: 8px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; font-weight: 700; font-size: 0.88rem; padding: 6px 14px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><div class="smallcaps">Multilingual puzzle production studio</div><h1>Word Search Studio</h1><p>Generate books in English, German, French, Spanish, and Italian with tailored alphabets, dynamic dimensions, and custom styles.</p></div>', unsafe_allow_html=True)


def clean_word_for_language(raw_word: str, language: str, accent_mode: str = "Standard Book Mode") -> str:
    """Normalize and clean a word according to the language and accent preferences."""
    w = (raw_word or "").strip().upper()
    if not w:
        return ""
    
    # Always convert German Eszett to SS for word search
    w = w.replace("ß", "SS").replace("ẞ", "SS")

    if accent_mode == "Preserve Exact Accents":
        # Keep any valid unicode letter (Ä, Ö, Ü, Ñ, É, È, Ê, Ç, À, Ô, etc.)
        return "".join(ch for ch in w if ch.isalpha())

    if accent_mode == "Strip All Accents (A-Z)":
        # Decompose all diacritics to basic A-Z
        nfkd = unicodedata.normalize("NFKD", w)
        return "".join(ch for ch in nfkd if "A" <= ch <= "Z")

    # "Standard Book Mode": Keep language-specific distinct letters, flatten remaining vowel accents
    if "Spanish" in language:
        # Preserve Ñ / ñ, flatten other accents (Á->A, É->E, etc.)
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
        # Preserve Ä, Ö, Ü, flatten any other stray accents
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
        # English, French, Italian: in standard word search grids, accents are flattened to A-Z
        nfkd = unicodedata.normalize("NFKD", w)
        return "".join(ch for ch in nfkd if "A" <= ch <= "Z")


def parse_input(uploaded, mode, raw_text, default_theme, language="English", accent_mode="Standard Book Mode"):
    groups = defaultdict(list)
    if mode == "Paste a word list":
        lines = raw_text.replace(";", "\n").splitlines()
        for x in lines:
            cw = clean_word_for_language(x, language, accent_mode)
            if len(cw) >= 3:
                groups[default_theme.strip() or "Word Search"].append(cw)
        return groups
    if not uploaded:
        lines = raw_text.replace(";", "\n").splitlines()
        for x in lines:
            cw = clean_word_for_language(x, language, accent_mode)
            if len(cw) >= 3:
                groups[default_theme.strip() or "My Theme"].append(cw)
        return groups
    rows = list(csv.reader(io.StringIO(uploaded.getvalue().decode("utf-8-sig", errors="replace"))))
    if not rows:
        return groups
    header = [c.strip().lower() for c in rows[0]]
    if "theme" in header and "word" in header:
        ti, wi = header.index("theme"), header.index("word")
        for row in rows[1:]:
            if len(row) > max(ti, wi) and row[wi].strip():
                cw = clean_word_for_language(row[wi].strip(), language, accent_mode)
                if len(cw) >= 3:
                    groups[row[ti].strip() or default_theme].append(cw)
    else:
        start = 1 if rows[0] and rows[0][0].strip().lower() in {"word", "words"} else 0
        for row in rows[start:]:
            if row and row[0].strip():
                cw = clean_word_for_language(row[0].strip(), language, accent_mode)
                if len(cw) >= 3:
                    groups[default_theme.strip() or "Word Search"].append(cw)
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


def render_png(puzzle, bank_columns=2, show_bank=True, solution=False, compact=False, style=None):
    """Render the grid image using the configurable rasterizer."""
    if style is None:
        style = SimpleNamespace(
            cell_style="boxes",
            grid_line_width=0.6,
            grid_line_color="#9da49f",
            letter_color="#202a26",
            letter_font="DejaVu Sans",
            font_scale=0.62,
            letter_size_pt=None,
            solution_style="capsule",
            solution_color="#202a26",
            row_shading=False,
        )
    dpi = 170 if compact else 300
    cell_mm = 12.5 if compact else 15.0
    if solution:
        return render_solution_image(puzzle, style, cell_mm=cell_mm, dpi=dpi)
    return render_grid_image(puzzle, style, cell_mm=cell_mm, dpi=dpi)


def render_word_bank(words, columns=2, title="Word bank"):
    """Show the word bank as separate UI text, never inside the grid image."""
    if not words:
        return
    st.markdown(f'<div class="word-bank-title">{title}</div>', unsafe_allow_html=True)
    bank_cols = st.columns(max(1, min(5, columns)), gap="small")
    for index, word in enumerate(sorted(words)):
        bank_cols[index % len(bank_cols)].markdown(f'<div class="word-bank-item">{word}</div>', unsafe_allow_html=True)


def build_workbooks(puzzles, out_dir, show_bank, bank_columns, solutions_per_page,
                     include_solution_in_bulk=False, progress_bar=None, style=None):
    import xlsxwriter
    from core.canva_bulk import write_bulk_excel

    os.makedirs(out_dir, exist_ok=True)
    img_dir = os.path.join(out_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    grid_paths, sol_paths = [], []
    total = len(puzzles)
    for i, puzzle in enumerate(puzzles, 1):
        gp = os.path.join(img_dir, f"page_{i:03d}_grid.png")
        sp = os.path.join(img_dir, f"page_{i:03d}_solution.png")
        render_png(puzzle, bank_columns, False, False, style=style).save(gp)
        render_png(puzzle, bank_columns, False, True, style=style).save(sp)
        grid_paths.append(gp)
        sol_paths.append(sp)
        
        if progress_bar:
            progress_bar.progress(int((i / total) * 75), text=f"Rendering images: page {i} of {total}...")

    if progress_bar:
        progress_bar.progress(80, text="Building Canva workbook...")
    max_words = max((len(p.words) for p in puzzles), default=0)
    text_columns = ["page", "title"] + [f"word_{i}" for i in range(1, max_words + 1)]
    image_columns = ["grid_image"]
    if include_solution_in_bulk:
        image_columns.append("solution_image")
    rows = []
    for i, puzzle in enumerate(puzzles, 1):
        row = {"page": i, "title": puzzle.theme, "grid_image": grid_paths[i - 1]}
        if include_solution_in_bulk:
            row["solution_image"] = sol_paths[i - 1]
        for j, word in enumerate(sorted(puzzle.words), 1):
            row[f"word_{j}"] = word
        rows.append(row)
    canva_path = os.path.join(out_dir, "word_search_canva_bulk.xlsx")
    canva_files = write_bulk_excel(canva_path, rows, text_columns, image_columns, max_rows=0)
    canva_path = canva_files[0]

    solutions_path = None
    if not include_solution_in_bulk:
        if progress_bar:
            progress_bar.progress(90, text="Building solutions workbook...")
        solutions_path = os.path.join(out_dir, "word_search_solutions.xlsx")
        wb = xlsxwriter.Workbook(solutions_path)
        ws = wb.add_worksheet("Solutions")
        solution_headers = ["page_number", "title"] + [f"solution_{i}" for i in range(1, solutions_per_page + 1)]
        for c, header in enumerate(solution_headers):
            ws.write(0, c, header)
        ws.set_column(0, 0, 12)
        ws.set_column(1, 1, 25)
        ws.set_column(2, 1 + solutions_per_page, 30)
        for page_start in range(0, len(puzzles), solutions_per_page):
            row_idx = page_start // solutions_per_page + 1
            ws.set_row(row_idx, 160)
            first_puzzle = puzzles[page_start]
            ws.write(row_idx, 0, page_start + 1)
            ws.write(row_idx, 1, first_puzzle.theme)
            for offset in range(solutions_per_page):
                index = page_start + offset
                if index >= len(sol_paths):
                    break
                ws.insert_image(row_idx, 2 + offset, sol_paths[index], {
                    "x_scale": .09, "y_scale": .09,
                    "x_offset": 5, "y_offset": 5, "positioning": 1,
                })
        wb.close()

    if progress_bar:
        progress_bar.progress(95, text="Creating ZIP bundle...")
    zip_path = os.path.join(out_dir, "word_search_canva_export.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(canva_path, os.path.basename(canva_path))
        if solutions_path:
            z.write(solutions_path, os.path.basename(solutions_path))
        for p in grid_paths + sol_paths:
            z.write(p, f"images/{os.path.basename(p)}")
    return canva_path, solutions_path, zip_path


# Initialize session state for language, themes, and styling
if "selected_language" not in st.session_state:
    st.session_state["selected_language"] = "English"
if "last_selected_language" not in st.session_state:
    st.session_state["last_selected_language"] = "English"
    st.session_state["default_theme"] = LANGUAGE_CONFIGS["English"]["default_theme"]
    st.session_state["raw_words"] = LANGUAGE_CONFIGS["English"]["sample_words"]

if "audience_theme" not in st.session_state:
    st.session_state["audience_theme"] = "👔 Adult Classic"
if "last_audience_theme" not in st.session_state:
    st.session_state["last_audience_theme"] = "👔 Adult Classic"
    init_p = THEME_PRESETS["👔 Adult Classic"]
    st.session_state["cell_style"] = init_p["cell_style"]
    st.session_state["grid_line_width"] = init_p["grid_line_width"]
    st.session_state["grid_line_color"] = init_p["grid_line_color"]
    st.session_state["font_scale"] = init_p["font_scale"]
    st.session_state["letter_font"] = init_p["letter_font"]
    st.session_state["letter_color"] = init_p["letter_color"]
    st.session_state["solution_style"] = init_p["solution_style"]

# Main layout: Left controls panel & right preview area
controls, preview_area = st.columns([1.04, 1.42], gap="medium")

with controls:
    # -------------------------------------------------------------
    # 1. LANGUAGE SELECTION (First option before words input)
    # -------------------------------------------------------------
    st.markdown('<div class="ctrl-card"><div class="panel-step">Step 1 · Language & Alphabet</div><div class="section-title">🌍 Select Puzzle Language</div>', unsafe_allow_html=True)
    
    lang_names = list(LANGUAGE_CONFIGS.keys())
    current_lang_idx = lang_names.index(st.session_state["selected_language"]) if st.session_state["selected_language"] in lang_names else 0
    
    selected_language = st.selectbox(
        "Language",
        lang_names,
        index=current_lang_idx,
        label_visibility="collapsed",
        key="lang_selector",
        help="Select language. Prompts, sample words, themes, and fill alphabets adapt automatically.",
    )

    # When language changes, update defaults
    if selected_language != st.session_state.get("last_selected_language"):
        st.session_state["last_selected_language"] = selected_language
        st.session_state["selected_language"] = selected_language
        new_lang_cfg = LANGUAGE_CONFIGS[selected_language]
        st.session_state["default_theme"] = new_lang_cfg["default_theme"]
        st.session_state["raw_words"] = new_lang_cfg["sample_words"]

    lang_cfg = LANGUAGE_CONFIGS[selected_language]
    st.markdown(f'<div class="lang-badge">{lang_cfg["flag"]} <b>{selected_language}</b>: {lang_cfg["badge_info"]}</div>', unsafe_allow_html=True)

    c_acc1, c_acc2 = st.columns([1.3, 0.7], gap="small")
    with c_acc1:
        accent_mode = st.selectbox(
            "Accents & Diacritics",
            ["Standard Book Mode", "Preserve Exact Accents", "Strip All Accents (A-Z)"],
            index=0,
            help="Standard Book Mode keeps official language letters (Ñ for Spanish, Ä/Ö/Ü for German) and flattens vowel accents. Preserve Exact keeps all accents typed.",
        )
    with c_acc2:
        if st.button("🔄 Reset Sample", help=f"Reset theme and words to {selected_language} defaults"):
            st.session_state["default_theme"] = lang_cfg["default_theme"]
            st.session_state["raw_words"] = lang_cfg["sample_words"]
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. TABS FOR WORDS, GRID SIZE, AND STYLES
    # -------------------------------------------------------------
    tab_words, tab_grid, tab_style = st.tabs(["📝 Words & Content", "📐 Grid Dimensions", "🎨 Style & Audience"])

    with tab_words:
        st.markdown('<div class="panel-step">Step 2 · Word Input & Theme</div>', unsafe_allow_html=True)
        mode = st.radio("Source", ["Import CSV", "Paste a word list"], horizontal=True)
        
        default_theme = st.text_input(
            "Theme / Title",
            value=st.session_state.get("default_theme", lang_cfg["default_theme"]),
            help="Title of the puzzle page",
        )
        st.session_state["default_theme"] = default_theme

        uploaded = st.file_uploader(f"CSV file ({selected_language})", type=["csv"], disabled=mode != "Import CSV")
        
        raw_text = st.text_area(
            f"Words ({selected_language})",
            value=st.session_state.get("raw_words", lang_cfg["sample_words"]),
            height=120,
            disabled=mode != "Paste a word list",
            help="Enter one word per line or separated by semicolons. Letters only.",
        )
        if mode == "Paste a word list":
            st.session_state["raw_words"] = raw_text

        st.markdown('<div class="panel-step" style="margin-top:.45rem">Step 3 · Puzzle Rules</div>', unsafe_allow_html=True)
        c_d1, c_d2 = st.columns(2, gap="small")
        with c_d1:
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1, help="Easy = forward (E, S) only; Medium = forward & diagonals; Hard = all 8 directions with reverse.")
        with c_d2:
            seed = st.number_input("Seed", min_value=0, value=42, step=1, help="Deterministic seed for reproducible puzzle layouts.")

        with st.expander(f"📥 Sample CSVs & AI Prompts ({selected_language})", expanded=False):
            ex1, ex2 = st.columns(2, gap="small")
            with ex1:
                st.download_button(f"Themed CSV ({lang_cfg['flag']})", lang_cfg["themed_csv"], f"themed_{lang_cfg['default_theme'].lower()}_sample.csv", "text/csv", use_container_width=True)
            with ex2:
                st.download_button(f"Simple CSV ({lang_cfg['flag']})", lang_cfg["simple_csv"], f"simple_{lang_cfg['default_theme'].lower()}_sample.csv", "text/csv", use_container_width=True)
            
            st.markdown(f"<div class='smallcaps' style='margin-top:.4rem;'>AI Prompts in {selected_language}</div>", unsafe_allow_html=True)
            prompt_type = st.selectbox("Prompt template", list(lang_cfg["prompts"].keys()), label_visibility="collapsed")
            st.code(lang_cfg["prompts"][prompt_type], language="text")

        groups = parse_input(uploaded, mode, raw_text, default_theme, selected_language, accent_mode)
        all_count = sum(len(v) for v in groups.values())
        sample_note = f" · {lang_cfg['flag']} {selected_language} sample" if not uploaded and mode == "Import CSV" else ""
        st.markdown(f'<div class="card" style="margin-top:.45rem;"><div class="smallcaps">Input Summary</div><b>{len(groups)} theme(s) · {all_count} valid word(s)</b><span style="color:#64746d;font-size:.8rem">{sample_note}</span></div>', unsafe_allow_html=True)

    with tab_grid:
        st.markdown('<div class="panel-step">Grid Sizing & Dimensions</div><div class="section-title">📐 Dimensions & Word Capacity</div>', unsafe_allow_html=True)
        grid_size_choice = st.selectbox(
            "Grid Dimensions",
            [
                "10 × 10 (Kids / Compact)",
                "12 × 10 (Activity Book)",
                "12 × 12 (Junior)",
                "13 × 13 (Medium)",
                "14 × 14 (Standard KDP)",
                "15 × 15 (Classic Newspaper)",
                "16 × 16 (Challenging)",
                "Auto (from Difficulty)",
                "Custom (Rows × Cols)",
            ],
            index=1,
            help="Choose standard popular book sizes or configure custom row × column dimensions.",
        )

        if grid_size_choice == "Auto (from Difficulty)":
            grid_rows, grid_cols = None, None
            eff_rows = 10 if difficulty == "easy" else (13 if difficulty == "medium" else 16)
            eff_cols = eff_rows
        elif grid_size_choice == "Custom (Rows × Cols)":
            c_r, c_c = st.columns(2, gap="small")
            with c_r:
                grid_rows = st.slider("Rows (Height)", min_value=6, max_value=25, value=12, step=1)
            with c_c:
                grid_cols = st.slider("Columns (Width)", min_value=6, max_value=25, value=10, step=1)
            eff_rows, eff_cols = grid_rows, grid_cols
        else:
            parts = grid_size_choice.split(" ")
            grid_rows, grid_cols = int(parts[0]), int(parts[2])
            eff_rows, eff_cols = grid_rows, grid_cols

        grid_capacity = max_words_for_grid(eff_rows, eff_cols)
        words_per_page = st.slider(
            "Words per page",
            min_value=4,
            max_value=max(25, grid_capacity + 6),
            value=min(12, grid_capacity),
            help=f"Optimal capacity for {eff_rows}×{eff_cols} is ~{grid_capacity} words.",
        )

        st.markdown(f"""
        <div class="card" style="margin-top:.4rem; padding:10px 14px;">
            <div class="smallcaps">Grid Shape & Capacity</div>
            <b>{eff_rows} Rows × {eff_cols} Columns</b> ({eff_rows * eff_cols} total cells)<br>
            <span style="color:#56675f; font-size:0.8rem;">
                Suggested capacity: ~{grid_capacity} words per page · {"Landscape / Rectangular" if eff_rows != eff_cols else "Square"} layout
            </span>
        </div>
        """, unsafe_allow_html=True)

    with tab_style:
        st.markdown('<div class="panel-step">Audience Themes & Visual Styling</div><div class="section-title">🎨 Theme & Line Appearance</div>', unsafe_allow_html=True)

        selected_audience = st.selectbox(
            "Audience Preset",
            list(THEME_PRESETS.keys()),
            index=list(THEME_PRESETS.keys()).index(st.session_state["audience_theme"]) if st.session_state["audience_theme"] in THEME_PRESETS else 1,
            key="audience_theme_picker",
            help="1-click preset that configures line style, thickness, and font sizes tailored to each audience.",
        )

        # Detect preset change and update values
        if selected_audience != st.session_state.get("last_audience_theme"):
            st.session_state["last_audience_theme"] = selected_audience
            st.session_state["audience_theme"] = selected_audience
            if selected_audience in THEME_PRESETS and selected_audience != "⚙️ Custom":
                p_data = THEME_PRESETS[selected_audience]
                st.session_state["cell_style"] = p_data["cell_style"]
                st.session_state["grid_line_width"] = p_data["grid_line_width"]
                st.session_state["grid_line_color"] = p_data["grid_line_color"]
                st.session_state["font_scale"] = p_data["font_scale"]
                st.session_state["letter_font"] = p_data["letter_font"]
                st.session_state["letter_color"] = p_data["letter_color"]
                st.session_state["solution_style"] = p_data["solution_style"]

        st.markdown(f'<div class="theme-badge">{THEME_PRESETS[selected_audience]["description"]}</div>', unsafe_allow_html=True)

        with st.expander("Grid Lines & Borders", expanded=True):
            style_map = {
                "none": "None (No Lines / Floating Letters)",
                "grid": "Classic Grid Lines",
                "boxes": "Individual Cell Boxes",
                "rounded_boxes": "Rounded Cell Boxes (Kids Style)",
                "outer_border": "Outer Border Only",
            }
            inv_style_map = {v: k for k, v in style_map.items()}
            current_cs_key = st.session_state.get("cell_style", "grid")
            cs_label = style_map.get(current_cs_key, "Classic Grid Lines")
            
            selected_style_label = st.selectbox(
                "Cell Line Style",
                list(style_map.values()),
                index=list(style_map.values()).index(cs_label),
                help="Choose border style or remove grid lines completely.",
            )
            st.session_state["cell_style"] = inv_style_map[selected_style_label]

            line_w = st.slider(
                "Line Thickness (mm)",
                min_value=0.0,
                max_value=2.5,
                value=float(st.session_state.get("grid_line_width", 0.6)),
                step=0.1,
                help="Set to 0.0 mm to remove lines. 0.5 = fine, 1.0 = bold, 1.5+ = extra thick for seniors.",
            )
            st.session_state["grid_line_width"] = line_w

            col_colors = ["Neutral Gray (#9da49f)", "Deep Black (#111815)", "Forest Green (#516d61)", "Navy Blue (#1a2c42)", "Custom Hex"]
            cur_lc = st.session_state.get("grid_line_color", "#9da49f")
            default_lc_idx = 0
            if cur_lc == "#111815": default_lc_idx = 1
            elif cur_lc == "#516d61": default_lc_idx = 2
            elif cur_lc == "#1a2c42": default_lc_idx = 3
            elif cur_lc not in ("#9da49f", "#111815", "#516d61", "#1a2c42"): default_lc_idx = 4

            picked_line_color_opt = st.selectbox("Line Color", col_colors, index=default_lc_idx)
            if picked_line_color_opt == "Neutral Gray (#9da49f)":
                st.session_state["grid_line_color"] = "#9da49f"
            elif picked_line_color_opt == "Deep Black (#111815)":
                st.session_state["grid_line_color"] = "#111815"
            elif picked_line_color_opt == "Forest Green (#516d61)":
                st.session_state["grid_line_color"] = "#516d61"
            elif picked_line_color_opt == "Navy Blue (#1a2c42)":
                st.session_state["grid_line_color"] = "#1a2c42"
            else:
                st.session_state["grid_line_color"] = st.text_input("Custom Line Hex", cur_lc)

        with st.expander("Letter Typography & Sizing", expanded=True):
            f_scale = st.slider(
                "Letter Font Size (% of cell)",
                min_value=50,
                max_value=88,
                value=int(st.session_state.get("font_scale", 62)),
                step=2,
                help="50% = Compact, 62% = Standard balanced, 76% = Kids large print, 82% = Senior giant print.",
            )
            st.session_state["font_scale"] = f_scale

            font_list = ["DejaVu Sans", "DejaVu Sans Bold", "DejaVu Serif", "DejaVu Serif Bold"]
            cur_font = st.session_state.get("letter_font", "DejaVu Sans")
            f_idx = font_list.index(cur_font) if cur_font in font_list else 0
            st.session_state["letter_font"] = st.selectbox("Letter Font", font_list, index=f_idx)

            let_colors = ["Dark Charcoal (#202a26)", "Jet Black (#000000)", "Forest Ink (#172721)", "Navy Blue (#1a2c42)", "Custom Hex"]
            cur_let_c = st.session_state.get("letter_color", "#202a26")
            default_let_idx = 0
            if cur_let_c == "#000000": default_let_idx = 1
            elif cur_let_c == "#172721": default_let_idx = 2
            elif cur_let_c == "#1a2c42": default_let_idx = 3
            elif cur_let_c not in ("#202a26", "#000000", "#172721", "#1a2c42"): default_let_idx = 4

            picked_let_color_opt = st.selectbox("Letter Color", let_colors, index=default_let_idx)
            if picked_let_color_opt == "Dark Charcoal (#202a26)":
                st.session_state["letter_color"] = "#202a26"
            elif picked_let_color_opt == "Jet Black (#000000)":
                st.session_state["letter_color"] = "#000000"
            elif picked_let_color_opt == "Forest Ink (#172721)":
                st.session_state["letter_color"] = "#172721"
            elif picked_let_color_opt == "Navy Blue (#1a2c42)":
                st.session_state["letter_color"] = "#1a2c42"
            else:
                st.session_state["letter_color"] = st.text_input("Custom Letter Hex", cur_let_c)

        with st.expander("Page Layout & Solutions", expanded=False):
            show_bank = st.toggle("Display word bank", True)
            bank_columns = st.selectbox("Word bank columns", [1, 2, 3, 4, 5], index=1)
            
            sol_map = {"capsule": "Capsule / Pill Highlighter", "box": "Box Outline", "bold": "Bold Letters"}
            inv_sol_map = {v: k for k, v in sol_map.items()}
            cur_sol = st.session_state.get("solution_style", "capsule")
            sol_label = sol_map.get(cur_sol, "Capsule / Pill Highlighter")
            chosen_sol_label = st.selectbox("Solution Marker", list(sol_map.values()), index=list(sol_map.values()).index(sol_label))
            st.session_state["solution_style"] = inv_sol_map[chosen_sol_label]

            include_solution_in_bulk = st.checkbox(
                "Include solution in Canva bulk",
                value=False,
                help="When checked, solution images are added as an extra column in the Canva bulk Excel. When unchecked, exported separately.",
            )
            solutions_per_page = st.selectbox(
                "Solutions per page",
                [1, 2, 3, 4, 5],
                index=3,
                disabled=include_solution_in_bulk,
            )

# Determine fill alphabet based on language and accent mode
active_fill_alphabet = lang_cfg["fill_alphabet"]
if accent_mode == "Strip All Accents (A-Z)":
    active_fill_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Assemble active style object
current_style = SimpleNamespace(
    cell_style=st.session_state["cell_style"],
    grid_line_width=st.session_state["grid_line_width"],
    grid_line_color=st.session_state["grid_line_color"],
    letter_color=st.session_state["letter_color"],
    letter_font=st.session_state["letter_font"],
    font_scale=st.session_state["font_scale"] / 100.0,
    letter_size_pt=None,
    solution_style=st.session_state["solution_style"],
    solution_color=st.session_state["letter_color"],
    row_shading=False,
)

@st.cache_data(show_spinner=False)
def get_puzzles(groups_dict, diff_str, words_per_page, seed_val, grid_rows=None, grid_cols=None, fill_alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    cfg = PuzzleConfig(
        difficulty=Difficulty(diff_str),
        words_per_page=words_per_page,
        seed=int(seed_val),
        grid_rows=grid_rows,
        grid_cols=grid_cols,
        fill_alphabet=fill_alphabet,
    )
    result = []
    for theme, words in groups_dict.items():
        cleaned = [w for w in words if len(w) >= 3]
        chunks = [cleaned[start:start + words_per_page]
                  for start in range(0, len(cleaned), words_per_page)
                  if cleaned[start:start + words_per_page]]
        if len(chunks) > 1 and len(chunks[-1]) < words_per_page:
            chunks = chunks[:-1]
        for chunk in chunks:
            local = cfg.model_copy(deep=True)
            local.seed = int(seed_val) + len(result)
            result.append(generate_reliably(chunk, local, theme))
    return result

with preview_area:
    if groups:
        puzzles = get_puzzles(
            dict(groups),
            difficulty,
            words_per_page,
            seed,
            grid_rows,
            grid_cols,
            active_fill_alphabet,
        )
        
        # Clear old export files if parameters, language, or styling change
        puz_hash = hash(
            str(dict(groups)) + difficulty + str(words_per_page) + str(seed) +
            str(grid_rows) + str(grid_cols) + str(active_fill_alphabet) + selected_language
        )
        style_hash = hash(
            f"{current_style.cell_style}_{current_style.grid_line_width}_{current_style.grid_line_color}_"
            f"{current_style.font_scale}_{current_style.letter_font}_{current_style.letter_color}_{current_style.solution_style}"
        )
        combined_hash = hash((puz_hash, style_hash))

        if st.session_state.get("last_combined_hash") != combined_hash:
            st.session_state["last_combined_hash"] = combined_hash
            for k in ["canva_bytes", "solutions_bytes", "zip_bytes"]:
                st.session_state.pop(k, None)

        if puzzles:
            # Metrics strip
            c1, c2, c3, c4, c5 = st.columns(5, gap="small")
            c1.metric("Pages", len(puzzles))
            c2.metric("Language", f"{lang_cfg['flag']} {selected_language.split(' ')[0]}")
            c3.metric("Grid Size", f"{puzzles[0].rows} × {puzzles[0].cols}")
            line_desc = "No Lines" if current_style.grid_line_width == 0 or current_style.cell_style == "none" else f"{current_style.cell_style.replace('_', ' ').title()} ({current_style.grid_line_width}mm)"
            c4.metric("Border", line_desc)
            c5.metric("Font Scale", f"{int(current_style.font_scale * 100)}%")

            preview_col, export_col = st.columns([1.55, .75], gap="small")
            with preview_col:
                top_p1, top_p2 = st.columns([1.4, 1.0], gap="small")
                with top_p1:
                    selected = st.selectbox(
                        "Preview page",
                        range(1, len(puzzles) + 1),
                        format_func=lambda x: f"Page {x}: {puzzles[x-1].theme}",
                        label_visibility="collapsed",
                    )
                with top_p2:
                    view_mode = st.radio("View Mode", ["🔲 Puzzle", "🎯 Solution"], horizontal=True, label_visibility="collapsed")

                st.image(
                    render_png(
                        puzzles[selected - 1],
                        bank_columns,
                        False,
                        solution=(view_mode == "🎯 Solution"),
                        compact=True,
                        style=current_style,
                    ),
                    use_container_width=True,
                )
                if show_bank:
                    render_word_bank(puzzles[selected - 1].words, bank_columns, title=lang_cfg.get("word_bank_title", "Word bank"))
                if puzzles[selected - 1].skipped:
                    st.warning("Some words could not be placed: " + ", ".join(puzzles[selected - 1].skipped))

            with export_col:
                st.markdown('<div class="section-title">Export Canva Bundle</div>', unsafe_allow_html=True)
                if include_solution_in_bulk:
                    st.caption("Solutions: included in Canva bulk")
                else:
                    st.caption(f"Solutions: {solutions_per_page} per page (separate workbook)")
                
                if st.button("Generate Export Bundle", type="primary", use_container_width=True):
                    progress_bar = st.progress(0, text="Starting generation...")
                    out_dir = tempfile.mkdtemp(prefix="word_search_studio_")
                    canva_path, solutions_path, zip_path = build_workbooks(
                        puzzles,
                        out_dir,
                        show_bank,
                        bank_columns,
                        solutions_per_page,
                        include_solution_in_bulk=include_solution_in_bulk,
                        progress_bar=progress_bar,
                        style=current_style,
                    )
                    
                    if progress_bar:
                        progress_bar.progress(100, text="Export bundle ready!")
                    
                    st.session_state["canva_bytes"] = Path(canva_path).read_bytes()
                    st.session_state["solutions_bytes"] = (
                        Path(solutions_path).read_bytes() if solutions_path else None
                    )
                    st.session_state["zip_bytes"] = Path(zip_path).read_bytes()
                    st.session_state["solution_in_bulk"] = include_solution_in_bulk
                    st.success("Export ready with custom grid styles!")

                if "canva_bytes" in st.session_state:
                    st.download_button("Canva Excel", st.session_state["canva_bytes"], "word_search_canva_bulk.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    if st.session_state.get("solutions_bytes"):
                        st.download_button("Solutions Excel", st.session_state["solutions_bytes"], "word_search_solutions.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    st.download_button("Canva ZIP (Images + Workbooks)", st.session_state["zip_bytes"], "word_search_canva_export.zip", "application/zip", use_container_width=True)

                st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
                render_square_ad()
        else:
            st.info("Add at least one valid word of three or more letters.")
    else:
        st.info("Import a CSV or paste words to begin.")
