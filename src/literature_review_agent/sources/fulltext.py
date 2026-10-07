"""Acquisition et lecture du texte intégral (SPEC §3.13-14, exigence : documents téléchargeables).

Chaîne déterministe, sans LLM :
    URL candidates (fournisseurs / Unpaywall) → téléchargement borné et sûr → stockage dans
    l'espace de session → extraction du texte (pdfminer.six) → découpage en sections → passages
    transmis au modèle.

Un document scanné (aucune couche texte) est signalé comme tel : le modèle ne pourra pas prétendre
l'avoir lu.
"""

import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..core.security_rules import quote_is_anchored
from .corpus import slugify

log = get_logger("sources.fulltext")

EXTRACTION_TOOL = "pdfminer.six"

# Repères de sections (français et anglais), utilisés par heuristique déterministe.
# Le préfixe tolère une numérotation (« 3. Résultats », « 4) Discussion »).
_NUM = r"(?:^|\n)\s*(?:\d{1,2}\s*[.)]\s*)?"
SECTION_PATTERNS = [
    ("abstract", _NUM + r"(?:abstract|r[ée]sum[ée]|synth[èe]se)\b"),
    ("introduction", _NUM + r"(?:introduction|contexte|probl[ée]matique et objectifs)\b"),
    ("method", _NUM + r"(?:method(?:ology|s)?|mat[ée]riel et m[ée]thodes?|m[ée]thodologie|"
               r"m[ée]thode|d[ée]marche m[ée]thodologique|data and methods?|"
               r"mat[ée]riels et m[ée]thodes)\b"),
    ("results", _NUM + r"(?:results?|findings?|r[ée]sultats?|principaux r[ée]sultats)\b"),
    ("discussion", _NUM + r"(?:discussion|analyse et discussion|interpretation)\b"),
    ("conclusion", _NUM + r"(?:conclusions?|conclusion and (?:future|perspectives?))\b"),
    ("limits", _NUM + r"(?:limits?|limitations?|limites?)\b"),
]

_SECTION_RE = [(name, re.compile(pattern, re.IGNORECASE | re.MULTILINE))
               for name, pattern in SECTION_PATTERNS]


@dataclass
class Page:
    number: int
    text: str


def extract_pages(data: bytes, max_pages: int = 40) -> tuple[list[Page], int]:
    """Extrait le texte page par page. Retourne (pages, nombre total de pages)."""
    from pdfminer.high_level import extract_text
    from pdfminer.pdfpage import PDFPage

    total = 0
    try:
        total = sum(1 for _ in PDFPage.get_pages(io.BytesIO(data)))
        safe_total = min(total, max_pages)
        raw = extract_text(io.BytesIO(data), maxpages=max_pages, page_numbers=None)
    except Exception as exc:  # noqa: BLE001 — un PDF corrompu ne doit pas casser la campagne
        raise PipelineError(ErrorState.TOOL_ERROR, f"extraction PDF impossible : {type(exc).__name__}") from exc

    # pdfminer sépare les pages par \f (form feed)
    chunks = raw.split("\f")
    pages = [Page(number=i + 1, text=chunk) for i, chunk in enumerate(chunks) if chunk is not None]
    if not pages:
        pages = [Page(number=1, text="")]
    return pages, max(total, 1)


def has_text_layer(pages: list[Page]) -> bool:
    """Heuristique : au moins 200 caractères exploitables par page en moyenne."""
    if not pages:
        return False
    chars = sum(len(re.sub(r"\s+", " ", p.text)) for p in pages)
    return (chars / len(pages)) >= 200


def split_sections(pages: list[Page]) -> list[tuple[str, int, str]]:
    """Découpe le document en (section, page, texte) par heuristique de titres.

    Aucun texte n'est inventé : les sections contiennent uniquement ce qui a été extrait.
    Un texte sans titres reconnus est renvoyé comme section « body ».
    """
    body = "\n".join(page.text for page in pages)
    if not body.strip():
        return []

    # Position approximative de chaque titre reconnu
    markers: list[tuple[int, str]] = []
    for name, regex in _SECTION_RE:
        for match in regex.finditer(body):
            markers.append((match.start(), name))
    markers.sort()

    if not markers:
        return [("body", 1, body)]

    # Page correspondante à une position de caractère
    offsets: list[int] = []
    running = 0
    for page in pages:
        offsets.append(running)
        running += len(page.text) + 1  # +1 pour le \n du regroupement

    def page_of(position: int) -> int:
        page_number = 1
        for index, offset in enumerate(offsets):
            if position >= offset:
                page_number = index + 1
        return page_number

    sections: list[tuple[str, int, str]] = []
    for index, (start, name) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(body)
        chunk = body[start:end].strip()
        if chunk:
            sections.append((name, page_of(start), chunk))
    return sections


def dedupe_sections(sections: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    """Une entrée par section : on garde l'occurrence la PLUS LONGUE (les titres reviennent
    dans les en-têtes de page, ce qui produit des sections parasites très courtes)."""
    best: dict[str, tuple[str, int, str]] = {}
    for name, page, text in sections:
        current = best.get(name)
        if current is None or len(text) > len(current[2]):
            best[name] = (name, page, text)
    ordered = sorted(best.values(), key=lambda item: item[1])
    return ordered


# Ordre d'intérêt décroissant pour l'extraction : méthode, résultats, limites, discussion…
SECTION_PRIORITY = ["method", "results", "limits", "discussion", "conclusion", "abstract",
                    "introduction", "body"]


def build_excerpts(sections: list[tuple[str, int, str]], window: int = 8000,
                   max_excerpts: int = 6) -> list[dict]:
    """Sélectionne les passages réellement transmis au modèle (bornés et ordonnés)."""
    ordered = sorted(
        sections,
        key=lambda item: (SECTION_PRIORITY.index(item[0]) if item[0] in SECTION_PRIORITY
                          else len(SECTION_PRIORITY)),
    )
    excerpts: list[dict] = []
    for name, page, text in ordered[:max_excerpts]:
        excerpts.append({"section": name, "page": page, "text": text[:window]})
    return excerpts


class FullTextStore:
    """Stocke les PDF téléchargés dans l'espace de la session et tient le manifeste."""

    def __init__(self, session_dir: Path, max_text_chars: int = 80000) -> None:
        self.dir = Path(session_dir) / "documents"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.dir / "manifest.json"
        self.max_text_chars = max_text_chars

    # --- stockage ---
    def store_pdf(self, doc_id: str, title: str, data: bytes) -> dict:
        name = f"{doc_id}_{slugify(title)}.pdf"
        path = self.dir / name
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        return {
            "file_name": name,
            "file_path": f"documents/{name}",
            "sha256": digest,
            "bytes": len(data),
        }

    def load_pdf(self, file_name: str) -> bytes:
        return (self.dir / Path(file_name).name).read_bytes()

    # --- manifeste ---
    def write_manifest(self, entries: list[dict]) -> Path:
        payload = {"documents_dir": str(self.dir), "count": len(entries), "entries": entries}
        self.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
        return self.manifest_path

    def read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {"count": 0, "entries": []}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))


def clean_extracted(text: str, max_chars: int) -> str:
    """Nettoie le texte extrait : césures de fin de ligne, espaces, caractères de contrôle."""
    if not text:
        return ""
    text = text.replace("\u00ad", "")
    text = re.sub(r"-\n(?=[a-zà-ÿ])", "", text)          # mots coupés en fin de ligne
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "".join(ch for ch in text if ch == "\n" or ch >= " ")
    return text[:max_chars]


def is_quote_anchored(quote: str, document_text: str) -> bool:
    """Vérifie qu'une citation existe réellement dans le texte lu (ancrage anti-hallucination)."""
    return quote_is_anchored(quote, document_text)


def normalize_for_search(text: str) -> str:
    return unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").lower()
