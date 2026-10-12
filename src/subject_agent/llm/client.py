"""Client LLM OpenAI-compatible (DeepSeek / Google / tout endpoint compatible).

Contraintes : timeouts, retries bornés, comptage des appels, aucune clé en logs (SPEC §22, §30).
Le transport est injectable pour permettre des tests à LLM simulé (zéro coût).
"""

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
            log.warning("Aucune clé LLM trouvée pour %s (%s)",
                        creds.get("provider"), creds.get("api_key_env"))

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
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PipelineError(ErrorState.TOOL_ERROR, "réponse LLM malformée") from exc
