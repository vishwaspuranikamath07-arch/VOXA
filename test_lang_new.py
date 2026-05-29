from backend.utils import detect_language

def test_language():
    text = "Henge iniya."
    lang, conf = detect_language(text)
    print(f"Text: {text} -> Lang: {lang}, Conf: {conf}")

    text2 = "Aap kaise ho."
    lang2, conf2 = detect_language(text2)
    print(f"Text: {text2} -> Lang: {lang2}, Conf: {conf2}")

    text3 = "Hegidira."
    lang3, conf3 = detect_language(text3)
    print(f"Text: {text3} -> Lang: {lang3}, Conf: {conf3}")

    text4 = "Ninna hesarenu?"
    lang4, conf4 = detect_language(text4)
    print(f"Text: {text4} -> Lang: {lang4}, Conf: {conf4}")

if __name__ == "__main__":
    test_language()
