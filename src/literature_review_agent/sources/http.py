"""Clients réseau bornés de l'Agent Revue de littérature.

Deux clients distincts, deux politiques :

- `ApiFetcher` : interroge les API déclarées. Hôtes en **liste blanche** (fournisseurs +
  enrichissement), HTTPS seulement, quotas globaux, réponses plafonnées.
- `FileDownloader` : télécharge un PDF candidat depuis une URL **renvoyée par une API déclarée**
  (dépôt, éditeur open access, prépublication). Les hôtes sont donc variés par nature : protections
  anti-SSRF spécifiques — HTTPS, refus des adresses privées/loopback/lien-local/métadonnées cloud,
  taille plafonnée, signature `%PDF-` obligatoire.
"""

import ipaddress
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger

log = get_logger("sources.http")


class _CheckedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Revalide CHAQUE saut d'une redirection HTTP (anti-SSRF).

    `urllib.request.urlopen` suit les redirections par défaut : le contrôle d'hôte (liste blanche
    des fournisseurs, refus des adresses privées) n'était appliqué qu'à l'URL INITIALE. Un
    fournisseur — ou un lien qu'il renvoie — pouvait donc rediriger la requête vers un service
    interne (127.0.0.1, 169.254.169.254, réseau privé) sans repasser par la liste blanche.
    Démontré en local : urlopen suit une redirection vers un autre hôte sans contrôle.
    """

    def __init__(self, check) -> None:
        super().__init__()
        self._check = check

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._check(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_checked(check, request, timeout):
    """Ouvre la requête en revalidant chaque redirection (même contrôle que l'URL initiale)."""
    opener = urllib.request.build_opener(_CheckedRedirectHandler(check))
    return opener.open(request, timeout=timeout)


class ApiFetcher:
    def __init__(self, sources_cfg: dict, limits, allowed_hosts: set[str]) -> None:
        self.cfg = sources_cfg or {}
        self.limits = limits
        self.allowed_hosts = set(allowed_hosts)
        self.requests = 0
        self.bytes_downloaded = 0
        self.errors: list[str] = []

    # --- garde-fous ---
    def _check_url(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise PipelineError(ErrorState.SECURITY_VIOLATION, "seul HTTPS est autorisé")
        if (parsed.hostname or "") not in self.allowed_hosts:
            raise PipelineError(
                ErrorState.SECURITY_VIOLATION,
                f"hôte non autorisé par la liste des fournisseurs : {parsed.hostname}",
            )

    def _budget(self, cost: int = 1) -> None:
        if self.requests + cost > self.limits.max_external_requests:
            raise PipelineError(
                ErrorState.RESOURCE_LIMIT,
                f"MAX_EXTERNAL_REQUESTS atteint ({self.limits.max_external_requests})",
            )

    def fetch(self, url: str, params: dict | None = None, cost: int = 1,
              headers: dict | None = None) -> str:
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        self._check_url(url)
        self._budget(cost)

        # Politesse envers les API publiques (limitation de débit) : petit délai entre appels.
        delay = float(self.cfg.get("polite_delay_seconds", 0.0) or 0.0)
        if delay and self.requests:
            time.sleep(delay)

        max_bytes = int(self.cfg.get("max_response_bytes", 3_000_000))
        retries = int(self.cfg.get("retry_on_transient", 2) or 0)
        attempts = 0
        while True:
            attempts += 1
            request = urllib.request.Request(url, headers={
                "User-Agent": self.cfg.get("user_agent", "memo-platform/0.1"),
                "Accept": "application/json, application/xml, text/xml, */*",
                # Les secrets (clé OpenAlex, OpenAIRE…) passent par des EN-TÊTES, jamais par
                # l'URL : une URL est journalisée et recopiée dans les erreurs, pas un en-tête.
                **(headers or {}),
            })
            try:
                with open_checked(self._check_url, request, self.limits.source_timeout) as resp:
                    raw = resp.read(max_bytes + 1)
                self.requests += cost
                break
            except urllib.error.HTTPError as exc:
                self.requests += cost
                # 429 (débit) et 5xx sont transitoires : on réessaie avec un temps d'attente borné,
                # en respectant Retry-After quand l'API l'indique.
                transient = exc.code == 429 or 500 <= exc.code < 600
                if transient and attempts <= retries:
                    wait = 0.0
                    header = (exc.headers.get("Retry-After") if exc.headers else None) or ""
                    if header.isdigit():
                        wait = min(float(header), float(self.cfg.get("max_retry_wait", 5.0)))
                    if not wait:
                        wait = min(1.5 * attempts, float(self.cfg.get("max_retry_wait", 5.0)))
                    log.info("HTTP %s sur %s : nouvelle tentative dans %.1fs (%s/%s)",
                             exc.code, url, wait, attempts, retries)
                    time.sleep(wait)
                    continue
                self.errors.append(f"{url}: HTTP {exc.code}")
                raise PipelineError(ErrorState.TOOL_ERROR, f"HTTP {exc.code} sur {url}") from exc
            except TimeoutError as exc:
                self.requests += cost
                if attempts <= retries:
                    continue
                self.errors.append(f"{url}: timeout")
                raise PipelineError(ErrorState.TIMEOUT, f"délai dépassé sur {url}") from exc
            except urllib.error.URLError as exc:
                self.requests += cost
                self.errors.append(f"{url}: {exc.reason}")
                raise PipelineError(ErrorState.TOOL_ERROR, f"réseau indisponible sur {url}") from exc

        if len(raw) > max_bytes:
            raise PipelineError(ErrorState.RESOURCE_LIMIT, f"réponse trop volumineuse : {url}")
        self.bytes_downloaded += len(raw)
        return raw.decode("utf-8", "replace")

    def fetch_json(self, url: str, params: dict | None = None, cost: int = 1,
                   headers: dict | None = None) -> dict:
        text = self.fetch(url, params, cost=cost, headers=headers)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise PipelineError(ErrorState.TOOL_ERROR, f"JSON invalide depuis {url}") from exc


def _is_public_ip(host: str) -> bool:
    """Vrai si tous les enregistrements DNS de l'hôte pointent vers des adresses publiques."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return True


class FileDownloader:
    """Télécharge un PDF candidat (accès ouvert légal) avec protections anti-SSRF."""

    def __init__(self, sources_cfg: dict, fulltext_cfg: dict, limits) -> None:
        self.cfg = sources_cfg or {}
        self.fulltext = fulltext_cfg or {}
        self.limits = limits
        self.downloads = 0
        self.bytes_downloaded = 0
        self.errors: list[str] = []

    def can_download(self) -> bool:
        return (self.fulltext.get("enabled", True)
                and self.downloads < self.limits.max_downloads)

    def _check_url(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise PipelineError(ErrorState.SECURITY_VIOLATION, "seul HTTPS est autorisé")
        host = parsed.hostname or ""
        if not host or host.endswith(".local") or host.endswith(".internal"):
            raise PipelineError(ErrorState.SECURITY_VIOLATION, f"hôte refusé : {host!r}")
        if self.fulltext.get("block_private_ips", True) and not _is_public_ip(host):
            raise PipelineError(
                ErrorState.SECURITY_VIOLATION,
                f"adresse non publique refusée (anti-SSRF) : {host}",
            )

    def download_pdf(self, url: str) -> bytes:
        self._check_url(url)
        if self.downloads >= self.limits.max_downloads:
            raise PipelineError(ErrorState.RESOURCE_LIMIT, "MAX_DOWNLOADS atteint")
        max_bytes = self.limits.max_download_mb * 1024 * 1024
        if (self.bytes_downloaded + max_bytes) > self.limits.max_session_download_mb * 1024 * 1024:
            raise PipelineError(ErrorState.RESOURCE_LIMIT, "quota disque de session atteint")

        request = urllib.request.Request(url, headers={
            "User-Agent": self.cfg.get("user_agent", "memo-platform/0.1"),
            "Accept": "application/pdf,*/*",
        })
        try:
            with open_checked(self._check_url, request, self.limits.download_timeout) as resp:
                data = resp.read(max_bytes + 1)
        except urllib.error.HTTPError as exc:
            self.errors.append(f"{url}: HTTP {exc.code}")
            raise PipelineError(ErrorState.TOOL_ERROR, f"HTTP {exc.code} (téléchargement)") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            self.errors.append(f"{url}: {exc}")
            raise PipelineError(ErrorState.TIMEOUT, "délai dépassé au téléchargement") from exc

        if len(data) > max_bytes:
            raise PipelineError(ErrorState.RESOURCE_LIMIT, "fichier trop volumineux")
        if self.fulltext.get("require_pdf_signature", True) and not data[:5] == b"%PDF-":
            raise PipelineError(ErrorState.TOOL_ERROR, "le fichier reçu n'est pas un PDF")
        self.downloads += 1
        self.bytes_downloaded += len(data)
        return data
