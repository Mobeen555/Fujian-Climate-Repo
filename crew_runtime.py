"""A bounded multi-provider adapter for CrewAI, with session-private task storage."""
from __future__ import annotations

from collections import deque
import hashlib
import math
import threading
import time
from typing import Any
from urllib.parse import urlparse

from ai_providers import DEFAULT_PROVIDER, PROVIDERS, validate_connection

import requests
from pydantic import PrivateAttr

from crew_config import (MAX_LLM_CALLS, MAX_OUTPUT_TOKENS, MAX_INPUT_CHARACTERS,
                         MAX_RUN_SECONDS, DEFAULT_TOKENS_PER_MINUTE)
from crewai_compat import BaseLLM, Crew


class CrewRunError(RuntimeError):
    """A sanitized, user-readable stop; provider response bodies stay private."""


class RunBudget:
    def __init__(self, max_calls=MAX_LLM_CALLS, seconds=MAX_RUN_SECONDS):
        self.max_calls = max_calls
        self.deadline = time.monotonic() + seconds
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.error = ""
        self.actual_models = []

    def check(self):
        if self.error:
            raise CrewRunError(self.error)
        if time.monotonic() >= self.deadline:
            self.error = "The AI run reached its time budget. Completed agent notes remain available."
            raise CrewRunError(self.error)
        if self.calls >= self.max_calls:
            self.error = "The AI run reached its request budget. Ask a narrower question."
            raise CrewRunError(self.error)

    def fail(self, message):
        self.error = message
        raise CrewRunError(message)


# One conservative rolling budget per key/model inside this server process.
# Only SHA-256 key digests are held here; actual credentials stay on the LLM instance.
_RATE_LOCK = threading.Lock()
_RATE_BUCKETS = {}


def reserve_rate_slot(key_hash, estimated_tokens, tokens_per_minute, budget, notify=None, requests_per_minute=10):
    if estimated_tokens > tokens_per_minute:
        budget.fail("This AI request exceeds the configured token-per-minute budget. Use a narrower question or adjust the budget to your selected provider account limit.")
    last_notice = 0.0
    while True:
        budget.check()
        now = time.monotonic()
        with _RATE_LOCK:
            # Remove expired account buckets; no credentials or prompts are stored.
            for old_key in list(_RATE_BUCKETS):
                q = _RATE_BUCKETS[old_key]
                while q and now - q[0][0] >= 61:
                    q.popleft()
                if not q:
                    del _RATE_BUCKETS[old_key]
            queue = _RATE_BUCKETS.setdefault(key_hash, deque())
            if len(queue) < requests_per_minute and sum(n for _, n in queue) + estimated_tokens <= tokens_per_minute:
                queue.append((now, estimated_tokens))
                return
            wait = max(.1, 61 - (now - queue[0][0]))
        if notify and now - last_notice > 10:
            notify({"event": "rate_pause", "seconds": round(wait)})
            last_notice = now
        time.sleep(min(1.0, wait))


class ProviderEvidenceLLM(BaseLLM):
    """CrewAI's ReAct tool loop uses this adapter's plain text responses.

    Only role/content message fields are sent. No LiteLLM prompt cache metadata,
    implicit OpenAI credentials, arbitrary endpoints or provider-side tools.
    """
    _credential: str = PrivateAttr(default="")
    _budget: Any = PrivateAttr()
    _notify: Any = PrivateAttr(default=None)
    _tokens_per_minute: int = PrivateAttr(default=DEFAULT_TOKENS_PER_MINUTE)
    _key_hash: str = PrivateAttr(default="")

    _provider_id: str = PrivateAttr(default=DEFAULT_PROVIDER)
    _endpoint: str = PrivateAttr(default="")
    _label: str = PrivateAttr(default="")
    _requests_per_minute: int = PrivateAttr(default=3)
    _max_output: int = PrivateAttr(default=MAX_OUTPUT_TOKENS)

    def __init__(self, key, model, budget=None, notify=None, tokens_per_minute=DEFAULT_TOKENS_PER_MINUTE,
                 provider=DEFAULT_PROVIDER, requests_per_minute=None, base_url=None):
        try:
            endpoint = validate_connection(provider, model, base_url)
        except ValueError as exc:
            raise CrewRunError(str(exc)) from None
        local_ollama = provider == "ollama" and urlparse(endpoint).hostname in {"localhost", "127.0.0.1", "::1"}
        if not str(key or "").strip() and not local_ollama:
            raise CrewRunError("Add the selected provider's API key in Streamlit Secrets or the private key field.")
        super().__init__(model=model, temperature=.1, provider=provider, max_tokens=MAX_OUTPUT_TOKENS)
        self._provider_id = provider
        self._endpoint = endpoint + "/chat/completions"
        self._label = PROVIDERS[provider]["label"]
        self._max_output = 3072 if provider in {"gemini", "ollama", "openrouter"} else MAX_OUTPUT_TOKENS
        self._credential = str(key or "ollama").strip()
        self._budget = budget or RunBudget()
        self._notify = notify
        self._tokens_per_minute = max(2000, min(1000000, int(tokens_per_minute)))
        self._requests_per_minute = max(1, min(120, int(requests_per_minute or PROVIDERS[provider]["rpm"])))
        self._key_hash = hashlib.sha256((provider + "|" + endpoint + "|" + self._credential + "|" + model).encode()).hexdigest()

    def supports_function_calling(self):
        # Tools execute through CrewAI's bounded ReAct executor, not recursive HTTP calls.
        return False

    def supports_stop_words(self):
        return False

    def get_context_window_size(self):
        return 16384

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        self._budget.check()
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        clean = []
        for message in messages:
            role, content = message.get("role"), message.get("content")
            if role not in ("system", "user", "assistant") or not isinstance(content, str):
                self._budget.fail("The AI framework produced an unsupported message format. Analysis results are preserved.")
            clean.append({"role": role, "content": content})
        characters = sum(len(m["content"]) for m in clean)
        if characters > MAX_INPUT_CHARACTERS:
            self._budget.fail("The AI context is too large for this bounded workflow. Ask a more focused question or analyse fewer modules.")
        estimate = math.ceil(characters / 3.5) + self._max_output
        reserve_rate_slot(self._key_hash, estimate, self._tokens_per_minute, self._budget, self._notify, self._requests_per_minute)
        self._budget.check()
        self._budget.calls += 1
        if self._notify:
            self._notify({"event": "model_request", "call": self._budget.calls})
        payload = {"model": self.model, "messages": clean, "temperature": .1}
        payload["max_completion_tokens" if self._provider_id == "groq" else "max_tokens"] = self._max_output
        if self._provider_id == "groq" and self.model in ("openai/gpt-oss-120b", "openai/gpt-oss-20b"):
            payload["reasoning_effort"] = "low"
            payload["reasoning_format"] = "hidden"
        elif self._provider_id == "gemini":
            if self.model.startswith("gemini-2.5-flash"):
                payload["reasoning_effort"] = "none"
            elif self.model.startswith("gemini-3"):
                payload["reasoning_effort"] = "low"
        headers = {"Authorization": "Bearer " + self._credential, "Content-Type": "application/json"}
        if self._provider_id == "openrouter":
            headers["X-Title"] = "AquaTerra Research AI"
        try:
            response = requests.post(
                self._endpoint, json=payload,
                headers=headers, allow_redirects=False,
                timeout=(8, min(120 if self._provider_id == "ollama" else 55, max(1, self._budget.deadline - time.monotonic()))),
            )
        except requests.RequestException:
            self._budget.fail(f"{self._label} did not respond. The AI review stopped; your environmental results remain available.")
        if response.status_code != 200:
            messages_by_status = {
                401: f"{self._label} rejected the API key. Check your Streamlit Secrets or session key.",
                403: "The selected provider key or model is not permitted for this account.",
                404: f"{self._label} could not find this model. Check the model ID in the AI connection settings.",
                429: f"{self._label} rate or token limit was reached. Check your account quota/reset time and wait before retrying. No automatic retry was made; completed agent notes are preserved.",
                402: "This provider requires available credits. Check the selected model and account; there is no automatic paid fallback.",
            }
            self._budget.fail(messages_by_status.get(response.status_code, f"{self._label} returned HTTP {response.status_code}. Check model support and account limits; the AI review stopped."))
        try:
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            actual_model = str(data.get("model") or self.model)[:150]
            if actual_model not in self._budget.actual_models:
                self._budget.actual_models.append(actual_model)
            if self._notify:
                self._notify({"event": "model_response", "provider": self._provider_id, "model": actual_model})
            usage = data.get("usage") or {}
            self._budget.prompt_tokens += int(usage.get("prompt_tokens", 0))
            self._budget.completion_tokens += int(usage.get("completion_tokens", 0))
        except (ValueError, KeyError, IndexError, TypeError):
            self._budget.fail(f"{self._label} returned an unreadable response. No final review was accepted.")
        if choice.get("finish_reason") == "length":
            self._budget.fail("The model response was cut off by its output budget. Ask a shorter question; no incomplete final report was accepted.")
        if not isinstance(content, str) or not content.strip():
            self._budget.fail(f"{self._label} returned no usable answer. Try a more focused question or another supported model.")
        # A model must not invent a tool observation. CrewAI inserts real tool results.
        for marker in ("\nObservation:", *self.stop_sequences):
            if marker and marker in content:
                content = content.split(marker, 1)[0]
        return content.strip()


class GroqEvidenceLLM(ProviderEvidenceLLM):
    """Compatibility for the existing Groq integration tests and local scripts."""
    def __init__(self, key, model, budget=None, notify=None, tokens_per_minute=DEFAULT_TOKENS_PER_MINUTE):
        super().__init__(key, model, budget, notify, tokens_per_minute, provider="groq")


class SessionTaskOutputs:
    """Disable CrewAI's shared latest-kickoff SQLite log; the UI owns session output."""
    def reset(self):
        pass

    def update(self, task_index, log):
        pass

    def load(self):
        return []


class SessionCrew(Crew):
    # This extension point is covered by tests and pinned to CrewAI 1.15.22.
    _task_output_handler: Any = PrivateAttr(default_factory=SessionTaskOutputs)
