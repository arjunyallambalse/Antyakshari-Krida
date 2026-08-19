import os
import torch
from transformers import pipeline

MODEL_NAME = "prathoshap/sushrota-sanskrit-asr"

print("Loading Sushrota Sanskrit ASR...")

try:
    asr_pipeline = pipeline(
        "automatic-speech-recognition",
        model=MODEL_NAME,
        device=0 if torch.cuda.is_available() else -1
    )

    print("SUCCESS: Sushrota ASR loaded.")

except Exception as e:
    print("ERROR: Sushrota ASR failed to load.")
    print(f"ASR LOAD ERROR: {type(e).__name__}: {e}")
    asr_pipeline = None


def transcribe_audio(audio_file_path: str) -> str:

    print(f"ASR: Received audio file: {audio_file_path}")

    if not audio_file_path:
        print("ASR ERROR: No audio path received.")
        return ""

    if not os.path.exists(audio_file_path):
        print(f"ASR ERROR: File does not exist: {audio_file_path}")
        return ""

    file_size = os.path.getsize(audio_file_path)
    print(f"ASR: Audio file size = {file_size} bytes")

    if file_size == 0:
        print("ASR ERROR: Audio file is empty.")
        return ""

    if asr_pipeline is None:
        print("ASR ERROR: Sushrota pipeline was not initialized.")
        return ""

    try:
        print("ASR: Starting Sushrota transcription...")

        result = asr_pipeline(audio_file_path)

        print(f"ASR RAW RESULT: {result}")

        if isinstance(result, dict):
            text = result.get("text", "")
        elif isinstance(result, list) and result:
            first_result = result[0]

            if isinstance(first_result, dict):
                text = first_result.get("text", "")
            else:
                text = str(first_result)
        else:
            text = str(result) if result is not None else ""

        text = text.strip()

        print(f"ASR TRANSCRIPTION: {text}")

        return text

    except Exception as e:
        print("ASR ERROR: Transcription failed.")
        print(f"ASR TRANSCRIPTION ERROR: {type(e).__name__}: {e}")
        return ""
