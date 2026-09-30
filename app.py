from __future__ import annotations

import csv
import io
import math
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
    from core.grid_raster import (
        render_grid_image,
        render_solution_image,
        render_word_search_solution_page_image,
    )
except ModuleNotFoundError:
    from modules.word_search.generator import generate_puzzle
    from modules.word_search.models import Difficulty, PuzzleConfig, max_words_for_grid
    from core.grid_raster import (
        render_grid_image,
        render_solution_image,
        render_word_search_solution_page_image,
    )

from core.canva_bulk import write_bulk_excel
from engine.sudoku import (
    DEFAULT_WORDOKU_WORDS,
    DIFFICULTY_LABELS,
    DIFFICULTY_STARS,
    TYPE_LABELS,
    SudokuConfig,
    SudokuDifficulty,
    SudokuPuzzle,
    SudokuType,
    clean_wordoku_letters,
    generate_sudoku_puzzle,
    get_default_clues,
)
from core.sudoku_raster import (
    SUDOKU_PRESETS,
    render_sudoku_image,
    render_sudoku_solution_image,
    render_sudoku_solution_page_image,
)
from core.sudoku_pdf import TRIM_SIZES
from core.sudoku_export import build_sudoku_workbooks

st.set_page_config(
    page_title="KDP Activity Studio · Word Search & Sudoku",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="collapsed",
)

GOOGLE_ADSENSE_CLIENT = os.getenv("GOOGLE_ADSENSE_CLIENT", "")
GOOGLE_ADSENSE_SLOT = os.getenv("GOOGLE_ADSENSE_SLOT", "")


def render_square_ad():
    """Render a 300x250 AdSense unit or a clean placeholder before setup."""
    if GOOGLE_ADSENSE_CLIENT and GOOGLE_ADSENSE_SLOT:
        components.html(
            f"""
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={GOOGLE_ADSENSE_CLIENT}" crossorigin="anonymous"></script>
        <ins class="adsbygoogle" style="display:inline-block;width:300px;height:250px"
             data-ad-client="{GOOGLE_ADSENSE_CLIENT}" data-ad-slot="{GOOGLE_ADSENSE_SLOT}"></ins>
        <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        """,
            height=265,
            scrolling=False,
        )
    else:
        st.markdown(
            """<div class="ad-placeholder"><div class="ad-label">ADVERTISEMENT</div><div class="ad-square">300 × 250<br><span>Add your Google AdSense details after hosting</span></div></div>""",
            unsafe_allow_html=True,
        )


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

# ==============================================================================
# UNIFIED MODERN STYLING WITH STICKY PREVIEW & SCROLLABLE CONTROLS
# ==============================================================================
st.markdown(
    """
<style>
:root {
    --ink: #14251f;
    --muted: #5e6f67;
    --cream: #f8f6f0;
    --primary: #17352b;
    --primary-light: #285b4a;
    --card-bg: #ffffff;
    --border-light: #e4dfd6;
}
.stApp { background: var(--cream); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
[data-testid="stHeader"] { visibility: hidden !important; }
.block-container { max-width: 1560px; padding: 0.65rem 1.4rem 1.8rem; }

/* Top Branding Hero Banner */
.hero {
    background: linear-gradient(135deg, #17352b 0%, #224c3e 60%, #2f6955 100%);
    color: white;
    border-radius: 14px;
    padding: 14px 22px;
    margin-bottom: 12px;
    box-shadow: 0 4px 15px rgba(23, 53, 43, 0.12);
}
.hero-tag {
    color: #a3d9be;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.hero h1 { margin: 0; font-size: 1.95rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.15; }
.hero p { margin: 0.25rem 0 0; color: #e1efe7; font-size: 0.88rem; font-weight: 400; }

/* Navigation Tab Switcher */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    margin-bottom: 12px;
    border-bottom: 2px solid #e1dcce;
    padding-bottom: 2px;
}
.stTabs [data-baseweb="tab"] {
    background: #ebe7dd !important;
    border: 1px solid #d5cebf !important;
    border-radius: 9px 9px 0 0 !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    padding: 7px 18px !important;
    color: #3b4e45 !important;
    transition: all 0.15s ease-in-out;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #17352b !important;
    border-bottom: 2px solid #ffffff !important;
    box-shadow: 0 -2px 8px rgba(20, 37, 31, 0.05) !important;
}

/* Control Cards & Summary Boxes */
.ctrl-card {
    background: var(--card-bg);
    border: 1px solid var(--border-light);
    border-radius: 12px;
    padding: 13px 15px;
    margin-bottom: 12px;
    box-shadow: 0 2px 7px rgba(20, 37, 31, 0.03);
}
.card {
    background: var(--card-bg);
    border: 1px solid var(--border-light);
    border-radius: 10px;
    padding: 10px 14px;
    margin: 8px 0;
    box-shadow: 0 1px 4px rgba(20, 37, 31, 0.02);
}
.panel-step {
    color: var(--primary-light);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 3px;
}
.smallcaps {
    color: var(--muted);
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
.section-title {
    font-size: 0.98rem;
    font-weight: 800;
    margin: 0 0 0.35rem;
    color: var(--ink);
}

/* Badges & Tags */
.lang-badge, .theme-badge {
    background: #e8f1eb;
    border: 1px solid #c9ded2;
    color: #194635;
    border-radius: 8px;
    padding: 6px 11px;
    font-size: 0.8rem;
    font-weight: 600;
    line-height: 1.35;
    margin: 0.35rem 0 0.45rem;
}
.status-pill {
    display: inline-block;
    background: #e0f2fe;
    border: 1px solid #bae6fd;
    color: #0369a1;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-top: 4px;
}

/* Metrics Strip */
div[data-testid="stMetric"] {
    background: white;
    border: 1px solid #e7e2d7;
    border-radius: 10px;
    padding: 0.35rem 0.65rem;
    box-shadow: 0 1px 4px rgba(20, 37, 31, 0.02);
}
div[data-testid="stMetricValue"] { color: var(--ink); font-size: 1.05rem; line-height: 1.05; font-weight: 800; }
div[data-testid="stMetricLabel"] { font-size: 0.65rem; margin-bottom: 0; font-weight: 700; color: var(--muted); text-transform: uppercase; }

/* Buttons & Downloads */
.stButton > button, .stDownloadButton > button {
    border-radius: 8px;
    font-weight: 700;
    transition: all 0.15s ease-in-out;
}

/* =========================================================
   SCROLLABLE CONTROLS & STATIC FIXED PREVIEW ON DESKTOP
   ========================================================= */
@media (min-width: 992px) {
    div[data-testid="column"]:has(.studio-controls-marker),
    div[data-testid="stColumn"]:has(.studio-controls-marker),
    div.stColumn:has(.studio-controls-marker) {
        max-height: calc(100vh - 130px) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding-right: 14px !important;
        padding-bottom: 24px !important;
        scrollbar-width: thin;
        scrollbar-color: #c5bead #f1ede3;
    }

    div[data-testid="column"]:has(.studio-preview-marker),
    div[data-testid="stColumn"]:has(.studio-preview-marker),
    div.stColumn:has(.studio-preview-marker) {
        position: sticky !important;
        top: 10px !important;
        align-self: flex-start !important;
        max-height: calc(100vh - 30px) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding-left: 8px !important;
        scrollbar-width: thin;
        scrollbar-color: #c5bead #f1ede3;
    }
}

/* Custom sleek WebKit scrollbars */
div[data-testid="column"]:has(.studio-controls-marker)::-webkit-scrollbar,
div[data-testid="stColumn"]:has(.studio-controls-marker)::-webkit-scrollbar,
div.stColumn:has(.studio-controls-marker)::-webkit-scrollbar,
div[data-testid="column"]:has(.studio-preview-marker)::-webkit-scrollbar,
div[data-testid="stColumn"]:has(.studio-preview-marker)::-webkit-scrollbar,
div.stColumn:has(.studio-preview-marker)::-webkit-scrollbar {
    width: 7px;
}
div[data-testid="column"]:has(.studio-controls-marker)::-webkit-scrollbar-track,
div[data-testid="stColumn"]:has(.studio-controls-marker)::-webkit-scrollbar-track,
div.stColumn:has(.studio-controls-marker)::-webkit-scrollbar-track,
div[data-testid="column"]:has(.studio-preview-marker)::-webkit-scrollbar-track,
div[data-testid="stColumn"]:has(.studio-preview-marker)::-webkit-scrollbar-track,
div.stColumn:has(.studio-preview-marker)::-webkit-scrollbar-track {
    background: #f1ede3;
    border-radius: 4px;
}
div[data-testid="column"]:has(.studio-controls-marker)::-webkit-scrollbar-thumb,
div[data-testid="stColumn"]:has(.studio-controls-marker)::-webkit-scrollbar-thumb,
div.stColumn:has(.studio-controls-marker)::-webkit-scrollbar-thumb,
div[data-testid="column"]:has(.studio-preview-marker)::-webkit-scrollbar-thumb,
div[data-testid="stColumn"]:has(.studio-preview-marker)::-webkit-scrollbar-thumb,
div.stColumn:has(.studio-preview-marker)::-webkit-scrollbar-thumb {
    background: #c5bead;
    border-radius: 4px;
}
div[data-testid="column"]:has(.studio-controls-marker)::-webkit-scrollbar-thumb:hover,
div[data-testid="stColumn"]:has(.studio-controls-marker)::-webkit-scrollbar-thumb:hover,
div.stColumn:has(.studio-controls-marker)::-webkit-scrollbar-thumb:hover,
div[data-testid="column"]:has(.studio-preview-marker)::-webkit-scrollbar-thumb:hover,
div[data-testid="stColumn"]:has(.studio-preview-marker)::-webkit-scrollbar-thumb:hover,
div.stColumn:has(.studio-preview-marker)::-webkit-scrollbar-thumb:hover {
    background: #9d9685;
}

/* Preview Image container */
[data-testid="stImage"] img {
    max-height: 60vh;
    width: auto !important;
    max-width: 100%;
    object-fit: contain;
    border-radius: 6px;
    display: block;
    margin: 0 auto;
}

/* AdSense placeholder */
.ad-placeholder {
    width: 300px;
    height: 250px;
    border: 1px dashed #c6ccc6;
    background: #f1f3f0;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #79837d;
    margin: 0.6rem auto 0;
}
.ad-label { font-size: 0.58rem; letter-spacing: 0.14em; font-weight: 800; margin-bottom: 0.45rem; }
.ad-square { text-align: center; font-size: 0.9rem; font-weight: 700; line-height: 1.5; }
.ad-square span { font-size: 0.68rem; font-weight: 500; }

.word-bank-title { color: #285b4a; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; margin: 0.4rem 0 0.2rem; }
.word-bank-item { color: #285b4a; font-size: 0.8rem; line-height: 1.35; padding: 0.08rem 0; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)

# Render Top Studio Hero
st.markdown(
    """
<div class="hero">
    <div class="hero-tag">KDP Activity Studio · Professional Book Creator</div>
    <h1>Activity Book Publishing Studio</h1>
    <p>Generate publication-ready Word Search and Sudoku puzzle books for Amazon KDP, Etsy, and Canva with custom styles, grids, and instant exports.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# TOP-LEVEL NAVIGATION TABS (Word Search vs Sudoku)
# ==============================================================================
tab_ws, tab_sudoku = st.tabs(["🔤 Word Search Studio", "🔢 Sudoku Studio"])


# ==============================================================================
# TAB 1: WORD SEARCH STUDIO
# ==============================================================================
def clean_word_for_language(raw_word: str, language: str, accent_mode: str = "Standard Book Mode") -> str:
    """Normalize and clean a word according to the language and accent preferences."""
    w = (raw_word or "").strip().upper()
    if not w:
        return ""

    w = w.replace("ß", "SS").replace("ẞ", "SS")

    if accent_mode == "Preserve Exact Accents":
        return "".join(ch for ch in w if ch.isalpha())

    if accent_mode == "Strip All Accents (A-Z)":
        nfkd = unicodedata.normalize("NFKD", w)
        return "".join(ch for ch in nfkd if "A" <= ch <= "Z")

    # Standard Book Mode
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
    if not words:
        return
    st.markdown(f'<div class="word-bank-title">{title}</div>', unsafe_allow_html=True)
    bank_cols = st.columns(max(1, min(5, columns)), gap="small")
    for index, word in enumerate(sorted(words)):
        bank_cols[index % len(bank_cols)].markdown(
            f'<div class="word-bank-item">{word}</div>', unsafe_allow_html=True
        )


def build_workbooks(
    puzzles,
    out_dir,
    show_bank,
    bank_columns,
    solutions_per_page,
    include_solution_in_bulk=False,
    progress_bar=None,
    style=None,
):
    import xlsxwriter

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
                ws.insert_image(
                    row_idx,
                    2 + offset,
                    sol_paths[index],
                    {
                        "x_scale": 0.09,
                        "y_scale": 0.09,
                        "x_offset": 5,
                        "y_offset": 5,
                        "positioning": 1,
                    },
                )
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


@st.cache_data(show_spinner=False)
def get_puzzles(
    groups_dict,
    diff_str,
    words_per_page,
    seed_val,
    grid_rows=None,
    grid_cols=None,
    fill_alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    target_count=None,
):
    cfg = PuzzleConfig(
        difficulty=Difficulty(diff_str),
        words_per_page=words_per_page,
        seed=int(seed_val),
        grid_rows=grid_rows,
        grid_cols=grid_cols,
        fill_alphabet=fill_alphabet,
    )
    base_chunks = []
    for theme, words in groups_dict.items():
        cleaned = [w for w in words if len(w) >= 3]
        chunks = [
            cleaned[start : start + words_per_page]
            for start in range(0, len(cleaned), words_per_page)
            if cleaned[start : start + words_per_page]
        ]
        if len(chunks) > 1 and len(chunks[-1]) < words_per_page:
            chunks = chunks[:-1]
        for c in chunks:
            base_chunks.append((theme, c))

    if not base_chunks:
        return []

    result = []
    total_needed = target_count if (target_count and target_count > 0) else len(base_chunks)
    for i in range(total_needed):
        theme, chunk = base_chunks[i % len(base_chunks)]
        local = cfg.model_copy(deep=True)
        local.seed = int(seed_val) + i * 19
        theme_title = theme if total_needed <= len(base_chunks) else f"{theme} #{i + 1}"
        result.append(generate_reliably(chunk, local, theme_title))

    return result


with tab_ws:
    # Initialize Word Search session states
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

    ws_controls, ws_preview = st.columns([1.08, 1.42], gap="medium")

    with ws_controls:
        st.markdown('<div class="studio-controls-marker"></div>', unsafe_allow_html=True)
        # Step 1: Language
        st.markdown(
            '<div class="ctrl-card"><div class="panel-step">Step 1 · Language & Alphabet</div><div class="section-title">🌍 Select Puzzle Language</div>',
            unsafe_allow_html=True,
        )
        lang_names = list(LANGUAGE_CONFIGS.keys())
        current_lang_idx = (
            lang_names.index(st.session_state["selected_language"])
            if st.session_state["selected_language"] in lang_names
            else 0
        )
        selected_language = st.selectbox(
            "Language",
            lang_names,
            index=current_lang_idx,
            label_visibility="collapsed",
            key="ws_lang_selector",
            help="Select language. Prompts, sample words, themes, and fill alphabets adapt automatically.",
        )
        if selected_language != st.session_state.get("last_selected_language"):
            st.session_state["last_selected_language"] = selected_language
            st.session_state["selected_language"] = selected_language
            new_lang_cfg = LANGUAGE_CONFIGS[selected_language]
            st.session_state["default_theme"] = new_lang_cfg["default_theme"]
            st.session_state["raw_words"] = new_lang_cfg["sample_words"]

        lang_cfg = LANGUAGE_CONFIGS[selected_language]
        st.markdown(
            f'<div class="lang-badge">{lang_cfg["flag"]} <b>{selected_language}</b>: {lang_cfg["badge_info"]}</div>',
            unsafe_allow_html=True,
        )

        c_acc1, c_acc2 = st.columns([1.3, 0.7], gap="small")
        with c_acc1:
            accent_mode = st.selectbox(
                "Accents & Diacritics",
                ["Standard Book Mode", "Preserve Exact Accents", "Strip All Accents (A-Z)"],
                index=0,
                key="ws_accent_mode",
                help="Standard Book Mode keeps official language letters (Ñ for Spanish, Ä/Ö/Ü for German).",
            )
        with c_acc2:
            if st.button("🔄 Reset Sample", key="ws_reset_btn", help=f"Reset to {selected_language} defaults"):
                st.session_state["default_theme"] = lang_cfg["default_theme"]
                st.session_state["raw_words"] = lang_cfg["sample_words"]
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Tabs for Content, Dimensions, Styles
        ws_tab_words, ws_tab_grid, ws_tab_style = st.tabs(
            ["📝 Words & Content", "📐 Grid Dimensions", "🎨 Style & Audience"]
        )

        with ws_tab_words:
            st.markdown('<div class="panel-step">Step 2 · Word Input & Theme</div>', unsafe_allow_html=True)
            c_w1, c_w2 = st.columns([1.05, 0.95], gap="small")
            with c_w1:
                mode = st.radio("Source", ["Import CSV", "Paste a word list"], horizontal=True, key="ws_source_mode")
            with c_w2:
                default_theme = st.text_input(
                    "Theme / Title",
                    value=st.session_state.get("default_theme", lang_cfg["default_theme"]),
                    key="ws_theme_input",
                    help="Title of the puzzle page",
                )
                st.session_state["default_theme"] = default_theme

            uploaded = st.file_uploader(
                f"CSV file ({selected_language})", type=["csv"], disabled=mode != "Import CSV", key="ws_csv_upload"
            )
            raw_text = st.text_area(
                f"Words ({selected_language})",
                value=st.session_state.get("raw_words", lang_cfg["sample_words"]),
                height=110,
                disabled=mode != "Paste a word list",
                key="ws_raw_words_input",
                help="Enter one word per line or separated by semicolons. Letters only.",
            )
            if mode == "Paste a word list":
                st.session_state["raw_words"] = raw_text

            # Custom Number of Puzzles Control
            c_cnt_tog, c_cnt_val = st.columns([1.1, 0.9], gap="small")
            with c_cnt_tog:
                ws_custom_count_enabled = st.toggle(
                    "Custom Puzzle Count",
                    value=False,
                    key="ws_cust_count_tog",
                    help="Enable to specify an exact number of puzzle pages to produce.",
                )
            with c_cnt_val:
                ws_target_puzzles = st.number_input(
                    "Target Puzzles",
                    min_value=1,
                    max_value=200,
                    value=12,
                    step=1,
                    disabled=not ws_custom_count_enabled,
                    key="ws_target_puz_in",
                )

            st.markdown(
                '<div class="panel-step" style="margin-top:.45rem">Step 3 · Puzzle Rules</div>',
                unsafe_allow_html=True,
            )
            c_d1, c_d2 = st.columns(2, gap="small")
            with c_d1:
                difficulty = st.selectbox(
                    "Difficulty",
                    ["easy", "medium", "hard"],
                    index=1,
                    key="ws_diff_select",
                    help="Easy = forward (E, S) only; Medium = forward & diagonals; Hard = all 8 directions with reverse.",
                )
            with c_d2:
                seed = st.number_input(
                    "Seed",
                    min_value=0,
                    value=42,
                    step=1,
                    key="ws_seed_input",
                    help="Deterministic seed for reproducible puzzle layouts.",
                )

            with st.expander(f"📥 Sample CSVs & AI Prompts ({selected_language})", expanded=False):
                ex1, ex2 = st.columns(2, gap="small")
                with ex1:
                    st.download_button(
                        f"Themed CSV ({lang_cfg['flag']})",
                        lang_cfg["themed_csv"],
                        f"themed_{lang_cfg['default_theme'].lower()}_sample.csv",
                        "text/csv",
                        width="stretch",
                    )
                with ex2:
                    st.download_button(
                        f"Simple CSV ({lang_cfg['flag']})",
                        lang_cfg["simple_csv"],
                        f"simple_{lang_cfg['default_theme'].lower()}_sample.csv",
                        "text/csv",
                        width="stretch",
                    )
                st.markdown(
                    f"<div class='smallcaps' style='margin-top:.4rem;'>AI Prompts in {selected_language}</div>",
                    unsafe_allow_html=True,
                )
                prompt_type = st.selectbox(
                    "Prompt template", list(lang_cfg["prompts"].keys()), label_visibility="collapsed", key="ws_prompt_tpl"
                )
                st.code(lang_cfg["prompts"][prompt_type], language="text")

            groups = parse_input(uploaded, mode, raw_text, default_theme, selected_language, accent_mode)
            all_count = sum(len(v) for v in groups.values())
            sample_note = (
                f" · {lang_cfg['flag']} {selected_language} sample" if not uploaded and mode == "Import CSV" else ""
            )
            st.markdown(
                f'<div class="card" style="margin-top:.45rem;"><div class="smallcaps">Input Summary</div><b>{len(groups)} theme(s) · {all_count} valid word(s)</b><span style="color:#64746d;font-size:.8rem">{sample_note}</span></div>',
                unsafe_allow_html=True,
            )

        with ws_tab_grid:
            st.markdown(
                '<div class="panel-step">Grid Sizing & Dimensions</div><div class="section-title">📐 Dimensions & Word Capacity</div>',
                unsafe_allow_html=True,
            )
            c_g1, c_g2 = st.columns([1.05, 0.95], gap="small")
            with c_g1:
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
                    key="ws_grid_size_choice",
                    help="Choose standard popular book sizes or configure custom dimensions.",
                )

                if grid_size_choice == "Auto (from Difficulty)":
                    grid_rows, grid_cols = None, None
                    eff_rows = 10 if difficulty == "easy" else (13 if difficulty == "medium" else 16)
                    eff_cols = eff_rows
                elif grid_size_choice == "Custom (Rows × Cols)":
                    c_r, c_c = st.columns(2, gap="small")
                    with c_r:
                        grid_rows = st.slider("Rows (Height)", min_value=6, max_value=25, value=12, step=1, key="ws_cust_rows")
                    with c_c:
                        grid_cols = st.slider("Columns (Width)", min_value=6, max_value=25, value=10, step=1, key="ws_cust_cols")
                    eff_rows, eff_cols = grid_rows, grid_cols
                else:
                    parts = grid_size_choice.split(" ")
                    grid_rows, grid_cols = int(parts[0]), int(parts[2])
                    eff_rows, eff_cols = grid_rows, grid_cols

            grid_capacity = max_words_for_grid(eff_rows, eff_cols)
            with c_g2:
                words_per_page = st.slider(
                    "Words per page",
                    min_value=4,
                    max_value=max(25, grid_capacity + 6),
                    value=min(12, grid_capacity),
                    key="ws_words_per_page_slider",
                    help=f"Optimal capacity for {eff_rows}×{eff_cols} is ~{grid_capacity} words.",
                )

            st.markdown(
                f"""
            <div class="card" style="margin-top:.4rem; padding:10px 14px;">
                <div class="smallcaps">Grid Shape & Capacity</div>
                <b>{eff_rows} Rows × {eff_cols} Columns</b> ({eff_rows * eff_cols} total cells)<br>
                <span style="color:#56675f; font-size:0.8rem;">
                    Suggested capacity: ~{grid_capacity} words per page · {"Landscape / Rectangular" if eff_rows != eff_cols else "Square"} layout
                </span>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with ws_tab_style:
            st.markdown(
                '<div class="panel-step">Audience Themes & Visual Styling</div><div class="section-title">🎨 Theme & Line Appearance</div>',
                unsafe_allow_html=True,
            )
            selected_audience = st.selectbox(
                "Audience Preset",
                list(THEME_PRESETS.keys()),
                index=list(THEME_PRESETS.keys()).index(st.session_state["audience_theme"])
                if st.session_state["audience_theme"] in THEME_PRESETS
                else 1,
                key="ws_audience_theme_picker",
                help="1-click preset that configures line style, thickness, and font sizes tailored to each audience.",
            )

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

            st.markdown(
                f'<div class="theme-badge">{THEME_PRESETS[selected_audience]["description"]}</div>',
                unsafe_allow_html=True,
            )

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

                col_colors = [
                    "Neutral Gray (#9da49f)",
                    "Deep Black (#111815)",
                    "Forest Green (#516d61)",
                    "Navy Blue (#1a2c42)",
                    "Custom Hex",
                ]
                cur_lc = st.session_state.get("grid_line_color", "#9da49f")
                default_lc_idx = 0
                if cur_lc == "#111815":
                    default_lc_idx = 1
                elif cur_lc == "#516d61":
                    default_lc_idx = 2
                elif cur_lc == "#1a2c42":
                    default_lc_idx = 3
                elif cur_lc not in ("#9da49f", "#111815", "#516d61", "#1a2c42"):
                    default_lc_idx = 4

                c_gl1, c_gl2 = st.columns(2, gap="small")
                with c_gl1:
                    selected_style_label = st.selectbox(
                        "Cell Line Style",
                        list(style_map.values()),
                        index=list(style_map.values()).index(cs_label),
                        key="ws_cell_style_sel",
                        help="Choose border style or remove grid lines completely.",
                    )
                    st.session_state["cell_style"] = inv_style_map[selected_style_label]
                with c_gl2:
                    picked_line_color_opt = st.selectbox(
                        "Line Color", col_colors, index=default_lc_idx, key="ws_line_color_pick"
                    )
                    if picked_line_color_opt == "Neutral Gray (#9da49f)":
                        st.session_state["grid_line_color"] = "#9da49f"
                    elif picked_line_color_opt == "Deep Black (#111815)":
                        st.session_state["grid_line_color"] = "#111815"
                    elif picked_line_color_opt == "Forest Green (#516d61)":
                        st.session_state["grid_line_color"] = "#516d61"
                    elif picked_line_color_opt == "Navy Blue (#1a2c42)":
                        st.session_state["grid_line_color"] = "#1a2c42"
                    else:
                        st.session_state["grid_line_color"] = st.text_input(
                            "Custom Line Hex", cur_lc, key="ws_line_hex_in"
                        )

                line_w = st.slider(
                    "Line Thickness (mm)",
                    min_value=0.0,
                    max_value=2.5,
                    value=float(st.session_state.get("grid_line_width", 0.6)),
                    step=0.1,
                    key="ws_line_w_slider",
                )
                st.session_state["grid_line_width"] = line_w

            with st.expander("Letter Typography & Sizing", expanded=True):
                font_list = ["DejaVu Sans", "DejaVu Sans Bold", "DejaVu Serif", "DejaVu Serif Bold"]
                cur_font = st.session_state.get("letter_font", "DejaVu Sans")
                f_idx = font_list.index(cur_font) if cur_font in font_list else 0

                let_colors = [
                    "Dark Charcoal (#202a26)",
                    "Jet Black (#000000)",
                    "Forest Ink (#172721)",
                    "Navy Blue (#1a2c42)",
                    "Custom Hex",
                ]
                cur_let_c = st.session_state.get("letter_color", "#202a26")
                default_let_idx = 0
                if cur_let_c == "#000000":
                    default_let_idx = 1
                elif cur_let_c == "#172721":
                    default_let_idx = 2
                elif cur_let_c == "#1a2c42":
                    default_let_idx = 3
                elif cur_let_c not in ("#202a26", "#000000", "#172721", "#1a2c42"):
                    default_let_idx = 4

                c_lt1, c_lt2 = st.columns(2, gap="small")
                with c_lt1:
                    st.session_state["letter_font"] = st.selectbox(
                        "Letter Font", font_list, index=f_idx, key="ws_letter_font_sel"
                    )
                with c_lt2:
                    picked_let_color_opt = st.selectbox(
                        "Letter Color", let_colors, index=default_let_idx, key="ws_let_color_pick"
                    )
                    if picked_let_color_opt == "Dark Charcoal (#202a26)":
                        st.session_state["letter_color"] = "#202a26"
                    elif picked_let_color_opt == "Jet Black (#000000)":
                        st.session_state["letter_color"] = "#000000"
                    elif picked_let_color_opt == "Forest Ink (#172721)":
                        st.session_state["letter_color"] = "#172721"
                    elif picked_let_color_opt == "Navy Blue (#1a2c42)":
                        st.session_state["letter_color"] = "#1a2c42"
                    else:
                        st.session_state["letter_color"] = st.text_input(
                            "Custom Letter Hex", cur_let_c, key="ws_let_hex_in"
                        )

                f_scale = st.slider(
                    "Letter Font Size (% of cell)",
                    min_value=50,
                    max_value=88,
                    value=int(st.session_state.get("font_scale", 62)),
                    step=2,
                    key="ws_font_scale_slider",
                )
                st.session_state["font_scale"] = f_scale

            with st.expander("Page Layout & Solutions", expanded=False):
                c_bk1, c_bk2 = st.columns([1, 1], gap="small")
                with c_bk1:
                    show_bank = st.toggle("Display word bank", True, key="ws_show_bank_tog")
                with c_bk2:
                    bank_columns = st.selectbox(
                        "Word bank columns", [1, 2, 3, 4, 5], index=1, key="ws_bank_cols_sel", disabled=not show_bank
                    )

                sol_map = {"capsule": "Capsule / Pill Highlighter", "box": "Box Outline", "bold": "Bold Letters"}
                inv_sol_map = {v: k for k, v in sol_map.items()}
                cur_sol = st.session_state.get("solution_style", "capsule")
                sol_label = sol_map.get(cur_sol, "Capsule / Pill Highlighter")

                include_solution_in_bulk = st.checkbox(
                    "Include solution on the same Excel with the game",
                    value=False,
                    key="ws_sol_in_bulk_chk",
                    help="When checked, solution images are added as an extra column in the Canva bulk Excel. When unchecked, exported to a separate workbook.",
                )

                c_sm1, c_sm2 = st.columns(2, gap="small")
                with c_sm1:
                    chosen_sol_label = st.selectbox(
                        "Solution Marker",
                        list(sol_map.values()),
                        index=list(sol_map.values()).index(sol_label),
                        key="ws_sol_style_sel",
                    )
                    st.session_state["solution_style"] = inv_sol_map[chosen_sol_label]
                with c_sm2:
                    solutions_per_page = st.selectbox(
                        "Solutions per page",
                        [1, 2, 3, 4, 5],
                        index=3,
                        disabled=include_solution_in_bulk,
                        key="ws_sols_per_page_sel",
                    )

    active_fill_alphabet = lang_cfg["fill_alphabet"]
    if accent_mode == "Strip All Accents (A-Z)":
        active_fill_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

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

    with ws_preview:
        st.markdown('<div class="studio-preview-marker"></div>', unsafe_allow_html=True)
        if groups:
            target_puz_val = ws_target_puzzles if ws_custom_count_enabled else None
            puzzles = get_puzzles(
                dict(groups),
                difficulty,
                words_per_page,
                seed,
                grid_rows,
                grid_cols,
                active_fill_alphabet,
                target_count=target_puz_val,
            )

            puz_hash = hash(
                str(dict(groups))
                + difficulty
                + str(words_per_page)
                + str(seed)
                + str(grid_rows)
                + str(grid_cols)
                + str(active_fill_alphabet)
                + selected_language
                + str(target_puz_val)
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
                c1, c2, c3, c4, c5 = st.columns(5, gap="small")
                c1.metric("Pages", len(puzzles))
                c2.metric("Language", f"{lang_cfg['flag']} {selected_language.split(' ')[0]}")
                c3.metric("Grid Size", f"{puzzles[0].rows} × {puzzles[0].cols}")
                line_desc = (
                    "No Lines"
                    if current_style.grid_line_width == 0 or current_style.cell_style == "none"
                    else f"{current_style.cell_style.replace('_', ' ').title()} ({current_style.grid_line_width}mm)"
                )
                c4.metric("Border", line_desc)
                c5.metric("Font Scale", f"{int(current_style.font_scale * 100)}%")

                preview_col, export_col = st.columns([1.55, 0.75], gap="small")
                with preview_col:
                    top_p1, top_p2 = st.columns([1.2, 1.2], gap="small")
                    with top_p2:
                        view_mode = st.radio(
                            "View Mode",
                            ["🔲 Single Puzzle", "🎯 Single Solution", "📑 Solution Page (Book)"],
                            horizontal=True,
                            label_visibility="collapsed",
                            key="ws_view_mode_rad",
                        )

                    if view_mode == "📑 Solution Page (Book)":
                        total_sol_pages = max(1, math.ceil(len(puzzles) / solutions_per_page))
                        with top_p1:
                            sol_page_idx = st.selectbox(
                                "Solution Page",
                                range(1, total_sol_pages + 1),
                                format_func=lambda x: f"Solution Page {x} of {total_sol_pages} (Puzzles {(x-1)*solutions_per_page + 1}–{min(len(puzzles), x*solutions_per_page)})",
                                label_visibility="collapsed",
                                key="ws_sol_page_sel",
                            )

                        start_i = (sol_page_idx - 1) * solutions_per_page
                        end_i = start_i + solutions_per_page
                        sol_slice = puzzles[start_i:end_i]
                        page_img = render_word_search_solution_page_image(
                            sol_slice, current_style, solutions_per_page, sol_page_idx, total_sol_pages, dpi=160
                        )
                        st.image(page_img, width="stretch")
                        st.caption(
                            f"📑 Book Solution Page Preview: showing {len(sol_slice)} of {solutions_per_page} solutions per page."
                        )
                    else:
                        with top_p1:
                            selected = st.selectbox(
                                "Preview page",
                                range(1, len(puzzles) + 1),
                                format_func=lambda x: f"Page {x}: {puzzles[x-1].theme}",
                                label_visibility="collapsed",
                                key="ws_preview_page_sel",
                            )

                        st.image(
                            render_png(
                                puzzles[selected - 1],
                                bank_columns,
                                False,
                                solution=(view_mode == "🎯 Single Solution"),
                                compact=True,
                                style=current_style,
                            ),
                            width="stretch",
                        )
                        if show_bank:
                            render_word_bank(
                                puzzles[selected - 1].words,
                                bank_columns,
                                title=lang_cfg.get("word_bank_title", "Word bank"),
                            )
                        if puzzles[selected - 1].skipped:
                            st.warning("Some words could not be placed: " + ", ".join(puzzles[selected - 1].skipped))

                with export_col:
                    st.markdown('<div class="section-title">Export Canva Bundle</div>', unsafe_allow_html=True)
                    if include_solution_in_bulk:
                        st.caption("Solutions: included in Canva bulk")
                    else:
                        st.caption(f"Solutions: {solutions_per_page} per page (separate workbook)")

                    if st.button("Generate Export Bundle", type="primary", width="stretch", key="ws_gen_btn"):
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
                        st.download_button(
                            "📦 Canva Excel",
                            st.session_state["canva_bytes"],
                            "word_search_canva_bulk.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch",
                            key="ws_down_canva",
                        )
                        if st.session_state.get("solutions_bytes"):
                            st.download_button(
                                "📑 Solutions Excel",
                                st.session_state["solutions_bytes"],
                                "word_search_solutions.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                width="stretch",
                                key="ws_down_sol",
                            )
                        st.download_button(
                            "🗂️ Canva ZIP (Images + Workbooks)",
                            st.session_state["zip_bytes"],
                            "word_search_canva_export.zip",
                            "application/zip",
                            width="stretch",
                            key="ws_down_zip",
                        )

                    st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
                    render_square_ad()
            else:
                st.info("Add at least one valid word of three or more letters.")
        else:
            st.info("Import a CSV or paste words to begin.")


# ==============================================================================
# TAB 2: SUDOKU STUDIO
# ==============================================================================
@st.cache_data(show_spinner=False)
def get_sudoku_batch(
    p_type_val: str,
    diff_val: str,
    count: int,
    start_num: int,
    seed_val: int,
    symmetric: bool,
    wordoku_word: str,
    custom_clues: int | None,
    title_tpl: str,
) -> list[SudokuPuzzle]:
    cfg = SudokuConfig(
        puzzle_type=SudokuType(p_type_val),
        difficulty=SudokuDifficulty(diff_val),
        target_clues=custom_clues,
        seed=int(seed_val),
        symmetric=symmetric,
        wordoku_word=wordoku_word,
        title_template=title_tpl,
    )
    results = []
    for i in range(count):
        p_id = start_num + i
        p = generate_sudoku_puzzle(p_id, cfg)
        results.append(p)
    return results


with tab_sudoku:
    # Initialize Sudoku session state
    if "sudoku_preset" not in st.session_state:
        st.session_state["sudoku_preset"] = "👔 Adult Classic"
    if "last_sudoku_preset" not in st.session_state:
        st.session_state["last_sudoku_preset"] = "👔 Adult Classic"
        init_s = SUDOKU_PRESETS["👔 Adult Classic"]
        st.session_state["s_cell_style"] = init_s["cell_style"]
        st.session_state["s_outer_line_width"] = init_s["outer_line_width"]
        st.session_state["s_block_line_width"] = init_s["block_line_width"]
        st.session_state["s_inner_line_width"] = init_s["inner_line_width"]
        st.session_state["s_grid_color"] = init_s["grid_color"]
        st.session_state["s_shading_mode"] = init_s["shading_mode"]
        st.session_state["s_shading_color"] = init_s["shading_color"]
        st.session_state["s_font_scale"] = init_s["font_scale"]
        st.session_state["s_clue_font"] = init_s["clue_font"]
        st.session_state["s_clue_color"] = init_s["clue_color"]
        st.session_state["s_solution_color"] = init_s["solution_color"]
        st.session_state["s_solution_mode"] = init_s["solution_mode"]

    sdk_controls, sdk_preview = st.columns([1.08, 1.42], gap="medium")

    with sdk_controls:
        st.markdown('<div class="studio-controls-marker"></div>', unsafe_allow_html=True)
        # Step 1: Puzzle Type & Rules
        st.markdown(
            '<div class="ctrl-card"><div class="panel-step">Step 1 · Puzzle Type & Rules</div><div class="section-title">🧩 Sudoku Game Type & Difficulty</div>',
            unsafe_allow_html=True,
        )

        type_options = {
            "Classic 9×9 (Standard)": SudokuType.CLASSIC_9X9,
            "Kids Mini 4×4 (Ages 4-8)": SudokuType.MINI_4X4,
            "Junior 6×6 (Ages 7-12)": SudokuType.JUNIOR_6X6,
            "Wordoku (Letter 9×9)": SudokuType.WORDOKU_9X9,
            "Sudoku X (Diagonal Constraints)": SudokuType.SUDOKU_X,
            "Windoku (Hyper 4-Window)": SudokuType.WINDOKU,
        }
        diff_options = {
            "Very Easy (Beginner)": SudokuDifficulty.VERY_EASY,
            "Easy (Casual)": SudokuDifficulty.EASY,
            "Medium (Standard)": SudokuDifficulty.MEDIUM,
            "Hard (Challenging)": SudokuDifficulty.HARD,
            "Expert (Master / Evil)": SudokuDifficulty.EXPERT,
        }

        c_t1, c_t2 = st.columns(2, gap="small")
        with c_t1:
            picked_type_label = st.selectbox(
                "Game Type",
                list(type_options.keys()),
                index=0,
                key="sdk_type_selector",
                help="Choose standard 9x9, kids mini grids, letter wordoku, or popular diagonal/window variants.",
            )
            selected_sudoku_type = type_options[picked_type_label]

        with c_t2:
            picked_diff_label = st.selectbox(
                "Difficulty Level",
                list(diff_options.keys()),
                index=2,
                key="sdk_diff_selector",
                help="Difficulty determines clue density and solving techniques required.",
            )
            selected_difficulty = diff_options[picked_diff_label]

        dim_size = 4 if selected_sudoku_type == SudokuType.MINI_4X4 else (6 if selected_sudoku_type == SudokuType.JUNIOR_6X6 else 9)
        std_clues = get_default_clues(dim_size, selected_difficulty)
        stars = DIFFICULTY_STARS[selected_difficulty]

        st.markdown(
            f'<div class="lang-badge"><b>{DIFFICULTY_LABELS[selected_difficulty]} {stars}</b>: ~{std_clues} clues on {dim_size}×{dim_size} grid · {TYPE_LABELS[selected_sudoku_type]}</div>',
            unsafe_allow_html=True,
        )

        # Wordoku Word configuration
        wordoku_word_val = "PUBLISHER"
        if selected_sudoku_type == SudokuType.WORDOKU_9X9:
            st.markdown('<div class="panel-step" style="margin-top:.4rem">Wordoku Keyword</div>', unsafe_allow_html=True)
            w_c1, w_c2 = st.columns([1.1, 0.9], gap="small")
            with w_c1:
                preset_word = st.selectbox(
                    "Preset 9-Letter Words",
                    DEFAULT_WORDOKU_WORDS,
                    index=0,
                    key="sdk_wordoku_preset",
                    help="Select a curated 9-letter keyword with distinct letters.",
                )
            with w_c2:
                custom_word = st.text_input(
                    "Or Custom Word",
                    value=preset_word,
                    max_chars=12,
                    key="sdk_wordoku_custom",
                    help="Type any word with 9 unique letters.",
                )
            cleaned_letters = clean_wordoku_letters(custom_word or preset_word)
            wordoku_word_val = "".join(cleaned_letters)
            st.markdown(
                f"<div class='status-pill'>Anagram Keyword: <b>{wordoku_word_val}</b> ({', '.join(cleaned_letters)})</div>",
                unsafe_allow_html=True,
            )

        # Clue symmetry & fine-tuning
        c_sym1, c_sym2 = st.columns([1.1, 0.9], gap="small")
        with c_sym1:
            symmetric_clues = st.toggle(
                "Rotational Symmetry (180°)",
                value=True,
                key="sdk_sym_toggle",
                help="Symmetric clue patterns create elegant, authentic print-quality puzzle book pages.",
            )
        with c_sym2:
            custom_clues_enabled = st.toggle("Custom Clue Count", value=False, key="sdk_cust_clues_toggle")

        custom_clues_val = None
        if custom_clues_enabled:
            min_c = 4 if dim_size == 4 else (10 if dim_size == 6 else 20)
            max_c = 12 if dim_size == 4 else (26 if dim_size == 6 else 55)
            custom_clues_val = st.slider(
                "Exact Target Clues",
                min_value=min_c,
                max_value=max_c,
                value=std_clues,
                step=1,
                key="sdk_clues_slider",
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # Tabs for Batch Volume & Visual Styling
        sdk_tab_vol, sdk_tab_style = st.tabs(["📚 Book Volume & Count", "🎨 Style & Audience"])

        with sdk_tab_vol:
            st.markdown(
                '<div class="panel-step">Book Generation Settings</div><div class="section-title">📚 Batch Puzzles & Numbering</div>',
                unsafe_allow_html=True,
            )

            # Custom count: slider + direct custom number input for unlimited customization
            c_cnt_s1, c_cnt_s2 = st.columns([1.1, 0.9], gap="small")
            with c_cnt_s1:
                sdk_count_slider_val = st.slider(
                    "Puzzles Slider (1–100)",
                    min_value=1,
                    max_value=100,
                    value=12,
                    step=1,
                    key="sdk_count_slider",
                    help="Quick slider for standard book batches.",
                )
            with c_cnt_s2:
                sdk_count = st.number_input(
                    "Exact Custom Count",
                    min_value=1,
                    max_value=300,
                    value=sdk_count_slider_val,
                    step=1,
                    key="sdk_exact_custom_count_in",
                    help="Type any custom number of puzzles up to 300.",
                )

            c_n1, c_n2 = st.columns([0.85, 1.15], gap="small")
            with c_n1:
                sdk_start_num = st.number_input(
                    "Starting Puzzle #",
                    min_value=1,
                    value=1,
                    step=1,
                    key="sdk_start_num_in",
                    help="E.g., start at 51 if creating Volume 2 of your puzzle book series.",
                )
            with c_n2:
                sdk_title_template = st.text_input(
                    "Title Template",
                    value="Sudoku #{num}",
                    key="sdk_title_tpl_in",
                    help="Template for puzzle titles. Tokens available: {num}, {diff}, {type}",
                )

            c_sd1, c_sd2 = st.columns([0.75, 1.25], gap="small")
            with c_sd1:
                sdk_seed = st.number_input(
                    "Random Seed",
                    min_value=0,
                    value=42,
                    step=1,
                    key="sdk_seed_in",
                    help="Deterministic seed for exact reproducible puzzle layouts.",
                )
            with c_sd2:
                st.markdown(
                    f"""
                <div class="card" style="margin-top:0; padding:8px 12px;">
                    <div class="smallcaps">Batch Summary</div>
                    <b>{sdk_count} Puzzles</b> · #{sdk_start_num} to #{sdk_start_num + sdk_count - 1}<br>
                    <span style="color:#56675f; font-size:0.75rem;">
                        Title: <i>{sdk_title_template.replace('{num}', str(sdk_start_num)).replace('{diff}', DIFFICULTY_LABELS[selected_difficulty])}</i> · 100% Unique
                    </span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        with sdk_tab_style:
            st.markdown(
                '<div class="panel-step">Visual Aesthetics & Presets</div><div class="section-title">🎨 Theme & Line Appearance</div>',
                unsafe_allow_html=True,
            )

            selected_sdk_preset = st.selectbox(
                "Audience Preset",
                list(SUDOKU_PRESETS.keys()),
                index=list(SUDOKU_PRESETS.keys()).index(st.session_state["sudoku_preset"])
                if st.session_state["sudoku_preset"] in SUDOKU_PRESETS
                else 0,
                key="sdk_preset_picker",
                help="1-click preset that configures line weights, font proportions, and colors.",
            )

            if selected_sdk_preset != st.session_state.get("last_sudoku_preset"):
                st.session_state["last_sudoku_preset"] = selected_sdk_preset
                st.session_state["sudoku_preset"] = selected_sdk_preset
                if selected_sdk_preset in SUDOKU_PRESETS and selected_sdk_preset != "⚙️ Custom":
                    s_data = SUDOKU_PRESETS[selected_sdk_preset]
                    st.session_state["s_cell_style"] = s_data["cell_style"]
                    st.session_state["s_outer_line_width"] = s_data["outer_line_width"]
                    st.session_state["s_block_line_width"] = s_data["block_line_width"]
                    st.session_state["s_inner_line_width"] = s_data["inner_line_width"]
                    st.session_state["s_grid_color"] = s_data["grid_color"]
                    st.session_state["s_shading_mode"] = s_data["shading_mode"]
                    st.session_state["s_shading_color"] = s_data["shading_color"]
                    st.session_state["s_font_scale"] = s_data["font_scale"]
                    st.session_state["s_clue_font"] = s_data["clue_font"]
                    st.session_state["s_clue_color"] = s_data["clue_color"]
                    st.session_state["s_solution_color"] = s_data["solution_color"]
                    st.session_state["s_solution_mode"] = s_data["solution_mode"]

            st.markdown(
                f'<div class="theme-badge">{SUDOKU_PRESETS[selected_sdk_preset]["description"]}</div>',
                unsafe_allow_html=True,
            )

            with st.expander("Grid Lines & Borders", expanded=True):
                s_style_map = {
                    "grid": "Classic Continuous Grid",
                    "rounded_boxes": "Rounded Cell Boxes (Kids / Modern)",
                    "boxes": "Individual Cell Cards",
                }
                inv_s_style = {v: k for k, v in s_style_map.items()}
                cur_cs = st.session_state.get("s_cell_style", "grid")

                s_grid_colors = [
                    "Jet Black (#111815)",
                    "Pure Black (#000000)",
                    "Charcoal Slate (#1f2937)",
                    "Navy Blue (#1e293b)",
                    "Forest Green (#14382d)",
                    "Custom Hex",
                ]
                cur_gc = st.session_state.get("s_grid_color", "#111815")
                def_gc_idx = 0
                if cur_gc == "#000000":
                    def_gc_idx = 1
                elif cur_gc == "#1f2937":
                    def_gc_idx = 2
                elif cur_gc == "#1e293b":
                    def_gc_idx = 3
                elif cur_gc == "#14382d":
                    def_gc_idx = 4
                elif cur_gc not in ("#111815", "#000000", "#1f2937", "#1e293b", "#14382d"):
                    def_gc_idx = 5

                c_b1, c_b2 = st.columns(2, gap="small")
                with c_b1:
                    picked_cs_label = st.selectbox(
                        "Cell Border Style",
                        list(s_style_map.values()),
                        index=list(s_style_map.values()).index(s_style_map.get(cur_cs, "Classic Continuous Grid")),
                        key="sdk_cell_style_sel",
                    )
                    st.session_state["s_cell_style"] = inv_s_style[picked_cs_label]
                with c_b2:
                    picked_gc_opt = st.selectbox(
                        "Grid Line Color", s_grid_colors, index=def_gc_idx, key="sdk_grid_color_sel"
                    )
                    if picked_gc_opt == "Jet Black (#111815)":
                        st.session_state["s_grid_color"] = "#111815"
                    elif picked_gc_opt == "Pure Black (#000000)":
                        st.session_state["s_grid_color"] = "#000000"
                    elif picked_gc_opt == "Charcoal Slate (#1f2937)":
                        st.session_state["s_grid_color"] = "#1f2937"
                    elif picked_gc_opt == "Navy Blue (#1e293b)":
                        st.session_state["s_grid_color"] = "#1e293b"
                    elif picked_gc_opt == "Forest Green (#14382d)":
                        st.session_state["s_grid_color"] = "#14382d"
                    else:
                        st.session_state["s_grid_color"] = st.text_input(
                            "Custom Grid Hex", cur_gc, key="sdk_grid_hex_in"
                        )

                c_lw1, c_lw2, c_lw3 = st.columns(3, gap="small")
                with c_lw1:
                    st.session_state["s_outer_line_width"] = st.slider(
                        "Outer Border (mm)",
                        min_value=0.5,
                        max_value=3.0,
                        value=float(st.session_state.get("s_outer_line_width", 1.4)),
                        step=0.1,
                        key="sdk_outer_lw_slider",
                    )
                with c_lw2:
                    st.session_state["s_block_line_width"] = st.slider(
                        "Block Lines (mm)",
                        min_value=0.4,
                        max_value=2.5,
                        value=float(st.session_state.get("s_block_line_width", 1.0)),
                        step=0.1,
                        key="sdk_block_lw_slider",
                        help="Thick lines separating 3×3 (or 2×2 / 2×3) regions.",
                    )
                with c_lw3:
                    st.session_state["s_inner_line_width"] = st.slider(
                        "Cell Lines (mm)",
                        min_value=0.1,
                        max_value=1.5,
                        value=float(st.session_state.get("s_inner_line_width", 0.4)),
                        step=0.1,
                        key="sdk_inner_lw_slider",
                        help="Thin divider lines between individual numbers.",
                    )

            with st.expander("Shading & Highlights", expanded=True):
                shading_modes = {
                    "none": "No Shading (Clean White)",
                    "checkerboard": "Checkerboard (Alternating 3×3)",
                    "diagonal": "Diagonal Highlight (Sudoku X)",
                    "windows": "Hyper Windows (Windoku)",
                }
                cur_sm = st.session_state.get("s_shading_mode", "none")
                inv_sm = {v: k for k, v in shading_modes.items()}

                shading_colors = [
                    "Soft Sage Gray (#ecefe9)",
                    "Warm Cream (#f4f3ec)",
                    "Cool Ice Slate (#e2e8f0)",
                    "Subtle Linen (#f5f5f4)",
                    "Custom Hex",
                ]
                cur_sc = st.session_state.get("s_shading_color", "#ecefe9")
                def_sc_idx = 0
                if cur_sc == "#f4f3ec":
                    def_sc_idx = 1
                elif cur_sc == "#e2e8f0":
                    def_sc_idx = 2
                elif cur_sc == "#f5f5f4":
                    def_sc_idx = 3
                elif cur_sc not in ("#ecefe9", "#f4f3ec", "#e2e8f0", "#f5f5f4"):
                    def_sc_idx = 4

                c_sh1, c_sh2 = st.columns(2, gap="small")
                with c_sh1:
                    picked_sm_label = st.selectbox(
                        "Region Shading Mode",
                        list(shading_modes.values()),
                        index=list(shading_modes.keys()).index(cur_sm) if cur_sm in shading_modes else 0,
                        key="sdk_shading_mode_sel",
                        help="Highlight blocks, diagonals, or windows to help solvers navigate the board.",
                    )
                    st.session_state["s_shading_mode"] = inv_sm[picked_sm_label]
                with c_sh2:
                    picked_sc_opt = st.selectbox(
                        "Shading Tone", shading_colors, index=def_sc_idx, key="sdk_shading_color_sel"
                    )
                    if picked_sc_opt == "Soft Sage Gray (#ecefe9)":
                        st.session_state["s_shading_color"] = "#ecefe9"
                    elif picked_sc_opt == "Warm Cream (#f4f3ec)":
                        st.session_state["s_shading_color"] = "#f4f3ec"
                    elif picked_sc_opt == "Cool Ice Slate (#e2e8f0)":
                        st.session_state["s_shading_color"] = "#e2e8f0"
                    elif picked_sc_opt == "Subtle Linen (#f5f5f4)":
                        st.session_state["s_shading_color"] = "#f5f5f4"
                    else:
                        st.session_state["s_shading_color"] = st.text_input(
                            "Custom Shading Hex", cur_sc, key="sdk_shading_hex_in"
                        )

            with st.expander("Typography & Solution Display", expanded=True):
                s_fonts = ["DejaVu Sans Bold", "DejaVu Sans", "DejaVu Serif Bold", "DejaVu Serif", "DejaVu Sans Mono"]
                cur_sf = st.session_state.get("s_clue_font", "DejaVu Sans Bold")
                sf_idx = s_fonts.index(cur_sf) if cur_sf in s_fonts else 0

                c_tp1, c_tp2 = st.columns(2, gap="small")
                with c_tp1:
                    st.session_state["s_font_scale"] = st.slider(
                        "Digit Size (% of cell)",
                        min_value=45,
                        max_value=85,
                        value=int(st.session_state.get("s_font_scale", 64)),
                        step=2,
                        key="sdk_font_scale_slider",
                        help="60-64% = Standard balanced, 76-82% = Senior giant print.",
                    )
                with c_tp2:
                    st.session_state["s_clue_font"] = st.selectbox(
                        "Number Font", s_fonts, index=sf_idx, key="sdk_font_sel"
                    )

                c_cl1, c_cl2 = st.columns(2, gap="small")
                with c_cl1:
                    sol_color_opts = [
                        "Royal Blue (#1d4ed8)",
                        "Emerald Green (#047857)",
                        "Terracotta Red (#b91c1c)",
                        "Slate Gray (#475569)",
                        "Jet Black (#111815)",
                    ]
                    cur_sol_c = st.session_state.get("s_solution_color", "#1d4ed8")
                    sol_c_idx = 0
                    if cur_sol_c == "#047857":
                        sol_c_idx = 1
                    elif cur_sol_c == "#b91c1c":
                        sol_c_idx = 2
                    elif cur_sol_c == "#475569":
                        sol_c_idx = 3
                    elif cur_sol_c == "#111815":
                        sol_c_idx = 4

                    picked_sol_c = st.selectbox(
                        "Solution Color", sol_color_opts, index=sol_c_idx, key="sdk_sol_c_sel"
                    )
                    st.session_state["s_solution_color"] = picked_sol_c.split("(")[1].replace(")", "")

                with c_cl2:
                    sol_mode_map = {"color": "Distinct Color", "circled": "Circled Digits", "plain": "Uniform Black"}
                    cur_sm_mode = st.session_state.get("s_solution_mode", "color")
                    picked_sm_label = st.selectbox(
                        "Solution Marking",
                        list(sol_mode_map.values()),
                        index=list(sol_mode_map.keys()).index(cur_sm_mode) if cur_sm_mode in sol_mode_map else 0,
                        key="sdk_sol_mode_sel",
                    )
                    inv_sm_mode = {v: k for k, v in sol_mode_map.items()}
                    st.session_state["s_solution_mode"] = inv_sm_mode[picked_sm_label]

            with st.expander("KDP Book & Solutions Layout", expanded=False):
                sdk_include_sol_in_same_excel = st.checkbox(
                    "Include solution on the same Excel with the game",
                    value=True,
                    key="sdk_sol_in_same_excel_chk",
                    help="When checked, both puzzle and solution image paths are included in the same Canva Bulk Excel row. When unchecked, solutions are exported to a separate workbook.",
                )

                c_kd1, c_kd2 = st.columns(2, gap="small")
                with c_kd1:
                    sdk_trim_choice = st.selectbox(
                        "KDP Book Trim Size",
                        list(TRIM_SIZES.keys()),
                        index=0,
                        key="sdk_trim_sel",
                        help="Standard 8.5x11 inch activity book or 6x9 pocket puzzle book.",
                    )
                with c_kd2:
                    sdk_solutions_per_page = st.selectbox(
                        "Solutions Per Page",
                        [1, 2, 4, 6, 9],
                        index=3,
                        disabled=sdk_include_sol_in_same_excel,
                        key="sdk_sol_per_page_sel",
                        help="4, 6, or 9 per page saves book page count in KDP solutions section or separate workbook.",
                    )

                c_tg1, c_tg2 = st.columns(2, gap="small")
                with c_tg1:
                    sdk_include_instructions = st.toggle(
                        "Include instructions on puzzle pages", value=True, key="sdk_inst_tog"
                    )
                with c_tg2:
                    sdk_embed_header_in_img = st.toggle(
                        "Embed title inside image",
                        value=False,
                        key="sdk_header_in_img_tog",
                        help="Keep off for Canva Bulk (Canva provides text boxes). Turn on for standalone PNG printing.",
                    )

    # Active Sudoku Style Object
    active_sudoku_style = SimpleNamespace(
        cell_style=st.session_state["s_cell_style"],
        outer_line_width=st.session_state["s_outer_line_width"],
        block_line_width=st.session_state["s_block_line_width"],
        inner_line_width=st.session_state["s_inner_line_width"],
        grid_color=st.session_state["s_grid_color"],
        shading_mode=st.session_state["s_shading_mode"],
        shading_color=st.session_state["s_shading_color"],
        font_scale=st.session_state["s_font_scale"],
        clue_font=st.session_state["s_clue_font"],
        clue_color=st.session_state["s_clue_color"],
        solution_color=st.session_state["s_solution_color"],
        solution_mode=st.session_state["s_solution_mode"],
    )

    with sdk_preview:
        st.markdown('<div class="studio-preview-marker"></div>', unsafe_allow_html=True)
        # Generate batch of Sudoku puzzles
        sudoku_puzzles = get_sudoku_batch(
            selected_sudoku_type.value,
            selected_difficulty.value,
            sdk_count,
            sdk_start_num,
            sdk_seed,
            symmetric_clues,
            wordoku_word_val,
            custom_clues_val,
            sdk_title_template,
        )

        # Clear old export buffers on config change
        sdk_hash = hash(
            f"{selected_sudoku_type.value}_{selected_difficulty.value}_{sdk_count}_{sdk_start_num}_{sdk_seed}_"
            f"{symmetric_clues}_{wordoku_word_val}_{custom_clues_val}_{sdk_title_template}_"
            f"{active_sudoku_style.cell_style}_{active_sudoku_style.outer_line_width}_{active_sudoku_style.block_line_width}_"
            f"{active_sudoku_style.inner_line_width}_{active_sudoku_style.grid_color}_{active_sudoku_style.shading_mode}_"
            f"{active_sudoku_style.font_scale}_{active_sudoku_style.clue_font}_{active_sudoku_style.solution_color}"
        )
        if st.session_state.get("last_sudoku_hash") != sdk_hash:
            st.session_state["last_sudoku_hash"] = sdk_hash
            for k in ["sdk_canva_bytes", "sdk_sol_bytes", "sdk_zip_bytes", "sdk_pdf_bytes"]:
                st.session_state.pop(k, None)

        if sudoku_puzzles:
            # Metrics strip
            sm1, sm2, sm3, sm4, sm5 = st.columns(5, gap="small")
            sm1.metric("Puzzles", len(sudoku_puzzles))
            sm2.metric("Type", TYPE_LABELS[selected_sudoku_type].split(" ")[0])
            sm3.metric("Difficulty", f"{DIFFICULTY_LABELS[selected_difficulty]} {stars}")
            sm4.metric("Grid Size", f"{dim_size} × {dim_size}")
            sm5.metric("Clues / Board", f"{sudoku_puzzles[0].clues_count}")

            sdk_prev_col, sdk_exp_col = st.columns([1.55, 0.75], gap="small")

            with sdk_prev_col:
                sp_nav1, sp_nav2 = st.columns([1.2, 1.2], gap="small")
                with sp_nav2:
                    sdk_view_mode = st.radio(
                        "Sudoku View Mode",
                        ["🔲 Single Puzzle", "🎯 Single Solution", "📑 Solution Page (Book)"],
                        horizontal=True,
                        label_visibility="collapsed",
                        key="sdk_view_mode_rad",
                    )

                if sdk_view_mode == "📑 Solution Page (Book)":
                    total_sdk_sol_pages = max(1, math.ceil(len(sudoku_puzzles) / sdk_solutions_per_page))
                    with sp_nav1:
                        sdk_sol_page_idx = st.selectbox(
                            "Solution Page",
                            range(1, total_sdk_sol_pages + 1),
                            format_func=lambda x: f"Solution Page {x} of {total_sdk_sol_pages} (Puzzles {(x-1)*sdk_solutions_per_page + 1}–{min(len(sudoku_puzzles), x*sdk_solutions_per_page)})",
                            label_visibility="collapsed",
                            key="sdk_sol_page_sel",
                        )

                    start_i = (sdk_sol_page_idx - 1) * sdk_solutions_per_page
                    end_i = start_i + sdk_solutions_per_page
                    sol_slice = sudoku_puzzles[start_i:end_i]
                    page_img = render_sudoku_solution_page_image(
                        sol_slice,
                        active_sudoku_style,
                        sdk_solutions_per_page,
                        sdk_sol_page_idx,
                        total_sdk_sol_pages,
                        dpi=160,
                    )
                    st.image(page_img, width="stretch")
                    st.caption(
                        f"📑 Book Solution Page Preview: showing {len(sol_slice)} of {sdk_solutions_per_page} solutions per page (KDP layout)."
                    )
                else:
                    with sp_nav1:
                        sdk_selected_idx = st.selectbox(
                            "Preview puzzle",
                            range(1, len(sudoku_puzzles) + 1),
                            format_func=lambda x: f"Page {x}: {sudoku_puzzles[x-1].title} ({sudoku_puzzles[x-1].difficulty_label})",
                            label_visibility="collapsed",
                            key="sdk_prev_puz_sel",
                        )

                    active_p = sudoku_puzzles[sdk_selected_idx - 1]
                    sdk_img = render_sudoku_image(
                        active_p,
                        style=active_sudoku_style,
                        cell_mm=12.0,
                        dpi=160,
                        solution=(sdk_view_mode == "🎯 Single Solution"),
                        include_header=sdk_embed_header_in_img,
                    )

                    st.image(sdk_img, width="stretch")

                    if active_p.wordoku_word:
                        st.markdown(
                            f"""
                        <div style="background:#eaf2ed; border:1px solid #cce3d4; border-radius:8px; padding:6px 12px; margin-top:8px; display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:700; color:#184534; font-size:0.82rem;">🔤 Wordoku Anagram:</span>
                            <span style="font-weight:800; color:#184534; letter-spacing:0.18em; font-size:0.95rem;">{active_p.wordoku_word}</span>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px; color:#5c6d66; font-size:0.78rem;">
                        <span>✓ 100% Unique Solution Verified</span>
                        <span>{active_p.clues_count} Initial Clues · {dim_size*dim_size - active_p.clues_count} Empty Cells</span>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            with sdk_exp_col:
                st.markdown('<div class="section-title">Export Sudoku Bundle</div>', unsafe_allow_html=True)
                if sdk_include_sol_in_same_excel:
                    st.caption(
                        f"Book Trim: {sdk_trim_choice.split(' ')[0]} · Solutions in Canva Bulk · 300 DPI print-ready"
                    )
                else:
                    st.caption(
                        f"Book Trim: {sdk_trim_choice.split(' ')[0]} · {sdk_solutions_per_page} solutions/page · 300 DPI print-ready"
                    )

                if st.button("Generate Sudoku Bundle", type="primary", width="stretch", key="sdk_gen_btn"):
                    sdk_bar = st.progress(0, text="Generating Sudoku export bundle...")
                    out_dir_sdk = tempfile.mkdtemp(prefix="sudoku_studio_")

                    canva_p, sol_p, zip_p, pdf_bytes = build_sudoku_workbooks(
                        sudoku_puzzles,
                        out_dir_sdk,
                        solutions_per_page=sdk_solutions_per_page,
                        style=active_sudoku_style,
                        trim_choice=sdk_trim_choice,
                        include_instructions=sdk_include_instructions,
                        include_solution_in_same_excel=sdk_include_sol_in_same_excel,
                        progress_bar=sdk_bar,
                    )

                    st.session_state["sdk_canva_bytes"] = Path(canva_p).read_bytes()
                    st.session_state["sdk_sol_bytes"] = Path(sol_p).read_bytes() if sol_p else None
                    st.session_state["sdk_zip_bytes"] = Path(zip_p).read_bytes()
                    st.session_state["sdk_pdf_bytes"] = pdf_bytes
                    st.session_state["sdk_sol_in_same_excel"] = sdk_include_sol_in_same_excel

                    st.success("Sudoku export bundle ready!")

                if "sdk_canva_bytes" in st.session_state:
                    canva_label = (
                        "📦 Canva Bulk Excel (Game + Solution)"
                        if st.session_state.get("sdk_sol_in_same_excel", True)
                        else "📦 Canva Bulk Excel"
                    )
                    st.download_button(
                        canva_label,
                        st.session_state["sdk_canva_bytes"],
                        "sudoku_canva_bulk.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch",
                        key="sdk_down_canva",
                    )
                    if st.session_state.get("sdk_sol_bytes"):
                        st.download_button(
                            "📑 Solutions Excel",
                            st.session_state["sdk_sol_bytes"],
                            "sudoku_solutions.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch",
                            key="sdk_down_sol",
                        )
                    if st.session_state.get("sdk_pdf_bytes"):
                        st.download_button(
                            "📚 KDP Interior PDF Book",
                            st.session_state["sdk_pdf_bytes"],
                            "sudoku_kdp_interior.pdf",
                            "application/pdf",
                            width="stretch",
                            key="sdk_down_pdf",
                        )
                    st.download_button(
                        "🗂️ Complete Bundle (ZIP)",
                        st.session_state["sdk_zip_bytes"],
                        "sudoku_complete_bundle.zip",
                        "application/zip",
                        width="stretch",
                        key="sdk_down_zip",
                    )

                st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
                render_square_ad()
