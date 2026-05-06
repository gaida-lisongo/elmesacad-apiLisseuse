import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.uri_parser import parse_uri

from core.config import Settings, get_settings
from utils.cloudinary_media import configure_cloudinary

from routes.admin import router as admin_router
from routes.auth import router as auth_router
from routes.author import router as author_router
from routes.reader import router as reader_router
from routes.user_route import router as user_router

logger = logging.getLogger("app")


def _resolve_db_name(uri: str, override: str | None) -> str:
    if override:
        return override
    parsed = parse_uri(uri)
    name = parsed.get("database")
    if not name:
        raise RuntimeError(
            "Impossible de déduire le nom de la base depuis MONGO_URI ; "
            "définissez MONGO_DB_NAME.",
        )
    return name


def _cors_origins(settings: Settings) -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    if settings.cors_github_pages_origin:
        origins.append(settings.cors_github_pages_origin.rstrip("/"))
    for chunk in settings.cors_extra_origins.split(","):
        o = chunk.strip()
        if o:
            origins.append(o.rstrip("/"))
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_cloudinary(settings)

    client = AsyncIOMotorClient(settings.mongo_uri)
    db_name = _resolve_db_name(settings.mongo_uri, settings.mongo_db_name)
    app.state.mongo_client = client
    app.state.db = client[db_name]

    yield

    client.close()


app = FastAPI(
    title="Liseuse ELMES API",
    version="1.0.0",
    lifespan=lifespan,
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(_settings),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(author_router)
app.include_router(admin_router)
app.include_router(user_router)
app.include_router(reader_router)


@app.get("/", include_in_schema=False)
async def root():
    """Navigateur : redirection vers la doc interactive OpenAPI."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    logger.exception("Erreur non gérée")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur."},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
