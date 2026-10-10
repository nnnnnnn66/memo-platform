"""Point d'entrée FastAPI de l'Agent Résultats et analyse V1 (paquet autonome)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.routes import router
from .core.config import get_settings
from .llm.client import LLMClient
from .storage import audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    audit.init(settings.audit_db)
    app.state.settings = settings
    app.state.llm = LLMClient(settings.llm_credentials(), settings.limits)
    app.state.verifier_llm = app.state.llm  # V1 : même provider, appels séparés
    yield


app = FastAPI(title="Agent Résultats et analyse V1", version="1.0", lifespan=lifespan)
app.include_router(router)
