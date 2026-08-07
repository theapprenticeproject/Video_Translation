import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ensure Windows console stdout prints UTF-8 (Hindi/Marathi characters) cleanly without charmap errors
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for older python versions
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.config import settings
from app.services import claude

test_texts = [
    "नमस्ते, आपका स्वागत है।",
    "आज हम इस ऐप के बारे में बात करेंगे।"
]

def run():
    key = settings.anthropic_api_key
    if not key:
        print("Error: ANTHROPIC_API_KEY is empty in settings! Make sure .env or .env.local contains it.")
        return

    print("Selected Model:", claude.DEFAULT_MODEL)
    print("Starting batch translation check...")
    try:
        res = claude.translate_texts(test_texts, "hi", "mr")
        print("\nBatch Translation Output SUCCESS:")
        for orig, trans in zip(test_texts, res):
            print(f"Original: {orig} -> Translated: {trans}")
    except Exception as e:
        print("\nBatch Translation Error occurred:", e)

if __name__ == "__main__":
    run()
