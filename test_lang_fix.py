"""
Smoke test: verify that previous Kannada context does NOT dominate
when the user switches to Bengali, Marathi, Tamil, or English.
"""
from backend.utils import LanguageDetector

TESTS = [
    # (transcript,               prev_lang_history,                     expected_lang)
    ("nanu hogthini",             [],                                    "Kannada"),
    ("ami kothay jabo",           ["Kannada"],                           "Bengali"),   # Switch Kannada→Bengali
    ("mala jaichi aahe tumhi",   ["Kannada", "Kannada"],                 "Marathi"),   # Switch Kannada→Marathi
    ("hello how are you",        ["Kannada"],                            "English"),   # Switch Kannada→English
    ("naan romba kashtapaduren", ["Kannada"],                            "Tamil"),     # Switch Kannada→Tamil
    ("main theek hoon yaar",     ["Bengali"],                            "Hindi"),     # Switch Bengali→Hindi
    ("nanu hogthini beku",       ["Bengali", "Bengali"],                 "Kannada"),   # Switch Bengali→Kannada
    ("how are you today",        ["Kannada", "Kannada"],                 "English"),   # English after Kannada
    ("kemon acho",               ["Hindi"],                              "Bengali"),   # Bengali after Hindi
    ("eppadi irukeenga machan",  ["Kannada"],                            "Tamil"),     # Tamil after Kannada
]

print(f"{'Input':<32} {'PrevHistory':<28} {'Expected':<14} {'Got':<14} {'Conf':>6}  {'Method':<22}  {'OK?'}")
print("-" * 130)

passes = 0
for transcript, history, expected in TESTS:
    result = LanguageDetector.detect(transcript, history)
    got    = result["lang_name_display"]
    conf   = result["confidence"]
    method = result["detection_method"]
    ok     = "PASS" if got == expected else "FAIL"
    if got == expected:
        passes += 1
    print(f"{transcript:<32} {str(history):<28} {expected:<14} {got:<14} {conf:>6.2f}  {method:<22}  {ok}")

print()
print(f"Result: {passes}/{len(TESTS)} tests passed")
