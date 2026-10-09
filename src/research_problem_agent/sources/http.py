"""Client HTTP borné et restreint aux hôtes déclarés (SPEC §8, §10.12, §10.13).

Aucune URL arbitraire : un hôte non déclaré dans providers.yaml est refusé. Bornes :
nombre de requêtes, délai, taille de réponse. Bibliothèque : urllib (stdlib), donc aucune
dépendance supplémentaire et aucun coût.
"""

import json
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


class Fetcher:
    def __init__(self, sources_cfg: dict, limits, allowed_hosts: set[str]) -> None:
        self.cfg = sources_cfg or {}
        self.limits = limits
        self.allowed_hosts = set(allowed_hosts)
        self.requests = 0
        self.bytes_downloaded = 0
        self.errors: list[str] = []

    # --- garde-fou ---
    def _check_url(self, url: str) -> None:
        host = urllib.parse.urlparse(url).hostname or ""
        if host not in self.allowed_hosts:
            raise PipelineError(
                ErrorState.SECURITY_VIOLATION,
                f"hôte non autorisé par la liste des fournisseurs : {host}",
            )
        if not url.lower().startswith("https://"):
            raise PipelineError(ErrorState.SECURITY_VIOLATION, "seul HTTPS est autorisé")

    def _budget(self) -> None:
        if self.requests >= self.limits.max_external_requests:
            raise PipelineError(
                ErrorState.RESOURCE_LIMIT,
                f"MAX_EXTERNAL_REQUESTS atteint ({self.limits.max_external_requests})",
            )

    def fetch(self, url: str, params: dict | None = None) -> str:
        """Récupère une ressource texte. Lève PipelineError(TIMEOUT/TOOL_ERROR/RESOURCE_LIMIT)."""
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        self._check_url(url)
        self._budget()

        request = urllib.request.Request(
            url, headers={
                "User-Agent": self.cfg.get("user_agent", "memo-platform/0.1"),
                "Accept": "application/json, application/xml, text/xml, */*",
            },
        )
        max_bytes = int(self.cfg.get("max_response_bytes", 2_000_000))
        try:
            with open_checked(self._check_url, request, self.limits.source_timeout) as resp:
                raw = resp.read(max_bytes + 1)
        except urllib.error.HTTPError as exc:
            self.requests += 1
            self.errors.append(f"{url}: HTTP {exc.code}")
            raise PipelineError(ErrorState.TOOL_ERROR, f"HTTP {exc.code} sur {url}") from exc
        except TimeoutError as exc:
            self.requests += 1
            self.errors.append(f"{url}: timeout")
            raise PipelineError(ErrorState.TIMEOUT, f"délai dépassé sur {url}") from exc
        except urllib.error.URLError as exc:
            self.requests += 1
            self.errors.append(f"{url}: {exc.reason}")
            raise PipelineError(ErrorState.TOOL_ERROR, f"réseau indisponible sur {url}") from exc

        self.requests += 1
        if len(raw) > max_bytes:
            raise PipelineError(ErrorState.RESOURCE_LIMIT, f"réponse trop volumineuse : {url}")
        self.bytes_downloaded += len(raw)
        return raw.decode("utf-8", "replace")

    def fetch_json(self, url: str, params: dict | None = None) -> dict:
        text = self.fetch(url, params)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise PipelineError(ErrorState.TOOL_ERROR, f"JSON invalide depuis {url}") from exc
