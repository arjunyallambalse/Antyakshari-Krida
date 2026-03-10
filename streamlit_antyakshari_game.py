#!/usr/bin/env python3

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
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
from sanskrit_asr import ASR_IMPORT_ERROR, LocalSanskritASR, asr_runtime_available
from yourvoic_tts import synthesize_yourvoic_tts


MAX_CHANCES = 3
VERSE_MODE_DATASET = "Within Dataset Only"
VERSE_MODE_OPEN = "Allow Other Verses"


st.set_page_config(
    page_title="Sanskrit Antyakshari Game",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _init_state() -> None:
    defaults = {
        "events": [],
        "used_ids": set(),
        "used_custom_texts": set(),
        "expected_letter": None,
        "free_start_allowed": True,
        "expected_rule_note": "",
        "chances_lost": 0,
        "passes_used": 0,
        "mistakes_used": 0,
        "game_over": False,
        "active_settings": None,
        "latest_asr_iast": "",
        "latest_asr_devanagari": "",
        "latest_tts_audio": None,
        "latest_tts_mime": "",
        "latest_tts_error": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_game() -> None:
    st.session_state["events"] = []
    st.session_state["used_ids"] = set()
    st.session_state["used_custom_texts"] = set()
    st.session_state["expected_letter"] = None
    st.session_state["free_start_allowed"] = True
    st.session_state["expected_rule_note"] = ""
    st.session_state["chances_lost"] = 0
    st.session_state["passes_used"] = 0
    st.session_state["mistakes_used"] = 0
    st.session_state["game_over"] = False
    st.session_state["latest_asr_iast"] = ""
    st.session_state["latest_asr_devanagari"] = ""
    st.session_state["latest_tts_audio"] = None
    st.session_state["latest_tts_mime"] = ""
    st.session_state["latest_tts_error"] = ""


@st.cache_resource(show_spinner=False)
def load_engine(csv_path: str) -> AntyakshariEngine:
    return AntyakshariEngine(csv_path)


@st.cache_resource(show_spinner=False)
def load_asr(model_path: str) -> LocalSanskritASR:
    return LocalSanskritASR(model_path=model_path)


def _verse_reference(entry) -> str:
    chapter = str(entry.chapter).strip() if entry.chapter is not None else ""
    verse_number = str(entry.verse_number).strip() if entry.verse_number is not None else ""
    if chapter and verse_number:
        return f"{chapter}.{verse_number}"
    if verse_number:
        return verse_number
    return str(entry.verse_id)


def _log_event(actor: str, action: str, note: str = "", **kwargs) -> None:
    event = {
        "event_no": len(st.session_state["events"]) + 1,
        "actor": actor,
        "action": action,
        "verse": kwargs.get("verse", ""),
        "reference": kwargs.get("reference", ""),
        "required_letter": kwargs.get("required_letter", ""),
        "detected_last": kwargs.get("detected_last", ""),
        "detected_swara": kwargs.get("detected_swara", ""),
        "match_score": kwargs.get("match_score", ""),
        "note": note,
    }
    st.session_state["events"].append(event)


def _append_to_last_event_note(extra_note: str) -> None:
    if not st.session_state["events"]:
        return
    previous = st.session_state["events"][-1].get("note", "")
    if previous:
        st.session_state["events"][-1]["note"] = f"{previous} | {extra_note}"
    else:
        st.session_state["events"][-1]["note"] = extra_note


def _get_yourvoic_api_key() -> str:
    if "yourvoic" in st.secrets and "api_key" in st.secrets["yourvoic"]:
        return str(st.secrets["yourvoic"]["api_key"])
    if "YOURVOIC_API_KEY" in st.secrets:
        return str(st.secrets["YOURVOIC_API_KEY"])
    return ""


def _generate_tts_for_computer_verse(
    verse_text: str,
    tts_enabled: bool,
    api_key: str,
    speaker: str,
    pace: float,
    target_language_code: str,
) -> None:
    if not tts_enabled:
        return
    if not api_key:
        st.session_state["latest_tts_audio"] = None
        st.session_state["latest_tts_mime"] = ""
        st.session_state["latest_tts_error"] = "YourVoic API key not configured."
        _append_to_last_event_note("TTS unavailable (missing API key).")
        return

    result = synthesize_yourvoic_tts(
        text=verse_text,
        api_key=api_key,
        voice=speaker,
        language=target_language_code,
        speed=pace,
    )
    if result.ok and result.audio_bytes:
        st.session_state["latest_tts_audio"] = result.audio_bytes
        st.session_state["latest_tts_mime"] = (result.content_type or "audio/mpeg").split(";")[0].strip()
        st.session_state["latest_tts_error"] = ""
        _append_to_last_event_note("TTS ready.")
    else:
        st.session_state["latest_tts_audio"] = None
        st.session_state["latest_tts_mime"] = ""
        st.session_state["latest_tts_error"] = result.error or "TTS failed."
        _append_to_last_event_note(f"TTS failed: {st.session_state['latest_tts_error']}")


def _pick_with_optional_difficulty(engine: AntyakshariEngine, candidates, used_ids, difficulty: str):
    try:
        return engine._pick_response(candidates, used_ids, difficulty=difficulty)
    except TypeError:
        return engine._pick_response(candidates, used_ids)


def _choose_response_for_end(
    engine: AntyakshariEngine,
    last_letter,
    swara,
    used_ids,
    rule_set: str,
    difficulty: str,
):
    if hasattr(engine, "choose_response_for_end"):
        try:
            return engine.choose_response_for_end(
                last_letter,
                swara,
                used_ids,
                rule_set=rule_set,
                difficulty=difficulty,
            )
        except TypeError:
            return engine.choose_response_for_end(last_letter, swara, used_ids, rule_set=rule_set)

    # Backward-compatible fallback for older cached engine objects.
    strict_ids = engine.ids_by_first.get(last_letter, []) if last_letter else []
    strict_candidates = [engine.entries_by_id[verse_id] for verse_id in strict_ids if verse_id not in used_ids]
    fallback_candidates = []
    chosen_candidates = strict_candidates
    required_letter = last_letter
    rule_applied = f"{rule_set} (strict)"
    if rule_set == RULE_SET_B and not strict_candidates and swara:
        fallback_ids = engine.ids_by_first.get(swara, [])
        fallback_candidates = [engine.entries_by_id[verse_id] for verse_id in fallback_ids if verse_id not in used_ids]
        chosen_candidates = fallback_candidates
        required_letter = swara
        rule_applied = f"{rule_set} (swara fallback)"

    bot_entry = _pick_with_optional_difficulty(engine, chosen_candidates, used_ids, difficulty) if chosen_candidates else None
    validation_warning = ""
    if bot_entry is not None and required_letter and getattr(bot_entry, "first_letter", None) != required_letter:
        valid_candidates = [entry for entry in chosen_candidates if entry.first_letter == required_letter]
        bot_entry = _pick_with_optional_difficulty(engine, valid_candidates, used_ids, difficulty) if valid_candidates else None
        validation_warning = "Corrected an invalid continuation candidate."
    return {
        "bot_entry": bot_entry,
        "rule_applied": rule_applied,
        "required_letter": required_letter,
        "strict_candidate_count": len(strict_candidates),
        "fallback_candidate_count": len(fallback_candidates),
        "validation_warning": validation_warning,
    }


def _choose_entry_for_start(engine: AntyakshariEngine, first_letter, used_ids, difficulty: str):
    if hasattr(engine, "choose_entry_for_start"):
        try:
            return engine.choose_entry_for_start(first_letter, used_ids, difficulty=difficulty)
        except TypeError:
            return engine.choose_entry_for_start(first_letter, used_ids)
    ids = engine.ids_by_first.get(first_letter, []) if first_letter else []
    candidates = [engine.entries_by_id[verse_id] for verse_id in ids if verse_id not in used_ids]
    return _pick_with_optional_difficulty(engine, candidates, used_ids, difficulty) if candidates else None


def _next_required_start_for_entry(engine: AntyakshariEngine, entry, used_ids, rule_set: str):
    if hasattr(engine, "next_required_start_for_entry"):
        return engine.next_required_start_for_entry(entry, used_ids, rule_set=rule_set)

    strict_ids = engine.ids_by_first.get(entry.last_letter, [])
    strict_candidates = [engine.entries_by_id[verse_id] for verse_id in strict_ids if verse_id not in used_ids]
    if strict_candidates:
        return {
            "required_letter": entry.last_letter,
            "rule_applied": f"{rule_set} (strict)",
            "free_start_allowed": False,
            "candidate_count": len(strict_candidates),
        }

    if rule_set == RULE_SET_B:
        fallback_ids = engine.ids_by_first.get(entry.swara_after_last, [])
        fallback_candidates = [engine.entries_by_id[verse_id] for verse_id in fallback_ids if verse_id not in used_ids]
        if fallback_candidates:
            return {
                "required_letter": entry.swara_after_last,
                "rule_applied": f"{rule_set} (swara fallback)",
                "free_start_allowed": False,
                "candidate_count": len(fallback_candidates),
            }

    return {
        "required_letter": None,
        "rule_applied": f"{rule_set} (no continuation path)",
        "free_start_allowed": True,
        "candidate_count": 0,
    }


def _get_suggestions(
    engine: AntyakshariEngine,
    required_letter,
    used_ids,
    difficulty: str,
    count: int = 3,
):
    if hasattr(engine, "suggest_entries_for_start"):
        try:
            return engine.suggest_entries_for_start(
                required_letter,
                used_ids,
                count=count,
                difficulty=difficulty,
            )
        except TypeError:
            return engine.suggest_entries_for_start(required_letter, used_ids, count=count)

    if required_letter:
        ids = engine.ids_by_first.get(required_letter, [])
        candidates = [engine.entries_by_id[verse_id] for verse_id in ids if verse_id not in used_ids]
    else:
        candidates = [entry for entry in engine.entries if entry.verse_id not in used_ids]

    if not candidates:
        return []

    ranked = sorted(
        candidates,
        key=lambda entry: (
            sum(1 for verse_id in engine.ids_by_first.get(entry.last_letter, []) if verse_id not in used_ids),
            -entry.verse_id,
        ),
        reverse=True,
    )
    return ranked[:count]


def _format_two_line_verse(text: str, width: int = 70) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= width:
        return compact
    first_cut = compact.rfind(" ", 0, width)
    if first_cut == -1:
        first_cut = width
    first = compact[:first_cut].strip()
    remainder = compact[first_cut:].strip()
    if len(remainder) > width:
        second_cut = remainder.rfind(" ", 0, width)
        if second_cut == -1:
            second_cut = width
        second = remainder[:second_cut].strip() + "..."
    else:
        second = remainder
    return f"{first}\n{second}"


def _render_log_table(events) -> None:
    if not events:
        st.info("Start by submitting a verse or passing your turn.")
        return

    rows = []
    for event in reversed(events):  # latest first
        rows.append(
            {
                "#": event.get("event_no", ""),
                "Actor": event.get("actor", ""),
                "Action": event.get("action", ""),
                "Ref": event.get("reference", ""),
                "Req": event.get("required_letter", ""),
                "Last": event.get("detected_last", ""),
                "Swara": event.get("detected_swara", ""),
                "Score": event.get("match_score", ""),
                "Verse": _format_two_line_verse(str(event.get("verse", ""))),
                "Note": event.get("note", ""),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        height=430,
        column_config={
            "Verse": st.column_config.TextColumn("Verse", width="large"),
            "Note": st.column_config.TextColumn("Note", width="large"),
        },
    )


def _update_next_requirement(engine: AntyakshariEngine, bot_entry, rule_set: str) -> None:
    requirement = _next_required_start_for_entry(engine, bot_entry, st.session_state["used_ids"], rule_set=rule_set)
    st.session_state["expected_letter"] = requirement["required_letter"]
    st.session_state["free_start_allowed"] = bool(requirement["free_start_allowed"])
    st.session_state["expected_rule_note"] = str(requirement["rule_applied"])

    if st.session_state["free_start_allowed"]:
        _log_event(
            actor="System",
            action="Free Start Enabled",
            note=(
                "No continuation path exists for the current letter and rule set. "
                "Player may start with any unused verse."
            ),
        )


def _computer_auto_continue(
    engine: AntyakshariEngine,
    rule_set: str,
    difficulty: str,
    tts_enabled: bool,
    yourvoic_api_key: str,
    tts_speaker: str,
    tts_pace: float,
    tts_language_code: str,
) -> None:
    if st.session_state["free_start_allowed"] or not st.session_state["expected_letter"]:
        _log_event(
            actor="System",
            action="No Auto Continue",
            note="Computer cannot auto-continue because no forced continuation letter is active.",
        )
        return

    expected_letter = st.session_state["expected_letter"]
    bot_entry = _choose_entry_for_start(engine, expected_letter, st.session_state["used_ids"], difficulty=difficulty)
    if bot_entry is None:
        st.session_state["expected_letter"] = None
        st.session_state["free_start_allowed"] = True
        st.session_state["expected_rule_note"] = f"{rule_set} (no continuation path)"
        _log_event(
            actor="System",
            action="Free Start Enabled",
            note=(
                f"No unused verse starts with '{expected_letter}'. "
                "Player may start with any unused verse."
            ),
            required_letter=expected_letter,
        )
        return

    st.session_state["used_ids"].add(bot_entry.verse_id)
    _log_event(
        actor="Computer",
        action="Auto Continuation",
        verse=bot_entry.verse,
        reference=_verse_reference(bot_entry),
        required_letter=expected_letter,
        detected_last=bot_entry.last_letter,
        detected_swara=bot_entry.swara_after_last,
        note="Computer continued after player lost the turn.",
    )
    _generate_tts_for_computer_verse(
        verse_text=bot_entry.verse,
        tts_enabled=tts_enabled,
        api_key=yourvoic_api_key,
        speaker=tts_speaker,
        pace=float(tts_pace),
        target_language_code=tts_language_code,
    )
    _update_next_requirement(engine, bot_entry, rule_set)


def _apply_penalty(
    engine: AntyakshariEngine,
    rule_set: str,
    reason: str,
    penalty_kind: str,
    difficulty: str,
    tts_enabled: bool,
    yourvoic_api_key: str,
    tts_speaker: str,
    tts_pace: float,
    tts_language_code: str,
) -> None:
    st.session_state["chances_lost"] += 1
    if penalty_kind == "pass":
        st.session_state["passes_used"] += 1
    else:
        st.session_state["mistakes_used"] += 1

    remaining = MAX_CHANCES - st.session_state["chances_lost"]
    _log_event(
        actor="System",
        action="Chance Lost",
        note=f"{reason} | Chances remaining: {max(remaining, 0)}",
    )

    if st.session_state["chances_lost"] >= MAX_CHANCES:
        st.session_state["game_over"] = True
        _log_event(
            actor="System",
            action="Game Over",
            note="Player lost 3 chances/passes. Game over.",
        )
        return

    _computer_auto_continue(
        engine,
        rule_set,
        difficulty,
        tts_enabled,
        yourvoic_api_key,
        tts_speaker,
        tts_pace,
        tts_language_code,
    )


_init_state()

st.title("Interactive Sanskrit Antyakshari")
st.caption("Rule-aware gameplay with continuation checks, pass limits, and no verse reuse.")

available_corpora = available_corpus_files(".")
if not available_corpora:
    st.error("No corpus CSV files found. Expected one of: BG_info.csv, Narayaneeyam_info.csv, BG_Nar_Info.csv")
    st.stop()

st.sidebar.header("Game Settings")
corpus_label = st.sidebar.selectbox("Corpus", list(available_corpora.keys()), index=0)
corpus_path = available_corpora[corpus_label]
rule_set = st.sidebar.radio(
    "Rule Set",
    [RULE_SET_A, RULE_SET_B],
    help=(
        "A: strict last-letter match only. "
        "B: strict first, fallback to swara only when strict has no continuation."
    ),
)
verse_mode = st.sidebar.radio("Verse Source", [VERSE_MODE_DATASET, VERSE_MODE_OPEN])
difficulty_mode = st.sidebar.selectbox(
    "Computer Difficulty",
    [DIFFICULTY_HARD, DIFFICULTY_MEDIUM, DIFFICULTY_EASY],
    index=0,
    help="Hard prefers strongest continuation, Medium varies among strong options, Easy prefers less optimal valid moves.",
)
practice_mode = st.sidebar.checkbox("Practice Mode (Show Suggestions)", value=False)
input_mode = st.sidebar.radio("Input Mode", ["ASR Recording", "Manual Text"])
min_similarity = st.sidebar.slider(
    "Dataset Match Sensitivity",
    min_value=0.35,
    max_value=0.95,
    value=0.55,
    step=0.05,
)
model_path = st.sidebar.text_input("Local ASR model path", value="./model_200_fixed.pth")
st.sidebar.markdown("---")
tts_enabled = st.sidebar.checkbox("Computer Voice (YourVoic TTS)", value=False)
tts_speaker = st.sidebar.text_input("TTS Voice ID", value="rahul")
tts_pace = st.sidebar.slider("TTS Pace", min_value=0.7, max_value=1.4, value=1.0, step=0.1)
tts_language_code = "hi-IN"
yourvoic_api_key = _get_yourvoic_api_key()
if tts_enabled:
    if yourvoic_api_key:
        st.sidebar.success("YourVoic API key loaded from Streamlit secrets.")
    else:
        st.sidebar.warning("YourVoic API key not found in Streamlit secrets.")

if st.sidebar.button("Reset Game"):
    _reset_game()

active_settings = (corpus_path, rule_set, verse_mode)
if st.session_state["active_settings"] != active_settings:
    st.session_state["active_settings"] = active_settings
    _reset_game()

engine = load_engine(corpus_path)
if not hasattr(engine, "choose_response_for_end"):
    # Clear stale cached resource from older class definition and reload once.
    st.cache_resource.clear()
    engine = load_engine(corpus_path)

if input_mode == "ASR Recording":
    if asr_runtime_available():
        st.sidebar.success("ASR runtime dependencies are available.")
    else:
        st.sidebar.warning(f"ASR runtime unavailable: {ASR_IMPORT_ERROR}")

remaining_chances = MAX_CHANCES - st.session_state["chances_lost"]
status_col1, status_col2, status_col3 = st.columns(3)
status_col1.metric("Chances Remaining", max(remaining_chances, 0), f"Lost: {st.session_state['chances_lost']}")
status_col2.metric("Passes Used", st.session_state["passes_used"], f"Limit: {MAX_CHANCES}")
status_col3.metric("Mistakes Used", st.session_state["mistakes_used"], f"Limit: {MAX_CHANCES}")

if st.session_state["game_over"]:
    st.error("Game over: player has lost 3 chances/passes.")

if st.session_state["free_start_allowed"] or not st.session_state["expected_letter"]:
    st.info("Current requirement: start with any unused verse.")
else:
    st.info(
        f"Current requirement: your verse must start with '{st.session_state['expected_letter']}' "
        f"({st.session_state['expected_rule_note']})."
    )

if practice_mode and not st.session_state["game_over"]:
    hint_letter = None if st.session_state["free_start_allowed"] else st.session_state["expected_letter"]
    if st.button("Show Practice Suggestions"):
        suggestions = _get_suggestions(
            engine,
            hint_letter,
            st.session_state["used_ids"],
            difficulty=difficulty_mode,
            count=3,
        )
        if suggestions:
            st.markdown("**Suggested next verses (Practice mode):**")
            for index, entry in enumerate(suggestions, start=1):
                st.markdown(f"{index}. `{_verse_reference(entry)}`")
                st.write(entry.verse)
        else:
            st.warning("No valid unused suggestions found for the current requirement.")

st.subheader("Your Turn")
audio_bytes = None
if input_mode == "ASR Recording":
    audio_bytes = st.audio_input("Record your verse")
    st.caption("You can also manually correct/replace the transcribed text below before submitting.")

manual_verse = st.text_area("Verse Text (Devanagari)", height=140, placeholder="धर्मक्षेत्रे कुरुक्षेत्रे ...")

button_col1, button_col2 = st.columns(2)
submit_turn = button_col1.button("Submit Verse", type="primary", disabled=st.session_state["game_over"])
pass_turn = button_col2.button("Pass Turn", disabled=st.session_state["game_over"])

if pass_turn and not st.session_state["game_over"]:
    _log_event(actor="Player", action="Pass", note="Player passed this turn.")
    _apply_penalty(
        engine,
        rule_set,
        reason="Player passed turn.",
        penalty_kind="pass",
        difficulty=difficulty_mode,
        tts_enabled=tts_enabled,
        yourvoic_api_key=yourvoic_api_key,
        tts_speaker=tts_speaker,
        tts_pace=float(tts_pace),
        tts_language_code=tts_language_code,
    )

if submit_turn and not st.session_state["game_over"]:
    raw_user_text = ""
    asr_iast = ""
    asr_devanagari = ""

    if input_mode == "ASR Recording" and audio_bytes is not None:
        if not asr_runtime_available():
            st.error(f"ASR dependencies are missing: {ASR_IMPORT_ERROR}")
            st.stop()
        if not Path(model_path).exists():
            st.error(f"ASR model file not found at: {model_path}")
            st.stop()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_bytes.read())
            temp_audio_path = temp_audio.name

        try:
            recognizer = load_asr(str(model_path))
            with st.spinner("Transcribing audio..."):
                asr_result = recognizer.transcribe_audio_to_devanagari(temp_audio_path)
            asr_iast = asr_result["iast"].strip()
            asr_devanagari = asr_result["devanagari"].strip()
            st.session_state["latest_asr_iast"] = asr_iast
            st.session_state["latest_asr_devanagari"] = asr_devanagari
        except Exception as exc:  # pragma: no cover - runtime dependent
            st.error(f"ASR transcription failed: {exc}")
            st.stop()
        finally:
            Path(temp_audio_path).unlink(missing_ok=True)

    manual_text = manual_verse.strip()
    if manual_text:
        raw_user_text = manual_text
    elif asr_devanagari:
        raw_user_text = asr_devanagari
    else:
        st.error("No verse input provided. Record audio or type a verse.")
        st.stop()

    matched_entry, match_score = engine.match_verse(raw_user_text, min_similarity=float(min_similarity))
    matched_in_dataset = matched_entry is not None

    if verse_mode == VERSE_MODE_DATASET and not matched_in_dataset:
        _log_event(
            actor="Player",
            action="Invalid Verse",
            verse=raw_user_text,
            note="No dataset match found above selected sensitivity.",
        )
        _apply_penalty(
            engine,
            rule_set,
            reason="Submitted verse did not match the dataset.",
            penalty_kind="mistake",
            difficulty=difficulty_mode,
            tts_enabled=tts_enabled,
            yourvoic_api_key=yourvoic_api_key,
            tts_speaker=tts_speaker,
            tts_pace=float(tts_pace),
            tts_language_code=tts_language_code,
        )
    else:
        if matched_in_dataset:
            if matched_entry.verse_id in st.session_state["used_ids"]:
                _log_event(
                    actor="Player",
                    action="Invalid Verse",
                    verse=raw_user_text,
                    reference=_verse_reference(matched_entry),
                    note="Matched verse was already used.",
                )
                _apply_penalty(
                    engine,
                    rule_set,
                    reason="Submitted verse was already used.",
                    penalty_kind="mistake",
                    difficulty=difficulty_mode,
                    tts_enabled=tts_enabled,
                    yourvoic_api_key=yourvoic_api_key,
                    tts_speaker=tts_speaker,
                    tts_pace=float(tts_pace),
                    tts_language_code=tts_language_code,
                )
            else:
                player_text = matched_entry.verse
                player_first = matched_entry.first_letter
                player_last = matched_entry.last_letter
                player_swara = matched_entry.swara_after_last

                if (
                    not st.session_state["free_start_allowed"]
                    and st.session_state["expected_letter"]
                    and player_first != st.session_state["expected_letter"]
                ):
                    _log_event(
                        actor="Player",
                        action="Invalid Continuation",
                        verse=player_text,
                        reference=_verse_reference(matched_entry),
                        required_letter=st.session_state["expected_letter"],
                        note=(
                            f"Expected verse starting with '{st.session_state['expected_letter']}', "
                            f"but got '{player_first}'."
                        ),
                    )
                    _apply_penalty(
                        engine,
                        rule_set,
                        reason="Submitted verse was not a continuation of the computer verse.",
                        penalty_kind="mistake",
                        difficulty=difficulty_mode,
                        tts_enabled=tts_enabled,
                        yourvoic_api_key=yourvoic_api_key,
                        tts_speaker=tts_speaker,
                        tts_pace=float(tts_pace),
                        tts_language_code=tts_language_code,
                    )
                else:
                    st.session_state["used_ids"].add(matched_entry.verse_id)
                    correction_note = ""
                    if normalize_devanagari_text(raw_user_text) != normalize_devanagari_text(player_text):
                        correction_note = "ASR/input corrected to closest dataset verse."

                    _log_event(
                        actor="Player",
                        action="Valid Verse",
                        verse=player_text,
                        reference=_verse_reference(matched_entry),
                        detected_last=player_last,
                        detected_swara=player_swara,
                        match_score=round(match_score, 3),
                        note=correction_note,
                    )

                    response = _choose_response_for_end(
                        engine,
                        last_letter=player_last,
                        swara=player_swara,
                        used_ids=st.session_state["used_ids"],
                        rule_set=rule_set,
                        difficulty=difficulty_mode,
                    )
                    bot_entry = response["bot_entry"]
                    required_letter = response.get("required_letter")
                    if bot_entry is not None and required_letter and bot_entry.first_letter != required_letter:
                        _log_event(
                            actor="System",
                            action="Computer Move Corrected",
                            note=(
                                f"Rejected invalid computer move '{bot_entry.first_letter}' for required '{required_letter}'."
                            ),
                        )
                        bot_entry = None

                    if response.get("validation_warning"):
                        _log_event(
                            actor="System",
                            action="Computer Move Corrected",
                            note=str(response["validation_warning"]),
                        )

                    if bot_entry is None:
                        st.session_state["expected_letter"] = None
                        st.session_state["free_start_allowed"] = True
                        st.session_state["expected_rule_note"] = str(response["rule_applied"])
                        _log_event(
                            actor="System",
                            action="Free Start Enabled",
                            required_letter=response["required_letter"] or "",
                            note=(
                                "No continuation found for player verse ending. "
                                "Player may start with any unused verse."
                            ),
                        )
                    else:
                        st.session_state["used_ids"].add(bot_entry.verse_id)
                        _log_event(
                            actor="Computer",
                            action="Response Verse",
                            verse=bot_entry.verse,
                            reference=_verse_reference(bot_entry),
                            required_letter=response["required_letter"] or "",
                            detected_last=bot_entry.last_letter,
                            detected_swara=bot_entry.swara_after_last,
                            note=str(response["rule_applied"]),
                        )
                        _generate_tts_for_computer_verse(
                            verse_text=bot_entry.verse,
                            tts_enabled=tts_enabled,
                            api_key=yourvoic_api_key,
                            speaker=tts_speaker,
                            pace=float(tts_pace),
                            target_language_code=tts_language_code,
                        )
                        _update_next_requirement(engine, bot_entry, rule_set)
        else:
            player_text = raw_user_text
            normalized_custom = normalize_devanagari_text(player_text)

            if not normalized_custom:
                _log_event(
                    actor="Player",
                    action="Invalid Verse",
                    verse=player_text,
                    note="Could not detect Devanagari text.",
                )
                _apply_penalty(
                    engine,
                    rule_set,
                    reason="Could not detect a valid Devanagari verse.",
                    penalty_kind="mistake",
                    difficulty=difficulty_mode,
                    tts_enabled=tts_enabled,
                    yourvoic_api_key=yourvoic_api_key,
                    tts_speaker=tts_speaker,
                    tts_pace=float(tts_pace),
                    tts_language_code=tts_language_code,
                )
            elif normalized_custom in st.session_state["used_custom_texts"]:
                _log_event(
                    actor="Player",
                    action="Invalid Verse",
                    verse=player_text,
                    note="Custom verse was already used.",
                )
                _apply_penalty(
                    engine,
                    rule_set,
                    reason="Custom verse was already used.",
                    penalty_kind="mistake",
                    difficulty=difficulty_mode,
                    tts_enabled=tts_enabled,
                    yourvoic_api_key=yourvoic_api_key,
                    tts_speaker=tts_speaker,
                    tts_pace=float(tts_pace),
                    tts_language_code=tts_language_code,
                )
            else:
                player_first = infer_first_letter(player_text)
                player_last, player_swara = infer_last_letter_and_swara(player_text)
                if not player_first or not player_last:
                    _log_event(
                        actor="Player",
                        action="Invalid Verse",
                        verse=player_text,
                        note="Could not infer first/last playable letters.",
                    )
                    _apply_penalty(
                        engine,
                        rule_set,
                        reason="Could not infer continuation letters from verse.",
                        penalty_kind="mistake",
                        difficulty=difficulty_mode,
                        tts_enabled=tts_enabled,
                        yourvoic_api_key=yourvoic_api_key,
                        tts_speaker=tts_speaker,
                        tts_pace=float(tts_pace),
                        tts_language_code=tts_language_code,
                    )
                elif (
                    not st.session_state["free_start_allowed"]
                    and st.session_state["expected_letter"]
                    and player_first != st.session_state["expected_letter"]
                ):
                    _log_event(
                        actor="Player",
                        action="Invalid Continuation",
                        verse=player_text,
                        required_letter=st.session_state["expected_letter"],
                        note=(
                            f"Expected verse starting with '{st.session_state['expected_letter']}', "
                            f"but got '{player_first}'."
                        ),
                    )
                    _apply_penalty(
                        engine,
                        rule_set,
                        reason="Submitted verse was not a continuation of the computer verse.",
                        penalty_kind="mistake",
                        difficulty=difficulty_mode,
                        tts_enabled=tts_enabled,
                        yourvoic_api_key=yourvoic_api_key,
                        tts_speaker=tts_speaker,
                        tts_pace=float(tts_pace),
                        tts_language_code=tts_language_code,
                    )
                else:
                    st.session_state["used_custom_texts"].add(normalized_custom)
                    _log_event(
                        actor="Player",
                        action="Valid Verse",
                        verse=player_text,
                        detected_last=player_last,
                        detected_swara=player_swara,
                        note="Played as non-dataset verse.",
                    )

                    response = _choose_response_for_end(
                        engine,
                        last_letter=player_last,
                        swara=player_swara,
                        used_ids=st.session_state["used_ids"],
                        rule_set=rule_set,
                        difficulty=difficulty_mode,
                    )
                    bot_entry = response["bot_entry"]
                    required_letter = response.get("required_letter")
                    if bot_entry is not None and required_letter and bot_entry.first_letter != required_letter:
                        _log_event(
                            actor="System",
                            action="Computer Move Corrected",
                            note=(
                                f"Rejected invalid computer move '{bot_entry.first_letter}' for required '{required_letter}'."
                            ),
                        )
                        bot_entry = None

                    if response.get("validation_warning"):
                        _log_event(
                            actor="System",
                            action="Computer Move Corrected",
                            note=str(response["validation_warning"]),
                        )
                    if bot_entry is None:
                        st.session_state["expected_letter"] = None
                        st.session_state["free_start_allowed"] = True
                        st.session_state["expected_rule_note"] = str(response["rule_applied"])
                        _log_event(
                            actor="System",
                            action="Free Start Enabled",
                            required_letter=response["required_letter"] or "",
                            note=(
                                "No continuation found for player verse ending. "
                                "Player may start with any unused verse."
                            ),
                        )
                    else:
                        st.session_state["used_ids"].add(bot_entry.verse_id)
                        _log_event(
                            actor="Computer",
                            action="Response Verse",
                            verse=bot_entry.verse,
                            reference=_verse_reference(bot_entry),
                            required_letter=response["required_letter"] or "",
                            detected_last=bot_entry.last_letter,
                            detected_swara=bot_entry.swara_after_last,
                            note=str(response["rule_applied"]),
                        )
                        _generate_tts_for_computer_verse(
                            verse_text=bot_entry.verse,
                            tts_enabled=tts_enabled,
                            api_key=yourvoic_api_key,
                            speaker=tts_speaker,
                            pace=float(tts_pace),
                            target_language_code=tts_language_code,
                        )
                        _update_next_requirement(engine, bot_entry, rule_set)

if st.session_state["events"]:
    last_event = st.session_state["events"][-1]
    if last_event["actor"] == "System" and last_event["action"] == "Game Over":
        st.error(last_event["note"])
    elif last_event["actor"] == "System" and last_event["action"] == "Chance Lost":
        st.warning(last_event["note"])
    elif last_event["actor"] == "Computer" and last_event["action"] in {"Response Verse", "Auto Continuation"}:
        st.success("Computer played a continuation verse.")
    elif last_event["actor"] == "Player" and last_event["action"] == "Valid Verse":
        st.success("Player verse accepted.")

    if st.session_state.get("latest_tts_audio"):
        st.markdown("**Computer Recitation (TTS)**")
        tts_format = st.session_state.get("latest_tts_mime") or "audio/mpeg"
        st.audio(st.session_state["latest_tts_audio"], format=tts_format)
    elif tts_enabled and st.session_state.get("latest_tts_error"):
        st.caption(f"TTS status: {st.session_state['latest_tts_error']}")

    st.subheader("Game Log")
    st.caption("Latest turns are shown first. Scroll to view older turns.")
    _render_log_table(st.session_state["events"])
else:
    _render_log_table(st.session_state["events"])
