"""
AI Meme & Poster Creator — Streamlit app
Step-by-step wizard, same order as the notebook pipeline:
    Font -> Theme -> Tone -> Caption -> Poster

Place this file at the project root ("Aicte project/"), next to fonts/ and output/.
Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

import os
import re
import random
from pathlib import Path
from io import BytesIO

import requests
import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# ============================================================
# SETUP
# ============================================================

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")

FONTS_DIR = BASE_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FONT_OPTIONS = {
    "Anton": "Anton-Regular.ttf",
    "Poppins Regular": "Poppins-Regular.ttf",
    "Poppins Medium": "Poppins-Medium.ttf",
    "Poppins SemiBold": "Poppins-SemiBold.ttf",
    "Poppins Bold": "Poppins-Bold.ttf",
    "Poppins ExtraBold": "Poppins-ExtraBold.ttf",
    "Poppins Black": "Poppins-Black.ttf",
    "Poppins Light": "Poppins-Light.ttf",
    "Poppins Italic": "Poppins-Italic.ttf",
    "Montserrat": "Montserrat-VariableFont_wght.ttf",
    "Montserrat Italic": "Montserrat-Italic-VariableFont_wght.ttf",
    "Inter": "Inter-VariableFont_opsz,wght.ttf",
    "Inter Italic": "Inter-Italic-VariableFont_opsz,wght.ttf",
}

THEME_OPTIONS = [
    "Mother's Day", "Friendship", "Love", "Birthday", "Motivation",
    "College", "Exam Stress", "Travel", "Nature", "Fitness",
    "Food", "Work", "Sad", "Funny",
]

THEME_QUERIES = {
    "Mother's Day": "mother daughter family love flowers",
    "Friendship": "friends friendship happiness",
    "Love": "love couple romantic",
    "Birthday": "birthday celebration party",
    "Motivation": "success achievement inspiration",
    "College": "college students campus",
    "Exam Stress": "student studying books exam",
    "Travel": "travel adventure landscape",
    "Nature": "nature peaceful landscape",
    "Fitness": "fitness workout gym",
    "Food": "food restaurant aesthetic",
    "Work": "office professional workplace",
    "Sad": "sad lonely emotional",
    "Funny": "funny people happiness",
}

# Multi-color per theme — accent + soft background tint used across the UI
THEME_COLORS = {
    "Mother's Day":  {"accent": "#D4537E", "soft": "#FBEAF0", "text": "#4B1528"},
    "Friendship":    {"accent": "#D85A30", "soft": "#FAECE7", "text": "#4A1B0C"},
    "Love":          {"accent": "#D4537E", "soft": "#FBEAF0", "text": "#4B1528"},
    "Birthday":      {"accent": "#EF9F27", "soft": "#FAEEDA", "text": "#412402"},
    "Motivation":    {"accent": "#EF9F27", "soft": "#FAEEDA", "text": "#412402"},
    "College":       {"accent": "#378ADD", "soft": "#E6F1FB", "text": "#042C53"},
    "Exam Stress":   {"accent": "#7F77DD", "soft": "#EEEDFE", "text": "#26215C"},
    "Travel":        {"accent": "#1D9E75", "soft": "#E1F5EE", "text": "#04342C"},
    "Nature":        {"accent": "#1D9E75", "soft": "#E1F5EE", "text": "#04342C"},
    "Fitness":       {"accent": "#E24B4A", "soft": "#FCEBEB", "text": "#501313"},
    "Food":          {"accent": "#D85A30", "soft": "#FAECE7", "text": "#4A1B0C"},
    "Work":          {"accent": "#888780", "soft": "#F1EFE8", "text": "#2C2C2A"},
    "Sad":           {"accent": "#7F77DD", "soft": "#EEEDFE", "text": "#26215C"},
    "Funny":         {"accent": "#D4537E", "soft": "#FBEAF0", "text": "#4B1528"},
}

TONE_INSTRUCTIONS = {
    "funny": '''You are a witty internet meme writer for Gen-Z college students.
    Avoid cliches like "coffee", "sleep deprivation", "brain marathon" - be original and unexpected.

    Caption 1: use an absurd exaggeration.
    Caption 2: use a sarcastic one-liner.
    Caption 3: use an unexpected/ironic twist.

    Vibe/energy to match (don't copy these words literally):
    - "Delulu is the only solulu for this physics exam."
    - "The plan: start studying at 6 PM. The reality: staring at the ceiling at 4 AM wondering if manifestation counts as extra credit."
    - "Confidence before opening the exam paper: main character energy. Confidence 30 seconds later: NPC behavior, staring at question one like it's ancient Sumerian."
    - "My relationship status: me negotiating with failing to lock in. We've been toxic for three semesters."''',
    "emotional": "You are a heartfelt, sincere writer. Write something touching and genuine, evoking real emotion.",
    "sad": "You are a reflective, melancholic writer. Write something poignant and moving, without being over-dramatic.",
    "patriotic": "You are an inspiring, patriotic writer. Write something proud, motivational, and respectful.",
    "horror": "You are a creepy, unsettling writer. Write something eerie and spine-chilling, building tension in few words.",
}

CAPTION_ICONS = ["\U0001F525", "\U0001F60F", "\U0001F4A1"]  # exaggeration, sarcastic, ironic twist

PUNCT_FIXES = {
    "\u2014": "-", "\u2013": "-", "\u2011": "-",
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u2026": "...",
}

STEPS = ["Font", "Theme", "Tone", "Caption", "Poster"]

# ============================================================
# CORE FUNCTIONS
# ============================================================

def generate_captions(theme: str, tone: str, asset_type: str = "meme") -> list[str]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    persona = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["funny"])

    prompt = f'''
You are generating a caption for a {asset_type}.

IMPORTANT RULES:

THEME: "{theme}"
TONE: "{tone}"

The THEME is the main subject of the caption.
The TONE controls only the writing style.

Never change the theme.
Never replace the theme with another subject.
Every caption MUST clearly relate to "{theme}".

{persona}

Write exactly 3 different {asset_type} captions about "{theme}".

Maximum 15 words per caption.

Do NOT write a generic quote.
Do NOT introduce an unrelated topic.
Do NOT mention the background image.
Do NOT mention image generation.

Output ONLY the 3 numbered captions:

1. ...
2. ...
3. ...
'''

    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 1.0,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]

    if "</think>" in raw:
        raw = raw.split("</think>")[-1]

    cleaned = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        text = re.sub(r"^\d+\.\s*", "", line).strip()
        text = text.replace("Wi\u2011Fi", "Wi-Fi")
        for bad, good in PUNCT_FIXES.items():
            text = text.replace(bad, good)
        if text:
            cleaned.append(text)

    return cleaned[:3] if cleaned else ["Could not generate a caption. Try again."]


@st.cache_data(show_spinner=False)
def fetch_background(theme: str) -> bytes:
    if not UNSPLASH_API_KEY:
        raise ValueError("UNSPLASH_API_KEY not found in .env")

    query = THEME_QUERIES.get(theme, theme)

    response = requests.get(
        "https://api.unsplash.com/search/photos",
        params={
            "client_id": UNSPLASH_API_KEY,
            "query": query,
            "per_page": 30,
            "orientation": "squarish",
            "content_filter": "high",
        },
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()["results"]

    if not results:
        raise ValueError(f"No images found for theme: {theme}")

    pick = random.choice(results)
    img_response = requests.get(pick["urls"]["regular"], timeout=30)
    img_response.raise_for_status()
    return img_response.content


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = word if not current else current + " " + word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_poster(background_bytes: bytes, caption: str, font_path: Path) -> Image.Image:
    image = Image.open(BytesIO(background_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    font_size = int(width * 0.085)
    font = ImageFont.truetype(str(font_path), font_size)
    max_text_width = int(width * 0.82)

    lines = wrap_text(draw, caption, font, max_text_width)
    while len(lines) > 5 and font_size > 35:
        font_size -= 4
        font = ImageFont.truetype(str(font_path), font_size)
        lines = wrap_text(draw, caption, font, max_text_width)

    spacing = int(font_size * 0.25)
    line_heights = [draw.textbbox((0, 0), l, font=font)[3] - draw.textbbox((0, 0), l, font=font)[1] for l in lines]
    total_text_height = sum(line_heights) + spacing * (len(lines) - 1)
    y_start = (height - total_text_height) // 2

    pad = int(font_size * 0.6)
    box_top = max(0, y_start - pad)
    box_bottom = min(height, y_start + total_text_height + pad)
    text_box = (0, box_top, width, box_bottom)

    plate = image.crop(text_box).convert("RGB")
    plate = plate.filter(ImageFilter.GaussianBlur(radius=max(6, font_size // 10)))
    plate = ImageEnhance.Brightness(plate).enhance(0.55)
    plate = plate.convert("RGBA")

    mask = Image.new("L", plate.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    fade = max(20, pad // 2)
    for row in range(plate.size[1]):
        if row < fade:
            alpha = int(235 * (row / fade))
        elif row > plate.size[1] - fade:
            alpha = int(235 * ((plate.size[1] - row) / fade))
        else:
            alpha = 235
        mask_draw.line([(0, row), (plate.size[0], row)], fill=alpha)
    plate.putalpha(mask)

    image.alpha_composite(plate, dest=(0, box_top))
    draw = ImageDraw.Draw(image)

    region = image.convert("RGB").crop(text_box).convert("L")
    pixels = list(region.getdata())
    brightness = sum(pixels) / len(pixels) if pixels else 128
    text_fill, outline_fill = ("black", "white") if brightness > 150 else ("white", "black")

    shadow_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    y = y_start
    for line, lh in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        offset = max(2, font_size // 30)
        shadow_draw.text((x + offset, y + offset), line, font=font, fill=(0, 0, 0, 180))
        y += lh + spacing
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(3, font_size // 25)))
    image.alpha_composite(shadow_layer)
    draw = ImageDraw.Draw(image)

    y = y_start
    for line, lh in zip(lines, line_heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (width - tw) // 2
        draw.text(
            (x, y), line, font=font, fill=text_fill,
            stroke_width=max(1, font_size // 55), stroke_fill=outline_fill,
        )
        y += lh + spacing

    return image.convert("RGB")


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "step": 1,
    "font_name": "Poppins Bold",
    "theme_name": "Friendship",
    "tone_name": "funny",
    "captions": [],
    "selected_caption": None,
    "background_bytes": None,
    "poster": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def go_next():
    st.session_state.step = min(5, st.session_state.step + 1)


def go_back():
    st.session_state.step = max(1, st.session_state.step - 1)


# ============================================================
# STYLING (theme-reactive) — "sticker sheet / print desk" look
#
# The product makes posters and meme stickers, so the UI borrows from
# that physical medium: halftone-dot paper, die-cut sticker cards with
# hard offset shadows (no blur/glow), a bold poster-lettering wordmark,
# dashed cut-lines between steps, and a taped-down selected caption.
# ============================================================

def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert '#RRGGBB' -> 'rgba(r, g, b, alpha)' for CSS tinting."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def mix_hex(hex_a: str, hex_b: str, weight: float) -> str:
    """Blend two '#RRGGBB' colors; weight is hex_a's share (0-1)."""
    a, b = hex_a.lstrip("#"), hex_b.lstrip("#")
    ar, ag, ab = (int(a[i:i + 2], 16) for i in (0, 2, 4))
    br, bg, bb = (int(b[i:i + 2], 16) for i in (0, 2, 4))
    r = round(ar * weight + br * (1 - weight))
    g = round(ag * weight + bg * (1 - weight))
    bl = round(ab * weight + bb * (1 - weight))
    return f"#{r:02x}{g:02x}{bl:02x}"


colors = THEME_COLORS[st.session_state.theme_name]
accent = colors["accent"]
ink = mix_hex(accent, "#0B0A08", 0.18)              # near-black, faintly theme-tinted
paper = "#FFFDF6"                                    # card / caption-card surface
page_bg = mix_hex(accent, "#FFFFFF", 0.09)           # pale theme-tinted paper
dot_rgba = hex_to_rgba(accent, 0.30)                 # halftone dots
accent_soft = hex_to_rgba(accent, 0.20)
ink_soft = hex_to_rgba(ink, 0.30)
tape_rgba = hex_to_rgba(accent, 0.55)

TILTS = [-1.4, 1.1, -0.7, 1.3, -1.0]  # alternating sticker rotation

st.set_page_config(page_title="AI Meme & Poster Creator", page_icon="\U0001F4CC", layout="centered")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bungee&family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {{
    font-family: 'Inter', sans-serif;
    color: {ink};
}}

[data-testid="stAppViewContainer"] {{
    background-color: {page_bg};
    background-image: radial-gradient({dot_rgba} 1.6px, transparent 1.6px);
    background-size: 18px 18px;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

footer {{ visibility: hidden; }}

.block-container {{
    max-width: 620px;
    margin: 2rem auto 3rem auto;
    padding: 2.5rem 2.4rem 2.3rem 2.4rem;
    background: {paper};
    border: 3px solid {ink};
    border-radius: 22px;
    box-shadow: 9px 9px 0 {ink};
}}

h1, h2, h3 {{
    font-family: 'Space Grotesk', sans-serif !important;
    color: {ink} !important;
    font-weight: 700 !important;
    letter-spacing: -0.01em;
}}

p, span, label, .stMarkdown, .stCaption {{
    font-family: 'Inter', sans-serif;
}}

.hero-eyebrow {{
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {paper};
    background: {ink};
    padding: 3px 9px;
    border-radius: 4px;
    transform: rotate(-2deg);
    margin-bottom: 10px;
}}

.hero-title {{
    font-family: 'Bungee', sans-serif;
    font-size: 30px;
    line-height: 1.25;
    font-weight: 400;
    color: {accent};
    -webkit-text-stroke: 1px {ink};
    text-shadow: 3px 3px 0 {ink};
    margin: 4px 0 10px 0;
}}

.hero-sub {{
    font-size: 13.5px;
    color: {hex_to_rgba(ink, 0.65)};
    margin-bottom: 1.6rem;
}}

div.stButton > button[kind="primary"] {{
    background: {accent};
    color: {ink};
    border: 2.5px solid {ink};
    border-radius: 12px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    padding: 0.6rem 1rem;
    box-shadow: 4px 4px 0 {ink};
    transition: transform 0.1s ease, box-shadow 0.1s ease;
}}
div.stButton > button[kind="primary"]:hover {{
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0 {ink};
}}
div.stButton > button[kind="primary"]:active {{
    transform: translate(4px, 4px);
    box-shadow: 0 0 0 {ink};
}}
div.stButton > button:not([kind="primary"]) {{
    background: {paper};
    color: {ink};
    border: 2px solid {ink};
    border-radius: 12px;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    box-shadow: 3px 3px 0 {ink_soft};
    transition: transform 0.1s ease, box-shadow 0.1s ease;
}}
div.stButton > button:not([kind="primary"]):hover {{
    transform: translate(1.5px, 1.5px);
    box-shadow: 1.5px 1.5px 0 {ink_soft};
}}
div.stDownloadButton > button {{
    background: {accent};
    color: {ink};
    border: 2.5px solid {ink};
    border-radius: 12px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    box-shadow: 4px 4px 0 {ink};
    transition: transform 0.1s ease, box-shadow 0.1s ease;
}}
div.stDownloadButton > button:hover {{
    transform: translate(2px, 2px);
    box-shadow: 2px 2px 0 {ink};
}}

div[data-baseweb="select"] > div {{
    background: {paper} !important;
    border: 2px solid {ink} !important;
    border-radius: 12px !important;
    color: {ink} !important;
}}
div[data-baseweb="select"] span {{ color: {ink} !important; }}
div[data-baseweb="select"]:focus-within > div {{
    border-color: {accent} !important;
    box-shadow: 3px 3px 0 {ink} !important;
}}
ul[data-baseweb="menu"] {{
    background: {paper} !important;
    border: 2px solid {ink} !important;
}}
li[data-baseweb="menu-item"]:hover {{
    background: {accent_soft} !important;
}}

[data-testid="stAlert"] {{
    background: {paper};
    border-radius: 12px;
    border: 2px solid {ink};
    box-shadow: 3px 3px 0 {ink_soft};
}}

[data-testid="stImage"] img {{
    border: 10px solid {paper};
    border-bottom-width: 44px;
    box-shadow: 6px 6px 0 {ink};
    transform: rotate(-1deg);
    display: block;
}}

.step-pill {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 12px;
    font-weight: 700;
    margin-right: 6px;
    border: 2px solid {ink};
}}
.step-pill-active {{
    background: {accent};
    color: {ink};
    transform: rotate(-4deg);
}}
.step-pill-inactive {{
    background: {paper};
    color: {hex_to_rgba(ink, 0.4)};
    border-color: {hex_to_rgba(ink, 0.35)};
}}
.caption-card {{
    position: relative;
    background: {paper};
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 14px;
    font-size: 15px;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
    border: 2px solid {hex_to_rgba(ink, 0.3)};
    box-shadow: 3px 3px 0 {hex_to_rgba(ink, 0.18)};
}}
.caption-card-selected {{
    border: 2px solid {ink};
    box-shadow: 4px 4px 0 {accent};
}}
.tape {{
    position: absolute;
    top: -11px;
    left: 50%;
    width: 46px;
    height: 18px;
    background: {tape_rgba};
    border: 1.5px solid {ink};
    border-radius: 2px;
    transform: translateX(-50%) rotate(-3deg);
}}
.theme-color-dot {{
    display: inline-block;
    width: 13px;
    height: 13px;
    border-radius: 3px;
    margin-right: 4px;
    border: 1.5px solid {ink};
}}

@media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; animation: none !important; }}
}}
</style>
""", unsafe_allow_html=True)

if not GROQ_API_KEY or not UNSPLASH_API_KEY:
    st.error("Missing GROQ_API_KEY or UNSPLASH_API_KEY — check your .env file.")
    st.stop()

# ============================================================
# HEADER: stepper (Font -> Theme -> Tone -> Caption -> Poster)
# ============================================================

st.markdown(
    """
    <div class="hero-eyebrow">\U0001F4CC Sticker &amp; poster desk</div>
    <div class="hero-title">AI Meme &amp; Poster Creator</div>
    <div class="hero-sub">Pick a vibe, let the model write the punchline, print a poster in five steps.</div>
    """,
    unsafe_allow_html=True,
)

stepper_html = '<div style="display:flex; align-items:center; gap:4px; margin-bottom: 1.5rem;">'
for i, label in enumerate(STEPS, start=1):
    active = i <= st.session_state.step
    pill_class = "step-pill-active" if active else "step-pill-inactive"
    stepper_html += '<div style="display:flex; align-items:center; gap:4px; flex:1;">'
    stepper_html += f'<span class="step-pill {pill_class}">{i}</span>'
    weight = "600" if i == st.session_state.step else "400"
    stepper_html += f'<span style="font-size:12px; font-weight:{weight};">{label}</span></div>'
    if i < len(STEPS):
        line_color = colors["accent"] if i < st.session_state.step else hex_to_rgba(ink, 0.25)
        stepper_html += (
            f'<div style="height:2px; flex:1; margin:0 2px; '
            f'background-image:linear-gradient(to right, {line_color} 55%, transparent 0%); '
            f'background-size:7px 2px; background-repeat:repeat-x;"></div>'
        )
stepper_html += "</div>"
st.markdown(stepper_html, unsafe_allow_html=True)

# ============================================================
# STEP 1 — FONT
# ============================================================

if st.session_state.step == 1:
    st.subheader("Choose a font")
    st.session_state.font_name = st.selectbox(
        "Font", list(FONT_OPTIONS.keys()),
        index=list(FONT_OPTIONS.keys()).index(st.session_state.font_name),
        label_visibility="collapsed",
    )
    st.button("Next \u2192", type="primary", on_click=go_next, use_container_width=True)

# ============================================================
# STEP 2 — THEME
# ============================================================

elif st.session_state.step == 2:
    st.subheader("Choose a theme")
    dots = " ".join(
        f'<span class="theme-color-dot" style="background:{THEME_COLORS[t]["accent"]}"></span>'
        for t in THEME_OPTIONS[:6]
    )
    st.markdown(
        f"<p style='font-size:12px; color:{hex_to_rgba(ink, 0.6)}; margin-bottom:0.75rem;'>{dots} colors change with your pick</p>",
        unsafe_allow_html=True,
    )
    st.session_state.theme_name = st.selectbox(
        "Theme", THEME_OPTIONS,
        index=THEME_OPTIONS.index(st.session_state.theme_name),
        label_visibility="collapsed",
    )
    col1, col2 = st.columns(2)
    col1.button("\u2190 Back", on_click=go_back, use_container_width=True)
    col2.button("Next \u2192", type="primary", on_click=go_next, use_container_width=True)

# ============================================================
# STEP 3 — TONE
# ============================================================

elif st.session_state.step == 3:
    st.subheader("Choose a tone")
    st.session_state.tone_name = st.selectbox(
        "Tone", list(TONE_INSTRUCTIONS.keys()),
        index=list(TONE_INSTRUCTIONS.keys()).index(st.session_state.tone_name),
        label_visibility="collapsed",
    )
    col1, col2 = st.columns(2)
    col1.button("\u2190 Back", on_click=go_back, use_container_width=True)
    if col2.button("\u2728 Generate captions", type="primary", use_container_width=True):
        with st.spinner("Asking the AI for captions..."):
            st.session_state.captions = generate_captions(
                st.session_state.theme_name, st.session_state.tone_name
            )
        with st.spinner("Finding a background image..."):
            st.session_state.background_bytes = fetch_background(st.session_state.theme_name)
        st.session_state.selected_caption = st.session_state.captions[0]
        go_next()
        st.rerun()

# ============================================================
# STEP 4 — CAPTION (big cards, icon per vibe, theme-colored)
# ============================================================

elif st.session_state.step == 4:
    st.subheader("Pick your caption")
    st.caption(
        f"Font: {st.session_state.font_name} \u00b7 Theme: {st.session_state.theme_name} \u00b7 Tone: {st.session_state.tone_name}"
    )

    if st.session_state.selected_caption is None and st.session_state.captions:
        st.session_state.selected_caption = st.session_state.captions[0]

    for i, cap in enumerate(st.session_state.captions):
        icon = CAPTION_ICONS[i % len(CAPTION_ICONS)]
        is_selected = cap == st.session_state.selected_caption
        card_class = "caption-card caption-card-selected" if is_selected else "caption-card"
        tilt = TILTS[i % len(TILTS)]
        tape = '<span class="tape"></span>' if is_selected else ""

        card_col, btn_col = st.columns([6, 1])
        with card_col:
            st.markdown(
                f'<div class="{card_class}" style="transform:rotate({tilt}deg);">'
                f'{tape}{icon} &nbsp; {cap}</div>',
                unsafe_allow_html=True,
            )
        with btn_col:
            if st.button("Pick", key=f"pick_{i}", use_container_width=True):
                st.session_state.selected_caption = cap
                st.rerun()

    col1, col2 = st.columns(2)
    col1.button("\u2190 Back", on_click=go_back, use_container_width=True)
    if col2.button("Create poster \u2192", type="primary", use_container_width=True):
        font_path = FONTS_DIR / FONT_OPTIONS[st.session_state.font_name]
        if not font_path.exists():
            st.error(f"Font file not found: {font_path}")
        else:
            with st.spinner("Blending your poster..."):
                st.session_state.poster = build_poster(
                    st.session_state.background_bytes,
                    st.session_state.selected_caption,
                    font_path,
                )
            go_next()
            st.rerun()

# ============================================================
# STEP 5 — POSTER
# ============================================================

elif st.session_state.step == 5:
    st.subheader("Your poster")
    if st.session_state.poster is not None:
        st.image(st.session_state.poster, use_container_width=True)

        buf = BytesIO()
        st.session_state.poster.save(buf, format="JPEG", quality=95)
        st.download_button(
            "\u2b07\ufe0f Download poster",
            data=buf.getvalue(),
            file_name=f"{st.session_state.theme_name.replace(' ', '_').lower()}_poster.jpg",
            mime="image/jpeg",
            use_container_width=True,
        )

        save_path = OUTPUT_DIR / "final_poster.jpg"
        st.session_state.poster.save(save_path, quality=95)
    else:
        st.warning("No poster yet — go back and create one.")

    col1, col2 = st.columns(2)
    col1.button("\u2190 Back", on_click=go_back, use_container_width=True)
    if col2.button("\U0001F501 Start over", use_container_width=True):
        for key, val in defaults.items():
            st.session_state[key] = val
        st.rerun()
