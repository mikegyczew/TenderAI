import logging
import time

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .ai_service import ask_groq
from .auth import login, require_authentication
from .document_service import extract_pdf_text
from .search_service import build_context, split_into_chunks


router = APIRouter()
logger = logging.getLogger("tenderai.routes")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def authenticate(credentials: LoginRequest):
    return login(credentials.username, credentials.password)


@router.post("/logout")
async def logout():
    response = JSONResponse({"authenticated": False})
    response.delete_cookie("tenderai_session")
    return response


@router.get("/auth/status")
async def auth_status(request: Request):
    from .auth import is_valid_session

    return {"authenticated": is_valid_session(request.cookies.get("tenderai_session"))}


@router.post("/analyze")
async def analyze(
    request: Request,
    file: UploadFile | None = File(None),
    questions: str = Form(...),
    document_text: str = Form(""),
):
    require_authentication(request)
    started_at = time.perf_counter()

    questions_list = [
        question.strip()
        for question in questions.splitlines()
        if question.strip()
    ]
    if not questions_list:
        raise HTTPException(status_code=400, detail="Podaj przynajmniej jedno pytanie.")

    if file is not None and file.filename:
        filename = file.filename
        logger.info("Rozpoczęto analizę pliku %s", filename)
        if not filename.lower().endswith(".pdf"):
            logger.warning("Odrzucono plik z niedozwolonym rozszerzeniem: %s", filename)
            raise HTTPException(status_code=400, detail="Dozwolone są tylko pliki PDF.")
        file_bytes = await file.read()
        document_text = extract_pdf_text(file_bytes)
    else:
        filename = "wklejony-tekst"
        logger.info("Rozpoczęto analizę wklejonego tekstu")

    if not document_text:
        raise HTTPException(
            status_code=400,
            detail="Wybierz plik PDF albo wklej treść dokumentu.",
        )

    chunks = split_into_chunks(document_text)
    context = build_context(questions_list, chunks)
    result = ask_groq(questions_list, context)
    duration = time.perf_counter() - started_at
    logger.info(
        "Zakończono analizę pliku %s: pytań=%d, chunków=%d, czas=%.2fs",
        filename,
        len(questions_list),
        len(chunks),
        duration,
    )

    return {
        "filename": filename,
        "document_characters": len(document_text),
        "document_words": len(document_text.split()),
        "chunks": len(chunks),
        "questions": len(questions_list),
        "result": result,
    }
