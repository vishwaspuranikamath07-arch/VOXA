from gtts import gTTS
import uuid
import os

AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

def generate_audio(text: str, lang: str) -> str | None:
    lang_map = {
        "English": "en",
        "Hindi": "hi",
        "Kannada": "kn",
        "Bengali": "bn"
    }

    tts_lang = lang_map.get(lang, "en")

    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(AUDIO_DIR, filename)

    try:
        tts = gTTS(text=text, lang=tts_lang)
        tts.save(filepath)
    except:
        return None

    return f"audio/{filename}"