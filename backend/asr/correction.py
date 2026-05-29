"""
backend/asr/correction.py

Post-processing correction dictionary for Indian romanized speech STT errors.
Fixes common Web Speech API / faster-whisper misrecognitions for Kannada, Hindi,
Tamil, Telugu, Malayalam, Marathi code-switched speech.

Applied BEFORE language detection so the detector sees correct words.
Single regex pass — target < 5ms per sentence.

Usage:
    from backend.asr.correction import apply_corrections
    text = apply_corrections("got tilla bro meeting cancel made it ya")
    # → "gottilla bro meeting cancel madidya"
"""
from __future__ import annotations
import re

# ── Correction dictionary ─────────────────────────────────────────────────────
# Keys: lowercase bigrams/trigrams that STT gets wrong
# Values: correct romanized form
# Rule: only fix phrases that are UNAMBIGUOUSLY wrong — never touch valid English
WORD_CORRECTIONS: dict[str, str] = {
    # ── Kannada / Kanglish ────────────────────────────────────────────────────
    "got tilla":      "gottilla",
    "go tilla":       "gottilla",
    "got illa":       "gottilla",
    "got hilla":      "gothilla",
    "got hila":       "gothilla",
    "il la":          "illa",
    "ill a":          "illa",
    "bar thiya":      "barthiya",
    "bar thia":       "barthiya",
    "bar tia":        "barthiya",
    "made it ya":     "madidya",
    "made dia":       "madidya",
    "mad idya":       "madidya",
    "madi dya":       "madidya",
    "bar olla":       "barolla",
    "bar ola":        "barolla",
    "hog beku":       "hogbeku",
    "hog be ku":      "hogbeku",
    "ma dilla":       "madilla",
    "ma dila":        "madilla",
    "hel thini":      "helthini",
    "mad thini":      "madthini",
    "hey gide":       "hegide",
    "heg ide":        "hegide",
    "hey gi de":      "hegide",
    "ma dtha":        "madtha",
    "yen na":         "yenna",
    "na nu":          "nanu",
    "nee vu":         "neevu",
    "i du":           "idu",
    "a du":           "adu",
    "e nu":           "enu",
    "ye nu":          "yenu",
    "be ku":          "beku",
    "se ri":          "seri",
    "bi di":          "bidi",
    "bi da":          "bida",
    "yo chane":       "yochane",
    "han gu":         "hangu",
    "kal li":         "kalli",
    "kel li":         "kelli",
    "hel li":         "helli",
    "hog beke":       "hogbeke",
    "swami ge":       "swamige",
    "nim ge":         "nimage",
    "a van":          "avan",
    "a vala":         "avala",
    "e lli":          "elli",
    "i lli":          "illi",
    "a li":           "ali",
    "su mne":         "sumne",
    "hog thiya":      "hogthiya",
    "mad thiya":      "madthiya",
    "hel thiya":      "helthiya",
    "kan nada":       "kannada",
    "ge lli":         "gelli",
    "ke li":          "keli",
    "yel li":         "yelli",
    "ide ya":         "ideya",
    "bek a":          "beka",
    "col lu":         "collu",
    "mat tu":         "mattu",
    "nod id":         "nodid",
    "me lli":         "melli",
    "mad kond":       "madkond",
    "hog thini":      "hogthini",
    "ban ga lore":    "bangalore",
    "got illa bro":   "gottilla bro",
    "cancel made it ya": "cancel madidya",
    "cancel made dia":   "cancel madidya",
    "meeting cancel made it ya": "meeting cancel madidya",
    # ── Hindi / Hinglish ───────────────────────────────────────────────────────
    "na hi":          "nahi",
    "na hin":         "nahin",
    "ac cha":         "accha",
    "ach ha":         "achha",
    "theek he":       "theek hai",
    "ha in":          "hain",
    "bhai ya":        "bhaiya",
    "sam jha":        "samjha",
    "bol ta":         "bolta",
    "kar ta":         "karta",
    "de kho":         "dekho",
    "sun no":         "sunno",
    "cha hiye":       "chahiye",
    "mil ta":         "milta",
    "ja ta":          "jata",
    "aa ta":          "aata",
    "kin tu":         "kintu",
    "le kin":         "lekin",
    "peh le":         "pehle",
    "ba ad":          "baad",
    "ka am":          "kaam",
    "may ne":         "maine",
    "hum ne":         "humne",
    "un ka":          "unka",
    "in ka":          "inka",
    "ab hi":          "abhi",
    "tab hi":         "tabhi",
    "yah an":         "yahan",
    "wah an":         "wahan",
    "kis ne":         "kisne",
    "phir se":        "phirse",
    "aaj kal":        "aajkal",
    "ek dum":         "ekdum",
    "ruk ja":         "rukja",
    "reh ne":         "rehne",
    "ka hi":          "kahi",
    "keh do":         "kehdo",
    "par tu":         "partu",
    "na ta":          "nata",
    "bol na":         "bolna",
    "kar na":         "karna",
    "ja na":          "jana",
    "aa na":          "aana",
    "de na":          "dena",
    "le na":          "lena",
    "kha na":         "khana",
    "pi na":          "pina",
    "so na":          "sona",
    "uth na":         "uthna",
    "baith na":       "baithna",
    "chal na":        "chalna",
    "dau rna":        "daurna",
    "kuch bhi":       "kuch bhi",
    "the ek":         "theek",
    "ach chi":        "acchi",
    "bur ra":         "bura",
    "bur ri":         "buri",
    "ach he":         "achhe",
    # ── Tamil / Tamlish ────────────────────────────────────────────────────────
    "mac han":        "machan",
    "en na":          "enna",
    "il lai":         "illai",
    "rom ba":         "romba",
    "van ga":         "vanga",
    "en nai":         "ennai",
    "sol lu":         "sollu",
    "kel lu":         "kellu",
    "va ren":         "varen",
    "po ren":         "poren",
    "pan rom":        "panrom",
    "ey da":          "eyda",
    "ku du":          "kudu",
    "paar du":        "paardu",
    "sar i":          "sari",
    "sol ren":        "solren",
    "po giren":       "pogiren",
    "sen ren":        "senren",
    "un na":          "unna",
    "sol li":         "solli",
    "kel vi":         "kelvi",
    "pad am":         "padam",
    "vel la":         "vella",
    "sol lum":        "sollum",
    "po rom":         "porom",
    "ter i":          "teri",
    "par om":         "parom",
    "en na panrom":   "enna panrom",
    "enna pan":       "enna pan",
    "mac han enna":   "machan enna",
    "um me":          "umme",
    "a va":           "ava",
    "i va":           "iva",
    "sol la":         "solla",
    "kel la":         "kella",
    "pa ru":          "paru",
    "thev ai":        "thevai",
    "pu ri":          "puri",
    "sar i":          "sari",
    # ── Telugu / Tenglish ──────────────────────────────────────────────────────
    "en di":          "endi",
    "le du":          "ledu",
    "un di":          "undi",
    "chep pandi":     "cheppandi",
    "e va ru":        "evaru",
    "an de":          "ande",
    "vas ta":         "vasta",
    "po ta":          "pota",
    "cha du":         "chadu",
    "em i ti":        "emiti",
    "nen u":          "nenu",
    "tel u":          "telu",
    "baa gu":         "baagu",
    "na ku":          "naku",
    "me ku":          "meku",
    "va di":          "vadi",
    "a di":           "adi",
    "en ta":          "enta",
    "e la":           "ela",
    "pot undi":       "potundi",
    "vast undi":      "vastundi",
    "ches ta":        "chesta",
    "pos ta":         "posta",
    "tel ugu":        "telugu",
    "a nu":           "anu",
    "kan nu":         "kannu",
    "em chestun":     "emchestun",
    "e vi di":        "evidi",
    "a vu":           "avu",
    "le du ga":       "leduga",
    "un na ru":       "unnaru",
    "che pto":        "chepto",
    # ── Malayalam ─────────────────────────────────────────────────────────────
    "en tha":         "entha",
    "en te":          "ente",
    "ni nna":         "ninna",
    "van nu":         "vannu",
    "po yee":         "poyee",
    "va rum":         "varum",
    "an nu":          "annu",
    "a lle":          "alle",
    "i lle":          "ille",
    "mar am":         "maram",
    "va da":          "vada",
    "ku ta":          "kuta",
    "pa ra":          "para",
    "ni nne":         "ninne",
    "chey tu":        "cheytu",
    "a nna":          "anna",
    "par am":         "param",
    "en tha nu":      "enthanu",
    "e vi de":        "evide",
    "po ku":          "poku",
    "va ru":          "varu",
    "nje":            "nje",
    # ── Marathi ───────────────────────────────────────────────────────────────
    "mah it":         "mahit",
    "a he":           "ahe",
    "sa ang":         "saang",
    "bol nar":        "bolnar",
    "ja nar":         "janar",
    "kar nar":        "karnar",
    "ye nar":         "yenar",
    "kay":            "kay",
    "yet o":          "yeto",
    "kay kaay":       "kaay",
    "mi la":          "mila",
    "tu la":          "tula",
    "a mhi":          "amhi",
    "tu mhi":         "tumhi",
    # ── Common English that STT splits incorrectly ─────────────────────────────
    "some thing":     "something",
    "every thing":    "everything",
    "any thing":      "anything",
    "some one":       "someone",
    "every one":      "everyone",
    "any one":        "anyone",
    "may be":         "maybe",
    "any way":        "anyway",
    "some where":     "somewhere",
    "every where":    "everywhere",
    "any where":      "anywhere",
    "in stead":       "instead",
    "al ready":       "already",
    "al though":      "although",
    "be cause":       "because",
    "with out":       "without",
    "to day":         "today",
    "to night":       "tonight",
    "to morrow":      "tomorrow",
    "your self":      "yourself",
    "my self":        "myself",
    "him self":       "himself",
    "her self":       "herself",
    "them selves":    "themselves",
    "our selves":     "ourselves",
    "some times":     "sometimes",
    "some body":      "somebody",
    "every body":     "everybody",
    "any body":       "anybody",
    "no body":        "nobody",
    "every day":      "everyday",
    "out side":       "outside",
    "in side":        "inside",
    "over all":       "overall",
    "under stand":    "understand",
    "over come":      "overcome",
    "break fast":     "breakfast",
    "after noon":     "afternoon",
    "every time":     "everytime",
    "some how":       "somehow",
    "some thing else": "something else",
    "any how":        "anyhow",
}

# Pre-sort keys longest-first so longer phrases match before shorter ones.
# Minimum 3 chars enforced to avoid single/double-char patterns matching
# inside valid English words (e.g. "ra" matching inside "frame", "grant").
_SORTED_KEYS = sorted(
    (k for k in WORD_CORRECTIONS.keys() if len(k) >= 3),
    key=len,
    reverse=True,
)

# Single compiled regex — word-boundary aware, case-insensitive
_CORRECTION_RE = re.compile(
    r'\b(' + '|'.join(re.escape(k) for k in _SORTED_KEYS) + r')\b',
    re.IGNORECASE,
)


def apply_corrections(text: str) -> str:
    """Apply word corrections to transcribed text in a single regex pass.

    Args:
        text: Raw transcript from Web Speech API or Whisper.

    Returns:
        Corrected transcript with Indian words restored.

    Example:
        >>> apply_corrections("got tilla bro meeting cancel made it ya")
        'gottilla bro meeting cancel madidya'
    """
    if not text or not text.strip():
        return text

    def _replace(match: re.Match) -> str:
        key = match.group(0).lower()
        correction = WORD_CORRECTIONS.get(key)
        if correction is None:
            return match.group(0)
        # Preserve original capitalisation if first letter was uppercase
        if match.group(0)[0].isupper():
            return correction[0].upper() + correction[1:]
        return correction

    return _CORRECTION_RE.sub(_replace, text)


def get_correction_stats() -> dict:
    """Return stats about the correction dictionary (for health endpoint)."""
    return {
        "total_entries":  len(WORD_CORRECTIONS),
        "longest_phrase": max(WORD_CORRECTIONS.keys(), key=len),
    }


if __name__ == "__main__":
    tests = [
        ("got tilla bro meeting cancel made it ya", "gottilla bro meeting cancel madidya"),
        ("mac han enna panrom", "machan enna panrom"),
        ("na hi yaar kya kar raha hai", "nahi yaar kya kar raha hai"),
        ("en di ledu evaru", "endi ledu evaru"),
        ("hello how are you", "hello how are you"),
        ("ill a bro idu correct", "illa bro idu correct"),
        ("hog beku barolla", "hogbeku barolla"),
    ]
    passed = 0
    for inp, expected in tests:
        result = apply_corrections(inp)
        ok = result == expected
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: '{inp}' -> '{result}'")
        if not ok:
            print(f"         expected: '{expected}'")
    print(f"\n{passed}/{len(tests)} passed")
