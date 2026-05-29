import asyncio
import os
import subprocess

import edge_tts

VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "bn": "bn-IN-TanishaaNeural",
    "kn": "kn-IN-SapnaNeural",
}


async def generate_speech(text: str, lang: str = "en", filename: str = "output.mp3") -> str:
    voice = VOICE_MAP.get(lang, "en-IN-NeerjaNeural")
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(filename)
    return filename


def speak(text: str, lang: str = "en") -> None:
    if os.getenv("VOXA_DISABLE_TTS", "").strip().lower() in {"1", "true", "yes"}:
        print("TTS playback skipped (VOXA_DISABLE_TTS is set).")
        return

    audio_file = asyncio.run(generate_speech(text, lang))

    try:
        # Start playback non-blocking on Windows.
        subprocess.Popen(["cmd", "/c", "start", "", audio_file], shell=False)
    except Exception as exc:
        print(f"Could not auto-play TTS output '{audio_file}': {exc}")
