import os
import torch
from transformers import pipeline

try:
    asr_pipeline = pipeline(
        "automatic-speech-recognition",
        model="prathoshap/sushrota-sanskrit-asr",
        device=0 if torch.cuda.is_available() else -1
    )
except Exception as e:
    print(f"Could not load Sushrota model: {e}")
    asr_pipeline = None


def transcribe_audio(audio_file_path: str) -> str:
    if not audio_file_path or not os.path.exists(audio_file_path):
        print(f"File not found: {audio_file_path}")
        return ""

    if asr_pipeline is None:
        print("ASR pipeline is not initialized.")
        return ""

    try:
        result = asr_pipeline(audio_file_path)

        if isinstance(result, dict) and "text" in result:
            return result["text"].strip()

        elif isinstance(result, list) and len(result) > 0 and "text" in result[0]:
            return result[0]["text"].strip()

        return str(result).strip()

    except Exception as e:
        print(f"Error during Sushrota transcription: {e}")
        return ""
    if not audio_file_path or not os.path.exists(audio_file_path):
        print(f"File not found: {audio_file_path}")
        return ""

    if asr_pipeline is None:
        print("ASR pipeline is not initialized.")
        return ""

    try:
        result = asr_pipeline(audio_file_path)
        # Handle pipeline return formats safely
        if isinstance(result, dict) and "text" in result:
            return result["text"].strip()
        elif isinstance(result, list) and len(result) > 0 and "text" in result[0]:
            return result[0]["text"].strip()
        return str(result).strip()
    except Exception as e:
        print(f"Error during Sushrota transcription: {e}")
        return ""
