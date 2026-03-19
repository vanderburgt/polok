"""FastAPI application entry point."""
import hashlib
import hmac
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.routers import parties, programs

COOKIE_NAME = "polok_auth"


def _make_token():
    return hmac.new(settings.SECRET_KEY.encode(), settings.SITE_PASSWORD.encode(), hashlib.sha256).hexdigest()[:32]


class AuthMiddleware(BaseHTTPMiddleware):
    OPEN_PATHS = {"/login", "/static", "/api/", "/_data/", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not settings.SITE_PASSWORD:
            return await call_next(request)
        if any(path.startswith(p) for p in self.OPEN_PATHS):
            return await call_next(request)
        token = request.cookies.get(COOKIE_NAME)
        if token == _make_token():
            return await call_next(request)
        return RedirectResponse(url="/login?next=" + path, status_code=302)


app = FastAPI(
    title="Polok",
    description="Verkiezingsprogramma's van Nederlandse gemeenteraadsverkiezingen 2026",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(AuthMiddleware)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(parties.router)
app.include_router(programs.router)


@app.get("/", include_in_schema=False)
async def index():
    return RedirectResponse(url="/programmas")


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request, error: str = "", next: str = "/programmas"):
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "next": next})


@app.post("/login", include_in_schema=False)
async def login_submit(password: str = Form(...), next: str = Form("/programmas")):
    if password == settings.SITE_PASSWORD:
        response = RedirectResponse(url=next, status_code=302)
        response.set_cookie(COOKIE_NAME, _make_token(), httponly=True, max_age=60 * 60 * 24 * 30, samesite="lax")
        return response
    return RedirectResponse(url="/login?error=1&next=" + next, status_code=302)
