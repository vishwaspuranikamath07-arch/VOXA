import sys
import logging

logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

sys.path.insert(0, ".")
from backend.utils import LanguageDetector, _compile_lexicons, _build_ngram_profiles

_compile_lexicons()
_build_ngram_profiles()

print("--- Full Detection Test (Indian + English context-switch) ---")

cases = [
    # Indian languages
    ("hegiddira",        [],          "Kannada",  "Romanized Kannada"),
    ("chennagide",       [],          "Kannada",  "Romanized Kannada 2"),
    ("yaar kya hua",     [],          "Hindi",    "Romanized Hindi"),
    ("tumhi kase aahat", [],          "Marathi",  "Romanized Marathi"),
    ("tumi kemon acho",  [],          "Bengali",  "Romanized Bengali"),
    ("enti ela unnaru",  [],          "Telugu",   "Romanized Telugu"),
    ("enna vanakkam",    [],          "Tamil",    "Romanized Tamil"),
    ("kiddan tussi",     [],          "Punjabi",  "Romanized Punjabi"),
    ("kem cho tamaro",   [],          "Gujarati", "Romanized Gujarati"),
    # English after Indian context (THE BUG from screenshot)
    ("how you are",      ["Gujarati"],"English",  "English after Gujarati context"),
    ("how are you",      ["Hindi"],   "English",  "English after Hindi context"),
    ("ok thanks",        ["Kannada"], "English",  "English ok after Indian context"),
    ("what is this",     ["Tamil"],   "English",  "English question after Tamil"),
    # Pure English (no context)
    ("hello how are you",[]          ,"English",  "Pure English"),
]

passed = 0
for text, hist, expected, desc in cases:
    res = LanguageDetector.detect(text, hist)
    detected = res["lang_name_display"]
    ok = detected == expected
    status = "PASS" if ok else "FAIL"
    print(f"{status}  [{desc}]")
    if not ok:
        print(f"       Got: {detected!r}  Expected: {expected!r}  conf={res['confidence']:.2f}  method={res['detection_method']}")
    if ok:
        passed += 1

print(f"\nResult: {passed}/{len(cases)} passed")
