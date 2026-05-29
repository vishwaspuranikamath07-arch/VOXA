def record_audio(filename="input.wav", duration=5):
    try:
        import sounddevice as sd
        from scipy.io.wavfile import write
    except ImportError as exc:
        raise RuntimeError(
            "Audio dependencies are missing. Install requirements or run with VOXA_INPUT_TEXT."
        ) from exc

    fs = 16000
    print("Recording...")

    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()

    write(filename, fs, recording)
    print("Recording saved")

    return filename
