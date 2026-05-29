import asyncio
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
from pathlib import Path

# Add project root
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from backend.utils import detect_language
from backend.llm.router import generate_reply
from backend.llm.key_manager import key_manager

async def main():
    await key_manager.initialize()
    test_phrases = [
        ("en", "Hello, I want to order some food."),
        ("ta", "enna saapidu irukku"), # Tamil
        ("te", "nenu em tinali"), # Telugu
        ("kn", "nange oota beku"), # Kannada
        ("ml", "enikku enthenkilum kazhikkanam"), # Malayalam
        ("hi", "mujhe kuch khana hai"), # Hindi
        ("bn", "ami kichu khete chai"), # Bengali
        ("mr", "mala kahi tari khaychay"), # Marathi
        ("gu", "mare kaik khavu che"), # Gujarati
        ("pa", "mainu kuch khana hai"), # Punjabi
    ]

    history = []
    lang_history = []
    
    for lang_code, text in test_phrases:
        print(f"\n--- Turn: {lang_code} ---")
        print(f"User input: {text}")
        
        detected_lang, conf = detect_language(text, lang_history)
        print(f"Detected: {detected_lang} (conf: {conf:.2f})")
        
        # Build LLM instruction logic from utils.py manually for the test
        is_cs = False
        _SARVAM = {"hi","kn","ta","te","ml","mr","bn","gu","pa"}
        if detected_lang != "English" and not text.isascii(): # very rough mock for script
           pass # native
           
        from backend.utils import LANGUAGE_CODE_MAP, _INDIAN_CODES
        
        is_cs = any(c.isascii() and c.isalpha() for c in text) and NAME_TO_CODE.get(detected_lang, "en") in _INDIAN_CODES
        code = NAME_TO_CODE.get(detected_lang, "en")
        
        lang_name = detected_lang
        
        if is_cs:
            llm_instruction = (f"User is speaking {lang_name} (mix of "
                f"{LANGUAGE_CODE_MAP.get(code, code)} and English). Reply naturally mixing both.")
        elif code in _SARVAM:
            llm_instruction = (f"User is speaking romanized "
                f"{LANGUAGE_CODE_MAP.get(code, code)}. Reply in natural romanized {LANGUAGE_CODE_MAP.get(code, code)}.")
        else:
            llm_instruction = (f"User is speaking {LANGUAGE_CODE_MAP.get(code, 'English')}. "
                f"Reply naturally in {LANGUAGE_CODE_MAP.get(code, 'English')}.")

        result = await generate_reply(text, detected_lang, history, llm_instruction)
        reply = result["text"]
        print(f"Voxa: {reply}")
        
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": reply})
        if len(history) > 8:
            history = history[-8:]
            
        lang_history.append(detected_lang)
        if len(lang_history) > 2:
            lang_history = lang_history[-2:]

from backend.utils import NAME_TO_CODE
asyncio.run(main())
