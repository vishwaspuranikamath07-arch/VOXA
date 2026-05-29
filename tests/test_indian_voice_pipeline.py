from backend.asr.correction import apply_corrections
from backend.utils import LanguageDetector


def test_indian_voice_transcript_detection_targets():
    samples = [
        ("mujhe kuch chahiye", "hi", "Hindi"),
        ("kemon acho tumi", "bn", "Bengali"),
        ("matte hege idira", "kn", "Kannada"),
        ("enna panra nee", "ta", "Tamil"),
        ("ela unnav meeru", "te", "Telugu"),
    ]

    for transcript, code, display in samples:
        result = LanguageDetector.detect(transcript)
        assert result["primary_language"] == code
        assert result["lang_name_display"] in {display, "Hinglish", "Kanglish", "Tamlish", "Tenglish"}


def test_voice_transcript_corrections_for_common_stt_splits():
    cases = {
        "got tilla bro meeting cancel made it ya": "gottilla bro meeting cancel madidya",
        "mac han enna panrom": "machan enna panrom",
        "na hi yaar kya kar raha hai": "nahi yaar kya kar raha hai",
        "en di ledu evaru": "endi ledu evaru",
    }

    for raw, expected in cases.items():
        assert apply_corrections(raw) == expected
