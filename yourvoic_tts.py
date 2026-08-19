import os
import importlib.util
from pathlib import Path

import requests


VAGDHENU_API_URL = os.environ.get(
    "VAGDHENU_API_URL",
    ""
).strip()


def tts_available() -> bool:
    """
    TTS is available if either:

    1. A remote Vāgdhenu API endpoint is configured, or
    2. A local vagdhenu Python module is installed.

    This function must never crash the Streamlit app.
    """

    if VAGDHENU_API_URL:
        return True

    try:
        return importlib.util.find_spec("vagdhenu") is not None
    except Exception:
        return False


def generate_speech(
    text: str,
    output_path: str = "computer_response.wav",
) -> str:
    """
    Generate Sanskrit speech using Vāgdhenu.

    Priority:
    1. Remote Vāgdhenu API
    2. Local Vāgdhenu installation
    3. Return empty string without crashing the game
    """

    if not text or not text.strip():
        return ""

    # ========================================================
    # OPTION 1: REMOTE VAGDHENU
    # ========================================================

    if VAGDHENU_API_URL:

        try:
            response = requests.post(
                VAGDHENU_API_URL,
                json={
                    "text": text.strip(),
                    "language": "sa",
                },
                timeout=180,
            )

            response.raise_for_status()

            content_type = (
                response.headers
                .get("content-type", "")
                .lower()
            )

            # Direct audio response
            if "audio" in content_type:

                Path(output_path).write_bytes(
                    response.content
                )

                return output_path

            # JSON response containing audio URL
            data = response.json()

            audio_url = (
                data.get("audio_url")
                or data.get("url")
            )

            if audio_url:

                audio_response = requests.get(
                    audio_url,
                    timeout=180,
                )

                audio_response.raise_for_status()

                Path(output_path).write_bytes(
                    audio_response.content
                )

                return output_path

        except Exception as exc:

            print(
                "Remote Vagdhenu error: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )


    # ========================================================
    # OPTION 2: LOCAL VAGDHENU
    # ========================================================

    try:
        from vagdhenu import VagdhenuTTS

        engine = VagdhenuTTS()

        engine.synthesize(
            text=text.strip(),
            output_file=output_path,
        )

        if os.path.exists(output_path):
            return output_path

    except ImportError:

        print(
            "Vagdhenu is not installed locally.",
            flush=True,
        )

    except Exception as exc:

        print(
            "Local Vagdhenu error: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )


    # TTS failure should NEVER stop Antyakshari gameplay
    return ""
