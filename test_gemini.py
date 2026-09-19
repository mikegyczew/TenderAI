import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("Brak GEMINI_API_KEY w pliku .env")

client = genai.Client(api_key=api_key)

interaction = client.interactions.create(
    model="gemini-3.6-flash",
    input="Napisz jedno zdanie wyjaśniające czym jest przetarg."
)

print(interaction.output_text)
