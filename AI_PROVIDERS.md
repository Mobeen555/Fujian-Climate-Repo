# Optional AI interpretation — no agents

HydroScope performs every data retrieval and scientific calculation without an LLM. The only AI feature is an explicit, single chat-completion request that explains already-computed evidence. CrewAI and all agent files/dependencies have been removed.

Supported choices are Gemini, Groq, OpenRouter free models and owner-enabled Ollama. Select one in **AI interpretation**. Configure its API key/model in Streamlit Secrets (see `secrets.example.toml`) or enter a key privately for the current session. Hosted endpoints are fixed; users cannot redirect server keys to arbitrary URLs. An Ollama URL can be configured only by the app owner.

| Provider | Secret | Model setting | Access |
|---|---|---|---|
| Gemini | GEMINI_API_KEY | GEMINI_MODEL | Account/model quotas and data terms apply |
| Groq | GROQ_API_KEY | GROQ_MODEL | Account/model quotas apply |
| OpenRouter | OPENROUTER_API_KEY | OPENROUTER_MODEL | Only `openrouter/free` or `:free` IDs accepted; quotas and upstream terms apply |
| Ollama | optional OLLAMA_API_KEY | OLLAMA_MODEL | Local hardware or an owner-configured authenticated server |

The supplied model IDs are defaults, not guarantees of continued availability. Change a model ID if the provider retires it or your account lacks access. Do not assume there is an unlimited free hosted API. Ollama has no hosted-provider quota when you run an open model locally, but compute, memory, electricity and model licensing still apply. A Streamlit Community Cloud process cannot reach `localhost` on your laptop.

For local Ollama, install it from [ollama.com](https://ollama.com/download), pull `qwen2.5:7b` (or an appropriate available model), and run this Streamlit app on the same computer. Set `ENABLE_OLLAMA = true`, `OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"` and the model ID in local secrets. An internet-accessible deployment needs a secured HTTPS proxy; never expose an unauthenticated Ollama service publicly.

## What is sent and retained

The displayed packet contains the study name/type, date range, evidence sources, calculated summaries, method/uncertainty notes and bounded table excerpts. It excludes raw files and raster arrays; direct sample identifiers and coordinate columns are filtered from table excerpts. Inspect it before consenting because your study name or uploaded parameter names may still be sensitive.

The provider receives the system prompt, your question and that packet. It receives no code-execution tools, retrieval tools or autonomous task loop. The app records the response, model IDs, prompt, evidence packet, usage, timestamp and evidence fingerprint, but no API credential.

A successful answer must cite existing source IDs. This checks that an ID exists, **not that every sentence or numerical claim is correct**. Review the text before sharing it. No result becomes scientifically validated merely because AI describes it.

The identical saved evidence/provider/model/question reuses the saved answer. A new request is limited to one HTTP call, with a 20-second minimum between requests per running server process. Provider HTTP 429 errors stop immediately; there are no hidden retries or automatic paid fallbacks. A changed evidence fingerprint invalidates the saved interpretation. Removing the interpretation also invalidates cached report packages. Scientific data and exports remain usable during provider outages or without a key.

Provider references:

- https://ai.google.dev/gemini-api/docs/openai
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/gemini-api/docs/pricing
- https://console.groq.com/docs/openai
- https://openrouter.ai/docs/api/reference/limits
- https://docs.ollama.com/api/openai-compatibility
