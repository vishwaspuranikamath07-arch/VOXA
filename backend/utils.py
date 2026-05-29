from __future__ import annotations

import re
import time
import logging
from collections import defaultdict

HAS_LANGID = False

try:
    from lingua import LanguageDetectorBuilder
    _lingua_detector = LanguageDetectorBuilder.from_all_languages().with_minimum_relative_distance(0.1).build()
    HAS_LINGUA = True
except ImportError:
    HAS_LINGUA = False

try:
    import fasttext  # type: ignore
    import os
    ft_path = os.path.join(os.path.dirname(__file__), "dictionaries", "lid.176.ftz")
    if os.path.exists(ft_path):
        _fasttext_model = fasttext.load_model(ft_path)
        HAS_FASTTEXT = True
    else:
        HAS_FASTTEXT = False
except ImportError:
    HAS_FASTTEXT = False

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

# Extended definitive words from all lexicons
_DEFINITIVE_INDIAN.update({
    "hegiddira": "kn", "chennagide": "kn", "barthini": "kn", "hogona": "kn",
    "sigutthe": "kn", "bekhu": "kn", "nimage": "kn",
    "theriyum": "ta", "aamam": "ta", "mudiyum": "ta", "varinga": "ta",
    "ledhu": "te", "unnaru": "te", "telusaa": "te", "randi": "te",
    "bilkul": "hi", "lekin": "hi", "abhi": "hi", "aapka": "hi",
    "kartos": "mr", "tumhi": "mr", "sangto": "mr", "yeto": "mr", "hoil": "mr",
    "kemon": "bn", "acho": "bn", "bolun": "bn", "korben": "bn",
    "thakben": "bn", "dekhun": "bn",
    "chhe": "gu", "tamaro": "gu", "gamse": "gu", "majama": "gu",
    "kiddan": "pa", "tussi": "pa", "channga": "pa", "dasdo": "pa", "kithey": "pa",
    "enikku": "ml", "ariyilla": "ml",
    "meherbani": "ur", "shukriya": "ur",
})

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
    "Tamlish": "🇮🇳", "Tenglish": "🇮🇳", "Urdu": "🇵🇰",
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

NAME_TO_CODE = {v: k for k, v in LANGUAGE_CODE_MAP.items()}
NAME_TO_CODE.update({"Hinglish": "hi", "Kanglish": "kn", "Tamlish": "ta", "Tenglish": "te"})

_INDIAN_CODES = frozenset({"hi","kn","ta","te","ml","mr","bn","gu","pa","ur"})

# ── Dynamic Vocabulary Compilation ─────────────────────────────────────────────
_VOCAB: dict[str, dict[str, float]] = {
    "kn": ALL_KANNADA_WORDS.copy(),
    "hi": HINDI_WORDS.copy(),
    "ta": TAMIL_WORDS.copy(),
    "te": TELUGU_WORDS.copy(),
    "ml": MALAYALAM_WORDS.copy(),
    "mr": MARATHI_WORDS.copy(),
    "bn": BENGALI_WORDS.copy(),
    "gu": GUJARATI_WORDS.copy(),
    "pa": PUNJABI_WORDS.copy(),
    "ur": URDU_WORDS.copy(),
    "es": SPANISH_WORDS.copy(),
    "fr": FRENCH_WORDS.copy(),
    "de": GERMAN_WORDS.copy(),
    "pt": PORTUGUESE_WORDS.copy(),
    "it": ITALIAN_WORDS.copy(),
    "en": ENGLISH_WORDS.copy()
}

# Apply High Confidence Weights
for d, high in [
    (_VOCAB["hi"], HINDI_HIGH), (_VOCAB["ta"], TAMIL_HIGH), (_VOCAB["te"], TELUGU_HIGH),
    (_VOCAB["ml"], MALAYALAM_HIGH), (_VOCAB["mr"], MARATHI_HIGH), (_VOCAB["bn"], BENGALI_HIGH),
    (_VOCAB["gu"], GUJARATI_HIGH), (_VOCAB["pa"], PUNJABI_HIGH), (_VOCAB["ur"], URDU_HIGH),
    (_VOCAB["es"], SPANISH_HIGH), (_VOCAB["fr"], FRENCH_HIGH), (_VOCAB["de"], GERMAN_HIGH),
    (_VOCAB["pt"], PORTUGUESE_HIGH), (_VOCAB["it"], ITALIAN_HIGH)
]:
    d.update(high)

# Anti-collision Penalty: Penalize words shared across multiple languages (e.g., 'ki', 'oye')
_word_lang_counts = defaultdict(list)
for lang, vocab in _VOCAB.items():
    for w in vocab:
        _word_lang_counts[w].append(lang)

for w, langs in _word_lang_counts.items():
    if len(langs) >= 3 and "en" not in langs:
        penalty = 1.0 / len(langs)
        for l in langs:
            if _VOCAB[l][w] <= 1.0:  # Don't strongly penalize unique high-weight markers
                _VOCAB[l][w] *= penalty

# Compile Morphological Patterns
_COMPILED_KANNADA_REGEX = [(re.compile(pat), weight) for pat, weight in KANNADA_SUFFIX_PATTERNS]
_COMPILED_DRAVIDIAN_REGEX = [(re.compile(pat), weight) for pat, weight in DRAVIDIAN_SUFFIXES]

# English Function Words
_ENGLISH_FUNC = frozenset(ENGLISH_WORDS.keys())

# Startup stubs
_compiled_lexicons = {}
def _compile_lexicons(): pass
def _build_ngram_profiles(): pass

class LanguagePipeline:
    def detect(self, text: str,
               rolling_history: list[str] | None = None,
               locked_lang: str | None = None) -> dict:

        t0 = time.perf_counter()
        text_clean = text.strip()
        text_lower = text_clean.lower()
        words: list[str] = _TOKEN_PAT.findall(text_lower)

        en_hits = sum(1 for w in words if w in _ENGLISH_FUNC)
        is_cs = False

        # Phase 0: Lock
        if locked_lang:
            code = NAME_TO_CODE.get(locked_lang, "en")
            is_cs = (en_hits / len(words) > 0.25) if words else False
            is_cs = is_cs and code in _INDIAN_CODES
            lang_name = self._get_cs_name(code) if is_cs else locked_lang
            return self._build_res(code, "en" if is_cs else None, 0.97, is_cs,
                                   "native", "frontend_lock", lang_name,
                                   (time.perf_counter()-t0)*1000)

        if not text_clean:
            return self._build_res("en", None, 1.0, False, "roman", "empty",
                                   "English", 0.0)

        # Phase 1: Unicode Override
        uni_counts: dict[str, int] = defaultdict(int)
        for ch in text_clean:
            if ch.isspace() or ord(ch) < 128:
                continue
            cp = ord(ch)
            for lang, (lo, hi) in UNICODE_RANGES.items():
                if lo <= cp <= hi:
                    uni_counts[lang] += 1
                    break
        if uni_counts:
            total_uni = sum(uni_counts.values())
            best_uni: str = max(uni_counts.keys(), key=lambda k: uni_counts[k])
            if uni_counts[best_uni] / total_uni >= 0.75:
                if best_uni == "hi":
                    word_set = set(text_clean.split())
                    if len(word_set & MARATHI_NATIVE_MARKERS) > len(word_set & HINDI_NATIVE_MARKERS):
                        best_uni = "mr"
                lang_name = LANGUAGE_CODE_MAP.get(best_uni, "English")
                return self._build_res(best_uni, None, 0.99, False, "native",
                                       "unicode_script", lang_name,
                                       (time.perf_counter()-t0)*1000)

        # Phase 2: Definitive Fast-Path
        # Requires ≥ 2 hits or ≥ 1 hit with a clear majority for single-word inputs
        # to avoid misfiring on ambiguous short phrases.
        def_hits = defaultdict(int)
        for w in set(words):
            if w in _DEFINITIVE_INDIAN:
                def_hits[_DEFINITIVE_INDIAN[w]] += 1
        if def_hits:
            def_lang: str = max(def_hits.keys(), key=lambda k: def_hits[k])
            top_hits = def_hits[def_lang]
            # Short transcripts (≤ 3 words): require ≥ 2 definitive hits to commit
            # Longer transcripts: 1 strong hit is sufficient
            min_hits_required = 2 if len(words) <= 3 else 1
            if top_hits >= min_hits_required:
                def_cs = en_hits > 0 and def_lang in _INDIAN_CODES
                def_name = self._get_cs_name(def_lang) if def_cs else LANGUAGE_CODE_MAP.get(def_lang, "English")
                return self._build_res(def_lang, "en" if def_cs else None, 0.97,
                                       def_cs, "roman", "definitive_word", def_name,
                                       (time.perf_counter()-t0)*1000)
            # Single hit on short text: continue to fuller scoring below

        # Phase 3: FastText High-Confidence Override (if available)
        if HAS_FASTTEXT:
            preds = _fasttext_model.predict(text_lower.replace('\n', ' '))
            ft_lang = preds[0][0].replace('__label__', '')
            ft_conf = preds[1][0]
            # FastText is reliable > 0.85, map its output to our codes
            ft_map = {"hin":"hi", "kan":"kn", "tam":"ta", "tel":"te", "mal":"ml", "mar":"mr",
                      "ben":"bn", "guj":"gu", "pan":"pa", "urd":"ur", "eng":"en", "spa":"es",
                      "fra":"fr", "deu":"de", "por":"pt", "ita":"it"}
            if ft_conf > 0.85 and ft_lang in ft_map:
                mapped_lang = ft_map[ft_lang]
                ft_cs = en_hits > 0 and mapped_lang in _INDIAN_CODES
                lang_name = self._get_cs_name(mapped_lang) if ft_cs else LANGUAGE_CODE_MAP.get(mapped_lang, "English")
                return self._build_res(mapped_lang, "en" if ft_cs else None, ft_conf,
                                       ft_cs, "roman", "fasttext", lang_name,
                                       (time.perf_counter()-t0)*1000)

        # Phase 4: Bigram & Vocabulary Scoring
        vocab_scores = defaultdict(float)
        
        # Bigrams (2x weight)
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        for bg in bigrams:
            for lang, vocab in _VOCAB.items():
                if bg in vocab:
                    vocab_scores[lang] += vocab[bg] * 2.0
            if bg in BANGALORE_SLANG:
                vocab_scores["kn"] += BANGALORE_SLANG[bg] * 2.0

        # Unigrams
        for w in words:
            for lang, vocab in _VOCAB.items():
                if w in vocab:
                    vocab_scores[lang] += vocab[w]

        # Phase 5: Morphological Regex Scoring (crucial for Kannada/Dravidian)
        for pat, weight in _COMPILED_KANNADA_REGEX:
            if pat.search(text_lower):
                vocab_scores["kn"] += weight * 1.5
                
        for pat, weight in _COMPILED_DRAVIDIAN_REGEX:
            if pat.search(text_lower):
                # Spread Dravidian suffix weight loosely, but prioritize kn/ta/te
                vocab_scores["kn"] += weight * 0.5
                vocab_scores["ta"] += weight * 0.5
                vocab_scores["te"] += weight * 0.5
                vocab_scores["ml"] += weight * 0.5

        # Anti-Kannada Exclusion for Portuguese
        if any(w in PORTUGUESE_KANNADA_EXCLUSIONS for w in words) and vocab_scores.get("pt", 0) > 0:
            vocab_scores["kn"] = max(0, vocab_scores.get("kn", 0) - 2.0)

        # ── Context history — weak signal only ──────────────────────────────────
        # Extract previous language as a very weak tie-breaker signal.
        # It MUST NOT override current-turn evidence. The only purpose here is
        # to nudge an ambiguous (near-tie) result toward the most-recent language.
        context_lang = None
        if rolling_history:
            hist_codes = [NAME_TO_CODE.get(h, "en") for h in rolling_history if h in NAME_TO_CODE]
            if hist_codes:
                # Use majority vote across recent history instead of just last turn
                from collections import Counter as _Counter
                hist_counter = _Counter(hist_codes)
                context_lang = hist_counter.most_common(1)[0][0]

        if not vocab_scores:
            # No lexical signal at all — context is a very weak fallback
            if context_lang and context_lang in _INDIAN_CODES:
                return self._build_res(context_lang, None, 0.35, False, "roman",
                                       "context_fallback", LANGUAGE_CODE_MAP.get(context_lang, "English"),
                                       (time.perf_counter()-t0)*1000)
            return self._build_res("en", None, 0.55, False, "roman", "no_signal",
                                   "English", (time.perf_counter()-t0)*1000)

        # Length normalization
        n = max(1, len(words))
        norm_scores = {lang: s / (n ** 0.5) for lang, s in vocab_scores.items()}

        # Sort BEFORE applying context nudge so we can measure how clear the winner is
        sorted_langs_pre = sorted(norm_scores.items(), key=lambda x: -x[1])
        top_score  = sorted_langs_pre[0][1]
        sec_score  = sorted_langs_pre[1][1] if len(sorted_langs_pre) > 1 else 0.0
        score_gap  = top_score - sec_score

        # ── Context nudge (ONLY applied when the current signal is genuinely ambiguous)
        # Threshold: if current best score beats second by >= 0.40 normalized points,
        # the current transcript is a clear winner — skip history bias entirely.
        # If the gap is small, apply a tiny 5% nudge (down from the old 25%).
        CLEAR_WIN_GAP   = 0.40   # current transcript dominates → ignore history
        WEAK_NUDGE_MULT = 1.05   # context nudge: only 5% boost (was 1.25 = 25%)

        if context_lang and context_lang in norm_scores and score_gap < CLEAR_WIN_GAP:
            # Apply only a tiny nudge so history can break ties, not override wins
            norm_scores[context_lang] = min(norm_scores[context_lang] * WEAK_NUDGE_MULT, 10.0)

        sorted_langs = sorted(norm_scores.items(), key=lambda x: -x[1])
        final_lang = sorted_langs[0][0]
        raw_score = sorted_langs[0][1]

        # Lingua Tie-Breaker
        if HAS_LINGUA and len(sorted_langs) > 1:
            score_diff = sorted_langs[0][1] - sorted_langs[1][1]
            if score_diff < 0.15 and raw_score < 1.0: # Only tie-break weak signals
                ling_res = _lingua_detector.detect_language_of(text_clean)
                if ling_res:
                    ling_code = ling_res.iso_code_639_1.name.lower()
                    if ling_code in norm_scores:
                        final_lang = ling_code

        # Confidence Calibration
        confidence = min(0.97, 0.4 + raw_score / (raw_score + 2.0))

        en_ratio = en_hits / n
        is_cs = final_lang in _INDIAN_CODES and en_hits > 0
        sec_code = "en" if is_cs else None
        lang_name = self._get_cs_name(final_lang) if is_cs else LANGUAGE_CODE_MAP.get(final_lang, "English")

        return self._build_res(final_lang, sec_code, confidence, is_cs,
                               "roman", "ensemble", lang_name,
                               (time.perf_counter()-t0)*1000)

    def _get_cs_name(self, code: str) -> str:
        cs = {"hi":"Hinglish","kn":"Kanglish","ta":"Tamlish","te":"Tenglish"}
        return cs.get(code, LANGUAGE_CODE_MAP.get(code, "English"))

    def _build_res(self, primary_code: str, sec_code: str | None, confidence: float,
                   is_cs: bool, script: str, method: str, lang_name: str,
                   latency: float) -> dict:
        _SARVAM = {"hi","kn","ta","te","ml","mr","bn","gu","pa"}
        tts_map = {"es":"es-ES","fr":"fr-FR","de":"de-DE","pt":"pt-BR","it":"it-IT",
                   "ru":"ru-RU","ja":"ja-JP","zh":"zh-CN","ko":"ko-KR","ar":"ar-SA"}
        tts_code = tts_map.get(primary_code, f"{primary_code}-IN" if primary_code in _SARVAM else "en-US")
        
        res = {
            "primary_language": primary_code,
            "secondary_language": sec_code,
            "confidence": round(confidence, 3),
            "is_code_switched": is_cs,
            "script": script,
            "detection_method": method,
            "tts_config": {
                "provider": "sarvam" if primary_code in _SARVAM else "elevenlabs",
                "voice_code": tts_code,
                "speaking_rate": 1.0
            },
            "lang_name_display": lang_name,
            "latency_ms": round(latency, 2)
        }
        
        lang = primary_code
        if is_cs:
            res["llm_instruction"] = (f"User is speaking {lang_name} (mix of "
                f"{LANGUAGE_CODE_MAP.get(lang, lang)} and English). You MUST reply in NATIVE {LANGUAGE_CODE_MAP.get(lang, lang)} script (with some English words if natural). NEVER use romanized {LANGUAGE_CODE_MAP.get(lang, lang)}.")
        elif lang in _SARVAM:
            res["llm_instruction"] = (f"User is speaking {LANGUAGE_CODE_MAP.get(lang, lang)}. "
                f"You MUST reply in NATIVE {LANGUAGE_CODE_MAP.get(lang, lang)} script. NEVER use romanized {LANGUAGE_CODE_MAP.get(lang, lang)}.")
        else:
            res["llm_instruction"] = (f"User is speaking {LANGUAGE_CODE_MAP.get(lang, 'English')}. "
                f"Reply naturally in {LANGUAGE_CODE_MAP.get(lang, 'English')}.")
                
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
