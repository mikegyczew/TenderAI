import json
import os
import re
from collections import Counter
from io import BytesIO
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import Groq
from pypdf import PdfReader


load_dotenv()

app = FastAPI(title="TenderAI")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ============================================================
# GROQ
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-oss-120b")

if not GROQ_API_KEY:
    raise RuntimeError("Brak GROQ_API_KEY w pliku .env")

client = Groq(api_key=GROQ_API_KEY)


# ============================================================
# USTAWIENIA
# ============================================================

CHUNK_WORDS = 500
TOP_CHUNKS_PER_QUESTION = 3

STOPWORDS = {
    "i", "a", "oraz", "lub", "czy", "jest", "są", "być",
    "do", "od", "na", "w", "we", "z", "ze", "za", "dla",
    "po", "przy", "o", "u", "nad", "pod", "przez",
    "jaki", "jaka", "jakie", "jakich", "jakim", "jaką",
    "co", "czego", "który", "która", "które", "których",
    "ten", "ta", "to", "te", "tych",
    "się", "nie", "tak", "ma", "mieć",
    "wynosi", "dotyczy", "należy", "może",
}


# ============================================================
# PDF -> TEXT
# ============================================================

def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))

        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        text = "\n".join(pages)

        return clean_text(text)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Nie udało się odczytać PDF: {e}",
        )


# ============================================================
# CZYSZCZENIE TEKSTU
# ============================================================

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line and len(line) > 2:
            lines.append(line)

    return "\n".join(lines).strip()


# ============================================================
# TEXT -> CHUNKS
# ============================================================

def split_into_chunks(
    text: str,
    words_per_chunk: int = CHUNK_WORDS,
) -> List[str]:

    words = text.split()
    chunks = []

    for i in range(0, len(words), words_per_chunk):
        chunk = " ".join(words[i:i + words_per_chunk])

        if chunk.strip():
            chunks.append(chunk)

    return chunks


# ============================================================
# TOKENIZACJA
# ============================================================

def tokenize(text: str) -> List[str]:

    words = re.findall(
        r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9]+",
        text.lower(),
    )

    return [
        word
        for word in words
        if len(word) >= 3 and word not in STOPWORDS
    ]


# ============================================================
# SCORE
# ============================================================

def score_chunk(
    question_words: List[str],
    chunk_words: List[str],
) -> float:

    if not question_words or not chunk_words:
        return 0

    counter = Counter(chunk_words)

    score = 0

    for word in question_words:

        if word in counter:
            score += 1

            score += min(counter[word] - 1, 2) * 0.25

    return score


# ============================================================
# SZUKANIE FRAGMENTÓW
# ============================================================

def find_relevant_chunks(
    question: str,
    chunks: List[str],
) -> List[str]:

    question_words = tokenize(question)

    scored = []

    for index, chunk in enumerate(chunks):

        chunk_words = tokenize(chunk)

        score = score_chunk(
            question_words,
            chunk_words,
        )

        scored.append(
            (score, index, chunk)
        )

    scored.sort(
        reverse=True,
        key=lambda item: item[0],
    )

    if not scored:
        return []

    if scored[0][0] == 0:
        return chunks[:TOP_CHUNKS_PER_QUESTION]

    return [
        chunk
        for score, index, chunk
        in scored[:TOP_CHUNKS_PER_QUESTION]
    ]


# ============================================================
# BUDOWANIE KONTEKSTU
# ============================================================

def build_context(
    questions: List[str],
    chunks: List[str],
) -> str:

    contexts = []

    already_used = set()

    for number, question in enumerate(
        questions,
        start=1,
    ):

        relevant = find_relevant_chunks(
            question,
            chunks,
        )

        question_context = []

        for chunk in relevant:

            chunk_id = hash(chunk)

            if chunk_id in already_used:
                continue

            already_used.add(chunk_id)
            question_context.append(chunk)

        contexts.append(
            f"""
===== PYTANIE {number} =====

{question}

RELEVANTNE FRAGMENTY:

{"\n\n---\n\n".join(question_context)}
"""
        )

    return "\n".join(contexts)


# ============================================================
# GROQ
# ============================================================

def ask_groq(
    questions: List[str],
    context: str,
):

    questions_text = "\n".join(
        f"{i}. {question}"
        for i, question in enumerate(
            questions,
            start=1,
        )
    )

    prompt = f"""
Jesteś ekspertem analizującym dokumenty przetargowe.

Odpowiadaj WYŁĄCZNIE na podstawie dostarczonych
fragmentów dokumentu.

Jeżeli informacji potrzebnej do odpowiedzi nie ma
w dostarczonych fragmentach, napisz:

"Brak informacji w dostarczonych fragmentach dokumentu."

Nie wymyślaj informacji.

Odpowiedzi powinny być konkretne i możliwie krótkie.

PYTANIA:

{questions_text}

FRAGMENTY DOKUMENTU:

{context}

Zwróć WYŁĄCZNIE poprawny JSON:

{{
  "answers": [
    {{
      "question": "oryginalne pytanie",
      "answer": "odpowiedź"
    }}
  ]
}}

Zachowaj dokładną kolejność pytań.
"""

    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Jesteś dokładnym analizatorem "
                    "dokumentów przetargowych. "
                    "Nie wolno Ci wymyślać danych."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        response_format={
            "type": "json_object",
        },
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Model zwrócił niepoprawny JSON.",
        )


# ============================================================
# STRONA
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
        },
    )


# ============================================================
# ANALIZA PDF
# ============================================================

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    questions: str = Form(...),
):

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Dozwolone są tylko pliki PDF.",
        )

    # Pytania wpisujemy po jednym wierszu.
    questions_list = [
        question.strip()
        for question in questions.splitlines()
        if question.strip()
    ]

    if not questions_list:
        raise HTTPException(
            status_code=400,
            detail="Podaj przynajmniej jedno pytanie.",
        )

    file_bytes = await file.read()

    # PDF -> TEXT
    document_text = extract_pdf_text(file_bytes)

    if not document_text:
        raise HTTPException(
            status_code=400,
            detail=(
                "Nie udało się wyciągnąć tekstu z PDF. "
                "Możliwe, że dokument jest skanem."
            ),
        )

    # TEXT -> CHUNKS
    chunks = split_into_chunks(
        document_text
    )

    # LOKALNE WYSZUKIWANIE
    context = build_context(
        questions_list,
        chunks,
    )

    # JEDEN REQUEST DO GROQ
    result = ask_groq(
        questions_list,
        context,
    )

    return {
        "filename": file.filename,
        "document_characters": len(document_text),
        "document_words": len(document_text.split()),
        "chunks": len(chunks),
        "questions": len(questions_list),
        "result": result,
    }

