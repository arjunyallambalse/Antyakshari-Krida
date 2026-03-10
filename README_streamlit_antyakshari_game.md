# Sanskrit Antyakshari Streamlit Game

## Run locally

1. Install dependencies:
```bash
pip install -r requirements_streamlit_game.txt
```
2. Keep the corpus CSVs in this folder (`BG_info.csv`, `Narayaneeyam_info.csv`, or `BG_Nar_Info.csv`).
3. (Optional for ASR mode) Place `model_200_fixed.pth` in this folder.
4. (Optional for computer voice) add YourVoic key in `.streamlit/secrets.toml`:
```toml
[yourvoic]
api_key = "YOUR_KEY_HERE"
```
5. Start app:
```bash
streamlit run streamlit_antyakshari_game.py
```

## Features

- Rule Set `A`: strict `last_letter -> first_letter` matching.
- Rule Set `B`: strict first, with `swara_after_last` fallback only when strict has no move.
- Computer difficulty:
  - `Hard`: strongest continuation (best-path bias).
  - `Medium`: varied among strong valid options.
  - `Easy`: valid but less optimal continuation choices.
- Practice mode:
  - suggest up to 3 valid next verses when the player needs help.
- Computer recitation (TTS):
  - optional YourVoic TTS integration for computer verses.
  - uses `hi-IN` language setting for Sanskrit-style recitation.
  - set `TTS Voice ID` in the sidebar.
- Verse source modes:
  - `Within Dataset Only`: player verse must match a corpus verse (with selected sensitivity).
  - `Allow Other Verses`: player may use non-dataset verses too.
- ASR typo/error handling in dataset mode:
  - closest matching verse is used as corrected text for continuation.
- No reuse:
  - dataset verses already used by player/computer are blocked.
  - custom non-dataset verses are also blocked from reuse.
- Turn-loss and game-over logic:
  - player can pass, but pass consumes a chance.
  - invalid/mistaken verses also consume a chance.
  - total `3` lost chances (pass + mistakes combined) ends the game.
- Continuation enforcement:
  - player verse must continue from the computer’s previous verse.
  - if no continuation path exists for current letter/rule set, player can start with any unused verse.
- Game log view:
  - latest turns are visible first, with two-line verse previews.
  - log area is scrollable to inspect older turns.
- Input modes:
  - `ASR Recording` (local Sanskrit STT model)
  - `Manual Text` (Devanagari verse input)
- Corpus selection:
  - Bhagavad Gita
  - Narayaneeyam
  - Combined
