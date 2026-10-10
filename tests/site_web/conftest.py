"""Rend la fixture `site` visible pour pytest, et met `src/` sur le chemin d'import."""

import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
if str(RACINE / "src") not in sys.path:
    sys.path.insert(0, str(RACINE / "src"))
if str(pathlib.Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from site_helpers import site, OrchestrateurSimule  # noqa: E402,F401
