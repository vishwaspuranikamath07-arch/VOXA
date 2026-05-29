import sys, os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

from backend.utils import detect_language, get_flag, SMART_FALLBACKS, SUPPORTED_LANGUAGES

tests = [
    # Basic English
    ("Hello how are you?", "English"),
    ("I want to know the weather today", "English"),
    ("Please help me with this task", "English"),
    
    # English with ambiguous short words
    ("is it ok if I go", "English"),
    ("no I do not want it", "English"),
    
    # European
    ("Hola como estas amigo", "Spanish"),
    ("Buenos dias a todos", "Spanish"),
    ("Bonjour, comment ca va?", "French"),
    ("Je suis tres fatigue", "French"),
    ("Danke schon, wie geht es dir", "German"),
    ("Ich muss gehen", "German"),
    ("Ciao come stai oggi", "Italian"),
    ("Ola tudo bem", "Portuguese"),
    ("Muito obrigado pela ajuda", "Portuguese"),
    
    # Hindi
    ("kya haal hai, namaste bhai", "Hindi"),
    ("mujhe khana khana hai", "Hindi"),
    ("main aaj bahut khush hoon", "Hindi"),
    ("yeh bilkul theek nahi hai", "Hindi"),
    ("haan yaar achha laga", "Hindi"),
    ("kya?", "Hindi"), # short word
    ("nahi", "Hindi"), # ambiguous with Marathi/Punjabi
    
    # Hinglish
    ("Hello yaar kya haal hai bhai", "Hinglish"),
    ("please mujhe batao ye kaise karna hai", "Hinglish"),
    ("main ready hoon, let's go", "Hinglish"),
    ("wow bahut badhiya lag raha hai", "Hinglish"),
    
    # Kannada
    ("Hegide nimma hesaru, dayavittu", "Kannada"),
    ("naanu bengluralli iddini", "Kannada"),
    ("oota aayta guru", "Kannada"),
    ("nanage thumba ishta aaythu", "Kannada"),
    ("illa", "Kannada"), # short
    ("beku", "Kannada"), # short
    ("agide", "Kannada"),
    
    # Kanglish
    ("Hello banni yellide, hegide tumba", "Kanglish"),
    ("office alli kelsa jaasti ide bro", "Kanglish"),
    ("cancel madidya?", "Kanglish"),
    ("please adjust madkoli", "Kanglish"),
    
    # Tamil
    ("eppadi irukkinga nalla irukkingala", "Tamil"),
    ("enakku onnum puriyala", "Tamil"),
    ("naan chennai ku poren", "Tamil"),
    ("romba nandri", "Tamil"),
    ("illai", "Tamil"),
    
    # Tamlish
    ("super a irukku machan", "Tamlish"),
    ("please konjam help pannunga", "Tamlish"),
    
    # Telugu
    ("ela unnaru bagunnara", "Telugu"),
    ("naku artham kaledu", "Telugu"),
    ("akkada em jarugutondi", "Telugu"),
    ("chala bagundi", "Telugu"),
    ("ledu", "Telugu"),
    
    # Tenglish
    ("please cheppandi", "Tenglish"),
    ("super ga undi bro", "Tenglish"),
    
    # Malayalam
    ("sugamano nattil enthendokke vishesham", "Malayalam"),
    ("enikku ariyilla", "Malayalam"),
    ("njaan varunnu", "Malayalam"),
    
    # Marathi
    ("tumhi kasa aahat, mala sangaa", "Marathi"),
    ("aaj kay zhala", "Marathi"),
    ("mala pan yeto", "Marathi"),
    ("hoil", "Marathi"),
    
    # Bengali
    ("ki koro tumi, bhalo achhe", "Bengali"),
    ("ami tomake bhalobashi", "Bengali"),
    ("ekhane asun", "Bengali"),
    
    # Gujarati
    ("kem cho majama", "Gujarati"),
    ("mane khabar nathi", "Gujarati"),
    ("shu karvu chhe", "Gujarati"),
    
    # Punjabi
    ("kiddan tussi theek ho", "Punjabi"),
    ("kithey ja rahe ho", "Punjabi"),
    ("saanu vi dasdo", "Punjabi"),
    
    # Urdu
    ("shukriya janab", "Urdu"),
    ("meherbani karke yahan aaye", "Urdu"),
]

print("LANGUAGE DETECTION RESULTS")
print("-" * 60)
passed = 0
for text, expected in tests:
    detected, conf = detect_language(text)
    ok = "PASS" if detected == expected else "FAIL"
    if detected == expected:
        passed += 1
    print(f"[{ok}] {detected:<15s} (expected: {expected:<15s}) | {text[:38]}")

print()
print(f"Score: {passed}/{len(tests)} correct")
print(f"Supported languages ({len(SUPPORTED_LANGUAGES)}): {', '.join(SUPPORTED_LANGUAGES)}")
print(f"Smart fallbacks configured: {len(SMART_FALLBACKS)} languages")
