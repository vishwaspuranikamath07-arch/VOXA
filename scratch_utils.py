from __future__ import annotations

import re
import time
import logging

try:
    import langid
    langid.set_languages(['en','hi','kn','ta','te','bn','mr','gu','ml','pa',
                          'es','fr','de','it','pt','ru','ja','zh','ko','ar'])
    HAS_LANGID = True
except ImportError:
    HAS_LANGID = False

try:
    from lingua import LanguageDetectorBuilder
    _lingua_detector = LanguageDetectorBuilder.from_all_languages().with_minimum_relative_distance(0.1).build()
    HAS_LINGUA = True
except ImportError:
    HAS_LINGUA = False

# Import our custom dictionaries
from backend.dictionaries.kannada_words import (
    ALL_KANNADA_WORDS, KANNADA_SUFFIX_PATTERNS, BANGALORE_SLANG, EURO_LOOKALIKES
)
from backend.dictionaries.indian_languages import (
    HINDI_WORDS, HINDI_HIGH, TAMIL_WORDS, TAMIL_HIGH,
    TELUGU_WORDS, TELUGU_HIGH, MALAYALAM_WORDS, MALAYALAM_HIGH,
    MARATHI_WORDS, MARATHI_HIGH, BENGALI_WORDS, BENGALI_HIGH,
    GUJARATI_WORDS, GUJARATI_HIGH, PUNJABI_WORDS, PUNJABI_HIGH,
    URDU_WORDS, URDU_HIGH, DRAVIDIAN_SUFFIXES
)
from backend.dictionaries.global_languages import (
    SPANISH_WORDS, SPANISH_HIGH, FRENCH_WORDS, FRENCH_HIGH,
    GERMAN_WORDS, GERMAN_HIGH, PORTUGUESE_WORDS, PORTUGUESE_HIGH,
    PORTUGUESE_KANNADA_EXCLUSIONS, ITALIAN_WORDS, ITALIAN_HIGH,
    ENGLISH_WORDS
)

logger = logging.getLogger(__name__)

# ── Unicode Script Block Ranges ───────────────────────────────────────────────
UNICODE_RANGES: dict[str, tuple[int, int]] = {
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "te": (0x0C00, 0x0C7F),  # Telugu
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "hi": (0x0900, 0x097F),  # Devanagari (Hindi/Marathi/Sanskrit)
    "bn": (0x0980, 0x09FF),  # Bengali
    "gu": (0x0A80, 0x0AFF),  # Gujarati
    "ml": (0x0D00, 0x0D7F),  # Malayalam
    "pa": (0x0A00, 0x0A7F),  # Punjabi (Gurmukhi)
    "ar": (0x0600, 0x06FF),  # Arabic/Urdu
    "ru": (0x0400, 0x04FF),  # Cyrillic
    "zh": (0x4E00, 0x9FFF),  # CJK
    "ja": (0x3040, 0x30FF),  # Hiragana/Katakana
    "ko": (0xAC00, 0xD7AF),  # Hangul
}

MARATHI_NATIVE_MARKERS = {"आहे", "नाही", "आणि", "का", "मला", "तुम्ही", "हे", "ते", "आम्ही"}
HINDI_NATIVE_MARKERS   = {"है", "नहीं", "और", "क्या", "मुझे", "आप", "यह", "वह", "हम"}

_TOKEN_PAT = re.compile(r"[a-zA-Z']+")

_DEFINITIVE_INDIAN: dict[str, str] = {
    "gottilla": "kn", "madilla":  "kn", "barolla":  "kn", "hogbeku":   "kn",
    "helthini": "kn", "madthini": "kn", "barthiya": "kn", "hogthiya":  "kn",
    "nodidya":  "kn", "madidya":  "kn", "hegide":   "kn", "yaaru":     "kn",
    "naanu":    "kn", "neevu":    "kn", "idira":    "kn", "agide":     "kn",
    "illa":     "kn", "matte":    "kn", "hege":     "kn", "beku":      "kn",
    "yelli":    "kn", "elli":     "kn", "yenu":     "kn", "enu":       "kn",
    "banni":    "kn", "agtide":   "kn", "haudhu":   "kn", "houdhu":    "kn",
    "gothilla": "kn", "helthilla":"kn", "sigthilla":"kn", "aagtilla":  "kn",
    "machan":   "ta", "illai":    "ta", "romba":    "ta", "vanakkam":  "ta",
    "eppadi":   "ta", "enna":     "ta", "pannrom":  "ta", "kashtam":   "ta",
    "sollu":    "ta", "irukku":   "ta", "yenna":    "ta", "seri":      "ta",
    "cheppandi":"te", "ledu":     "te", "undi":     "te", "evaru":     "te",
    "enti":     "te", "ekkada":   "te", "ayindi":   "te", "bagunna":   "te",
    "antunnaru":"te", "endi":     "te", "avunu":    "te", "kaadu":     "te",
    "yaar":     "hi", "nahi":     "hi", "achha":    "hi", "theek":     "hi",
    "bhai":     "hi", "matlab":   "hi", "samjha":   "hi", "chahiye":   "hi",
    "kyun":     "hi", "kaise":    "hi", "wahan":    "hi", "yahan":     "hi",
    "enthanu":  "ml", "paranju":  "ml", "cheyyum":  "ml", "evide":     "ml",
    "njaan":    "ml", "varunnu":  "ml",
    "aahe":     "mr", "zhala":    "mr", "aalo":     "mr",
}
_EUROPEAN_LANGS: set[str] = {"it", "pt", "es", "fr", "fi", "ro", "de", "nl", "pl"}

LANGUAGE_CODE_MAP: dict[str, str] = {
    "en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil",
    "te": "Telugu", "ml": "Malayalam", "mr": "Marathi", "bn": "Bengali",
    "gu": "Gujarati", "pa": "Punjabi", "ur": "Urdu",
    "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese",
    "it": "Italian", "ru": "Russian", "zh": "Chinese", "ja": "Japanese",
    "ko": "Korean", "ar": "Arabic"
}

LANGUAGE_FLAGS: dict[str, str] = {
    "English": "🇬🇧", "Hindi": "🇮🇳", "Kannada": "🇮🇳", "Tamil": "🇮🇳",
    "Telugu": "🇮🇳", "Malayalam": "🇮🇳", "Marathi": "🇮🇳", "Bengali": "🇮🇳",
    "Gujarati": "🇮🇳", "Punjabi": "🇮🇳", "Hinglish": "🇮🇳", "Kanglish": "🇮🇳",
    "Tamlish": "🇮🇳", "Tenglish": "🇮🇳",
    "Spanish": "🇪🇸", "French": "🇫🇷", "German": "🇩🇪", "Portuguese": "🇧🇷",
    "Italian": "🇮🇹", "Russian": "🇷🇺", "Chinese": "🇨🇳", "Japanese": "🇯🇵",
    "Korean": "🇰🇷", "Arabic": "🇸🇦"
}

SUPPORTED_LANGUAGES = sorted(LANGUAGE_FLAGS.keys())

SMART_FALLBACKS: dict[str, str] = {
    "English": "Sorry, I hit a snag. please try again.",
    "Hindi": "क्षमा करें, मुझे समझने में थोड़ी परेशानी हुई। क्या आप दोबारा बोल सकते हैं?",
    "Kannada": "ಕ್ಷಮಿಸಿ, ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಹೇಳುತ್ತೀರಾ?",
}

STT_CODE_MAP: dict[str, str] = {
    "English": "en-US",
    "Hindi": "hi-IN", "Kannada": "kn-IN", "Tamil": "ta-IN", "Telugu": "te-IN",
    "Bengali": "bn-IN", "Marathi": "mr-IN", "Gujarati": "gu-IN", "Malayalam": "ml-IN",
    "Punjabi": "pa-IN",
    "Hinglish": "hi-IN", "Kanglish": "kn-IN", "Tenglish": "te-IN", "Tamlish": "ta-IN",
    "Spanish": "es-ES", "French": "fr-FR", "German": "de-DE",
}

NAME_TO_CODE = {v: k for k, v in LANGUAGE_CODE_MAP.items()}
NAME_TO_CODE.update({"Hinglish": "hi", "Kanglish": "kn", "Tamlish": "ta", "Tenglish": "te"})


class FeatureExtractor:
    """Base class for language feature extractors."""
    def extract(self, text: str, words: list[str]) -> dict[str, float]:
        raise NotImplementedError

class ScriptFeatureExtractor(FeatureExtractor):
    def extract(self, text: str, words: list[str]) -> dict[str, float]:
        counts: dict[str, int] = {}
        total = 0
        for ch in text:
            cp = ord(ch)
            for lang, (lo, hi) in UNICODE_RANGES.items():
                if lo <= cp <= hi:
                    counts[lang] = counts.get(lang, 0) + 1
                    total += 1
                    break
        if not total:
            return {}
        if "hi" in counts:
            hi_words = set(text.split())
            mr_score = len(hi_words & MARATHI_NATIVE_MARKERS)
            hi_score = len(hi_words & HINDI_NATIVE_MARKERS)
            conf = counts["hi"] / total
            return {"mr": conf} if mr_score >= hi_score else {"hi": conf}
        return {lang: cnt / total for lang, cnt in counts.items()}

class DictionaryFeatureExtractor(FeatureExtractor):
    def __init__(self):
        self.ind_dicts = {
            "hi": (HINDI_WORDS, HINDI_HIGH), "ta": (TAMIL_WORDS, TAMIL_HIGH),
            "te": (TELUGU_WORDS, TELUGU_HIGH), "ml": (MALAYALAM_WORDS, MALAYALAM_HIGH),
            "mr": (MARATHI_WORDS, MARATHI_HIGH), "bn": (BENGALI_WORDS, BENGALI_HIGH),
            "gu": (GUJARATI_WORDS, GUJARATI_HIGH), "pa": (PUNJABI_WORDS, PUNJABI_HIGH),
            "ur": (URDU_WORDS, URDU_HIGH)
        }
        self.glob_dicts = {
            "es": (SPANISH_WORDS, SPANISH_HIGH), "fr": (FRENCH_WORDS, FRENCH_HIGH),
            "de": (GERMAN_WORDS, GERMAN_HIGH), "pt": (PORTUGUESE_WORDS, PORTUGUESE_HIGH),
            "it": (ITALIAN_WORDS, ITALIAN_HIGH),
        }

    def extract(self, text: str, words: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        text_lower = text.lower()
        if not words: return scores

        # Kannada specific
        kn_score = 0.0
        for phrase, weight in BANGALORE_SLANG.items():
            if phrase in text_lower: kn_score += weight * 2.0
        for word in words:
            if word in ALL_KANNADA_WORDS: kn_score += ALL_KANNADA_WORDS[word]
        for pattern, weight in KANNADA_SUFFIX_PATTERNS:
            hits = len(re.findall(pattern, text_lower))
            kn_score += hits * weight
        if kn_score > 0:
            scores["kn"] = min(kn_score / max(1, len(words) * 0.4), 3.0)

        # Other Indians
        for lang, (vocab, high_vocab) in self.ind_dicts.items():
            lang_score = 0.0
            for word in words:
                if word in high_vocab: lang_score += high_vocab[word] * 1.5
                elif word in vocab: lang_score += vocab[word]
            if lang_score > 0:
                scores[lang] = min(lang_score / max(1, len(words) * 0.5), 2.5)
        
        dravidian_boost = sum(weight for pat, weight in DRAVIDIAN_SUFFIXES if re.search(pat, text_lower))
        if dravidian_boost > 0:
            for d_lang in ["ta", "te", "ml"]:
                if d_lang in scores: scores[d_lang] += dravidian_boost
                else: scores[d_lang] = dravidian_boost

        # Globals
        for lang, (vocab, high_vocab) in self.glob_dicts.items():
            lang_score = 0.0
            for word in words:
                if word in high_vocab: lang_score += high_vocab[word] * 1.5
                elif word in vocab: lang_score += vocab[word]
            if lang == "pt":
                exclusion_hits = sum(1 for w in words if w in PORTUGUESE_KANNADA_EXCLUSIONS)
                if exclusion_hits > 0: lang_score -= exclusion_hits * 1.0
            if lang_score > 0:
                scores[lang] = min(lang_score / max(1, len(words) * 0.5), 2.0)

        # English
        en_score = sum(ENGLISH_WORDS.get(w, 0.0) for w in words)
        if en_score > 0:
            scores["en"] = min(en_score / max(1, len(words) * 0.5), 2.0)

        return scores

class LangidFeatureExtractor(FeatureExtractor):
    def extract(self, text: str, words: list[str]) -> dict[str, float]:
        if not HAS_LANGID: return {}
        try:
            lang, _ = langid.classify(text)
            if lang in LANGUAGE_CODE_MAP:
                return {lang: 0.5}
        except: pass
        return {}

class LinguaFeatureExtractor(FeatureExtractor):
    def extract(self, text: str, words: list[str]) -> dict[str, float]:
        if not HAS_LINGUA: return {}
        scores = {}
        try:
            res = _lingua_detector.compute_language_confidence_values(text)
            for cv in res[:3]:
                iso_code = cv.language.iso_code_639_1.name.lower()
                if iso_code in LANGUAGE_CODE_MAP:
                    scores[iso_code] = cv.value * 1.0
        except: pass
        return scores

class LanguagePipeline:
    def __init__(self):
        self.script_ext = ScriptFeatureExtractor()
        self.dict_ext = DictionaryFeatureExtractor()
        self.langid_ext = LangidFeatureExtractor()
        self.lingua_ext = LinguaFeatureExtractor()

    def detect(self, text: str, rolling_history: list[str] | None = None, locked_lang: str | None = None) -> dict:
        t0 = time.time()
        text_clean = text.strip()
        words = _TOKEN_PAT.findall(text_clean.lower())
        
        # Determine code-switching with English
        en_hits = sum(1 for w in words if w in ENGLISH_WORDS)
        is_cs = en_hits > 0

        # Phase 1: Fast Path Native Scripts
        if locked_lang:
            code = NAME_TO_CODE.get(locked_lang, "en")
            cs_lang = self._get_cs_name(code) if is_cs else locked_lang
            return self._build_res(code, "en" if is_cs else None, 0.97, is_cs, "native", "frontend_lock", cs_lang, (time.time()-t0)*1000)

        if not text_clean:
            return self._build_res("en", None, 1.0, False, "roman", "empty", "English", 0.0)

        # Phase 2: Signal Extraction
        script_scores = self.script_ext.extract(text_clean, words)
        if script_scores:
            best_code = max(script_scores, key=lambda k: script_scores[k])
            if script_scores[best_code] > 0.5:
                lang_name = LANGUAGE_CODE_MAP.get(best_code, "English")
                return self._build_res(best_code, None, 0.95, False, "native", "unicode_block", lang_name, (time.time()-t0)*1000)

        # Phase 3: Romanized Evaluation & Fusion
        final_scores: dict[str, float] = {}
        
        # 3a. Definitive Indian word override
        definitive_hits = {}
        for w in set(words):
            if w in _DEFINITIVE_INDIAN:
                lang_hit = _DEFINITIVE_INDIAN[w]
                definitive_hits[lang_hit] = definitive_hits.get(lang_hit, 0) + 4.0
        
        dict_scores = self.dict_ext.extract(text_clean, words)
        langid_scores = self.langid_ext.extract(text_clean, words)
        lingua_scores = self.lingua_ext.extract(text_clean, words)

        # Fuse
        for d in [dict_scores, langid_scores, lingua_scores, definitive_hits]:
            for k, v in d.items():
                final_scores[k] = final_scores.get(k, 0) + v

        # Apply definitive penalty
        if definitive_hits:
            for eu in _EUROPEAN_LANGS:
                if eu in final_scores: final_scores[eu] *= 0.05

        if not final_scores:
            return self._build_res("en", None, 0.5, False, "roman", "default", "English", (time.time()-t0)*1000)

        best_code = max(final_scores, key=lambda k: final_scores[k])
        
        # Confidence calculation
        top_score = final_scores[best_code]
        second_score = sorted(final_scores.values(), reverse=True)[1] if len(final_scores) > 1 else 0.0
        confidence = 0.5 + min(0.45, (top_score - second_score) * 0.2)
        
        sec_code = None
        lang_name = LANGUAGE_CODE_MAP.get(best_code, "English")

        # Code Switching Resolution
        if best_code in ["hi", "kn", "ta", "te"] and final_scores.get("en", 0) > 0.3:
            is_cs = True
            sec_code = "en"
            lang_name = self._get_cs_name(best_code)
        elif best_code == "en" and second_score > 0.8 and second_score >= top_score * 0.5:
            sec_lang = max([k for k in final_scores if k != "en"], key=lambda k: final_scores[k])
            if sec_lang in ["hi", "kn", "ta", "te"]:
                best_code = sec_lang
                sec_code = "en"
                is_cs = True
                lang_name = self._get_cs_name(best_code)
                confidence = 0.5 + min(0.45, second_score * 0.2)

        if confidence < 0.40 and not definitive_hits:
            best_code, lang_name, is_cs, sec_code, confidence = "en", "English", False, None, 0.5

        # Smoothing
        if rolling_history:
            hist_codes = [NAME_TO_CODE.get(h, "en") for h in rolling_history if h in NAME_TO_CODE]
            if len(hist_codes) >= 2 and hist_codes[-1] == hist_codes[-2] and hist_codes[-1] != best_code:
                best_code = hist_codes[-1]
                if is_cs: lang_name = self._get_cs_name(best_code)
                else: lang_name = LANGUAGE_CODE_MAP.get(best_code, "English")

        return self._build_res(best_code, sec_code, confidence, is_cs, "roman", "fused_heuristics", lang_name, (time.time()-t0)*1000, final_scores)

    def _get_cs_name(self, code: str) -> str:
        if code == "hi": return "Hinglish"
        elif code == "kn": return "Kanglish"
        elif code == "ta": return "Tamlish"
        elif code == "te": return "Tenglish"
        return LANGUAGE_CODE_MAP.get(code, "English")

    def _build_res(self, primary_code, sec_code, confidence, is_cs, script, method, lang_name, latency, all_scores=None):
        tts_code = f"{primary_code}-IN" if primary_code in ["kn", "hi", "ta", "te", "ml", "mr", "bn", "gu", "pa", "ur"] else f"{primary_code}-US"
        if primary_code == "es": tts_code = "es-ES"
        elif primary_code == "fr": tts_code = "fr-FR"
        elif primary_code == "de": tts_code = "de-DE"
        
        res = {
            "primary_language": primary_code,
            "secondary_language": sec_code,
            "confidence": round(confidence, 3),
            "is_code_switched": is_cs,
            "script": script,
            "all_languages": all_scores or {primary_code: 1.0},
            "detection_method": method,
            "tts_config": {
                "provider": "sarvam" if primary_code in ["hi", "kn", "ta", "te", "ml", "mr", "bn", "gu", "pa"] else "elevenlabs",
                "voice_code": tts_code,
                "speaking_rate": 1.0
            },
            "lang_name_display": lang_name,
            "latency_ms": round(latency, 2)
        }
        
        lang = res["primary_language"]
        if is_cs: res["llm_instruction"] = f"User is speaking {lang_name} (a mix of {LANGUAGE_CODE_MAP.get(lang, lang)} and English). Reply naturally mixing both languages. Use colloquial expressions and romanized script."
        elif lang in ["kn", "ta", "te", "ml", "hi", "mr", "bn", "gu", "pa"]: res["llm_instruction"] = f"User is speaking romanized {LANGUAGE_CODE_MAP.get(lang, lang)}. Reply in natural romanized {LANGUAGE_CODE_MAP.get(lang, lang)}."
        else: res["llm_instruction"] = f"User is speaking {LANGUAGE_CODE_MAP.get(lang, 'English')}. Reply naturally in {LANGUAGE_CODE_MAP.get(lang, 'English')}."
        
        logger.debug(f"[LangDetect] primary={primary_code} conf={confidence:.2f} method={method} ms={latency:.1f}")
        return res

class LanguageDetector:
    _pipeline = LanguagePipeline()
    @staticmethod
    def detect(text: str, rolling_history: list[str] | None = None, locked_lang: str | None = None) -> dict:
        return LanguageDetector._pipeline.detect(text, rolling_history, locked_lang)


def detect_language(text: str, rolling_history: list[str] | None = None, locked_lang: str | None = None) -> tuple[str, float]:
    res = LanguageDetector.detect(text, rolling_history, locked_lang)
    return res["lang_name_display"], res["confidence"]

def get_flag(language: str) -> str:
    return LANGUAGE_FLAGS.get(language, "🌐")

def get_fallback(language: str) -> str:
    return SMART_FALLBACKS.get(language, "Sorry, please try again.")
