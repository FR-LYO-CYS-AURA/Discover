"""
Client LLM DISCOVER.

Deux backends sélectionnables via Config.LLM_BACKEND :
  - "opencode" (défaut) : délègue au harness OpenCode (serveur HTTP local).
    L'authentification et le choix du modèle sont gérés par la config OpenCode
    (`opencode auth login`, `opencode.json`) — aucune LLM_API_KEY requise.
  - "openai" : appel direct au format OpenAI (rétro-compatibilité).

L'interface publique (chat / chat_json) est identique quel que soit le backend,
afin que les services (crisis_graph_extractor, expert_society...) restent
inchangés.
"""

import json
import re
import time
from typing import Optional, Dict, Any, List

import httpx
from openai import OpenAI

from ..config import Config, trust_env_for
from .logger import get_logger

logger = get_logger('discover.llm_client')

# Outils OpenCode désactivés pour de la génération pure (pas d'agent qui lit/écrit des fichiers)
_OPENCODE_TOOLS = [
    "invalid", "question", "bash", "read", "glob", "grep", "edit", "write",
    "task", "webfetch", "todowrite", "websearch", "skill", "apply_patch",
]


def _strip_think(content: str) -> str:
    """Retire les blocs <think>...</think> de certains modèles à raisonnement visible."""
    return re.sub(r'<think>[\s\S]*?</think>', '', content or '').strip()


def _clean_json_text(text: str) -> str:
    """Nettoie les fences Markdown autour d'un bloc JSON."""
    cleaned = (text or '').strip()
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    return cleaned.strip()


def _loads_dict(text: str) -> Dict[str, Any]:
    """
    Parse un texte JSON et garantit un objet (dict).

    Contrat de chat_json : les appelants (expert_society, crisis_graph_extractor,
    domino_engine, trajectory_generator) attendent tous un dict et font `raw.get()`.
    Un JSON valide mais non-objet (chaîne, liste, nombre) provoquait un
    `'str' object has no attribute 'get'`. On lève ici un ValueError explicite
    pour déclencher proprement le fallback des appelants.

    Raises:
        json.JSONDecodeError si le texte n'est pas du JSON valide.
        ValueError si le JSON est valide mais n'est pas un objet.
    """
    obj = json.loads(_clean_json_text(text))
    if not isinstance(obj, dict):
        logger.debug(f"chat_json: réponse JSON non-objet ({type(obj).__name__}) : {text!r}")
        raise ValueError(f"réponse JSON non-objet ({type(obj).__name__})")
    return obj



def _messages_to_prompt(messages: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Convertit une liste de messages OpenAI en (system, prompt) pour OpenCode.
    - messages system -> concaténés dans `system`
    - messages user/assistant -> concaténés dans `prompt`
    """
    system_parts: List[str] = []
    prompt_parts: List[str] = []
    for m in messages:
        role = m.get('role', 'user')
        content = m.get('content', '') or ''
        if role == 'system':
            system_parts.append(content)
        elif role == 'assistant':
            prompt_parts.append(f"[Assistant précédent]\n{content}")
        else:
            prompt_parts.append(content)
    return {
        'system': "\n\n".join(system_parts).strip(),
        'prompt': "\n\n".join(prompt_parts).strip(),
    }


# --------------------------------------------------------------------------- #
# Backend OpenCode
# --------------------------------------------------------------------------- #
class OpenCodeClient:
    """Client s'appuyant sur le serveur HTTP d'OpenCode (`opencode serve`)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        agent: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 300.0,
        usage_tracker: Optional[Any] = None,
    ):
        self.base_url = (base_url or Config.OPENCODE_SERVER_URL).rstrip('/')
        self.model = model if model is not None else Config.OPENCODE_MODEL
        self.agent = agent if agent is not None else Config.OPENCODE_AGENT
        username = username if username is not None else Config.OPENCODE_SERVER_USERNAME
        password = password if password is not None else Config.OPENCODE_SERVER_PASSWORD
        auth = (username or 'opencode', password) if password else None
        self.timeout = timeout
        self._auth = auth
        self.usage_tracker = usage_tracker

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout,
                            auth=self._auth, trust_env=trust_env_for(self.base_url))

    def _model_obj(self) -> Optional[Dict[str, str]]:
        """Parse OPENCODE_MODEL 'providerID/modelID' -> {providerID, modelID}."""
        if not self.model:
            return None
        if '/' not in self.model:
            logger.warning(f"OPENCODE_MODEL '{self.model}' invalide (attendu 'provider/model'), ignoré")
            return None
        provider, model_id = self.model.split('/', 1)
        return {"providerID": provider, "modelID": model_id}

    def _base_body(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {"tools": {t: False for t in _OPENCODE_TOOLS}}
        model_obj = self._model_obj()
        if model_obj:
            body["model"] = model_obj
        if self.agent:
            body["agent"] = self.agent
        return body

    def _prompt(self, messages: List[Dict[str, str]],
                output_format: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crée une session éphémère, envoie le prompt, renvoie la réponse brute, supprime la session."""
        mapped = _messages_to_prompt(messages)
        body = self._base_body()
        body["parts"] = [{"type": "text", "text": mapped['prompt'] or ' '}]
        if mapped['system']:
            body["system"] = mapped['system']
        if output_format:
            body["format"] = output_format

        with self._client() as client:
            session = client.post('/session', json={"title": "discover"})
            session.raise_for_status()
            session_id = session.json()['id']
            try:
                t0 = time.perf_counter()
                resp = client.post(f'/session/{session_id}/message', json=body)
                resp.raise_for_status()
                data = resp.json()
                self._record_usage(data, time.perf_counter() - t0)
                return data
            finally:
                try:
                    client.delete(f'/session/{session_id}')
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Suppression de session OpenCode échouée ({session_id}): {e}")

    def _record_usage(self, response: Dict[str, Any], duration: float) -> None:
        if self.usage_tracker is None:
            return
        info = response.get('info') or {}
        tk = info.get('tokens') or {}
        provider = info.get('providerID')
        model_id = info.get('modelID')
        model = f"{provider}/{model_id}" if (provider and model_id) else (model_id or None)
        try:
            self.usage_tracker.record(
                tokens_input=tk.get('input', 0),
                tokens_output=tk.get('output', 0),
                tokens_reasoning=tk.get('reasoning', 0),
                tokens_total=tk.get('total', 0),
                cost=info.get('cost', 0.0),
                duration=duration,
                model=model,
            )
        except Exception as e:  # noqa: BLE001
            logger.debug(f"Enregistrement usage échoué : {e}")

    @staticmethod
    def _extract_text(response: Dict[str, Any]) -> str:
        parts = response.get('parts', []) or []
        texts = [p.get('text', '') for p in parts if p.get('type') == 'text']
        return _strip_think("\n".join(t for t in texts if t))

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,   # ignoré (géré par la config du modèle OpenCode)
        max_tokens: int = 4096,     # ignoré
        response_format: Optional[Dict] = None,
    ) -> str:
        response = self._prompt(messages)
        return self._extract_text(response)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Voie 1 : sortie structurée native d'OpenCode (JSON validé)
        if schema:
            output_format = {"type": "json_schema", "schema": schema, "retryCount": 2}
            response = self._prompt(messages, output_format=output_format)
            structured = (response.get('info') or {}).get('structured')
            if isinstance(structured, dict) and structured:
                return structured
            logger.warning("Sortie structurée OpenCode vide, repli sur le parsing texte")
            # repli : tenter d'extraire du texte si présent
            text = self._extract_text(response)
            if text:
                try:
                    return _loads_dict(text)
                except (json.JSONDecodeError, ValueError):
                    pass
            raise ValueError("OpenCode n'a pas produit de sortie structurée valide")

        # Voie 2 : prompt libre + parsing (compat. sans schéma)
        response = self._prompt(messages)
        text = self._extract_text(response)
        try:
            return _loads_dict(text)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"JSON invalide renvoyé par OpenCode: {e}")

    def health(self) -> bool:
        try:
            with self._client() as client:
                r = client.get('/global/health')
                return r.status_code == 200 and bool(r.json().get('healthy'))
        except Exception:  # noqa: BLE001
            return False


# --------------------------------------------------------------------------- #
# Backend OpenAI (rétro-compatibilité)
# --------------------------------------------------------------------------- #
class OpenAILLMClient:
    """Client LLM direct au format OpenAI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        usage_tracker: Optional[Any] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self.usage_tracker = usage_tracker
        if not self.api_key:
            raise ValueError("LLM_API_KEY non configurée")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        t0 = time.perf_counter()
        response = self.client.chat.completions.create(**kwargs)
        if self.usage_tracker is not None:
            u = getattr(response, 'usage', None)
            try:
                self.usage_tracker.record(
                    tokens_input=getattr(u, 'prompt_tokens', 0) if u else 0,
                    tokens_output=getattr(u, 'completion_tokens', 0) if u else 0,
                    tokens_total=getattr(u, 'total_tokens', 0) if u else 0,
                    duration=time.perf_counter() - t0,
                    model=self.model,
                )
            except Exception:  # noqa: BLE001
                pass
        return _strip_think(response.choices[0].message.content)

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        schema: Optional[Dict[str, Any]] = None,  # non utilisé (mode json_object)
    ) -> Dict[str, Any]:
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        cleaned = _clean_json_text(response)
        try:
            return _loads_dict(cleaned)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"JSON invalide renvoyé par le LLM: {e}")


# --------------------------------------------------------------------------- #
# Façade à sélecteur de backend
# --------------------------------------------------------------------------- #
class LLMClient:
    """
    Façade LLM. Choisit le backend selon Config.LLM_BACKEND
    ('opencode' par défaut, 'openai' en repli). Interface : chat / chat_json.
    """

    def __init__(self, backend: Optional[str] = None, **kwargs):
        backend = (backend or Config.LLM_BACKEND or 'opencode').lower()
        if backend == 'openai':
            self._impl = OpenAILLMClient(**kwargs)
        else:
            self._impl = OpenCodeClient(**kwargs)
        self.backend = backend

    def chat(self, messages, temperature: float = 0.7, max_tokens: int = 4096,
             response_format: Optional[Dict] = None) -> str:
        return self._impl.chat(messages, temperature=temperature,
                               max_tokens=max_tokens, response_format=response_format)

    def chat_json(self, messages, temperature: float = 0.3, max_tokens: int = 4096,
                  schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._impl.chat_json(messages, temperature=temperature,
                                    max_tokens=max_tokens, schema=schema)
