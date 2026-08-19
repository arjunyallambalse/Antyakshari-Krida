#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import html
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

from yourvoic_tts import (
    generate_speech,
    get_last_tts_error,
    tts_available,
)


MAX_CHANCES = 3

VERSE_MODE_DATASET = (
    "Within Dataset Only"
)

VERSE_MODE_OPEN = (
    "Allow Other Verses"
)

VYOMA_LOGO_URL = (
    "https://avatars.githubusercontent.com/"
    "u/108797006?v=4"
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
    page_title=(
        "Sanskrit Antyakshari Krida"
    ),
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLE
# ============================================================

st.html(
    """
<style>

.stApp {
    background: #F5F8FC;
}

.block-container {
    max-width: 1320px;
    padding-top: 3.2rem;
    padding-bottom: 2.5rem;
}


/* SIDEBAR */

[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #0C2744 0%,
            #163754 100%
        );
}

[data-testid="stSidebar"] * {
    color: #F7FAFC;
}

[data-testid="stSidebar"]
.stCaptionContainer,

[data-testid="stSidebar"]
small {
    color: #C8D6E5 !important;
}


/* HERO */

.hero-card {

    background:
        linear-gradient(
            135deg,
            #083C6D 0%,
            #0B5FA5 62%,
            #1677BC 100%
        );

    border-radius: 20px;

    border-bottom:
        5px solid #E7B73C;

    box-shadow:
        0 12px 30px
        rgba(8,60,109,.18);

    padding:
        25px 28px;

    margin-bottom:
        22px;

    color: white;

    position: relative;
}


.hero-title {

    font-size: 2.15rem;

    line-height: 1.2;

    font-weight: 800;

    color: white;

    margin: 0;
}


.hero-subtitle {

    margin-top: 9px;

    max-width: 850px;

    color: #E5F1FB;

    font-size: 1rem;

    line-height: 1.55;
}


.hero-badge {

    position: absolute;

    top: 15px;

    right: 17px;

    display: flex;

    align-items: center;

    gap: 7px;

    background:
        rgba(
            255,
            255,
            255,
            .14
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            .15
        );

    border-radius:
        999px;

    padding:
        6px 10px;

    color: white;

    font-size:
        .72rem;
}


.hero-badge img {

    width: 23px;

    height: 23px;

    border-radius: 50%;
}


.hero-chips {

    display: flex;

    flex-wrap: wrap;

    gap: 9px;

    margin-top: 16px;
}


.hero-chip {

    background:
        rgba(
            255,
            255,
            255,
            .13
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            .14
        );

    border-radius:
        10px;

    padding:
        7px 10px;

    color: white;

    font-size:
        .78rem;
}


/* TARGET */

.target-card {

    background:
        linear-gradient(
            180deg,
            #FFFFFF 0%,
            #F9FBFE 100%
        );

    border:
        2px solid #C9DFF3;

    border-radius:
        17px;

    box-shadow:
        0 7px 20px
        rgba(20,45,75,.06);

    text-align:
        center;

    padding:
        19px 20px 20px;

    margin-bottom:
        16px;
}


.target-label {

    color: #5D7185;

    font-size:
        .75rem;

    font-weight:
        800;

    letter-spacing:
        .9px;

    text-transform:
        uppercase;
}


.target-akshara {

    color: #083C6D;

    font-size:
        3.6rem;

    line-height:
        1.1;

    font-weight:
        850;

    margin:
        8px 0;
}


.target-note {

    color:
        #334E68;

    font-size:
        .92rem;
}


/* HISTORY */

.history-heading {

    color:
        #102A43;

    font-size:
        1.55rem;

    font-weight:
        800;

    margin:
        0 0 13px;
}


.move-card {

    background:
        #FFFFFF;

    border:
        1px solid #E7EDF4;

    border-radius:
        13px;

    padding:
        13px 14px;

    margin-bottom:
        10px;

    box-shadow:
        0 4px 12px
        rgba(16,42,67,.05);
}


.move-player {

    border-left:
        5px solid #0B5FA5;
}


.move-computer {

    border-left:
        5px solid #E48A2A;
}


.move-system {

    border-left:
        5px solid #73889B;

    background:
        #F9FBFD;
}


.move-speaker {

    color:
        #102A43;

    font-weight:
        800;

    margin-bottom:
        4px;
}


.move-text {

    color:
        #243B53;

    line-height:
        1.52;

    font-size:
        1.02rem;
}


.move-meta {

    margin-top:
        7px;

    color:
        #718096;

    font-size:
        .72rem;
}


/* VAGDHENU */

.vagdhenu-note {

    background:
        #EEF6FF;

    border:
        1px solid #CFE3F6;

    border-radius:
        10px;

    padding:
        9px 10px;

    margin-top:
        7px;

    color:
        #315A7D;

    font-size:
        .76rem;

    line-height:
        1.4;
}


/* FOOTER */

.footer-credit {

    margin-top:
        28px;

    border-top:
        1px solid #D9E3EC;

    padding-top:
        14px;

    text-align:
        center;

    color:
        #6B7C93;

    font-size:
        .75rem;
}


.footer-credit img {

    width: 19px;

    height: 19px;

    border-radius:
        50%;

    vertical-align:
        middle;

    margin-right:
        5px;
}


/* STREAMLIT COMPONENTS */

.stButton > button {

    border-radius:
        10px !important;

    font-weight:
        700 !important;
}


.stTextArea textarea {

    border-radius:
        12px !important;
}


div[data-testid="stMetric"] {

    background:
        rgba(
            255,
            255,
            255,
            .08
        );

    border-radius:
        11px;

    padding:
        8px 9px;
}


div[data-testid="stMetricLabel"] {

    font-weight:
        700;
}

</style>
"""
)


# ============================================================
# SESSION STATE
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

        "last_tts_error": "",

        "last_error": "",

        "active_corpus": "",
    }


    for key, value in defaults.items():

        if key not in st.session_state:

            st.session_state[
                key
            ] = value


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

    st.session_state.last_tts_error = ""

    st.session_state.last_error = ""


def clear_input():

    st.session_state.verse_input = ""

    st.session_state.last_audio_digest = ""

    st.session_state.last_error = ""

    st.session_state.audio_nonce += 1


init_state()


# ============================================================
# ENGINE
# ============================================================

@st.cache_resource(
    show_spinner=False
)
def load_engine(
    csv_path: str
):

    return AntyakshariEngine(
        csv_path
    )


def verse_reference(
    entry
):

    chapter = str(
        entry.chapter
        or ""
    ).strip()

    number = str(
        entry.verse_number
        or ""
    ).strip()


    if chapter and number:

        return (
            f"{chapter}."
            f"{number}"
        )


    return (
        number
        or
        str(
            entry.verse_id
        )
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
            "Record or type a "
            "Sanskrit verse to begin."
        )

        return


    for move in reversed(
        st.session_state.history
    ):

        if (
            move["speaker"]
            == "Player"
        ):

            css_class = (
                "move-player"
            )

            label = (
                "👤 Player"
            )


        elif (
            move["speaker"]
            == "Computer"
        ):

            css_class = (
                "move-computer"
            )

            label = (
                "🤖 Computer"
            )


        else:

            css_class = (
                "move-system"
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


        safe_label = html.escape(
            label
        )

        safe_text = html.escape(
            str(
                move[
                    "text"
                ]
            )
        )

        safe_meta = html.escape(
            " · ".join(
                meta
            )
        )


        st.html(

            f'<div class="move-card {css_class}">'

            f'<div class="move-speaker">'
            f'{safe_label}'
            f'</div>'

            f'<div class="move-text">'
            f'{safe_text}'
            f'</div>'

            f'<div class="move-meta">'
            f'{safe_meta}'
            f'</div>'

            f'</div>'
        )


# ============================================================
# GAME HELPERS
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
        >=
        MAX_CHANCES
    ):

        st.session_state.game_over = (
            True
        )


def update_requirement(
    engine,
    bot_entry,
    rule_set,
):

    result = (
        engine
        .next_required_start_for_entry(

            bot_entry,

            st.session_state.used_ids,

            rule_set=rule_set,
        )
    )


    st.session_state.expected_letter = (
        result[
            "required_letter"
        ]
    )


    st.session_state.free_start_allowed = bool(
        result[
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
                result[
                    "rule_applied"
                ]
            ),
        )


# ============================================================
# HERO
# ============================================================

st.html(

    f'<div class="hero-card">'

    f'<div class="hero-badge">'

    f'<img '
    f'src="{VYOMA_LOGO_URL}" '
    f'alt="Vyoma">'

    f'<span>'
    f'Vyoma Linguistic Labs'
    f'</span>'

    f'</div>'


    f'<div class="hero-title">'

    f'🕉️ '
    f'संस्कृत-अन्त्याक्षरी क्रीडा'

    f'</div>'


    f'<div class="hero-subtitle">'

    f'Interactive Sanskrit '
    f'Antyakshari with '

    f'<strong>'
    f'Su-śrotā speech recognition'
    f'</strong>, '

    f'real corpus-based '
    f'continuation, and '

    f'<strong>'
    f'Vāgdhenu Sanskrit chant'
    f'</strong>.'

    f'</div>'


    f'<div class="hero-chips">'

    f'<div class="hero-chip">'
    f'🎙️ Speak or type'
    f'</div>'

    f'<div class="hero-chip">'
    f'🧠 Real game engine'
    f'</div>'

    f'<div class="hero-chip">'
    f'📚 Corpus or open verse'
    f'</div>'

    f'<div class="hero-chip">'
    f'🔊 Vāgdhenu chant'
    f'</div>'

    f'</div>'

    f'</div>'
)


# ============================================================
# CORPUS
# ============================================================

available_corpora = (
    available_corpus_files(
        "."
    )
)


if not available_corpora:

    st.error(
        "No supported corpus "
        "CSV files were found."
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
            "A: strict last-letter continuation. "
            "B: strict first, then swara fallback "
            "only if necessary."
        ),
    )


    verse_mode = st.radio(

        "Verse Source",

        [
            VERSE_MODE_DATASET,
            VERSE_MODE_OPEN,
        ],

        help=(
            "Allow Other Verses preserves "
            "the original Vyoma open-verse setting."
        ),
    )


    difficulty = st.selectbox(

        "Computer Difficulty",

        [
            DIFFICULTY_HARD,
            DIFFICULTY_MEDIUM,
            DIFFICULTY_EASY,
        ],
    )


    min_similarity = (
        st.slider(

            "Verse match sensitivity",

            0.45,
            0.90,
            0.60,
            0.05,

            help=(
                "Higher values require "
                "a closer match to "
                "the selected corpus."
            ),
        )
    )


    st.divider()


    st.subheader(
        "📊 Game Tally"
    )


    score1, score2 = (
        st.columns(2)
    )


    score1.metric(

        "Player Verses",

        st.session_state
        .player_score,
    )


    score2.metric(

        "Computer Verses",

        st.session_state
        .computer_score,
    )


    chain_length = (

        st.session_state
        .player_score

        +

        st.session_state
        .computer_score
    )


    st.metric(

        "🔗 Chain Length",

        chain_length,
    )


    chances_left = max(

        0,

        MAX_CHANCES
        -
        st.session_state
        .chances_lost,
    )


    hearts = (

        "❤️" * chances_left

        +

        "🖤"
        *
        st.session_state
        .chances_lost
    )


    st.markdown(
        f"**Chances:** {hearts}"
    )


    st.caption(
        "Build the longest "
        "verse chain you can."
    )


    st.divider()


    tts_ready = (
        tts_available()
    )


    tts_enabled = (
        st.checkbox(

            "🔊 Vāgdhenu computer chant",

            value=True,

            disabled=not tts_ready,

            help=(
                "Uses the official public "
                "Vāgdhenu Hugging Face "
                "ZeroGPU demo."
            ),
        )
    )


    if tts_ready:

        st.html(

            '<div '
            'class="vagdhenu-note">'

            'Vāgdhenu is connected. '
            'The first chant may take '
            '30–60 seconds while the '
            'ZeroGPU model wakes up.'

            '</div>'
        )


    else:

        st.caption(

            "Vāgdhenu client "
            "is unavailable. "

            "Gameplay still works "
            "without TTS."
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
    !=
    corpus_path
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

    final_chain = (

        st.session_state
        .player_score

        +

        st.session_state
        .computer_score
    )


    st.error(
        "Game Over — all 3 chances "
        "have been used."
    )


    a, b, c = (
        st.columns(3)
    )


    a.metric(
        "Your Valid Verses",
        st.session_state.player_score,
    )


    b.metric(
        "Computer Verses",
        st.session_state.computer_score,
    )


    c.metric(
        "Final Chain Length",
        final_chain,
    )


    st.info(
        "Reset the game to begin "
        "a new Antyakshari chain."
    )


# ============================================================
# MAIN LAYOUT
# ============================================================

left_col, right_col = (
    st.columns(

        [
            1.15,
            0.85,
        ],

        gap="large",
    )
)


# ============================================================
# PLAYER AREA
# ============================================================

with left_col:


    if (
        st.session_state
        .free_start_allowed

        or

        not st.session_state
        .expected_letter
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
            st.session_state
            .expected_letter
        )

        target_note = (

            "Your next verse must "
            "begin with "

            f"{st.session_state.expected_letter}."
        )


    st.html(

        f'<div class="target-card">'

        f'<div class="target-label">'
        f'Target starting अक्षर'
        f'</div>'

        f'<div class="target-akshara">'
        f'{html.escape(target_display)}'
        f'</div>'

        f'<div class="target-note">'
        f'{html.escape(target_note)}'
        f'</div>'

        f'</div>'
    )


    with st.container(
        border=True
    ):


        st.subheader(
            "🎤 Your Turn"
        )


        st.caption(

            "Record a Sanskrit verse. "

            "Su-śrotā will transcribe it, "

            "and you can correct the text "
            "before submitting."
        )


        if (
            st.session_state
            .pending_clear_input
        ):

            st.session_state.verse_input = ""

            st.session_state.pending_clear_input = (
                False
            )


        audio_val = st.audio_input(

            "Record your Sanskrit verse",

            disabled=(
                st.session_state
                .game_over
            ),

            key=(
                "audio_input_"
                f"{st.session_state.audio_nonce}"
            ),
        )


        # ----------------------------------------------------
        # SPEECH RECOGNITION
        # ----------------------------------------------------

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
                .sha256(
                    audio_bytes
                )
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


                with tempfile.NamedTemporaryFile(

                    suffix=".wav",

                    delete=False,

                ) as tmp:

                    tmp.write(
                        audio_bytes
                    )

                    temp_path = (
                        tmp.name
                    )


                try:


                    with st.spinner(

                        "Su-śrotā is transcribing "
                        "your recitation…"
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


                        st.session_state.last_error = ""


                        st.success(

                            "Transcription ready. "

                            "Review it, then press "
                            "Play Verse."
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


        st.text_area(

            "Recognized / typed verse",

            key="verse_input",

            height=125,

            placeholder=(

                "The Su-śrotā transcription "
                "will appear here, "

                "or type/paste a "
                "Sanskrit verse."
            ),

            disabled=(
                st.session_state
                .game_over
            ),
        )


        play_col, clear_col = (
            st.columns(
                [
                    2,
                    1,
                ]
            )
        )


        submit_turn = (
            play_col.button(

                "▶️ Play Verse",

                type="primary",

                use_container_width=True,

                disabled=(
                    st.session_state
                    .game_over
                ),
            )
        )


        clear_col.button(

            "Clear",

            use_container_width=True,

            disabled=(
                st.session_state
                .game_over
            ),

            on_click=clear_input,
        )


        if (
            st.session_state
            .last_error
        ):

            st.warning(
                st.session_state
                .last_error
            )


        # ====================================================
        # PLAY TURN
        # ====================================================

        if (
            submit_turn

            and

            not st.session_state
            .game_over
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


            (
                matched_entry,
                match_score,

            ) = (
                engine
                .match_verse(

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


            # -----------------------------------------------
            # DATASET MODE
            # -----------------------------------------------

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
                    "selected corpus closely enough."
                )

                st.rerun()


            # -----------------------------------------------
            # MATCHED VERSE
            # -----------------------------------------------

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

                    st.session_state
                    .used_ids
                ):

                    penalize(
                        "That verse has "
                        "already been used."
                    )

                    st.rerun()


            # -----------------------------------------------
            # OPEN VERSE MODE
            # -----------------------------------------------

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

                        "Could not detect usable "
                        "Devanagari text in that verse."
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
                        "verse has already been used."
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

                        "Could not determine the "
                        "starting or ending अक्षर."
                    )

                    st.rerun()


            # -----------------------------------------------
            # REQUIRED STARTING AKSHARA
            # -----------------------------------------------

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

                    f"Your verse must begin with "
                    f"{st.session_state.expected_letter}, "

                    f"not {player_first}."
                )

                st.rerun()


            # -----------------------------------------------
            # MARK USED
            # -----------------------------------------------

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


            # -----------------------------------------------
            # PLAYER TALLY
            # -----------------------------------------------

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


            # -----------------------------------------------
            # COMPUTER TURN
            # -----------------------------------------------

            response = (
                engine
                .choose_response_for_end(

                    player_last,

                    player_swara,

                    st.session_state
                    .used_ids,

                    rule_set=rule_set,

                    difficulty=difficulty,
                )
            )


            bot_entry = (
                response[
                    "bot_entry"
                ]
            )


            # -----------------------------------------------
            # NO RESPONSE
            # -----------------------------------------------

            if bot_entry is None:


                st.session_state.expected_letter = (
                    None
                )


                st.session_state.free_start_allowed = (
                    True
                )


                st.session_state.last_tts_path = ""


                st.session_state.last_tts_error = ""


                log_move(

                    "System",

                    (
                        "The computer has no "
                        "unused continuation "
                        "in this corpus. "
                        "Free start is enabled."
                    ),

                    note=str(
                        response[
                            "rule_applied"
                        ]
                    ),
                )


            # -----------------------------------------------
            # COMPUTER VERSE
            # -----------------------------------------------

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


                update_requirement(

                    engine,

                    bot_entry,

                    rule_set,
                )


                # -------------------------------------------
                # VAGDHENU
                # -------------------------------------------

                if tts_enabled:


                    with st.spinner(

                        "Vāgdhenu is chanting "
                        "the computer's verse…"
                    ):


                        audio_path = (
                            generate_speech(

                                bot_entry.verse,

                                "computer_response.wav",
                            )
                        )


                    st.session_state.last_tts_path = (

                        audio_path
                        or ""
                    )


                    st.session_state.last_tts_error = (

                        get_last_tts_error()
                    )


                else:


                    st.session_state.last_tts_path = ""


                    st.session_state.last_tts_error = ""


            # -----------------------------------------------
            # NEXT ROUND
            # -----------------------------------------------

            st.session_state.pending_clear_input = (
                True
            )


            st.session_state.last_audio_digest = ""


            st.session_state.audio_nonce += 1


            st.rerun()


    # ========================================================
    # COMPUTER AUDIO
    # ========================================================

    if (
        st.session_state
        .last_tts_path

        and

        os.path.exists(
            st.session_state
            .last_tts_path
        )
    ):


        with st.container(
            border=True
        ):


            st.subheader(
                "🔊 Computer Chant"
            )


            st.audio(

                st.session_state
                .last_tts_path,

                format="audio/wav",
            )


            st.caption(

                "Generated by "
                "Vāgdhenu Sanskrit Chant TTS."
            )


    elif (
        st.session_state
        .last_tts_error
    ):


        st.warning(

            "The computer move was valid, "

            "but Vāgdhenu audio could "
            "not be generated: "

            +

            st.session_state
            .last_tts_error
        )


# ============================================================
# HISTORY PANEL
# ============================================================

with right_col:


    with st.container(
        border=True
    ):


        st.html(

            '<div '
            'class="history-heading">'

            '📜 Game History'

            '</div>'
        )


        render_history()


        with st.expander(
            "How the rules work"
        ):


            st.markdown(
                f"""
**Rule A — Strict**  
The next verse must begin with the last playable अक्षर of the previous verse.

**Rule B — Swara fallback**  
Strict continuation is tried first. If the selected corpus has no strict continuation, the recorded **Swara After Last** is used.

**{VERSE_MODE_DATASET}**  
Your recitation must match a verse in the selected corpus.

**{VERSE_MODE_OPEN}**  
This preserves the original Vyoma open-Antyakshari setting. You may recite another Sanskrit verse outside the selected corpus; the app checks its starting अक्षर and infers its ending अक्षर.

**No repeats**  
Used verses cannot be repeated.

**Chances**  
You have **{MAX_CHANCES} chances**. Invalid moves consume one chance.

**Goal**  
Keep the Antyakshari chain alive for as long as possible.
                """
            )


# ============================================================
# FOOTER
# ============================================================

st.html(

    f'<div class="footer-credit">'

    f'<img '
    f'src="{VYOMA_LOGO_URL}" '
    f'alt="Vyoma">'

    f'Based on the original '

    f'<a '
    f'href="{VYOMA_REPO_URL}" '
    f'target="_blank">'

    f'Vyoma Linguistic Labs '
    f'Antyakshari-Krida'

    f'</a> '

    f'project · enhanced with '

    f'Su-śrotā ASR and '
    f'Vāgdhenu chant.'

    f'</div>'
)
