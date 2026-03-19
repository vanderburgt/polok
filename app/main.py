"""FastAPI application entry point."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import parties, programs

app = FastAPI(
    title="Polok",
    description="Verkiezingsprogramma's van Nederlandse gemeenteraadsverkiezingen 2026",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(parties.router)
app.include_router(programs.router)


@app.get("/", include_in_schema=False)
async def index():
    return RedirectResponse(url="/programmas")
