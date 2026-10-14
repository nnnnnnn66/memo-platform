"""Client LLM de l'Agent Hypothèses de recherche (OpenAI-compatible)."""

import httpx

from ..core.errors import ErrorState, PipelineError
from ..core.logging import get_logger
from ..core.security_rules import redact

log = get_logger("llm")


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
        if self.calls >= self.limits.max_llm_calls:
            raise PipelineError(ErrorState.RESOURCE_LIMIT,
                                f"MAX_LLM_CALLS atteint ({self.limits.max_llm_calls})")
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
        try:
            with httpx.Client(timeout=self.limits.timeout, transport=self._transport) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise PipelineError(ErrorState.TIMEOUT, redact(str(exc))) from exc
        except httpx.HTTPError as exc:
            raise PipelineError(ErrorState.TOOL_ERROR, redact(str(exc))) from exc

        self.calls += 1
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PipelineError(ErrorState.TOOL_ERROR, "réponse LLM malformée") from exc

        if not content or not str(content).strip():
            usage = data.get("usage") or {}
            raise PipelineError(
                ErrorState.TOOL_ERROR,
                "réponse LLM vide (finish_reason="
                f"{choice.get('finish_reason')}, completion_tokens="
                f"{usage.get('completion_tokens')}/{self.limits.max_output_tokens}, "
                "reasoning_tokens="
                f"{(usage.get('completion_tokens_details') or {}).get('reasoning_tokens')}). "
                "Réponds directement et respecte le schéma JSON.",
            )
        return content
