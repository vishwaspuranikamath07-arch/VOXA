"""
tests/benchmark_language_detection.py

Script to benchmark the accuracy and latency of the LanguageDetector.
"""

import time
import sys
from backend.utils import LanguageDetector

TEST_CASES = [
    # Kannada
    ("gothilla bro adu hege madodu", "kn"),
    ("nanu hogbeku illa barolla", "kn"),
    ("idu yenu aagtha ide", "kn"),
    ("bro idu correct illa", "kn"),
    ("meeting cancel madidya", "kn"),
    ("ನಾನು ಹೋಗಬೇಕು", "kn"),
    # Hindi
    ("yaar kya kar raha hai", "hi"),
    ("kya ho raha hai", "hi"),
    ("mujhe nahi pata", "hi"),
    ("मैं नहीं जानता", "hi"),
    # Tamil
    ("machan enna panrom", "ta"),
    ("romba kashtam bro", "ta"),
    # Telugu
    ("enti emiti chestunnaru", "te"),
    ("nenu vastanu", "te"),
    # Malayalam
    ("enthanu evide", "ml"),
    ("njaan varunnu", "ml"),
    # Spanish
    ("hola como estas", "es"),
    ("no entiendo que dices", "es"),
    ("quiero comer", "es"),
    # French
    ("bonjour merci beaucoup", "fr"),
    ("je ne sais pas", "fr"),
    # German
    ("ich verstehe nicht", "de"),
    ("danke schon", "de"),
    # Portuguese
    ("ola tudo bem", "pt"),
    ("muito obrigado", "pt"),
    # English
    ("hello how are you", "en"),
    ("this is a test", "en"),
]

def run_benchmark():
    correct = 0
    total = len(TEST_CASES)
    total_time = 0.0

    print("Running LanguageDetector Benchmark...\n")

    for text, expected_lang in TEST_CASES:
        t0 = time.time()
        res = LanguageDetector.detect(text)
        latency = (time.time() - t0) * 1000
        total_time += latency
        
        detected = res["primary_language"]
        is_match = detected == expected_lang
        
        if is_match:
            correct += 1
            status = "PASS"
        else:
            status = f"FAIL (Expected {expected_lang}, Got {detected})"
            
        print(f"{status:<30} | {text:<30} | Latency: {latency:.2f}ms")

    accuracy = (correct / total) * 100
    avg_latency = total_time / total

    print("\n--- Benchmark Results ---")
    print(f"Total Sentences : {total}")
    print(f"Accuracy        : {accuracy:.2f}% ({correct}/{total})")
    print(f"Average Latency : {avg_latency:.2f}ms")

if __name__ == "__main__":
    run_benchmark()
