#!/usr/bin/env python3
"""
Core game logic for Sanskrit Antyakshari.

Rule set A:
- Strict matching only: next verse must start with the previous verse's last letter.

Rule set B:
- Same as A by default.
- If no strict continuation exists, fallback to "swara after last".
"""

from __future__ import annotations

import csv
import random
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple


RULE_SET_A = "A"
RULE_SET_B = "B"

DIFFICULTY_HARD = "Hard"
DIFFICULTY_MEDIUM = "Medium"
DIFFICULTY_EASY = "Easy"


DEVANAGARI_RANGE_RE = re.compile(r"[^\u0900-\u097F]+")

INDEPENDENT_VOWELS = {"अ", "आ", "इ", "ई", "उ", "ऊ", "ऋ", "ॠ", "ऌ", "ॡ", "ए", "ऐ", "ओ", "औ"}
VOWEL_SIGNS_TO_SWARA = {
    "ा": "आ",
    "ि": "इ",
    "ी": "ई",
    "ु": "उ",
    "ू": "ऊ",
    "ृ": "ऋ",
    "ॄ": "ॠ",
    "ॢ": "ऌ",
    "ॣ": "ॡ",
    "े": "ए",
    "ै": "ऐ",
    "ो": "ओ",
    "ौ": "औ",
}
CONSONANTS = {
    "क", "ख", "ग", "घ", "ङ",
    "च", "छ", "ज", "झ", "ञ",
    "ट", "ठ", "ड", "ढ", "ण",
    "त", "थ", "द", "ध", "न",
    "प", "फ", "ब", "भ", "म",
    "य", "र", "ल", "व",
    "श", "ष", "स", "ह",
}


@dataclass(frozen=True)
class VerseEntry:
    verse_id: int
    verse: str
    first_letter: str
    last_letter: str
    swara_after_last: str
    chapter: str
    verse_number: str
    cumulative_number: str
    normalized_verse: str


def normalize_devanagari_text(text: str) -> str:
    """Keep Devanagari letters only for robust fuzzy matching."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("।", " ").replace("॥", " ")
    return DEVANAGARI_RANGE_RE.sub("", text)


def infer_last_letter_and_swara(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fallback extractor when verse match is unavailable.

    This is intentionally lightweight and best-effort:
    - looks for a trailing matra + consonant pattern
    - otherwise uses trailing consonant with implicit "अ"
    - otherwise trailing independent vowel
    """

    filtered = [ch for ch in text if "\u0900" <= ch <= "\u097F"]
    if not filtered:
        return None, None

    pending_swara: Optional[str] = None
    for ch in reversed(filtered):
        if ch in {"ं", "ः", "ँ", "्"}:
            continue
        if ch in VOWEL_SIGNS_TO_SWARA:
            pending_swara = VOWEL_SIGNS_TO_SWARA[ch]
            continue
        if ch in CONSONANTS:
            return ch, pending_swara or "अ"
        if ch in INDEPENDENT_VOWELS:
            return ch, ch

    return None, None


def infer_first_letter(text: str) -> Optional[str]:
    """Best-effort first playable Devanagari letter extractor."""
    filtered = [ch for ch in text if "\u0900" <= ch <= "\u097F"]
    for ch in filtered:
        if ch in {"ं", "ः", "ँ", "्"}:
            continue
        if ch in CONSONANTS or ch in INDEPENDENT_VOWELS:
            return ch
    return None


class AntyakshariEngine:
    def __init__(self, csv_path: str | Path):
        self.csv_path = str(csv_path)
        self.entries: List[VerseEntry] = self._load_entries(self.csv_path)
        self.entries_by_id: Dict[int, VerseEntry] = {entry.verse_id: entry for entry in self.entries}
        self.ids_by_first: Dict[str, List[int]] = {}
        self.ids_by_normalized_text: Dict[str, List[int]] = {}

        for entry in self.entries:
            self.ids_by_first.setdefault(entry.first_letter, []).append(entry.verse_id)
            self.ids_by_normalized_text.setdefault(entry.normalized_verse, []).append(entry.verse_id)

    @staticmethod
    def _load_entries(csv_path: str) -> List[VerseEntry]:
        rows: List[VerseEntry] = []
        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                verse = (row.get("Verse") or "").strip()
                first_letter = (row.get("First Letter") or "").strip()
                last_letter = (row.get("Last Letter") or "").strip()
                swara_after_last = (row.get("Swara After Last") or "").strip()
                chapter = (row.get("Chapter") or "").strip()
                verse_number = (row.get("Verse Number") or "").strip()
                cumulative_number = (row.get("Cumulative Number") or "").strip()
                normalized = normalize_devanagari_text(verse)
                verse_id = int(cumulative_number) if cumulative_number.isdigit() else len(rows) + 1
                rows.append(
                    VerseEntry(
                        verse_id=verse_id,
                        verse=verse,
                        first_letter=first_letter,
                        last_letter=last_letter,
                        swara_after_last=swara_after_last,
                        chapter=chapter,
                        verse_number=verse_number,
                        cumulative_number=cumulative_number,
                        normalized_verse=normalized,
                    )
                )
        return rows

    def match_verse(self, input_text: str, min_similarity: float = 0.55) -> Tuple[Optional[VerseEntry], float]:
        normalized = normalize_devanagari_text(input_text)
        if not normalized:
            return None, 0.0

        exact_ids = self.ids_by_normalized_text.get(normalized)
        if exact_ids:
            return self.entries_by_id[exact_ids[0]], 1.0

        best_entry: Optional[VerseEntry] = None
        best_score = 0.0
        input_len = len(normalized)

        for entry in self.entries:
            candidate_len = len(entry.normalized_verse)
            if candidate_len == 0:
                continue
            if abs(candidate_len - input_len) > max(candidate_len, input_len) * 0.65:
                continue
            score = SequenceMatcher(None, normalized, entry.normalized_verse).ratio()
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry is None or best_score < min_similarity:
            return None, best_score
        return best_entry, best_score

    def _available_entries(self, verse_ids: Sequence[int], used_ids: Set[int]) -> List[VerseEntry]:
        return [self.entries_by_id[verse_id] for verse_id in verse_ids if verse_id not in used_ids]

    def _future_options_score(self, entry: VerseEntry, used_ids: Set[int]) -> Tuple[int, int]:
        strict_next = self.ids_by_first.get(entry.last_letter, [])
        swara_next = self.ids_by_first.get(entry.swara_after_last, [])
        strict_available = sum(1 for verse_id in strict_next if verse_id not in used_ids)
        swara_available = sum(1 for verse_id in swara_next if verse_id not in used_ids)
        return strict_available, swara_available

    def _pick_response(
        self,
        candidates: Sequence[VerseEntry],
        used_ids: Set[int],
        difficulty: str = DIFFICULTY_HARD,
    ) -> Optional[VerseEntry]:
        if not candidates:
            return None
        ranked = sorted(
            candidates,
            key=lambda entry: (
                self._future_options_score(entry, used_ids),
                -entry.verse_id,
            ),
            reverse=True,
        )
        if difficulty == DIFFICULTY_HARD or len(ranked) == 1:
            return ranked[0]

        if difficulty == DIFFICULTY_MEDIUM:
            top_n = min(5, len(ranked))
            top_pool = ranked[:top_n]
            weights = list(range(top_n, 0, -1))
            return random.choices(top_pool, weights=weights, k=1)[0]

        # Easy: bias toward less optimal valid choices.
        lower_start = max(1, len(ranked) // 2)
        lower_pool = ranked[lower_start:]
        if not lower_pool:
            lower_pool = ranked
        return random.choice(lower_pool)

    def get_unused_candidates_for_start(self, first_letter: Optional[str], used_ids: Set[int]) -> List[VerseEntry]:
        if first_letter:
            ids = self.ids_by_first.get(first_letter, [])
            return self._available_entries(ids, used_ids)
        return [entry for entry in self.entries if entry.verse_id not in used_ids]

    def choose_entry_for_start(
        self,
        first_letter: Optional[str],
        used_ids: Set[int],
        difficulty: str = DIFFICULTY_HARD,
    ) -> Optional[VerseEntry]:
        candidates = self.get_unused_candidates_for_start(first_letter, used_ids)
        return self._pick_response(candidates, used_ids, difficulty=difficulty)

    def suggest_entries_for_start(
        self,
        first_letter: Optional[str],
        used_ids: Set[int],
        count: int = 3,
        difficulty: str = DIFFICULTY_HARD,
    ) -> List[VerseEntry]:
        candidates = self.get_unused_candidates_for_start(first_letter, used_ids)
        if not candidates:
            return []
        ranked = sorted(
            candidates,
            key=lambda entry: (
                self._future_options_score(entry, used_ids),
                -entry.verse_id,
            ),
            reverse=True,
        )
        if difficulty == DIFFICULTY_HARD:
            return ranked[:count]
        if difficulty == DIFFICULTY_MEDIUM:
            top_pool = ranked[: min(len(ranked), max(count * 2, 4))]
            random.shuffle(top_pool)
            return top_pool[:count]
        lower_start = max(1, len(ranked) // 2)
        lower_pool = ranked[lower_start:] or ranked
        random.shuffle(lower_pool)
        return lower_pool[:count]

    def choose_response_for_end(
        self,
        last_letter: Optional[str],
        swara: Optional[str],
        used_ids: Set[int],
        rule_set: str = RULE_SET_A,
        difficulty: str = DIFFICULTY_HARD,
    ) -> Dict[str, object]:
        strict_candidates = self.get_unused_candidates_for_start(last_letter, used_ids)
        fallback_candidates: List[VerseEntry] = []
        chosen_candidates = strict_candidates
        rule_applied = f"{rule_set} (strict)"
        required_letter = last_letter

        if rule_set == RULE_SET_B and not strict_candidates and swara:
            fallback_candidates = self.get_unused_candidates_for_start(swara, used_ids)
            chosen_candidates = fallback_candidates
            required_letter = swara
            rule_applied = f"{rule_set} (swara fallback)"

        bot_entry = self._pick_response(chosen_candidates, used_ids, difficulty=difficulty)
        validation_warning = ""
        if bot_entry is not None and required_letter and bot_entry.first_letter != required_letter:
            valid_candidates = [entry for entry in chosen_candidates if entry.first_letter == required_letter]
            bot_entry = self._pick_response(valid_candidates, used_ids, difficulty=difficulty)
            validation_warning = (
                "Corrected an invalid candidate choice to enforce first-letter continuation."
            )
        return {
            "bot_entry": bot_entry,
            "rule_applied": rule_applied,
            "required_letter": required_letter,
            "strict_candidate_count": len(strict_candidates),
            "fallback_candidate_count": len(fallback_candidates),
            "validation_warning": validation_warning,
        }

    def next_required_start_for_entry(
        self,
        entry: VerseEntry,
        used_ids: Set[int],
        rule_set: str = RULE_SET_A,
    ) -> Dict[str, object]:
        strict_candidates = self.get_unused_candidates_for_start(entry.last_letter, used_ids)
        if strict_candidates:
            return {
                "required_letter": entry.last_letter,
                "rule_applied": f"{rule_set} (strict)",
                "free_start_allowed": False,
                "candidate_count": len(strict_candidates),
            }

        if rule_set == RULE_SET_B:
            fallback_candidates = self.get_unused_candidates_for_start(entry.swara_after_last, used_ids)
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

    def play_turn(
        self,
        user_text: str,
        used_ids: Set[int],
        rule_set: str = RULE_SET_A,
        min_similarity: float = 0.55,
        difficulty: str = DIFFICULTY_HARD,
    ) -> Dict[str, object]:
        """
        Process one user turn and select model response.
        """

        matched_entry, match_score = self.match_verse(user_text, min_similarity=min_similarity)
        user_verse_id = matched_entry.verse_id if matched_entry else None

        if matched_entry:
            last_letter = matched_entry.last_letter
            swara = matched_entry.swara_after_last
        else:
            last_letter, swara = infer_last_letter_and_swara(user_text)

        response = self.choose_response_for_end(
            last_letter,
            swara,
            used_ids,
            rule_set=rule_set,
            difficulty=difficulty,
        )

        return {
            "matched_entry": matched_entry,
            "match_score": match_score,
            "user_verse_id": user_verse_id,
            "detected_last_letter": last_letter,
            "detected_swara": swara,
            "required_letter": response["required_letter"],
            "rule_applied": response["rule_applied"],
            "strict_candidate_count": response["strict_candidate_count"],
            "fallback_candidate_count": response["fallback_candidate_count"],
            "bot_entry": response["bot_entry"],
            "validation_warning": response["validation_warning"],
        }


CORPUS_OPTIONS = {
    "Bhagavad Gita": "BG_info.csv",
    "Narayaneeyam": "Narayaneeyam_info.csv",
    "Combined (BG + Narayaneeyam)": "BG_Nar_Info.csv",
}


def available_corpus_files(base_dir: str | Path) -> Dict[str, str]:
    base = Path(base_dir)
    existing: Dict[str, str] = {}
    for label, rel_path in CORPUS_OPTIONS.items():
        absolute = base / rel_path
        if absolute.exists():
            existing[label] = str(absolute)
    return existing
