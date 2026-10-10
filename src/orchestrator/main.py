"""Point d'entrée de l'orchestrateur (serveur FastAPI dédié).

Il ne fait qu'une chose au démarrage : charger la carte des étapes et préparer l'état des dossiers.
Aucune logique méthodologique, aucun appel de modèle.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.routes import router
from .core.config import charger
from .storage import state


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = charger()
    state.initialiser(settings.state_db)
    app.state.settings = settings
    yield


app = FastAPI(
    title="Orchestrateur — accompagnement méthodologique du mémoire",
    version="1.0",
    description=(
        "Fait circuler la sortie RÉELLE d'une étape vers la suivante, applique le portillon humain "
        "et protège le portefeuille par un quota. N'appelle aucun modèle de langage."),
    lifespan=lifespan,
)
app.include_router(router)
