"""Thin LLM client adapter for Hermes.

Reads `config/llm-endpoints.yaml`, exposes:
  - chat_client(role)            -> an openai.OpenAI client for the role's endpoint
  - embed(role, text)            -> list[float], OpenAI-compat or Gemini-native
  - endpoint_for(role)           -> endpoint config dict (for diagnostics)
  - model_name_for(role)         -> model id string for the role
  - default_max_tokens_for(role) -> sensible per-endpoint default
  - health_check(role)           -> bool

Failover behavior: this adapter does NOT auto-failover. If `endpoint_for(role)`
returns an endpoint that fails at request time, the caller must handle it.
The `failover_to:` field in the YAML is documentation only — the orchestration
layer (Hermes) decides whether/when to retry on a sibling endpoint, per the
spike doctrine of explicit, traceable behavior (Criterion #9: fail into
quarantine, don't hang or silently retry).

Design constraints
  - Stateless: no module-level state beyond the loaded config. Re-instantiate
    LLMClient per Hermes task. Cheap (a YAML parse).
  - Env vars only for secrets. Never prints API key values.
  - No retry/backoff in this adapter; that's Hermes/orchestration's job.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import yaml
from openai import OpenAI


class LLMConfigError(RuntimeError):
    """Raised when the config is missing or invalid."""


class NoEndpointForRole(LLMConfigError):
    """Raised when no endpoint declares the requested role."""


class LLMClient:
    """Reads the LLM endpoint registry and produces clients per role."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            # Default: <project-root>/config/llm-endpoints.yaml
            here = Path(__file__).resolve().parent
            config_path = here.parent / "config" / "llm-endpoints.yaml"
        self.config_path = Path(config_path)
        if not self.config_path.is_file():
            raise LLMConfigError(f"config not found: {self.config_path}")
        self.config: dict[str, Any] = yaml.safe_load(self.config_path.read_text())
        self.endpoints: dict[str, dict[str, Any]] = self.config.get("endpoints", {})
        if not self.endpoints:
            raise LLMConfigError(f"no `endpoints` block in {self.config_path}")

    # ── Lookup ────────────────────────────────────────────────────────

    def endpoint_for(self, role: str) -> dict[str, Any]:
        """Return the endpoint config dict for the first endpoint matching role."""
        for eid, ec in self.endpoints.items():
            if role in (ec.get("roles") or []):
                return {"id": eid, **ec}
        raise NoEndpointForRole(
            f"no endpoint with role={role!r} in {self.config_path.name}; "
            f"available roles: {sorted({r for ec in self.endpoints.values() for r in (ec.get('roles') or [])})}"
        )

    def _api_key(self, ec: dict[str, Any]) -> str:
        env_name = ec.get("api_key_env") or ""
        if not env_name:
            # Local endpoint, no key needed
            return "not-required"
        v = os.environ.get(env_name)
        if not v:
            raise LLMConfigError(
                f"endpoint {ec.get('id') or '?'} expects env var {env_name!r}, but it is not set"
            )
        return v

    # ── Chat ──────────────────────────────────────────────────────────

    def chat_client(self, role: str) -> Any:
        """Return a chat client configured for the role's endpoint.

        Return type depends on the endpoint's `api_style`:
          - openai_compatible (default): returns an `openai.OpenAI` instance.
          - gemini: returns OpenAI client pointed at Google's OpenAI-compat
            shim at .../v1beta/openai/.
          - anthropic: returns a minimal `_AnthropicChatAdapter` that mimics
            the OpenAI `.chat.completions.create()` surface used by callers;
            translates request/response on the wire.

        All three expose `.chat.completions.create(model=..., messages=...,
        max_tokens=..., temperature=...)` returning an object with
        `.choices[0].message.content` and `.choices[0].finish_reason`.
        """
        return self._build_chat_client(self.endpoint_for(role))

    def chat_client_for_endpoint(self, endpoint_id: str) -> Any:
        """Return a chat client for an endpoint by id, bypassing role lookup.

        Useful for direct comparisons (e.g., quality-checking a demoted
        endpoint against the active one without temporarily flipping
        `active`/`roles` in the config).
        """
        ec = self.endpoints.get(endpoint_id)
        if not ec:
            raise LLMConfigError(
                f"no endpoint with id={endpoint_id!r}; "
                f"known: {sorted(self.endpoints)}"
            )
        return self._build_chat_client({"id": endpoint_id, **ec})

    def _build_chat_client(self, ec: dict[str, Any]) -> Any:
        base_url = ec["base_url"]
        api_style = ec.get("api_style")
        if api_style == "anthropic":
            return _AnthropicChatAdapter(
                base_url=base_url,
                api_key=self._api_key(ec),
                timeout_s=int(ec.get("timeout_s", 60)),
            )
        if api_style == "gemini" and "/v1beta" in base_url and "/openai" not in base_url:
            base_url = base_url.rstrip("/") + "/openai"
        return OpenAI(
            base_url=base_url,
            api_key=self._api_key(ec),
            timeout=httpx.Timeout(ec.get("timeout_s", 60), connect=10),
        )

    def model_name_for(self, role: str) -> str:
        return self.endpoint_for(role)["model"]

    def default_max_tokens_for(self, role: str) -> int:
        """Return the endpoint's `default_max_tokens`, or 1024 if not set.

        Use this whenever the caller doesn't have a stronger reason to override.
        Prevents the 32-token footgun where Qwen / gpt-5-mini burn all output
        tokens on internal reasoning and return empty content.
        """
        return int(self.endpoint_for(role).get("default_max_tokens", 1024))

    # ── Embeddings ────────────────────────────────────────────────────

    def embed(self, role: str, text: str | list[str]) -> list[list[float]]:
        """Embed a single string or a batch. Returns list of vectors.

        Handles both OpenAI-compatible (most providers, OpenRouter) and
        Gemini-native shapes (Google AI direct).
        """
        ec = self.endpoint_for(role)
        texts = [text] if isinstance(text, str) else list(text)

        if ec.get("api_style") == "gemini":
            return self._embed_gemini_native(ec, texts)

        # OpenAI-compatible path
        client = OpenAI(
            base_url=ec["base_url"],
            api_key=self._api_key(ec),
            timeout=httpx.Timeout(ec.get("timeout_s", 60), connect=10),
        )
        resp = client.embeddings.create(model=ec["model"], input=texts)
        return [d.embedding for d in resp.data]

    def _embed_gemini_native(self, ec: dict[str, Any], texts: list[str]) -> list[list[float]]:
        """Call Google's native embedContent endpoint (different request shape)."""
        api_key = self._api_key(ec)
        base = ec["base_url"].rstrip("/")
        model = ec["model"]
        out: list[list[float]] = []
        with httpx.Client(timeout=ec.get("timeout_s", 60)) as client:
            for t in texts:
                r = client.post(
                    f"{base}/models/{model}:embedContent",
                    params={"key": api_key},
                    json={"content": {"parts": [{"text": t}]}},
                )
                r.raise_for_status()
                out.append(r.json()["embedding"]["values"])
        return out

    # ── Health ────────────────────────────────────────────────────────

    def health_check(self, role: str) -> bool:
        """Light probe. For OpenAI/Gemini styles, GET /models. For Anthropic
        style, POST a 1-token /v1/messages probe (more reliable than /models
        on Anthropic-compat servers, and effectively free on MiniMax's flat
        plan / sub-cent on Anthropic-proper). Returns True on HTTP 200.
        """
        ec = self.endpoint_for(role)
        base_url = ec["base_url"]
        api_style = ec.get("api_style")

        if api_style == "anthropic":
            try:
                with httpx.Client(timeout=5) as c:
                    r = c.post(
                        f"{base_url.rstrip('/')}/v1/messages",
                        headers={
                            "x-api-key": self._api_key(ec),
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": ec["model"],
                            "max_tokens": 1,
                            "messages": [{"role": "user", "content": "."}],
                        },
                    )
                    return r.status_code == 200
            except httpx.HTTPError:
                return False

        if api_style == "gemini" and "/v1beta" in base_url and "/openai" not in base_url:
            base_url = base_url.rstrip("/") + "/openai"
        headers = {}
        if ec.get("api_key_env"):
            headers["Authorization"] = f"Bearer {self._api_key(ec)}"
        try:
            with httpx.Client(timeout=5) as c:
                r = c.get(f"{base_url.rstrip('/')}/models", headers=headers)
                return r.status_code == 200
        except httpx.HTTPError:
            return False


# ── Anthropic Messages adapter ────────────────────────────────────────
# Wraps the Anthropic /v1/messages surface (e.g., MiniMax's $80/mo plan
# at https://api.minimax.io/anthropic) so callers can keep using the
# OpenAI `.chat.completions.create()` shape without branching.

class _AnthropicChatAdapter:
    """Adapter exposing `.chat.completions.create()` over Anthropic Messages.

    Supported request params: model, messages, max_tokens, temperature.
    Unsupported OpenAI-only params (response_format, tools, tool_choice,
    stream) are silently ignored — extend when needed. JSON-mode requires
    Anthropic's tool-use pattern; that lives in the caller, not here.
    """

    def __init__(self, base_url: str, api_key: str, timeout_s: int) -> None:
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_s
        self.chat = _AnthropicChatNamespace(self)


class _AnthropicChatNamespace:
    def __init__(self, parent: "_AnthropicChatAdapter") -> None:
        self.completions = _AnthropicCompletions(parent)


class _AnthropicCompletions:
    _FINISH_MAP = {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "stop",
        "tool_use": "tool_calls",
    }

    def __init__(self, parent: "_AnthropicChatAdapter") -> None:
        self._parent = parent

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float = 0.0,
        **_ignored: Any,
    ) -> "_AnthropicResponse":
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        anth_messages = [m for m in messages if m.get("role") != "system"]
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anth_messages,
            "temperature": temperature,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)

        with httpx.Client(timeout=self._parent._timeout) as c:
            r = c.post(
                f"{self._parent._base}/v1/messages",
                headers={
                    "x-api-key": self._parent._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
            )
        r.raise_for_status()
        data = r.json()
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
        finish = self._FINISH_MAP.get(data.get("stop_reason") or "", "stop")
        return _AnthropicResponse(text, finish, data)


class _AnthropicResponse:
    """Mimics the slice of OpenAI ChatCompletion that callers actually use."""

    def __init__(self, content: str, finish_reason: str, raw: dict[str, Any]) -> None:
        self.choices = [_AnthropicChoice(content, finish_reason)]
        self.raw = raw


class _AnthropicChoice:
    def __init__(self, content: str, finish_reason: str) -> None:
        self.message = _AnthropicMessage(content)
        self.finish_reason = finish_reason


class _AnthropicMessage:
    def __init__(self, content: str) -> None:
        self.content = content


__all__ = ["LLMClient", "LLMConfigError", "NoEndpointForRole"]


if __name__ == "__main__":
    # Smoke test when run directly:
    #   python -m code.llm_client
    # or
    #   python code/llm_client.py
    import sys

    client = LLMClient()
    print("Loaded:", client.config_path)
    print("Endpoints:", list(client.endpoints))
    print()

    role = sys.argv[1] if len(sys.argv) > 1 else "extractor"
    print(f"Resolving role={role!r}…")
    ec = client.endpoint_for(role)
    print(f"  → {ec['id']} ({ec.get('family')}, model={ec['model']})")
    print(f"  health: {client.health_check(role)}")

    if "embedding" in role:
        v = client.embed(role, "apolipoprotein B is a marker of cardiovascular risk")
        print(f"  embed dim: {len(v[0])}")
    else:
        oc = client.chat_client(role)
        # Use the endpoint's default_max_tokens (config-driven). Asking for 32
        # is unsafe: gpt-5-mini reserves >= 16 for internal reasoning, and Qwen
        # can burn all output tokens on its own CoT before producing content.
        max_tokens = client.default_max_tokens_for(role)
        prompt = (
            "Reply with the single sentence: "
            "'apoB measures atherogenic particle count.' Nothing else."
        )
        r = oc.chat.completions.create(
            model=client.model_name_for(role),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0,
        )
        content = r.choices[0].message.content
        finish = r.choices[0].finish_reason
        print(f"  max_tokens={max_tokens}, finish_reason={finish}")
        if not content or not content.strip():
            print(
                f"  ⚠ EMPTY content (finish_reason={finish}). "
                f"Likely token starvation — raise default_max_tokens in the config."
            )
            sys.exit(2)
        print(f"  chat: {content!r}")
