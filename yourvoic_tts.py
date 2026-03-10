#!/usr/bin/env python3
"""
YourVoic Text-to-Speech integration helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests


YOURVOIC_TTS_URL = "https://yourvoic.com/api/v1/tts/generate"


@dataclass
class YourVoicTTSResult:
    ok: bool
    audio_bytes: Optional[bytes] = None
    content_type: Optional[str] = None
    error: Optional[str] = None


def synthesize_yourvoic_tts(
    text: str,
    api_key: str,
    voice: str = "Deepti",
    language: str = "sa-IN",
    model: str = "aura-lite",
    speed: float = 1.0,
    audio_format: str = "mp3",
    timeout_seconds: int = 45,
) -> YourVoicTTSResult:
    if not api_key:
        return YourVoicTTSResult(ok=False, error="Missing YourVoic API key.")
    if not text or not text.strip():
        return YourVoicTTSResult(ok=False, error="Empty text for TTS.")

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text.strip(),
        "voice": voice,
        "language": language,
        "model": model,
        "speed": speed,
        "format": audio_format,
    }

    try:
        response = requests.post(
            YOURVOIC_TTS_URL,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
    except requests.RequestException as exc:
        return YourVoicTTSResult(ok=False, error=f"TTS request failed: {exc}")

    if response.status_code != 200:
        try:
            body = response.json()
        except ValueError:
            body = {"message": response.text}
        message = body.get("message") or body.get("error") or str(body)
        return YourVoicTTSResult(ok=False, error=f"TTS API error {response.status_code}: {message}")

    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type.lower():
        try:
            body = response.json()
        except ValueError:
            body = {"message": response.text}
        message = body.get("message") or body.get("error") or str(body)
        return YourVoicTTSResult(ok=False, error=f"TTS API returned JSON instead of audio: {message}")

    return YourVoicTTSResult(ok=True, audio_bytes=response.content, content_type=content_type)
