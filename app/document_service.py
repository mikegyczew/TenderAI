from io import BytesIO
import re

from fastapi import HTTPException
from pypdf import PdfReader


def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_bytes))
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )
        return clean_text(text)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Nie udało się odczytać PDF: {error}",
        ) from error


def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and len(line.strip()) > 2
    ]
    return "\n".join(lines).strip()
