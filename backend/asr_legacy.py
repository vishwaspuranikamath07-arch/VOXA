import whisper

# FAST model
model = whisper.load_model("tiny")

def speech_to_text(file):
    result = model.transcribe(file)
    return result["text"], result["language"]