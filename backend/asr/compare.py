# asr/compare.py
from .whisper_asr import run_whisper
from .wav2vec_asr import run_wav2vec


def _is_unavailable(text: str) -> bool:
    lowered = text.lower()
    return " unavailable:" in lowered or lowered.startswith("missing ")


def compare_asr(audio):
    results = {}

    text1, t1 = run_whisper(audio)
    results["Whisper"] = (text1, t1)

    text2, t2 = run_wav2vec(audio)
    results["Wav2Vec2"] = (text2, t2)

    return results


def select_best(results):
    valid_results = {
        model_name: (text, latency)
        for model_name, (text, latency) in results.items()
        if text and not _is_unavailable(text)
    }
    source = valid_results if valid_results else results
    return min(source, key=lambda x: source[x][1])
