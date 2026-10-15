"""Client LLM OpenAI-compatible (DeepSeek / Google / tout endpoint compatible).

Contraintes : timeouts, retries bornés, comptage des appels, aucune clé en logs (SPEC §22, §30).
Le transport est injectable pour permettre des tests à LLM simulé (zéro coût).
"""

import time

import httpx

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..core.security_rules import redact

log = get_logger("llm")


# Reprises sur erreur PASSAGÈRE du fournisseur de modèle (503/429/502/504/délai).
_TENTATIVES = 3
_ATTENTES = (3, 10)
_TRANSITOIRES = {429, 500, 502, 503, 504}


class LLMClient:
    def __init__(self, creds: dict, limits, transport: httpx.BaseTransport | None = None) -> None:
        self.creds = creds
        self.limits = limits
        self._transport = transport
        self.calls = 0
        if not creds.get("api_key"):
            # Message SANS AUCUNE valeur issue des identifiants : l'analyse de sécurité statique
            # (CodeQL, règle py/clear-text-logging-sensitive-data) signalait ce message parce que
            # le nom de la variable d'environnement attendue était lu dans le dictionnaire des
            # identifiants — un faux positif, mais qui masquait les vraies fuites éventuelles.
            # On indique où poser la clé, sans jamais toucher au contenu des identifiants.
            log.warning("Aucune clé LLM trouvée pour le fournisseur configuré : la clé se pose "
                        "dans ~/.hermes/.env (voir le fichier de configuration de l'agent).")

    def nouvelle_campagne(self) -> None:
        """Remet le compteur à zéro : la limite protege UNE execution, pas la vie du processus.

        Defaut reel (premier parcours de bout en bout) : le client est cree UNE fois au demarrage du
        serveur et son compteur n'etait jamais remis a zero. Apres `max_llm_calls` appels cumules
        depuis le demarrage — TOUS dossiers confondus — l'agent refusait toute nouvelle etape
        jusqu'a son redemarrage : un agent en production s'arretait en silence au bout de quelques
        dossiers, et sur une seule session un peu longue.
        """
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.creds["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.creds.get("temperature", 0.2),
            "max_tokens": self.limits.max_output_tokens,
            "stream": False,
        }
        headers = {"Authorization": f"Bearer {self.creds['api_key']}"}
        url = self.creds["base_url"].rstrip("/") + "/chat/completions"
        # Une coupure PASSAGÈRE du fournisseur de modèle ne doit jamais tuer une campagne déjà
        # avancée : la revue de littérature avait lu 250 documents et 30 textes intégraux quand un
        # 503 a tout perdu. On retente donc, un nombre borné de fois, avec une attente croissante.
        # Une erreur DÉFINITIVE (400, 401, 404…) n'est pas retentée : elle ne guérira pas.
        dernier: Exception | None = None
        for tentative in range(1, _TENTATIVES + 1):
            try:
                with httpx.Client(timeout=self.limits.timeout,
                                  transport=self._transport) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                break
            except httpx.TimeoutException as exc:
                dernier, passager = exc, True
            except httpx.HTTPStatusError as exc:
                dernier = exc
                passager = exc.response.status_code in _TRANSITOIRES
            except httpx.HTTPError as exc:
                dernier, passager = exc, True

            if not passager or tentative == _TENTATIVES:
                if isinstance(dernier, httpx.TimeoutException):
                    raise PipelineError(ErrorState.TIMEOUT, redact(str(dernier))) from dernier
                raise PipelineError(ErrorState.TOOL_ERROR, redact(str(dernier))) from dernier
            attente = _ATTENTES[tentative - 1]
            log.warning("fournisseur de modèle indisponible (%s), nouvelle tentative dans %ss "
                        "[%s/%s]", type(dernier).__name__, attente, tentative, _TENTATIVES)
            time.sleep(attente)

        self.calls += 1
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PipelineError(ErrorState.TOOL_ERROR, "réponse LLM malformée") from exc
