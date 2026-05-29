"""
tests/test_language_detection.py

Unit tests for the new LanguageDetector engine.
Covers Kannada overrides, Hinglish/Kanglish code-switching, and global languages.
"""

import pytest
from backend.utils import LanguageDetector, detect_language

def test_kannada_kanglish():
    # 1. Kannada override (gothilla/illa should trigger kn)
    res = LanguageDetector.detect("gothilla bro adu hege madodu")
    assert res["primary_language"] == "kn"
    assert res["is_code_switched"] == True
    assert res["lang_name_display"] == "Kanglish"

    # 2. Pure Kannada
    res = LanguageDetector.detect("nanu hogbeku illa barolla")
    assert res["primary_language"] == "kn"
    assert res["is_code_switched"] == False
    assert res["lang_name_display"] == "Kannada"

    # 3. Kanglish ("yenu" is English loanword in spoken Kannada)
    res = LanguageDetector.detect("idu yenu aagtha ide")
    assert res["primary_language"] == "kn"
    assert res["lang_name_display"] in ("Kannada", "Kanglish")

    # 4. Kanglish
    res = LanguageDetector.detect("bro idu correct illa")
    assert res["primary_language"] == "kn"
    assert res["is_code_switched"] == True
    assert res["lang_name_display"] == "Kanglish"

    # 5. Kanglish (meeting cancel madidya)
    res = LanguageDetector.detect("meeting cancel madidya")
    assert res["primary_language"] == "kn"
    assert res["is_code_switched"] == True
    assert res["lang_name_display"] == "Kanglish"

def test_hindi_hinglish():
    # 6. Hinglish
    res = LanguageDetector.detect("yaar kya kar raha hai")
    assert res["primary_language"] == "hi"
    assert res["is_code_switched"] == False  # "yaar" is hindi
    assert res["lang_name_display"] == "Hindi"

    # Hinglish with English
    res = LanguageDetector.detect("yaar what is this problem, kya kar raha hai")
    assert res["primary_language"] == "hi"
    assert res["is_code_switched"] == True
    assert res["lang_name_display"] == "Hinglish"

def test_tamil_tamlish():
    # 7. Tamlish ("machan" is common English-origin slang in Tamil)
    res = LanguageDetector.detect("machan enna panrom")
    assert res["primary_language"] == "ta"
    assert res["lang_name_display"] in ("Tamil", "Tamlish")
    
    res = LanguageDetector.detect("bro enna panrom we need to go")
    assert res["primary_language"] == "ta"
    assert res["is_code_switched"] == True
    assert res["lang_name_display"] == "Tamlish"

def test_global_languages():
    # 8. Spanish
    res = LanguageDetector.detect("hola como estas")
    assert res["primary_language"] == "es"
    assert res["lang_name_display"] == "Spanish"

    # 9. Spanish
    res = LanguageDetector.detect("no entiendo que dices")
    assert res["primary_language"] == "es"

    # 10. German
    res = LanguageDetector.detect("ich verstehe nicht")
    assert res["primary_language"] == "de"
    assert res["lang_name_display"] == "German"
    
    # French
    res = LanguageDetector.detect("bonjour merci beaucoup")
    assert res["primary_language"] == "fr"

def test_native_scripts():
    # 12. Native Kannada
    res = LanguageDetector.detect("ನಾನು ಹೋಗಬೇಕು")
    assert res["primary_language"] == "kn"
    assert res["script"] == "native"
    assert res["lang_name_display"] == "Kannada"

    # 13. Native Hindi
    res = LanguageDetector.detect("मैं नहीं जानता")
    assert res["primary_language"] == "hi"
    assert res["script"] == "native"
    assert res["lang_name_display"] == "Hindi"

def test_edge_cases():
    # 11. Mixed generic (English)
    res = LanguageDetector.detect("bro the output illa coming")
    assert res["primary_language"] == "kn"  # illa pushes it to Kanglish
    assert res["is_code_switched"] == True
    assert res["lang_name_display"] == "Kanglish"

    # Empty
    res = LanguageDetector.detect("   ")
    assert res["primary_language"] == "en"
    
    # Numbers
    res = LanguageDetector.detect("12345 67890")
    assert res["primary_language"] == "en"

def test_backward_compat():
    name, conf = detect_language("gothilla bro adu hege madodu")
    assert name == "Kanglish"
    assert isinstance(conf, float)
    
    name, conf = detect_language("मैं नहीं जानता")
    assert name == "Hindi"

def test_false_positives():
    # Portuguese without Kannada overlap
    res = LanguageDetector.detect("ola tudo bem")
    assert res["primary_language"] == "pt"

    # "alla" in Portuguese vs Kannada. 
    # If it's just "alla" with no other Kannada words, it might be ambiguous.
    # But "alla" + Kannada words should be Kannada.
    res = LanguageDetector.detect("adu nandu alla")
    assert res["primary_language"] == "kn"
