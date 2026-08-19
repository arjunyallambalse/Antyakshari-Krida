import os
import numpy as np
import torch
import soundfile as sf
import librosa

from huggingface_hub import hf_hub_download

MODEL_REPO = "prathoshap/sushrota-sanskrit-asr"
MODEL_FILE = "sushrota_sanskrit_asr_v5.nemo"

# Sanskrit slice in the aggregate IndicConformer vocabulary
OFF = 4096
VOCAB_SIZE = 256
BLANK = 5632

_MODEL = None


def _load_model():
    global _MODEL

    if _MODEL is not None:
        return _MODEL

    try:
        print("Su-srota: downloading/checking model...", flush=True)

        model_path = hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE
        )

        print(
            f"Su-srota: model checkpoint = {model_path}",
            flush=True
        )

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Downloaded model not found: {model_path}"
            )

        print("Su-srota: importing NeMo...", flush=True)

        import nemo.collections.asr as nemo_asr

        print("Su-srota: restoring .nemo checkpoint...", flush=True)

        _MODEL = (
            nemo_asr.models.EncDecHybridRNNTCTCBPEModel
            .restore_from(model_path)
        )

        _MODEL.eval()

        print(
            "Su-srota: model loaded successfully!",
            flush=True
        )

        return _MODEL

    except Exception as e:
        print(
            f"Su-srota MODEL ERROR: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return None


def _prepare_audio(path):
    wav, sr = sf.read(
        path,
        dtype="float32"
    )

    # Stereo -> mono
    if wav.ndim > 1:
        wav = wav.mean(axis=1)

    # Su-srota expects 16 kHz
    if sr != 16000:
        wav = librosa.resample(
            wav,
            orig_sr=sr,
            target_sr=16000
        )

    wav = np.asarray(
        wav,
        dtype=np.float32
    )

    return wav


def _decode_sanskrit(model, wav):

    device = next(model.parameters()).device

    signal = torch.tensor(
        wav,
        dtype=torch.float32
    ).unsqueeze(0).to(device)

    signal_length = torch.tensor(
        [len(wav)],
        dtype=torch.long
    ).to(device)

    print(
        "Su-srota: running neural network...",
        flush=True
    )

    with torch.no_grad():

        encoded, _ = model.forward(
            input_signal=signal,
            input_signal_length=signal_length
        )

        logits = model.ctc_decoder(
            encoder_output=encoded
        )[0]

    logits = logits.detach().cpu().numpy()

    # Restrict decoding to Sanskrit vocabulary
    columns = [BLANK] + list(
        range(
            OFF,
            OFF + VOCAB_SIZE
        )
    )

    P = logits[:, columns]

    maximum = P.max(
        axis=1,
        keepdims=True
    )

    P = P - (
        maximum
        + np.log(
            np.exp(
                P - maximum
            ).sum(
                axis=1,
                keepdims=True
            )
        )
    )

    ids = P.argmax(axis=1)

    tokenizer = (
        model.tokenizer
        .tokenizers_dict["sa"]
    )

    output = []
    previous = -1

    for i in ids:
        i = int(i)

        # Standard CTC collapse
        if i != previous and i != 0:

            token = tokenizer.ids_to_tokens(
                [i - 1]
            )[0]

            output.append(token)

        previous = i

    text = "".join(output)

    text = text.replace(
        "▁",
        " "
    )

    return text.strip()


def transcribe_audio(audio_file_path: str) -> str:

    print(
        f"Su-srota: received {audio_file_path}",
        flush=True
    )

    if not audio_file_path:
        print(
            "Su-srota ERROR: no audio supplied",
            flush=True
        )
        return ""

    if not os.path.exists(audio_file_path):
        print(
            f"Su-srota ERROR: file not found: "
            f"{audio_file_path}",
            flush=True
        )
        return ""

    try:

        size = os.path.getsize(
            audio_file_path
        )

        print(
            f"Su-srota: audio size = {size} bytes",
            flush=True
        )

        if size == 0:
            return ""

        model = _load_model()

        if model is None:
            return ""

        print(
            "Su-srota: preparing 16 kHz audio...",
            flush=True
        )

        wav = _prepare_audio(
            audio_file_path
        )

        print(
            f"Su-srota: {len(wav)} samples ready",
            flush=True
        )

        text = _decode_sanskrit(
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
