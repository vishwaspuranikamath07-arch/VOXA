import edge_tts
import asyncio
import uuid
import os

# 🎤 Female human-like voices
VOICE_MAP = {
    "English": "en-IN-NeerjaNeural",
    "Hindi": "hi-IN-SwaraNeural",
    "Bengali": "bn-IN-TanishaaNeural",
    "Kannada": "en-IN-NeerjaNeural"  # fallback
}

async def generate_tts(text, lang):
    voice = VOICE_MAP.get(lang, "en-IN-NeerjaNeural")

    filename = f"audio_{uuid.uuid4().hex}.mp3"
    file_path = os.path.join("audio", filename)

    os.makedirs("audio", exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)

    await communicate.save(file_path)

    return file_path