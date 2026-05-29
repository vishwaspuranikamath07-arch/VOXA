import time

try:
    import torch
    import torchaudio
    from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
except ImportError:
    torch = None
    torchaudio = None
    Wav2Vec2Processor = None
    Wav2Vec2ForCTC = None

processor = None
model = None


def _load_model():
    global processor, model
    if processor is not None and model is not None:
        return processor, model

    if not all([torch, torchaudio, Wav2Vec2Processor, Wav2Vec2ForCTC]):
        raise RuntimeError("wav2vec dependencies are not installed.")

    processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
    model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
    return processor, model

def run_wav2vec(audio):
    start = time.time()
    try:
        loaded_processor, loaded_model = _load_model()
        speech, sr = torchaudio.load(audio)

        input_values = loaded_processor(
            speech.squeeze(),
            return_tensors="pt",
            sampling_rate=16000,
        ).input_values

        with torch.no_grad():
            logits = loaded_model(input_values).logits

        ids = torch.argmax(logits, dim=-1)
        text = loaded_processor.decode(ids[0])

        latency = round(time.time() - start, 2)
        return text, latency
    except Exception as e:
        latency = round(time.time() - start, 2)
        return f"Wav2Vec2 unavailable: {e}", 10_000 + latency
