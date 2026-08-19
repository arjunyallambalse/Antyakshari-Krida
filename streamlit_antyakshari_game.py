#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import os
import tempfile
from textwrap import dedent

import streamlit as st

from antyakshari_engine import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_MEDIUM,
    RULE_SET_A,
    RULE_SET_B,
    AntyakshariEngine,
    available_corpus_files,
    infer_first_letter,
    infer_last_letter_and_swara,
    normalize_devanagari_text,
)
from sanskrit_asr import transcribe_audio
from yourvoic_tts import generate_speech, tts_available


MAX_CHANCES = 3

VERSE_MODE_DATASET = "Within Dataset Only"
VERSE_MODE_OPEN = "Allow Other Verses"

VYOMA_BLUE = "#0B5FA5"
VYOMA_BLUE_DARK = "#083C6D"
VYOMA_GOLD = "#E7B73C"
VYOMA_LIGHT = "#EAF4FF"

VYOMA_LOGO_URL = "https://avatars.githubusercontent.com/u/108797006?v=4"
VYOMA_REPO_URL = "https://github.com/Vyoma-Linguistic-Labs/Antyakshari-Krida"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Sanskrit Antyakshari Krida",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    dedent(
        f"""
        <style>
        .stApp {{
            background: #F5F8FC;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #10243D 0%, #1A2D45 100%);
        }}

        [data-testid="stSidebar"] * {{
            color: white !important;
        }}

        .block-container {{
            padding-top: 1.8rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }}

        .hero-card {{
            background: linear-gradient(135deg, {VYOMA_BLUE_DARK} 0%, {VYOMA_BLUE} 100%);
            color: white;
            border-radius: 22px;
            padding: 26px 28px 24px 28px;
            box-shadow: 0 14px 28px rgba(8,60,109,.15);
            border-bottom: 5px solid {VYOMA_GOLD};
            position: relative;
            margin-bottom: 22px;
        }}

        .hero-badge {{
            position: absolute;
            top: 16px;
            right: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,.14);
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 12px;
            color: #FFFFFF;
        }}

        .hero-badge img {{
            width: 22px;
            height: 22px;
            border-radius: 50%;
        }}

        .hero-title {{
            margin: 0;
            font-size: 2.2rem;
            font-weight: 800;
            color: #FFFFFF !important;
            letter-spacing: .2px;
        }}

        .hero-subtitle {{
            margin-top: 10px;
            font-size: 1rem;
            color: #E7F1FB !important;
            line-height: 1.55;
            max-width: 900px;
        }}

        .glass-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 16px;
        }}

        .glass-chip {{
            background: rgba(255,255,255,.14);
            color: white;
            padding: 9px 13px;
            border-radius: 12px;
            font-size: 13px;
            border: 1px solid rgba(255,255,255,.12);
        }}

        .panel-card {{
            background: white;
            border-radius: 18px;
            padding: 20px 20px 18px 20px;
            box-shadow: 0 10px 26px rgba(17,24,39,.06);
            border: 1px solid #E5ECF4;
        }}

        .panel-title {{
            margin: 0 0 10px 0;
            font-size: 1.55rem;
            font-weight: 750;
            color: #102A43 !important;
        }}

        .target-card {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F9FBFE 100%);
            border: 2px solid #CFE0F3;
            border-radius: 18px;
            padding: 22px;
            text-align: center;
            box-shadow: 0 6px 18px rgba(15,23,42,.05);
            margin-bottom: 18px;
        }}

        .target-label {{
            color: #5C6F82;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .target-akshara {{
            font-size: 3.6rem;
            font-weight: 850;
            color: {VYOMA_BLUE_DARK};
            line-height: 1.1;
            margin: 10px 0 8px 0;
        }}

        .target-note {{
            font-size: 15px;
            color: #334E68;
            margin-top: 8px;
        }}

        .mini-note {{
            color: #5C6F82;
            font-size: 13px;
            margin-top: 4px;
        }}

        .history-card {{
            background: white;
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 10px 26px rgba(17,24,39,.06);
            border: 1px solid #E5ECF4;
        }}

        .move-card {{
            background: #FFFFFF;
            border-radius: 14px;
            padding: 14px 15px;
            margin-bottom: 12px;
            box-shadow: 0 4px 14px rgba(17,24,39,.05);
            border: 1px solid #EEF2F7;
        }}

        .move-player {{
            border-left: 5px solid {VYOMA_BLUE};
        }}

        .move-computer {{
            border-left: 5px solid #E2872A;
        }}

        .move-system {{
            border-left: 5px solid #6B7C93;
            background: #FAFBFD;
        }}

        .move-speaker {{
            font-weight: 800;
            color: #102A43;
            margin-bottom: 6px;
        }}

        .move-text {{
            font-size: 1.06rem;
            color: #243B53;
            line-height: 1.55;
        }}

        .move-meta {{
            font-size: 12px;
            color: #6B7C93;
            margin-top: 8px;
        }}

        .section-divider {{
            height: 1px;
            background: #E5ECF4;
            margin: 18px 0;
            border-radius: 999px;
        }}

        .footer-credit {{
            margin-top: 28px;
            padding-top: 14px;
            border-top: 1px solid #D8E2EC;
            text-align: center;
            color: #6B7C93;
            font-size: 12px;
        }}

        .footer-credit img {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            vertical-align: middle;
            margin-right: 6px;
        }}

        .stButton > button {{
            border-radius: 12px !important;
            font-weight: 700 !important;
            padding-top: .55rem !important;
            padding-bottom: .55rem !important;
        }}

        .stTextArea textarea {{
            border-radius: 14px !important;
        }}

        .stAudioInput {{
            border-radius: 14px !important;
        }}

        div[data-testid="stMetric"] {{
            background: rgba(255,255,255,.07);
            border-radius: 12px;
            padding: 10px 10px 8px 10px;
        }}

        div[data-testid="stMetricLabel"] {{
            color: white !important;
            font-weight: 700;
        }}

        div[data-testid="stMetricValue"] {{
            color: white !important;
        }}

        .main-metric-wrap div[data-testid="stMetric"] {{
            background: #F3F8FE;
        }}

        .main-metric-wrap div[data-testid="stMetricLabel"] {{
            color: #486581 !important;
        }}

        .main-metric-wrap div[data-testid="stMetricValue"] {{
            color: #102A43 !important;
        }}
        </style>
        """
    ),
    unsafe_allow_html=True,
)


# ============================================================
# STATE
# ============================================================

def init_state() -> None:
    defaults = {
        "history": [],
        "used_ids": set(),
        "used_custom_texts": set(),
        "expected_letter": None,
        "free_start_allowed": True,
        "player_score": 0,
        "computer_score": 0,
        "chances_lost": 0,
        "game_over": False,
        "last_audio_digest": "",
        "verse_input": "",
        "pending_clear_input": False,
        "audio_nonce": 0,
        "last_tts_path": "",
        "last_error": "",
        "active_corpus": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_game() -> None:
    st.session_state.history = []
    st.session_state.used_ids = set()
    st.session_state.used_custom_texts = set()
    st.session_state.expected_letter = None
    st.session_state.free_start_allowed = True
    st.session_state.player_score = 0
    st.session_state.computer_score = 0
    st.session_state.chances_lost = 0
    st.session_state.game_over = False
    st.session_state.last_audio_digest = ""
    st.session_state.verse_input = ""
    st.session_state.pending_clear_input = False
    st.session_state.audio_nonce += 1
    st.session_state.last_tts_path = ""
    st.session_state.last_error = ""


def clear_input() -> None:
    st.session_state.verse_input = ""
    st.session_state.last_audio_digest = ""
    st.session_state.last_error = ""
    st.session_state.audio_nonce += 1


init_state()


# ============================================================
# ENGINE
# ============================================================

@st.cache_resource(show_spinner=False)
def load_engine(csv_path: str) -> AntyakshariEngine:
    return AntyakshariEngine(csv_path)


def verse_reference(entry) -> str:
    chapter = str(entry.chapter or "").strip()
    verse_number = str(entry.verse_number or "").strip()

    if chapter and verse_number:
        return f"{chapter}.{verse_number}"
    if verse_number:
        return verse_number
    return str(entry.verse_id)


# ============================================================
# HISTORY HELPERS
# ============================================================

def log_move(
    speaker: str,
    text: str,
    reference: str = "",
    note: str = "",
    required_letter: str = "",
) -> None:
    st.session_state.history.append(
        {
            "speaker": speaker,
            "text": text,
            "reference": reference,
            "note": note,
            "required_letter": required_letter,
        }
    )


def render_history() -> None:
    if not st.session_state.history:
        st.info("No moves yet. Record or type a Sanskrit verse to begin.")
        return

    for move in reversed(st.session_state.history):
        speaker = move["speaker"]

        if speaker == "Player":
            cls = "move-player"
            label = "👤 Player"
        elif speaker == "Computer":
            cls = "move-computer"
            label = "🤖 Computer"
        else:
            cls = "move-system"
            label = "ℹ️ System"

        meta = []
        if move.get("reference"):
            meta.append(f"Ref: {move['reference']}")
        if move.get("required_letter"):
            meta.append(f"Required: {move['required_letter']}")
        if move.get("note"):
            meta.append(move["note"])

        meta_text = " · ".join(meta)

        st.markdown(
            dedent(
                f"""
                <div class="move-card {cls}">
                    <div class="move-speaker">{label}</div>
                    <div class="move-text">{move["text"]}</div>
                    <div class="move-meta">{meta_text}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )


# ============================================================
# GAME HELPERS
# ============================================================

def penalize(message: str) -> None:
    st.session_state.chances_lost += 1
    st.session_state.last_error = message

    log_move(
        "System",
        message,
        note="Invalid player move",
    )

    if st.session_state.chances_lost >= MAX_CHANCES:
        st.session_state.game_over = True


def update_requirement(
    engine: AntyakshariEngine,
    bot_entry,
    rule_set: str,
) -> None:
    requirement = engine.next_required_start_for_entry(
        bot_entry,
        st.session_state.used_ids,
        rule_set=rule_set,
    )

    st.session_state.expected_letter = requirement["required_letter"]
    st.session_state.free_start_allowed = bool(requirement["free_start_allowed"])

    if st.session_state.free_start_allowed:
        log_move(
            "System",
            "No continuation exists in the selected corpus. You may start with any unused verse.",
            note=str(requirement["rule_applied"]),
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    dedent(
        f"""
        <div class="hero-card">
            <div class="hero-badge">
                <img src="{VYOMA_LOGO_URL}" alt="Vyoma">
                <span>Inspired by Vyoma Linguistic Labs</span>
            </div>

            <div class="hero-title">🕉️ संस्कृत-अन्त्याक्षरी क्रीडा</div>
            <div class="hero-subtitle">
                Interactive Sanskrit Antyakshari with
                <strong>Su-śrotā speech recognition</strong>,
                real corpus-based continuation,
                and optional <strong>Vāgdhenu</strong> computer voice.
            </div>

            <div class="glass-row">
                <div class="glass-chip">🎙️ Speak or type a verse</div>
                <div class="glass-chip">🧠 Real Antyakshari engine</div>
                <div class="glass-chip">📚 Corpus or open-verse mode</div>
                <div class="glass-chip">🔁 Rule A / Rule B support</div>
            </div>
        </div>
        """
    ),
    unsafe_allow_html=True,
)


# ============================================================
# CORPUS DISCOVERY
# ============================================================

available_corpora = available_corpus_files(".")

if not available_corpora:
    st.error("No supported corpus CSV files were found.")
    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Game Settings")

    corpus_label = st.selectbox(
        "Corpus",
        list(available_corpora.keys()),
    )
    corpus_path = available_corpora[corpus_label]

    rule_set = st.radio(
        "Rule Set",
        [RULE_SET_A, RULE_SET_B],
        horizontal=True,
        help=(
            "Rule A = strict last-letter continuation. "
            "Rule B = strict continuation first, then swara fallback if needed."
        ),
    )

    verse_mode = st.radio(
        "Verse Source",
        [VERSE_MODE_DATASET, VERSE_MODE_OPEN],
        help=(
            "Within Dataset Only verifies your verse against the selected corpus. "
            "Allow Other Verses preserves the original Vyoma-style open Antyakshari option."
        ),
    )

    difficulty = st.selectbox(
        "Computer Difficulty",
        [DIFFICULTY_HARD, DIFFICULTY_MEDIUM, DIFFICULTY_EASY],
    )

    min_similarity = st.slider(
        "Verse match sensitivity",
        min_value=0.45,
        max_value=0.90,
        value=0.60,
        step=0.05,
        help="Higher values require a closer ASR/text match to a verse in the selected corpus.",
    )

    st.divider()
    st.subheader("📊 Game Tally")

    score_a, score_b = st.columns(2)
    score_a.metric("Player Verses", st.session_state.player_score)
    score_b.metric("Computer Verses", st.session_state.computer_score)

    total_chain = st.session_state.player_score + st.session_state.computer_score
    st.metric("🔗 Chain Length", total_chain)

    chances_left = max(0, MAX_CHANCES - st.session_state.chances_lost)
    hearts = "❤️" * chances_left + "🖤" * st.session_state.chances_lost
    st.markdown(f"**Chances:** {hearts}")
    st.caption("Keep the verse chain alive for as long as possible.")

    st.divider()

    tts_ready = tts_available()
    tts_enabled = st.checkbox(
        "🔊 Enable Vāgdhenu voice",
        value=False,
        disabled=not tts_ready,
        help=(
            "Enable computer verse audio when a Vāgdhenu endpoint or local module is configured."
        ),
    )

    if not tts_ready:
        st.caption("Vāgdhenu voice is not configured yet. Gameplay still works fully without TTS.")

    st.divider()

    if st.button("🔄 Reset Game", use_container_width=True):
        reset_game()
        st.rerun()


# ============================================================
# HANDLE CORPUS CHANGE
# ============================================================

if st.session_state.active_corpus and st.session_state.active_corpus != corpus_path:
    reset_game()

st.session_state.active_corpus = corpus_path
engine = load_engine(corpus_path)


# ============================================================
# GAME OVER PANEL
# ============================================================

if st.session_state.game_over:
    final_chain = st.session_state.player_score + st.session_state.computer_score

    st.error("Game Over — all 3 chances have been used.")

    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown('<div class="main-metric-wrap">', unsafe_allow_html=True)
        st.metric("Your Valid Verses", st.session_state.player_score)
        st.markdown("</div>", unsafe_allow_html=True)

    with g2:
        st.markdown('<div class="main-metric-wrap">', unsafe_allow_html=True)
        st.metric("Computer Verses", st.session_state.computer_score)
        st.markdown("</div>", unsafe_allow_html=True)

    with g3:
        st.markdown('<div class="main-metric-wrap">', unsafe_allow_html=True)
        st.metric("Final Chain Length", final_chain)
        st.markdown("</div>", unsafe_allow_html=True)

    st.info("Reset the game to begin a new Antyakshari chain.")


# ============================================================
# MAIN LAYOUT
# ============================================================

left_col, right_col = st.columns([1.18, 0.82], gap="large")


# ============================================================
# LEFT SIDE
# ============================================================

with left_col:
    if st.session_state.free_start_allowed or not st.session_state.expected_letter:
        target_display = "स्वेच्छा"
        target_note = "Free start — choose any unused Sanskrit verse."
    else:
        target_display = st.session_state.expected_letter
        target_note = f"Your next verse must begin with {st.session_state.expected_letter}."

    st.markdown(
        dedent(
            f"""
            <div class="target-card">
                <div class="target-label">Target starting अक्षर</div>
                <div class="target-akshara">{target_display}</div>
                <div class="target-note">{target_note}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">🎤 Your Turn</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="mini-note">Record your verse in Sanskrit, or type/paste it below. You may also correct the transcription before playing.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.pending_clear_input:
        st.session_state.verse_input = ""
        st.session_state.pending_clear_input = False

    audio_val = st.audio_input(
        "Record your Sanskrit verse",
        disabled=st.session_state.game_over,
        key=f"audio_input_{st.session_state.audio_nonce}",
    )

    if audio_val is not None and not st.session_state.game_over:
        audio_bytes = audio_val.getvalue()
        digest = hashlib.sha256(audio_bytes).hexdigest()

        if digest != st.session_state.last_audio_digest:
            st.session_state.last_audio_digest = digest

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

            try:
                with st.spinner("Su-śrotā is transcribing your recitation…"):
                    recognized = transcribe_audio(temp_path)

                if recognized:
                    st.session_state.verse_input = recognized.strip()
                    st.session_state.last_error = ""
                    st.success("Transcription ready. Review it and then press Play Verse.")
                else:
                    st.session_state.last_error = "Su-śrotā could not transcribe this recording."
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    st.text_area(
        "Recognized / typed verse",
        key="verse_input",
        height=130,
        placeholder="Enter or review the Sanskrit verse here…",
        disabled=st.session_state.game_over,
    )

    button_col1, button_col2 = st.columns([2.1, 1])

    submit_turn = button_col1.button(
        "▶️ Play Verse",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.game_over,
    )

    button_col2.button(
        "Clear",
        use_container_width=True,
        disabled=st.session_state.game_over,
        on_click=clear_input,
    )

    if st.session_state.last_error:
        st.warning(st.session_state.last_error)

    if submit_turn and not st.session_state.game_over:
        raw_user_text = st.session_state.verse_input.strip()

        if not raw_user_text:
            st.error("Record or type a verse first.")
            st.stop()

        matched_entry, match_score = engine.match_verse(
            raw_user_text,
            min_similarity=float(min_similarity),
        )

        matched_in_dataset = matched_entry is not None

        if verse_mode == VERSE_MODE_DATASET and not matched_in_dataset:
            penalize(
                "That recitation did not match a verse in the selected corpus closely enough."
            )
            st.rerun()

        if matched_in_dataset:
            player_text = matched_entry.verse
            player_first = matched_entry.first_letter
            player_last = matched_entry.last_letter
            player_swara = matched_entry.swara_after_last
            player_reference = verse_reference(matched_entry)

            if matched_entry.verse_id in st.session_state.used_ids:
                penalize("That verse has already been used.")
                st.rerun()
        else:
            player_text = raw_user_text
            normalized_custom = normalize_devanagari_text(player_text)

            if not normalized_custom:
                penalize("Could not detect usable Devanagari text in that verse.")
                st.rerun()

            if normalized_custom in st.session_state.used_custom_texts:
                penalize("That outside-dataset verse has already been used.")
                st.rerun()

            player_first = infer_first_letter(player_text)
            player_last, player_swara = infer_last_letter_and_swara(player_text)
            player_reference = "Outside selected corpus"

            if not player_first or not player_last:
                penalize("Could not determine the starting or ending अक्षर.")
                st.rerun()

        if (
            not st.session_state.free_start_allowed
            and st.session_state.expected_letter
            and player_first != st.session_state.expected_letter
        ):
            penalize(
                f"Invalid continuation. Your verse must begin with {st.session_state.expected_letter}, not {player_first}."
            )
            st.rerun()

        if matched_in_dataset:
            st.session_state.used_ids.add(matched_entry.verse_id)
            correction_note = ""

            if normalize_devanagari_text(raw_user_text) != normalize_devanagari_text(player_text):
                correction_note = f"Matched corpus verse ({match_score:.0%})."
        else:
            st.session_state.used_custom_texts.add(normalize_devanagari_text(player_text))
            correction_note = "Accepted via Allow Other Verses."

        st.session_state.player_score += 1
        st.session_state.last_error = ""

        log_move(
            "Player",
            player_text,
            reference=player_reference,
            note=correction_note,
            required_letter=st.session_state.expected_letter or "",
        )

        response = engine.choose_response_for_end(
            player_last,
            player_swara,
            st.session_state.used_ids,
            rule_set=rule_set,
            difficulty=difficulty,
        )

        bot_entry = response["bot_entry"]

        if bot_entry is None:
            st.session_state.expected_letter = None
            st.session_state.free_start_allowed = True

            log_move(
                "System",
                "The computer has no unused continuation in this corpus. Free start is enabled.",
                note=str(response["rule_applied"]),
            )
            st.session_state.last_tts_path = ""
        else:
            st.session_state.used_ids.add(bot_entry.verse_id)
            st.session_state.computer_score += 1

            log_move(
                "Computer",
                bot_entry.verse,
                reference=verse_reference(bot_entry),
                note=str(response["rule_applied"]),
                required_letter=str(response["required_letter"] or ""),
            )

            if tts_enabled:
                audio_path = generate_speech(bot_entry.verse, "computer_response.wav")
                st.session_state.last_tts_path = audio_path or ""
            else:
                st.session_state.last_tts_path = ""

            update_requirement(engine, bot_entry, rule_set)

        st.session_state.pending_clear_input = True
        st.session_state.last_audio_digest = ""
        st.session_state.audio_nonce += 1
        st.rerun()

    if st.session_state.last_tts_path and os.path.exists(st.session_state.last_tts_path):
        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 🔊 Computer Recitation")
        st.audio(st.session_state.last_tts_path, format="audio/wav")

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# RIGHT SIDE
# ============================================================

with right_col:
    st.markdown('<div class="history-card">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">📜 Game History</div>', unsafe_allow_html=True)
    render_history()

    with st.expander("How the rules work"):
        st.markdown(
            f"""
**Rule A — Strict**  
The next verse must begin with the last playable अक्षर of the previous verse.

**Rule B — Swara fallback**  
The game first tries the strict continuation. If the selected corpus has no strict continuation, it uses the recorded **Swara After Last**.

**{VERSE_MODE_DATASET}**  
Your recitation must match a verse in the selected corpus.

**{VERSE_MODE_OPEN}**  
This preserves the original Vyoma open-Antyakshari setting. You may recite another Sanskrit verse outside the selected corpus. The game checks its required starting अक्षर, infers its ending अक्षर, and the computer continues from the selected corpus.

**No repeats**  
A corpus verse or outside-dataset verse cannot be reused.

**Chances**  
You have **{MAX_CHANCES} chances**. Invalid moves use one chance.

**Goal**  
Keep the verse chain alive for as long as possible.
            """
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    dedent(
        f"""
        <div class="footer-credit">
            <img src="{VYOMA_LOGO_URL}" alt="Vyoma">
            Based on the original
            <a href="{VYOMA_REPO_URL}" target="_blank">
                Vyoma Linguistic Labs Antyakshari-Krida
            </a>
            project · enhanced with Su-śrotā ASR.
        </div>
        """
    ),
    unsafe_allow_html=True,
)
