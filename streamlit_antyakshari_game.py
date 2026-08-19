#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import os
import tempfile

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

# Small Vyoma credit mark.
# This uses the Vyoma Linguistic Labs GitHub organization avatar.
VYOMA_LOGO_URL = (
    "https://avatars.githubusercontent.com/u/108797006?v=4"
)

VYOMA_REPO_URL = (
    "https://github.com/"
    "Vyoma-Linguistic-Labs/"
    "Antyakshari-Krida"
)


# ============================================================
# PAGE
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
    """
    <style>

    .stApp {
        background: #F4F7FA;
    }

    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3 {
        color: #132238;
    }

    [data-testid="stSidebar"] {
        background: #202531;
    }

    [data-testid="stSidebar"] * {
        color: #FFFFFF;
    }

    .header-card {
        position: relative;

        background:
            linear-gradient(
                135deg,
                #0D3B66 0%,
                #104F8B 58%,
                #1A65A4 100%
            );

        color: white;

        padding: 24px 28px;

        border-radius: 16px;

        box-shadow:
            0 5px 18px rgba(13,59,102,.18);

        border-bottom:
            5px solid #F4C430;

        margin-bottom: 22px;

        text-align: center;
    }

    .header-card h1 {
        color: #FFFFFF !important;

        margin: 0;

        font-size: 34px;

        font-weight: 750;
    }

    .header-card p {
        color: #EAF3FB !important;

        margin: 7px 0 0 0;

        font-size: 16px;
    }

    .vyoma-badge {
        position: absolute;

        right: 16px;

        top: 14px;

        display: flex;

        align-items: center;

        gap: 7px;

        padding: 5px 9px;

        border-radius: 999px;

        background:
            rgba(255,255,255,.14);

        font-size: 12px;

        color: white;
    }

    .vyoma-badge img {
        width: 25px;
        height: 25px;

        border-radius: 50%;
    }

    .target-card {
        background: white;

        border:
            2px solid #0D3B66;

        border-radius: 14px;

        padding: 22px;

        text-align: center;

        box-shadow:
            0 3px 12px rgba(15,23,42,.06);

        margin-bottom: 18px;
    }

    .target-label {
        color: #64748B;

        font-size: 13px;

        font-weight: 700;

        text-transform: uppercase;

        letter-spacing: .7px;
    }

    .target-letter {
        font-size: 54px;

        line-height: 1.1;

        font-weight: 800;

        color: #0D3B66;

        margin: 10px 0;
    }

    .target-note {
        color: #334155;

        font-size: 14px;
    }

    .move-card {
        background: #FFFFFF;

        border-radius: 10px;

        padding: 14px 16px;

        margin-bottom: 11px;

        box-shadow:
            0 2px 8px rgba(15,23,42,.05);

        color: #0F172A;
    }

    .player-move {
        border-left:
            5px solid #1769AA;
    }

    .computer-move {
        border-left:
            5px solid #D97706;
    }

    .system-move {
        border-left:
            5px solid #64748B;

        background: #F8FAFC;
    }

    .move-meta {
        color: #64748B;

        font-size: 12px;

        margin-top: 7px;
    }

    .footer-vyoma {
        margin-top: 34px;

        padding-top: 16px;

        border-top:
            1px solid #D9E2EC;

        display: flex;

        align-items: center;

        justify-content: center;

        gap: 8px;

        color: #64748B;

        font-size: 12px;
    }

    .footer-vyoma img {
        width: 22px;
        height: 22px;

        border-radius: 50%;
    }

    .stButton > button {
        border-radius: 9px;

        font-weight: 650;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# STATE
# ============================================================

def init_state():

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


def reset_game():

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


init_state()


# ============================================================
# ENGINE
# ============================================================

@st.cache_resource(
    show_spinner=False
)
def load_engine(
    csv_path
):

    return AntyakshariEngine(
        csv_path
    )


def verse_reference(
    entry
):

    chapter = str(
        entry.chapter or ""
    ).strip()

    verse_number = str(
        entry.verse_number or ""
    ).strip()

    if chapter and verse_number:

        return (
            f"{chapter}."
            f"{verse_number}"
        )

    if verse_number:

        return verse_number

    return str(
        entry.verse_id
    )


# ============================================================
# HISTORY
# ============================================================

def log_move(
    speaker,
    text,
    reference="",
    note="",
    required_letter="",
):

    st.session_state.history.append(
        {

            "speaker":
                speaker,

            "text":
                text,

            "reference":
                reference,

            "note":
                note,

            "required_letter":
                required_letter,
        }
    )


def render_history():

    if not st.session_state.history:

        st.info(
            "No moves yet. "
            "Record or type a Sanskrit "
            "verse to begin."
        )

        return

    for move in reversed(
        st.session_state.history
    ):

        speaker = move[
            "speaker"
        ]

        if speaker == "Player":

            css_class = (
                "player-move"
            )

            label = (
                "👤 Player"
            )

        elif speaker == "Computer":

            css_class = (
                "computer-move"
            )

            label = (
                "🤖 Computer"
            )

        else:

            css_class = (
                "system-move"
            )

            label = (
                "ℹ️ System"
            )

        meta = []

        if move.get(
            "reference"
        ):

            meta.append(
                "Ref: "
                + move[
                    "reference"
                ]
            )

        if move.get(
            "required_letter"
        ):

            meta.append(
                "Required: "
                + move[
                    "required_letter"
                ]
            )

        if move.get(
            "note"
        ):

            meta.append(
                move[
                    "note"
                ]
            )

        meta_text = (
            " · ".join(meta)
        )

        st.markdown(
            f"""
            <div
            class="move-card
            {css_class}">

            <strong>
            {label}
            </strong>

            <br>

            <span
            style="font-size:18px;">

            {move["text"]}

            </span>

            <div
            class="move-meta">

            {meta_text}

            </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# PENALTIES
# ============================================================

def penalize(
    message
):

    st.session_state.chances_lost += 1

    st.session_state.last_error = (
        message
    )

    log_move(
        "System",
        message,
        note=(
            "Invalid player move"
        ),
    )

    if (
        st.session_state.chances_lost
        >= MAX_CHANCES
    ):

        st.session_state.game_over = (
            True
        )


# ============================================================
# NEXT LETTER
# ============================================================

def update_requirement(
    engine,
    bot_entry,
    rule_set,
):

    requirement = (
        engine
        .next_required_start_for_entry(
            bot_entry,
            st.session_state.used_ids,
            rule_set=rule_set,
        )
    )

    st.session_state.expected_letter = (
        requirement[
            "required_letter"
        ]
    )

    st.session_state.free_start_allowed = bool(
        requirement[
            "free_start_allowed"
        ]
    )

    if (
        st.session_state
        .free_start_allowed
    ):

        log_move(
            "System",

            (
                "No continuation exists "
                "in the selected corpus. "
                "You may start with any "
                "unused verse."
            ),

            note=str(
                requirement[
                    "rule_applied"
                ]
            ),
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    f"""
    <div class="header-card">

        <div class="vyoma-badge">

            <img
            src="{VYOMA_LOGO_URL}"
            alt="Vyoma">

            <span>
            Vyoma-origin project
            </span>

        </div>

        <h1>
        🕉️ संस्कृत-अन्त्याक्षरी क्रीडा
        </h1>

        <p>
        Graph-based Sanskrit Antyakshari
        · Su-śrotā ASR
        · Vāgdhenu TTS
        </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CORPUS
# ============================================================

available_corpora = (
    available_corpus_files(".")
)

if not available_corpora:

    st.error(
        "No supported corpus CSV "
        "files were found."
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "⚙️ Game Settings"
    )

    corpus_label = (
        st.selectbox(
            "Corpus",
            list(
                available_corpora.keys()
            ),
        )
    )

    corpus_path = (
        available_corpora[
            corpus_label
        ]
    )

    rule_set = st.radio(
        "Rule Set",
        [
            RULE_SET_A,
            RULE_SET_B,
        ],
        horizontal=True,

        help=(
            "A = strict last-letter "
            "continuation. "
            "B = strict first; "
            "if impossible, use the "
            "Swara After Last."
        ),
    )

    # --------------------------------------------------------
    # ORIGINAL VYOMA OPEN VERSE OPTION
    # --------------------------------------------------------

    verse_mode = st.radio(
        "Verse Source",

        [
            VERSE_MODE_DATASET,
            VERSE_MODE_OPEN,
        ],

        help=(
            "Within Dataset Only verifies "
            "the verse against the selected "
            "corpus. "

            "Allow Other Verses preserves "
            "the Vyoma open-verse rule: "
            "you may recite a Sanskrit verse "
            "outside the dataset as long as "
            "it obeys the required अक्षर."
        ),
    )

    difficulty = (
        st.selectbox(
            "Computer Difficulty",
            [
                DIFFICULTY_HARD,
                DIFFICULTY_MEDIUM,
                DIFFICULTY_EASY,
            ],
        )
    )

    min_similarity = (
        st.slider(
            "Verse match sensitivity",

            min_value=0.45,

            max_value=0.90,

            value=0.60,

            step=0.05,

            help=(
                "Higher values demand "
                "a closer match to the "
                "corpus verse."
            ),
        )
    )

    st.divider()

st.subheader(
    "📊 Game Tally"
)

score_a, score_b = st.columns(2)

score_a.metric(
    "Player Verses",
    st.session_state.player_score,
)

score_b.metric(
    "Computer Verses",
    st.session_state.computer_score,
)

total_chain = (
    st.session_state.player_score
    + st.session_state.computer_score
)

st.metric(
    "🔗 Chain Length",
    total_chain,
)

chances_left = max(
    0,
    MAX_CHANCES
    - st.session_state.chances_lost
)

hearts = (
    "❤️" * chances_left
    + "🖤" * st.session_state.chances_lost
)

st.markdown(
    f"**Chances:** {hearts}"
)

st.caption(
    "Keep the Antyakshari chain alive "
    "for as many verses as possible."
)
    st.divider()

    tts_ready = (
        tts_available()
    )

    tts_enabled = (
        st.checkbox(
            "🔊 Vāgdhenu computer voice",

            value=False,

            disabled=not tts_ready,

            help=(
                "Vāgdhenu speech can be "
                "enabled when a Vāgdhenu "
                "endpoint is configured."
            ),
        )
    )

    if not tts_ready:

        st.caption(
            "Vāgdhenu voice is not "
            "configured yet. "
            "The full game still works "
            "without audio output."
        )

    st.divider()

    if st.button(
        "🔄 Reset Game",
        use_container_width=True,
    ):

        reset_game()

        st.rerun()


# ============================================================
# CORPUS CHANGE
# ============================================================

if (
    st.session_state.active_corpus
    and
    st.session_state.active_corpus
    != corpus_path
):

    reset_game()

st.session_state.active_corpus = (
    corpus_path
)


engine = load_engine(
    corpus_path
)


# ============================================================
# GAME OVER
# ============================================================

if st.session_state.game_over:

    st.error(
        "Game over — all 3 chances "
        "were used. Reset to play again."
    )


# ============================================================
# LAYOUT
# ============================================================

left_col, right_col = (
    st.columns(
        [1.05, 0.95],
        gap="large",
    )
)


# ============================================================
# LEFT
# ============================================================

with left_col:

    if (
        st.session_state.free_start_allowed
        or
        not st.session_state.expected_letter
    ):

        target_display = (
            "स्वेच्छा"
        )

        target_note = (
            "Free start — choose any "
            "unused Sanskrit verse."
        )

    else:

        target_display = (
            st.session_state.expected_letter
        )

        target_note = (
            "Your verse must start with "
            + st.session_state.expected_letter
            + "."
        )

    st.markdown(
        f"""
        <div class="target-card">

        <div class="target-label">
        Target starting अक्षर
        </div>

        <div class="target-letter">
        {target_display}
        </div>

        <div class="target-note">
        {target_note}
        </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    st.subheader(
        "🎤 Your Turn"
    )


    # --------------------------------------------------------
    # MICROPHONE
    # --------------------------------------------------------

    audio_val = (
        st.audio_input(
            "Record your Sanskrit verse",

            disabled=(
                st.session_state.game_over
            ),
        )
    )


    if (
        audio_val is not None
        and
        not st.session_state.game_over
    ):

        audio_bytes = (
            audio_val.getvalue()
        )

        digest = (
            hashlib
            .sha256(audio_bytes)
            .hexdigest()
        )

        if (
            digest
            !=
            st.session_state
            .last_audio_digest
        ):

            st.session_state.last_audio_digest = (
                digest
            )

            with (
                tempfile
                .NamedTemporaryFile(
                    suffix=".wav",
                    delete=False,
                )
                as tmp
            ):

                tmp.write(
                    audio_bytes
                )

                temp_path = (
                    tmp.name
                )

            try:

                with st.spinner(
                    "Su-śrotā is "
                    "transcribing…"
                ):

                    recognized = (
                        transcribe_audio(
                            temp_path
                        )
                    )

                if recognized:

                    st.session_state.verse_input = (
                        recognized.strip()
                    )

                    st.session_state.last_error = (
                        ""
                    )

                    st.success(
                        "Su-śrotā transcription "
                        "ready. You may correct "
                        "the text before playing."
                    )

                else:

                    st.session_state.last_error = (
                        "Su-śrotā could not "
                        "transcribe this recording."
                    )

            finally:

                try:

                    os.remove(
                        temp_path
                    )

                except OSError:

                    pass


    # --------------------------------------------------------
    # MANUAL / ASR TEXT
    # --------------------------------------------------------

    verse_input = (
        st.text_area(
            "Recognized / typed verse",

            value=(
                st.session_state
                .verse_input
            ),

            height=125,

            placeholder=(
                "Record above or type/"
                "paste a Sanskrit verse."
            ),

            disabled=(
                st.session_state.game_over
            ),
        )
    )

    st.session_state.verse_input = (
        verse_input
    )


    submit_turn = (
        st.button(
            "▶️ Play Verse",

            type="primary",

            use_container_width=True,

            disabled=(
                st.session_state.game_over
            ),
        )
    )


    if (
        st.session_state.last_error
    ):

        st.warning(
            st.session_state.last_error
        )


    # ========================================================
    # PROCESS PLAYER TURN
    # ========================================================

    if (
        submit_turn
        and
        not st.session_state.game_over
    ):

        raw_user_text = (
            st.session_state
            .verse_input
            .strip()
        )

        if not raw_user_text:

            st.error(
                "Record or type "
                "a verse first."
            )

            st.stop()


        matched_entry, match_score = (
            engine.match_verse(
                raw_user_text,

                min_similarity=float(
                    min_similarity
                ),
            )
        )


        matched_in_dataset = (
            matched_entry
            is not None
        )


        # ----------------------------------------------------
        # DATASET ONLY
        # ----------------------------------------------------

        if (
            verse_mode
            ==
            VERSE_MODE_DATASET
            and
            not matched_in_dataset
        ):

            penalize(
                "That recitation did not "
                "match a verse in the "
                "selected corpus."
            )

            st.rerun()


        # ----------------------------------------------------
        # DATASET VERSE
        # ----------------------------------------------------

        if matched_in_dataset:

            player_text = (
                matched_entry.verse
            )

            player_first = (
                matched_entry.first_letter
            )

            player_last = (
                matched_entry.last_letter
            )

            player_swara = (
                matched_entry
                .swara_after_last
            )

            player_reference = (
                verse_reference(
                    matched_entry
                )
            )


            if (
                matched_entry.verse_id
                in
                st.session_state.used_ids
            ):

                penalize(
                    "That verse has "
                    "already been used."
                )

                st.rerun()


        # ----------------------------------------------------
        # ORIGINAL VYOMA OPEN VERSE
        # ----------------------------------------------------

        else:

            player_text = (
                raw_user_text
            )

            normalized_custom = (
                normalize_devanagari_text(
                    player_text
                )
            )

            if not normalized_custom:

                penalize(
                    "Could not detect "
                    "usable Devanagari text."
                )

                st.rerun()


            if (
                normalized_custom
                in
                st.session_state
                .used_custom_texts
            ):

                penalize(
                    "That outside-dataset "
                    "verse has already "
                    "been used."
                )

                st.rerun()


            player_first = (
                infer_first_letter(
                    player_text
                )
            )

            (
                player_last,
                player_swara,
            ) = (
                infer_last_letter_and_swara(
                    player_text
                )
            )

            player_reference = (
                "Outside selected corpus"
            )


            if (
                not player_first
                or
                not player_last
            ):

                penalize(
                    "Could not determine "
                    "the starting or ending "
                    "अक्षर."
                )

                st.rerun()


        # ----------------------------------------------------
        # REQUIRED START LETTER
        # ----------------------------------------------------

        if (
            not st.session_state
            .free_start_allowed

            and

            st.session_state
            .expected_letter

            and

            player_first
            !=
            st.session_state
            .expected_letter
        ):

            penalize(
                "Invalid continuation. "
                "Your verse must begin with "
                f"{st.session_state.expected_letter}, "
                f"not {player_first}."
            )

            st.rerun()


        # ----------------------------------------------------
        # MARK USED
        # ----------------------------------------------------

        if matched_in_dataset:

            st.session_state.used_ids.add(
                matched_entry.verse_id
            )

            correction_note = ""

            if (
                normalize_devanagari_text(
                    raw_user_text
                )
                !=
                normalize_devanagari_text(
                    player_text
                )
            ):

                correction_note = (
                    "Matched corpus verse "
                    f"({match_score:.0%})."
                )

        else:

            st.session_state.used_custom_texts.add(
                normalize_devanagari_text(
                    player_text
                )
            )

            correction_note = (
                "Accepted via "
                "Allow Other Verses."
            )


        # ----------------------------------------------------
        # SCORE PLAYER
        # ----------------------------------------------------

        st.session_state.player_score += 1

        st.session_state.last_error = ""


        log_move(
            "Player",

            player_text,

            reference=(
                player_reference
            ),

            note=(
                correction_note
            ),

            required_letter=(
                st.session_state
                .expected_letter
                or ""
            ),
        )


        # ----------------------------------------------------
        # COMPUTER RESPONSE
        # ----------------------------------------------------

        response = (
            engine
            .choose_response_for_end(
                player_last,
                player_swara,
                st.session_state.used_ids,

                rule_set=rule_set,

                difficulty=difficulty,
            )
        )


        bot_entry = (
            response[
                "bot_entry"
            ]
        )


        # ----------------------------------------------------
        # NO COMPUTER RESPONSE
        # ----------------------------------------------------

        if bot_entry is None:

            st.session_state.expected_letter = (
                None
            )

            st.session_state.free_start_allowed = (
                True
            )

            log_move(
                "System",

                (
                    "The computer has no "
                    "unused continuation "
                    "in this corpus. "
                    "Free start enabled."
                ),

                note=str(
                    response[
                        "rule_applied"
                    ]
                ),
            )


        # ----------------------------------------------------
        # COMPUTER PLAYS
        # ----------------------------------------------------

        else:

            st.session_state.used_ids.add(
                bot_entry.verse_id
            )

            st.session_state.computer_score += 1


            log_move(
                "Computer",

                bot_entry.verse,

                reference=(
                    verse_reference(
                        bot_entry
                    )
                ),

                note=str(
                    response[
                        "rule_applied"
                    ]
                ),

                required_letter=str(
                    response[
                        "required_letter"
                    ]
                    or ""
                ),
            )


            # -----------------------------------------------
            # OPTIONAL VAGDHENU
            # -----------------------------------------------

            if tts_enabled:

                output_path = (
                    "computer_response.wav"
                )

                audio_path = (
                    generate_speech(
                        bot_entry.verse,
                        output_path,
                    )
                )

                st.session_state.last_tts_path = (
                    audio_path
                    or ""
                )

            else:

                st.session_state.last_tts_path = ""


            update_requirement(
                engine,
                bot_entry,
                rule_set,
            )


        # ----------------------------------------------------
        # PREPARE NEXT TURN
        # ----------------------------------------------------

        st.session_state.verse_input = ""

        st.session_state.last_audio_digest = ""

        st.rerun()


    # ========================================================
    # COMPUTER AUDIO
    # ========================================================

    if (
        st.session_state.last_tts_path
        and
        os.path.exists(
            st.session_state
            .last_tts_path
        )
    ):

        st.markdown(
            "#### 🔊 Computer recitation"
        )

        st.audio(
            st.session_state
            .last_tts_path,

            format="audio/wav",
        )


# ============================================================
# RIGHT
# ============================================================

with right_col:

    st.subheader(
        "📜 Game History"
    )

    render_history()


    with st.expander(
        "How the rules work"
    ):

        st.markdown(
            f"""
**Rule A**  
Strict last-letter continuation.

**Rule B**  
Strict continuation is tried first.  
If no verse is available, the game uses the recorded **Swara After Last**.

**{VERSE_MODE_DATASET}**  
Your recitation must match the selected corpus.

**{VERSE_MODE_OPEN}**  
This preserves the original Vyoma-style open Antyakshari option. You may recite a Sanskrit verse outside the selected corpus. The app checks the required first अक्षर, determines the ending अक्षर, and the computer continues using its corpus.

A verse cannot be reused.

You have **{MAX_CHANCES} chances** for invalid moves.
            """
        )


# ============================================================
# VYOMA CREDIT
# ============================================================

st.markdown(
    f"""
    <div class="footer-vyoma">

        <img
        src="{VYOMA_LOGO_URL}"
        alt="Vyoma">

        <span>

        Based on the original

        <a
        href="{VYOMA_REPO_URL}"
        target="_blank">

        Vyoma Linguistic Labs
        Antyakshari-Krida

        </a>

        project · enhanced with
        Su-śrotā ASR.

        </span>

    </div>
    """,

    unsafe_allow_html=True,
)
