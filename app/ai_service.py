import json
import logging

from fastapi import HTTPException
from groq import APIStatusError, Groq

from .config import AI_MODEL, GROQ_API_KEY


logger = logging.getLogger("tenderai.ai")
client = Groq(api_key=GROQ_API_KEY)


def ask_groq(questions: list[str], context: str) -> dict:
    questions_text = "\n".join(
        f"{index}. {question}"
        for index, question in enumerate(questions, start=1)
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

    logger.info(
        "Wysyłanie zapytania do modelu %s dla %d pytań",
        AI_MODEL,
        len(questions),
    )
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś dokładnym analizatorem dokumentów przetargowych. "
                        "Nie wolno Ci wymyślać danych."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
    except APIStatusError as error:
        if error.status_code == 413:
            raise HTTPException(
                status_code=413,
                detail="Dokument lub liczba pytań jest za duża dla wybranego modelu.",
            ) from error
        raise HTTPException(
            status_code=502,
            detail="Usługa AI chwilowo nie mogła przetworzyć analizy.",
        ) from error

    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as error:
        logger.exception("Model zwrócił niepoprawny JSON")
        raise HTTPException(
            status_code=500,
            detail="Model zwrócił niepoprawny JSON.",
        ) from error
