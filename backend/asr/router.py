# backend/asr/router.py


def run_asr(audio_file):
    # Lazy import so text-only mode does not require ASR packages.
    from backend.asr.whisper_asr import transcribe as whisper_asr

    text, time_taken = whisper_asr(audio_file)
    return text, time_taken
