import time

_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model

    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "Whisper is not installed. Install requirements to use audio transcription."
        ) from exc

    # Use smaller but stable model for CPU
    _model = whisper.load_model("small")
    return _model

def transcribe(audio_path):
    start = time.time()
    model = _get_model()

    result = model.transcribe(
        audio_path,
        task="transcribe",
        language=None,
        fp16=False,  # Important for CPU stability
    )

    end = time.time()

    print("Detected language:", result.get("language"))

    return result["text"], round(end - start, 2)
