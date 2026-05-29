from transformers import pipeline

# Fast lightweight model
generator = pipeline(
    "text-generation",
    model="distilgpt2",
    device=-1
)


def call_local_model(prompt):
    try:
        res = generator(
            prompt,
            max_new_tokens=25,
            do_sample=True,
            temperature=0.7
        )

        text = res[0]["generated_text"]
        cleaned = text.replace(prompt, "").strip().split("\n")[0]

        # Fix weak or malformed outputs
        if len(cleaned) < 3 or cleaned == ".":
            cleaned = "Sure! How can I help you?"

        if "not going to happen" in cleaned.lower():
            cleaned = "I'm here to help! What would you like to ask?"

        return cleaned, "Local Model (Fast)"

    except Exception as e:
        print("Local Model Error:", e)
        return None, None