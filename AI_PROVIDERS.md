# AI services and limits

Checked against official documentation on **3 October 2026**. Provider models,
prices, eligibility and quotas can change. No unlimited free hosted LLM API is
promised by this application.

| Option | Cost/limits | Use in this app |
| --- | --- | --- |
| Google Gemini | Selected models have a free tier; project/model RPM, TPM and daily quotas apply. | Default hosted option; initial model `gemini-3.5-flash-lite`. |
| OpenRouter free models | Free models/free router still have daily and per-minute caps and variable capacity. | Supported; only `openrouter/free` or `:free` model IDs are accepted. |
| Groq | Free access is rate-limited. | Retained as an optional provider. |
| Ollama local | No hosted-provider token quota for models running locally; your hardware, electricity and model licence still matter. | Owner-enabled local/self-hosted option. |
| Cerebras | Official docs currently describe a $5 trial, expiring after 30 days, requiring a verified payment method. No permanently renewing free tier. | Not included as a free provider. |

For Streamlit Community Cloud, begin with Gemini and use OpenRouter as another
explicitly selected option. Do not assume either can keep five agents running
without limits. One review requires at least five generation calls and may use
up to 18, including tool rounds and corrections. The connection test uses one
additional call. Completed identical reviews are reused unless you request a
fresh one. Public environmental data analysis needs no LLM key.

Provider switching is manual. The application does not rotate keys, bypass
quotas, retry indefinitely or switch silently to a paid service. On quota errors
it stops and retains completed agent notes. Per-minute settings only slow the
application; they cannot increase an account's limits. Gemini quotas are per
project, so another key from the same project does not create a new allowance.

The default budgets are 18 model requests, 10 minutes and 22,000 input characters
per individual model request. Output limits are 3,072 tokens for Gemini,
OpenRouter and Ollama, and 1,800 for Groq. These bounded runs prevent agent loops;
they are distinct from provider quotas. Input/token estimates are approximate.
Pacing is shared within this Python server process, not across other apps or
server replicas using the same credentials.

## Privacy and reproducibility

The chosen service receives the question, coordinates, saved evidence summaries
and tool-returned statistics/table previews. It does not receive full upload
files or raw satellite rasters. Google documents product-improvement use for
unpaid-service data. OpenRouter also involves the selected underlying provider;
check its data policies before sending confidential or unpublished research.

Keys are kept per LLM instance, never exported in reports, and hosted endpoints
are fixed. Local model inference can keep the AI prompt on your own machine.
AI wording is not guaranteed reproducible. Numerical replay is separate and
uses frozen processed snapshots, explicit settings and saved scientific code.
The requested and returned model IDs are recorded, including when the free
OpenRouter router changes the selected model.

## Official references

- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini active quotas: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini compatibility: https://ai.google.dev/gemini-api/docs/openai
- Gemini lifecycle: https://ai.google.dev/gemini-api/docs/deprecations
- OpenRouter limits: https://openrouter.ai/docs/api/reference/limits
- OpenRouter free router: https://openrouter.ai/docs/guides/routing/routers/free-router
- Cerebras trial: https://inference-docs.cerebras.ai/support/rate-limits
- Ollama API: https://docs.ollama.com/api/openai-compatibility
- Ollama FAQ: https://docs.ollama.com/faq
- Groq limits: https://console.groq.com/docs/rate-limits
