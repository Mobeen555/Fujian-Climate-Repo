# Beginner deployment: a new application

App name: **AquaTerra Research AI**  
Suggested repository: **aquaterra-research-ai**  
Python version: **3.12**  
Main file path: **app.py**

## 1. Extract the ZIP

Download the ZIP and extract it. Open the extracted `aquaterra_research_ai`
folder. You should see `app.py`, `requirements.txt`, `environment.py`,
`evidence.py`, `ai_providers.py`, `crew_runtime.py` and the `agents` folder.
Use a computer for the upload if possible; dragging folders is easier there.

## 2. Create a separate GitHub repository

1. Sign in at https://github.com/new.
2. Enter `aquaterra-research-ai` as the repository name.
3. Choose Public for the simplest setup. Only publish source files; keep actual
   keys and private research datasets out of the repository.
4. Do not generate a README, licence or gitignore there: they are included here.
5. Click **Create repository**.

Your old EcoScope repository remains a separate project.

## 3. Upload the extracted files and folders

1. Click **uploading an existing file** (or **Add file → Upload files**).
2. Open the extracted `aquaterra_research_ai` folder on your computer.
3. Drag its **contents** into GitHub: all top-level files AND the folders.
4. Do not drag every agent file out of `agents/`. Folder paths must be preserved.
5. Commit the upload to `main`.

Check these paths in GitHub:

| Path | Required purpose |
| --- | --- |
| `app.py` | Streamlit entrypoint at the top level |
| `requirements.txt` | Runtime dependencies at the top level |
| `environment.py` and `evidence.py` | Environmental engine and evidence handling |
| `ai_providers.py` | Provider settings |
| `crew_config.py`, `crew_runtime.py`, `crew_workflow.py`, `crewai_compat.py` | CrewAI configuration and execution |
| `agent_common.py`, `agent_tools.py` | Shared agent construction and tools |
| `agents/coordinator.py` | Agent 1 |
| `agents/climate_air.py` | Agent 2 |
| `agents/geospatial_water.py` | Agent 3 |
| `agents/ecology_field.py` | Agent 4 |
| `agents/reviewer_reporter.py` | Agent 5 |
| `.streamlit/config.toml` | Streamlit theme/configuration |

Some file explorers hide dotfiles. If `.streamlit/config.toml` is missing, use
GitHub **Add file → Create new file**, type `.streamlit/config.toml` as the name,
and copy that file's contents from this package. Do the same for `.gitignore`.
The Python app also applies its main theme itself.

If `app.py` is inside an extra wrapper directory in GitHub, move/upload the
contents to the repository root before continuing. Do not choose `api/`.

## 4. Create your Gemini API key

1. Open https://aistudio.google.com/apikey and sign in with Google.
2. Choose **Create API key** and select/create the Google project requested.
3. Copy the key privately. You need one key for all five agents.
4. In AI Studio, check the project's active limits and access to
   `gemini-3.5-flash-lite`. Choose a currently available free-tier text model if
   your account differs. Free-tier access is subject to eligibility and quotas.

Do not enable billing merely because you want unlimited free use: paid billing
does not make requests free. Google also documents different data-use terms for
unpaid services. Review those before sending confidential field information.

## 5. Create the Streamlit app

1. Open https://share.streamlit.io and sign in through GitHub.
2. Click **Create app**, then **Yup, I have an app** if that question appears.
3. Select repository `YOUR_GITHUB_USERNAME/aquaterra-research-ai`.
4. Select branch `main`.
5. Enter **app.py** in **Main file path**.
6. Choose an available app URL, for example `aquaterra-research-mobeen`.
7. Open **Advanced settings** and select **Python 3.12**.

## 6. Paste secrets

In Streamlit's **Secrets** field paste:

```toml
AI_PROVIDER = "gemini"
GEMINI_API_KEY = "PASTE_YOUR_REAL_GEMINI_KEY_HERE"
GEMINI_MODEL = "gemini-3.5-flash-lite"
AI_REQUESTS_PER_MINUTE = 3
AI_TOKENS_PER_MINUTE = 20000
```

Replace only the placeholder key with your actual key, keeping the quotes.
Do not put a key inside the source code, README or a public GitHub file.
The pacing values above are starting settings, not a claim about your allowance;
lower them to match your account if necessary. They cannot raise provider quotas.

Click **Save**, then **Deploy**. Dependencies can take several minutes to install.
No Groq key is required when Gemini is selected. You can also initially deploy
without any key and use maps/statistics before enabling AI.

## 7. First use

1. Open **AI team**. Confirm **Google Gemini** is selected.
2. Click **Test AI connection**. This sends one short test, not your dataset.
3. Open **Study & analysis**. Start with a small area such as Rawal Lake, a short
   historical period and the climate module.
4. Run the selected analysis; check source dates and any unavailable modules.
5. Open **Research workspace** for the blank Excel template, field-data upload,
   sampling points, satellite matchups and statistical tools.
6. Return to **AI team**, tick the permission checkbox for the selected service,
   enter the research question and click **Run five-agent review**.
7. Allow time for request pacing. One review uses several API calls, not one.
8. Download reports and the reproducible research package before closing/rebooting.

## 8. Use OpenRouter instead

Create a key at https://openrouter.ai/settings/keys. In the deployed app's
Streamlit settings → Secrets, add:

```toml
OPENROUTER_API_KEY = "PASTE_YOUR_REAL_OPENROUTER_KEY_HERE"
OPENROUTER_MODEL = "openrouter/free"
```

Select **OpenRouter free models** in the app and test the connection. To make
it the default, change `AI_PROVIDER` to `"openrouter"`. Keep the other key if
you still want Gemini as an option. `openrouter/free` selects a free model;
model quality/availability varies. For more consistent research interpretation,
choose a specific supported model whose ID ends in `:free`. The app blocks paid
OpenRouter model IDs and has no automatic provider or paid-model fallback.

Ollama is a separate local/self-hosted route: see LOCAL_OLLAMA.md. Do not put
your laptop's `localhost` address into a Streamlit Cloud deployment expecting
it to connect to the laptop.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `No module named evidence` or another project module | Upload every helper file at the root and preserve `agents/`; check `app.py` is from this package. |
| Dependency installation failed | Use this requirements.txt and Python 3.12; read the first error in Streamlit logs. |
| 401 or rejected key | Check the selected provider and its matching key in Secrets. |
| 403 / model not permitted | Check project eligibility, model access and regional restrictions with the provider. |
| 404 / model not found | Use a currently available model ID for the selected provider. |
| 429 / quota reached | Check provider reset times; wait or reduce usage. Repeated retries and extra keys on the same project do not create unlimited quota. |
| Request too large for configured budget | Narrow the analysis/question, or set the estimate budget within your verified account allowance. |
| AI stopped with partial notes | Download/review those notes; standard numerical results remain available. |
| No satellite observations | Try an appropriate historical date range; inspect clouds, study geometry and source errors. Do not treat missing data as a zero. |
| Landsat connection failed | Live download remains unverified for this release; inspect provider status/network access and use available Sentinel-2/field analysis meanwhile. |
| App exceeds memory | Reduce area, dates and scene count; process separate studies. |

To update this NEW app later, commit changes to its NEW GitHub repository.
Streamlit normally redeploys linked changes. Use **Manage app → Reboot** when
needed. Settings/secrets are configured separately for each Streamlit app.

Official instructions checked 3 October 2026:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
