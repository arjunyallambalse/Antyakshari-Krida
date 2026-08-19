from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

try:
    from gradio_client import Client
except Exception:
    Client = None


def _setting(name: str, default: str = "") -> str:
    value = os.environ.get(name, "")

    if value:
        return value.strip()

    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()

    except Exception:
        pass

    return default.strip()


# Official public Vāgdhenu ZeroGPU Space.
# You can later replace this with your own duplicated Space.
VAGDHENU_SPACE_ID = _setting(
    "VAGDHENU_SPACE_ID",
    "prathoshap/vagdhenu-demo",
)

# Optional. Public Space normally does not require this.
HF_TOKEN = _setting(
    "HF_TOKEN",
    "",
)

VAGDHENU_API_NAME = "/synthesize"

# Vāgdhenu's demo uses this value for automatic meter detection.
VAGDHENU_METER = "__auto__"

# Same default seed used by the official demo.
VAGDHENU_SEED = 60

_CLIENT = None
_LAST_ERROR = ""


def _set_error(message: str) -> None:
    global _LAST_ERROR

    _LAST_ERROR = message

    if message:
        print(
            f"Vagdhenu TTS: {message}",
            flush=True,
        )


def get_last_tts_error() -> str:
    return _LAST_ERROR


def tts_available() -> bool:
    """
    Return True when the Gradio client is installed
    and a Vāgdhenu Space is configured.
    """

    return (
        Client is not None
        and bool(VAGDHENU_SPACE_ID)
    )


def _get_client():
    global _CLIENT

    if _CLIENT is not None:
        return _CLIENT

    if Client is None:
        raise RuntimeError(
            "gradio_client is not installed."
        )

    kwargs = {
        "verbose": False,
    }

    if HF_TOKEN:
        kwargs["token"] = HF_TOKEN

    _CLIENT = Client(
        VAGDHENU_SPACE_ID,
        **kwargs,
    )

    return _CLIENT


def _find_audio_path(
    value: Any,
) -> str:
    """
    Find the downloaded audio path returned by
    the Gradio client.

    Handles strings, Path objects, FileData-like
    objects and dictionaries.
    """

    if value is None:
        return ""

    if isinstance(
        value,
        (str, Path),
    ):
        return str(value)

    if isinstance(
        value,
        dict,
    ):
        for key in (
            "path",
            "name",
            "url",
        ):
            candidate = value.get(key)

            if candidate:
                found = _find_audio_path(
                    candidate
                )

                if found:
                    return found

    if isinstance(
        value,
        (list, tuple),
    ):
        for item in value:
            found = _find_audio_path(
                item
            )

            if found:
                return found

    for attr in (
        "path",
        "name",
    ):
        if hasattr(
            value,
            attr,
        ):
            found = _find_audio_path(
                getattr(
                    value,
                    attr,
                )
            )

            if found:
                return found

    return ""


def generate_speech(
    text: str,
    output_path: str = "computer_response.wav",
) -> str:
    """
    Generate Sanskrit chant using the official
    Vāgdhenu Hugging Face ZeroGPU Space.

    Returns output_path on success.

    TTS failure never crashes the Antyakshari game.
    """

    _set_error("")

    text = (
        text
        or ""
    ).strip()

    if not text:

        _set_error(
            "No text was provided."
        )

        return ""

    if not tts_available():

        _set_error(
            "gradio_client is not installed "
            "or the Vāgdhenu Space ID is empty."
        )

        return ""

    try:

        client = _get_client()

        print(
            "Vagdhenu TTS: sending verse...",
            flush=True,
        )

        result = client.predict(
            text,
            VAGDHENU_METER,
            VAGDHENU_SEED,
            api_name=VAGDHENU_API_NAME,
        )

        # Vāgdhenu returns:
        #
        # (
        #     audio,
        #     meter/status text
        # )
        #
        # so result[0] is the audio output.

        audio_result = (
            result[0]
            if isinstance(
                result,
                (list, tuple),
            )
            and result
            else result
        )

        source_path = (
            _find_audio_path(
                audio_result
            )
        )

        if not source_path:

            _set_error(
                "Vāgdhenu returned no audio file."
            )

            return ""

        destination = Path(
            output_path
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        source = Path(
            source_path
        )

        # Gradio normally downloads the audio
        # and returns a local path.
        if source.exists():

            shutil.copyfile(
                source,
                destination,
            )

            print(
                f"Vagdhenu TTS: "
                f"saved {destination}",
                flush=True,
            )

            return str(
                destination
            )

        # Compatibility fallback in case a client
        # returns a remote URL instead.
        if source_path.startswith(
            (
                "http://",
                "https://",
            )
        ):

            import requests

            response = requests.get(
                source_path,
                timeout=180,
            )

            response.raise_for_status()

            destination.write_bytes(
                response.content
            )

            return str(
                destination
            )

        _set_error(
            "Returned audio file "
            f"was not found: {source_path}"
        )

        return ""

    except Exception as exc:

        _set_error(
            f"{type(exc).__name__}: {exc}"
        )

        return ""
