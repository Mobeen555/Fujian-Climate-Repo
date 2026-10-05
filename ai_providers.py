"""Provider metadata only; no SDK imports, credentials or network calls."""
from urllib.parse import urlparse

DEFAULT_PROVIDER = "gemini"
PROVIDERS = {
    "gemini": {
        "label": "Google Gemini", "key_name": "GEMINI_API_KEY",
        "model": "gemini-3.5-flash-lite", "model_name": "GEMINI_MODEL",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_url": "https://aistudio.google.com/apikey",
        "limits_url": "https://ai.google.dev/gemini-api/docs/rate-limits",
        "rpm": 3, "tpm": 20000,
        "note": "Eligible models have a free tier with project quotas. Check your active limits in AI Studio. Unpaid-service data terms apply.",
    },
    "openrouter": {
        "label": "OpenRouter free models", "key_name": "OPENROUTER_API_KEY",
        "model": "openrouter/free", "model_name": "OPENROUTER_MODEL",
        "base_url": "https://openrouter.ai/api/v1",
        "key_url": "https://openrouter.ai/settings/keys",
        "limits_url": "https://openrouter.ai/docs/api/reference/limits",
        "rpm": 5, "tpm": 20000,
        "note": "Only openrouter/free or a :free model is accepted here. Daily and per-minute limits apply. The free router may select different models; returned model IDs are recorded.",
    },
    "groq": {
        "label": "Groq", "key_name": "GROQ_API_KEY",
        "model": "openai/gpt-oss-120b", "model_name": "GROQ_MODEL",
        "base_url": "https://api.groq.com/openai/v1",
        "key_url": "https://console.groq.com/keys",
        "limits_url": "https://console.groq.com/docs/rate-limits",
        "rpm": 10, "tpm": 10000,
        "note": "Existing Groq support remains available. Account and model quotas still apply.",
    },
    "ollama": {
        "label": "Ollama on your own computer/server", "key_name": "OLLAMA_API_KEY",
        "model": "aquaterra-local", "model_name": "OLLAMA_MODEL",
        "base_url": "http://127.0.0.1:11434/v1",
        "key_url": "https://ollama.com/download",
        "limits_url": "https://docs.ollama.com/faq",
        "rpm": 30, "tpm": 100000,
        "note": "Local inference has no hosted API quota. Your hardware, electricity, model licence and app run budgets still limit capacity. Community Cloud cannot reach localhost on your laptop.",
    },
}


def validate_connection(provider, model, base_url=None):
    """Hosted endpoints are fixed. An Ollama endpoint is owner-configured only."""
    if provider not in PROVIDERS:
        raise ValueError("Choose a supported AI provider.")
    if not model or len(model) > 150 or any(c.isspace() for c in model):
        raise ValueError("Enter a model ID without spaces.")
    if provider == "openrouter" and not (model == "openrouter/free" or model.endswith(":free")):
        raise ValueError("This app's OpenRouter option accepts only openrouter/free or a model ID ending in :free.")
    endpoint = PROVIDERS[provider]["base_url"]
    if provider == "ollama":
        endpoint = str(base_url or endpoint).rstrip("/")
        parsed = urlparse(endpoint)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname or
                parsed.username or parsed.password or parsed.query or parsed.fragment or
                parsed.path.rstrip("/") != "/v1" or (not local and parsed.scheme != "https")):
            raise ValueError("OLLAMA_BASE_URL must be a local HTTP /v1 endpoint or an authenticated HTTPS /v1 proxy.")
    return endpoint
