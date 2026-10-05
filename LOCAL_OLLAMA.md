# Local AI without a hosted-provider quota

This is an optional alternative to Streamlit Community Cloud. Run **both
Streamlit and Ollama on your own computer**. It needs suitable memory/compute,
disk space for model weights, electricity and an initial model download. It is
not unlimited hardware and does not remove data-provider quotas.

## Local setup

1. Install Python 3.12 and follow README.md's local installation steps.
2. Install Ollama from https://ollama.com/download and start Ollama.
3. In a terminal, download the instruct model:

```bash
ollama pull qwen2.5:7b
```

4. Open a terminal inside this project's folder. Use the included `Modelfile`
   to give the model a 16,384-token context window:

```bash
ollama create aquaterra-local -f Modelfile
```

5. Create `.streamlit/secrets.toml` on your computer containing:

```toml
AI_PROVIDER = "ollama"
ENABLE_OLLAMA = true
OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
OLLAMA_MODEL = "aquaterra-local"
```

6. Run `python -m streamlit run app.py` and open the local browser link.
7. In **AI team**, select Ollama and click **Test AI connection**.
8. Keep Ollama running during the agent review. No local Ollama API key is needed.

Model weights and their context cache need several GB of memory. A CPU may be
slow, and smaller models can be less reliable at following the agent/tool format.
Failed or incomplete reviews are labelled accordingly. No environmental accuracy
claim follows from using a larger/local model.

The included Modelfile uses a locally downloaded model, not an Ollama cloud
model. You can disable Ollama cloud features with `OLLAMA_NO_CLOUD=1` as explained
in https://docs.ollama.com/faq. Environmental data retrieval still needs internet.

## Streamlit Cloud with your own AI server (advanced)

`localhost` in a Streamlit Cloud app means the Streamlit server. It does not mean
your laptop. This ZIP does not install or start an LLM inside Community Cloud.

If you independently operate a server, put Ollama behind an authenticated HTTPS
reverse proxy. Configure `OLLAMA_BASE_URL` to that owner's `/v1` endpoint and
`OLLAMA_API_KEY` to its proxy token, through Streamlit Secrets. This code requires
HTTPS and a credential for remote endpoints; the proxy itself must enforce the
credential. Do not expose Ollama's unauthenticated port directly. Keeping that
server available is your responsibility and may involve hosting costs.

A Cloud-only deployment with an ordinary hosted free key cannot promise
unrestricted, permanent AI usage.
