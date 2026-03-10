#!/usr/bin/env python3
"""
Local Sanskrit ASR wrapper + transliteration bridge (IAST-like -> Devanagari).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ASR_IMPORT_ERROR: Optional[Exception] = None

try:
    import numpy as np
    import soundfile as sf
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torchaudio
except Exception as exc:  # pragma: no cover - environment-specific
    ASR_IMPORT_ERROR = exc
    np = None  # type: ignore[assignment]
    sf = None  # type: ignore[assignment]
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    F = None  # type: ignore[assignment]
    torchaudio = None  # type: ignore[assignment]


IAST_CONSONANTS = {
    "kṣh": "क्ष",
    "kṣ": "क्ष",
    "ksh": "क्ष",
    "jñ": "ज्ञ",
    "śh": "श",
    "ṣh": "ष",
    "chh": "छ",
    "kh": "ख",
    "gh": "घ",
    "ch": "छ",
    "jh": "झ",
    "ṭh": "ठ",
    "ḍh": "ढ",
    "th": "थ",
    "dh": "ध",
    "ph": "फ",
    "bh": "भ",
    "k": "क",
    "g": "ग",
    "ṅ": "ङ",
    "c": "च",
    "j": "ज",
    "ñ": "ञ",
    "ṭ": "ट",
    "ḍ": "ड",
    "ṇ": "ण",
    "t": "त",
    "d": "द",
    "n": "न",
    "p": "प",
    "b": "ब",
    "m": "म",
    "y": "य",
    "r": "र",
    "l": "ल",
    "v": "व",
    "ś": "श",
    "ṣ": "ष",
    "s": "स",
    "h": "ह",
    "ḻ": "ळ",
}

IAST_VOWELS = {
    "a": "अ",
    "ā": "आ",
    "i": "इ",
    "ī": "ई",
    "u": "उ",
    "ū": "ऊ",
    "ṛ": "ऋ",
    "ṝ": "ॠ",
    "ḷ": "ऌ",
    "ḹ": "ॡ",
    "e": "ए",
    "ai": "ऐ",
    "o": "ओ",
    "au": "औ",
}

IAST_MATRAS = {
    "a": "",
    "ā": "ा",
    "i": "ि",
    "ī": "ी",
    "u": "ु",
    "ū": "ू",
    "ṛ": "ृ",
    "ṝ": "ॄ",
    "ḷ": "ॢ",
    "ḹ": "ॣ",
    "e": "े",
    "ai": "ै",
    "o": "ो",
    "au": "ौ",
}

IAST_SIGNS = {
    "ṃ": "ं",
    "ḥ": "ः",
    "'": "ऽ",
    "~": "",
}

TOKEN_ORDER: List[str] = sorted(
    list(IAST_CONSONANTS.keys()) + list(IAST_VOWELS.keys()) + list(IAST_SIGNS.keys()),
    key=len,
    reverse=True,
)


def _match_token(text: str, start: int) -> Optional[str]:
    for token in TOKEN_ORDER:
        if text.startswith(token, start):
            return token
    return None


def iast_to_devanagari(text: str) -> str:
    """
    Convert ASR transliteration output to Devanagari.

    This is a compact converter tailored to the ASR model's output token set.
    """

    if not text:
        return ""

    text = unicodedata.normalize("NFC", text).lower()
    text = (
        text.replace("kṣh", "kṣ")
        .replace("ksh", "kṣ")
        .replace("śh", "ś")
        .replace("ṣh", "ṣ")
        .replace("chh", "ch")
    )

    output: List[str] = []
    pending_consonant = False
    i = 0
    while i < len(text):
        ch = text[i]

        if ch.isspace():
            if pending_consonant:
                output.append("्")
                pending_consonant = False
            output.append(ch)
            i += 1
            continue

        token = _match_token(text, i)
        if token is None:
            if pending_consonant and re.match(r"[.,;:!?|/\-]", ch):
                output.append("्")
                pending_consonant = False
            output.append(ch)
            i += 1
            continue

        i += len(token)

        if token in IAST_CONSONANTS:
            if pending_consonant:
                output.append("्")
            output.append(IAST_CONSONANTS[token])
            pending_consonant = True
            continue

        if token in IAST_VOWELS:
            if pending_consonant:
                matra = IAST_MATRAS[token]
                if matra:
                    output.append(matra)
                pending_consonant = False
            else:
                output.append(IAST_VOWELS[token])
            continue

        if token in IAST_SIGNS:
            if pending_consonant:
                pending_consonant = False
            output.append(IAST_SIGNS[token])
            continue

    if pending_consonant:
        output.append("्")

    return "".join(output)


def asr_runtime_available() -> bool:
    return ASR_IMPORT_ERROR is None


if ASR_IMPORT_ERROR is None:
    class TextTransform:
        """Maps characters to integers and vice versa."""

        def __init__(self):
            char_map_str = """
            ' 0
            ~ 1
            <SPACE> 2
            a 3
            ā 4
            i 5
            ī 6
            u 7
            ū 8
            ṛ 9
            ṝ 10
            ḷ 11
            ḹ 12
            e 13
            ai 14
            o 15
            au 16
            ṃ 17
            ḥ 18
            k 19
            c 20
            ṭ 21
            t 22
            p 23
            ch 24
            ṭh 25
            th 26
            ph 27
            g 28
            j 29
            ḍ 30
            d 31
            b 32
            gh 33
            jh 34
            ḍh 35
            dh 36
            bh 37
            ṅ 38
            ñ 39
            ṇ 40
            n 41
            m 42
            h 43
            y 44
            r 45
            l 46
            v 47
            ś 48
            ṣ 49
            s 50
            kh 51
            ḻ 52
            """
            self.char_map: Dict[str, int] = {}
            self.index_map: Dict[int, str] = {}
            for line in char_map_str.strip().split("\n"):
                token, index = line.split()
                self.char_map[token] = int(index)
                self.index_map[int(index)] = token
            self.index_map[1] = " "

        def int_to_text(self, labels: Sequence[int]) -> str:
            chars = [self.index_map[int(label)] for label in labels]
            return "".join(chars).replace("<SPACE>", " ")


    class CNNLayerNorm(nn.Module):
        def __init__(self, n_feats: int):
            super().__init__()
            self.layer_norm = nn.LayerNorm(n_feats)

        def forward(self, x):
            x = x.transpose(2, 3).contiguous()
            x = self.layer_norm(x)
            return x.transpose(2, 3).contiguous()


    class ResidualCNN(nn.Module):
        def __init__(self, in_channels, out_channels, kernel, stride, dropout, n_feats):
            super().__init__()
            self.cnn1 = nn.Conv2d(in_channels, out_channels, kernel, stride, padding=kernel // 2)
            self.cnn2 = nn.Conv2d(out_channels, out_channels, kernel, stride, padding=kernel // 2)
            self.dropout1 = nn.Dropout(dropout)
            self.dropout2 = nn.Dropout(dropout)
            self.layer_norm1 = CNNLayerNorm(n_feats)
            self.layer_norm2 = CNNLayerNorm(n_feats)

        def forward(self, x):
            residual = x
            x = self.layer_norm1(x)
            x = F.gelu(x)
            x = self.dropout1(x)
            x = self.cnn1(x)
            x = self.layer_norm2(x)
            x = F.gelu(x)
            x = self.dropout2(x)
            x = self.cnn2(x)
            x += residual
            return x


    class BidirectionalGRU(nn.Module):
        def __init__(self, rnn_dim, hidden_size, dropout, batch_first):
            super().__init__()
            # Keep module name aligned with training checkpoint keys (BiGRU).
            self.BiGRU = nn.GRU(
                input_size=rnn_dim,
                hidden_size=hidden_size,
                num_layers=1,
                batch_first=batch_first,
                bidirectional=True,
            )
            self.layer_norm = nn.LayerNorm(rnn_dim)
            self.dropout = nn.Dropout(dropout)

        def forward(self, x):
            x = self.layer_norm(x)
            x = F.gelu(x)
            x, _ = self.BiGRU(x)
            x = self.dropout(x)
            return x


    class SpeechRecognitionModel(nn.Module):
        def __init__(
            self,
            n_cnn_layers: int,
            n_rnn_layers: int,
            rnn_dim: int,
            n_class: int,
            n_feats: int,
            stride: int = 2,
            dropout: float = 0.1,
        ):
            super().__init__()
            n_feats = n_feats // 2
            self.cnn = nn.Conv2d(2, 32, 3, stride=stride, padding=3 // 2)
            self.rescnn_layers = nn.Sequential(
                *[
                    ResidualCNN(32, 32, kernel=3, stride=1, dropout=dropout, n_feats=n_feats)
                    for _ in range(n_cnn_layers)
                ]
            )
            self.fully_connected = nn.Linear(n_feats * 32, rnn_dim)
            self.birnn_layers = nn.Sequential(
                *[
                    BidirectionalGRU(
                        rnn_dim=rnn_dim if layer_index == 0 else rnn_dim * 2,
                        hidden_size=rnn_dim,
                        dropout=dropout,
                        batch_first=layer_index == 0,
                    )
                    for layer_index in range(n_rnn_layers)
                ]
            )
            self.classifier = nn.Sequential(
                nn.Linear(rnn_dim * 2, rnn_dim),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(rnn_dim, n_class),
            )

        def forward(self, x):
            x = self.cnn(x)
            x = self.rescnn_layers(x)
            sizes = x.size()
            x = x.view(sizes[0], sizes[1] * sizes[2], sizes[3])
            x = x.transpose(1, 2)
            x = self.fully_connected(x)
            x = self.birnn_layers(x)
            x = self.classifier(x)
            return x


    class LocalSanskritASR:
        """
        Local model inference for Sanskrit STT.
        """

        def __init__(self, model_path: str = "model_200_fixed.pth"):
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.text_transform = TextTransform()
            self.hparams = {
                "n_cnn_layers": 3,
                "n_rnn_layers": 5,
                "rnn_dim": 512,
                "n_class": 54,
                "n_feats": 128,
                "stride": 2,
                "dropout": 0.1,
            }
            self.audio_transforms = torchaudio.transforms.MelSpectrogram(sample_rate=22050, n_mels=128)
            self.model = self._load_model(model_path)

        def _load_model(self, model_path: str):
            model_file = Path(model_path)
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")

            model = SpeechRecognitionModel(
                self.hparams["n_cnn_layers"],
                self.hparams["n_rnn_layers"],
                self.hparams["rnn_dim"],
                self.hparams["n_class"],
                self.hparams["n_feats"],
                self.hparams["stride"],
                self.hparams["dropout"],
            )

            checkpoint = torch.load(model_file, map_location=self.device)
            if isinstance(checkpoint, nn.Module):
                model = checkpoint
            elif isinstance(checkpoint, dict):
                state_dict = checkpoint.get("state_dict") or checkpoint.get("model_state_dict") or checkpoint
                if all(key.startswith("module.") for key in state_dict.keys()):
                    state_dict = {key.replace("module.", "", 1): value for key, value in state_dict.items()}

                # Handle naming drift between "BiGRU" and "bigru" keys.
                expects_bigru = any(".BiGRU." in key for key in model.state_dict().keys())
                has_bigru = any(".BiGRU." in key for key in state_dict.keys())
                has_lower_bigru = any(".bigru." in key for key in state_dict.keys())
                if expects_bigru and has_lower_bigru and not has_bigru:
                    state_dict = {key.replace(".bigru.", ".BiGRU."): value for key, value in state_dict.items()}
                elif not expects_bigru and has_bigru and not has_lower_bigru:
                    state_dict = {key.replace(".BiGRU.", ".bigru."): value for key, value in state_dict.items()}

                model.load_state_dict(state_dict)
            else:
                raise RuntimeError("Unsupported model checkpoint format.")

            model.to(self.device)
            model.eval()
            return model

        def _preprocess_audio(self, audio_path: str):
            data, sample_rate = sf.read(audio_path, dtype="float32")
            waveform = torch.from_numpy(data if data.ndim > 1 else data[:, None]).transpose(0, 1).contiguous()

            if waveform.shape[0] == 1:
                waveform = waveform.repeat(2, 1)
            elif waveform.shape[0] > 2:
                waveform = waveform[:2, :]

            if sample_rate != 22050:
                resampler = torchaudio.transforms.Resample(sample_rate, 22050)
                waveform = resampler(waveform)

            spec = self.audio_transforms(waveform)  # [channels, n_mels, time]
            spec = spec.unsqueeze(0)  # [1, channels, n_mels, time]
            return spec.to(self.device)

        def _greedy_decode(self, output, blank_label: int = 53) -> str:
            arg_maxes = torch.argmax(output, dim=2)
            decoded: List[int] = []
            for time_index, class_index in enumerate(arg_maxes[0]):
                if int(class_index) == blank_label:
                    continue
                if time_index > 0 and int(class_index) == int(arg_maxes[0][time_index - 1]):
                    continue
                decoded.append(int(class_index))
            return self.text_transform.int_to_text(decoded).strip()

        def transcribe_audio(self, audio_path: str) -> str:
            spectrogram = self._preprocess_audio(audio_path)
            with torch.no_grad():
                output = self.model(spectrogram)
                output = F.log_softmax(output, dim=2)
            return self._greedy_decode(output)

        def transcribe_audio_to_devanagari(self, audio_path: str) -> Dict[str, str]:
            iast_text = self.transcribe_audio(audio_path)
            devanagari_text = iast_to_devanagari(iast_text)
            return {"iast": iast_text, "devanagari": devanagari_text}


else:
    class LocalSanskritASR:  # pragma: no cover - only used when runtime deps missing
        def __init__(self, model_path: str = "model_200_fixed.pth"):
            raise RuntimeError(f"ASR runtime is unavailable: {ASR_IMPORT_ERROR}")
