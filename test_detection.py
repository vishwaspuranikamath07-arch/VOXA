"""Quick validation of the upgraded language detection engine."""
from backend.utils import detect_language

tests = [
    # (input_text, expected_language)
    ("matte hege idira",             "Kannada"),    # pure Kannada romanized
    ("sumne guru bidu",              "Kannada"),    # pure Kannada slang
    ("yaake idira",                  "Kannada"),    # pure Kannada romanized
    ("hegiddira aata",               "Kannada"),    # pure Kannada romanized
    ("bartha idira matte",           "Kannada"),    # multiple Kannada words
    ("kya ho raha hai yaar",         "Hindi"),      # pure Hindi romanized
    ("bahut achha hai bhai",         "Hindi"),      # pure Hindi romanized
    ("arre yaar kya kar raha hai",   "Hindi"),      # pure Hindi romanized
    ("what is the weather today",    "English"),
    ("can you help me please",       "English"),
    ("bonjour comment allez vous",   "French"),
    ("hola como estas amigo",        "Spanish"),
    ("kemon acho tumi",              "Bengali"),    # Bengali
    ("enna panra nee",               "Tamil"),       # Tamil slang (romanized)
    ("ela unnav meeru",              "Telugu"),      # Telugu romanized
]

print("Language Detection Test Results")
print("=" * 65)
passed = 0
for text, expected in tests:
    result, conf = detect_language(text)
    ok = result == expected
    if ok:
        passed += 1
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] Expected: {expected:12s} | Got: {result:12s} ({conf:.2f}) | \"{text}\"")

print("=" * 65)
print(f"Result: {passed}/{len(tests)} passed")
