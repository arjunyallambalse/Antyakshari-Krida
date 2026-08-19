import os
import numpy as np
import torch
import soundfile as sf

# Load NeMo lazily so Streamlit can start before the model is downloaded.
_MODEL = None

MODEL_NAME = "prathoshap/sushrota-sanskrit-asr"

# Su-srota Sanskrit vocabulary slice
OFF = 4096
VOCAB_SIZE = 256
BLANK = 5632


def _load_model():
    global _MODEL

    if _MODEL is not None:
        return _MODEL

    print("Su-srota: loading Sanskrit ASR model...", flush=True)

    try:
        import nemo.collections.asr as nemo_asr

        _MODEL = nemo_asr.models.ASRModel.from_pretrained(
            MODEL_NAME
        )

        _MODEL.eval()

        print("Su-srota: model loaded successfully.", flush=True)

        return _MODEL

    except Exception as e:
        print(
            f"Su-srota MODEL ERROR: {type(e).__name__}: {e}",
            flush=True
        )
        return None


def _prepare_audio(audio_file_path):
    """
    Read Streamlit recording and convert it to
    16 kHz mono float32 for Su-srota.
    """

    wav, sr = sf.read(audio_file_path, dtype="float32")

    # Convert stereo to mono
    if wav.ndim > 1:
        wav = wav.mean(axis=1)

    # Resample to 16 kHz when necessary
    if sr != 16000:
        import librosa

        wav = librosa.resample(
            wav,
            orig_sr=sr,
            target_sr=16000
        )

    wav = np.asarray(wav, dtype=np.float32)

    return wav


def _greedy_sanskrit_decode(model, wav):
    """
    Decode only the Sanskrit token slice of the
    aggregate IndicConformer vocabulary.
    """

    signal = torch.tensor(
        wav,
        dtype=torch.float32
    ).unsqueeze(0)

    signal_length = torch.tensor(
        [len(wav)],
        dtype=torch.long
    )

    device = next(model.parameters()).device

    signal = signal.to(device)
    signal_length = signal_length.to(device)

    with torch.no_grad():

        encoded, _ = model.forward(
            input_signal=signal,
            input_signal_length=signal_length
        )

        logits = model.ctc_decoder(
            encoder_output=encoded
        )[0]

    logits = logits.detach().cpu().numpy()

    # Sanskrit vocabulary + CTC blank
    columns = [BLANK] + list(
        range(OFF, OFF + VOCAB_SIZE)
    )

    probabilities = logits[:, columns]

    # Re-normalize over Sanskrit slice
    maximum = probabilities.max(
        axis=1,
        keepdims=True
    )

    probabilities = probabilities - (
        maximum
        + np.log(
            np.exp(
                probabilities - maximum
            ).sum(
                axis=1,
                keepdims=True
            )
        )
    )

    ids = probabilities.argmax(axis=1)

    tokenizer = model.tokenizer.tokenizers_dict["sa"]

    output_tokens = []

    previous = -1

    for token_id in ids:

        token_id = int(token_id)

        # CTC collapse repeated tokens and remove blank
        if token_id != previous and token_id != 0:

            token = tokenizer.ids_to_tokens(
                [token_id - 1]
            )[0]

            output_tokens.append(token)

        previous = token_id

    text = "".join(output_tokens)

    text = text.replace("▁", " ")

    return text.strip()


def transcribe_audio(audio_file_path: str) -> str:

    print(
        f"Su-srota: received {audio_file_path}",
        flush=True
    )

    if not audio_file_path:
        print("Su-srota: no audio supplied.", flush=True)
        return ""

    if not os.path.exists(audio_file_path):
        print(
            f"Su-srota: file missing: {audio_file_path}",
            flush=True
        )
        return ""

    try:

        size = os.path.getsize(audio_file_path)

        print(
            f"Su-srota: audio size = {size} bytes",
            flush=True
        )

        if size == 0:
            return ""

        model = _load_model()

        if model is None:
            return ""

        wav = _prepare_audio(audio_file_path)

        print(
            f"Su-srota: samples = {len(wav)}",
            flush=True
        )

        text = _greedy_sanskrit_decode(
            model,
            wav
        )

        print(
            f"Su-srota RESULT: {text}",
            flush=True
        )

        return text

    except Exception as e:

        print(
            f"Su-srota TRANSCRIPTION ERROR: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return ""
