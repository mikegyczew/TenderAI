import os
import json

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("Brak GEMINI_API_KEY w pliku .env")

client = genai.Client(api_key=api_key)

app = FastAPI(title="Tender AI API")

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)


@app.get("/", response_class=HTMLResponse)
def home():
    with open("app/templates/index.html", encoding="utf-8") as file:
        return file.read()


@app.post("/api/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    questions: str = Form(...)
):
    # Odczyt pliku
    contents = await file.read()

    temp_path = "/tmp/document.pdf"

    with open(temp_path, "wb") as temp_file:
        temp_file.write(contents)

    # Wyciągnięcie tekstu z PDF
    reader = PdfReader(temp_path)

    document_text = ""

    for page in reader.pages:
        text = page.extract_text()

        if text:
            document_text += text + "\n"

    # Odczyt pytań
    try:
        question_list = json.loads(questions)

        if not isinstance(question_list, list):
            raise ValueError("questions musi być listą")

    except (json.JSONDecodeError, ValueError):
        question_list = [
            line.strip()
            for line in questions.splitlines()
            if line.strip()
        ]

    # Prompt dla Gemini
    prompt = f"""
Jesteś ekspertem analizującym dokumenty przetargowe.

Przeanalizuj poniższy dokument.

DOKUMENT:
----------------
{document_text}
----------------

PYTANIA:
{json.dumps(question_list, ensure_ascii=False, indent=2)}

Zasady:
- odpowiedz na każde pytanie,
- zachowaj kolejność pytań,
- odpowiadaj wyłącznie na podstawie dokumentu,
- jeśli informacji nie ma w dokumencie, napisz:
  "Brak informacji w dokumencie",
- nie wymyślaj informacji,
- odpowiedzi mają być konkretne i zwięzłe.

Zwróć odpowiedzi jako JSON:

{{
    "answers": [
        "odpowiedź na pierwsze pytanie",
        "odpowiedź na drugie pytanie",
        "odpowiedź na trzecie pytanie"
    ]
}}
"""

    # Zapytanie do Gemini
    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    ai_response = interaction.output_text

    # Odczyt odpowiedzi Gemini
    try:
        result = json.loads(ai_response)

    except json.JSONDecodeError:
        result = {
            "answers": [ai_response]
        }

    return {
        "filename": file.filename,
        "answers": result.get("answers", [])
    }
