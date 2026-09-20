import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .logging_config import configure_logging
from .routes import router


logger = configure_logging()
app = FastAPI(title="TenderAI")
base_dir = Path(__file__).parent
templates = Jinja2Templates(directory=base_dir / "templates")
app.mount("/static", StaticFiles(directory=base_dir / "static"), name="static")
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logger.info("Wyświetlono stronę główną")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )
