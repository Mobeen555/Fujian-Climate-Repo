# AquaTerra Research AI

A separate Streamlit application for water, ecology and climate research.
Python **3.12** · main file **app.py** · exactly **five CrewAI agents**.

This package includes the enhanced research workspace, all helper modules, all five
agent files, dependencies, configuration, examples, tests and the MIT licence.
It does not require the old application's repository. Supplied photos, decorative
icons and image frames are removed. No Supabase or Vercel setup is required.

## Start here

Follow **DEPLOY_STREAMLIT.md** to create a NEW GitHub repository and a NEW Streamlit
app. Keep the `agents/`, `examples/`, `tests/` and `.streamlit/` folders intact.
Place `app.py`, `environment.py`, `evidence.py`, `ai_providers.py` and
`requirements.txt` at the repository root. Upload extracted files, not the ZIP.

Use Google Gemini initially. Create a key at https://aistudio.google.com/apikey
and put it in Streamlit Secrets, using `secrets.example.toml` as the template.
The initial model is `gemini-3.5-flash-lite`; models and account access can change.
Use **AI team → Test AI connection** before submitting research data.

## Included tools

- Place/coordinate study setup, drawn reservoir polygons and sampling points.
- Public climate, weather, air-quality, river-outlook, earthquake-catalogue and
  biodiversity sources, with availability and retrieval dates shown.
- Sentinel-2 water indices, quality masks, maps and common-footprint comparisons.
- Research Excel/CSV uploads, explicit units, cleaning audit and field/satellite
  matching using locations, timestamps and clear-water pixel support.
- Landsat surface-temperature processing with quality screening. Live downloads
  still require verification from the deployed environment.
- Sentinel-1 catalogue footprints and metadata; no SAR classification engine.
- Pearson/Spearman, group-held-out regression/Gaussian GAM, PCA, Hellinger RDA,
  clustering, monthly seasonal decomposition and supplied-estimate validation.
- Phytoplankton community diversity, composition and environmental associations.
- Generic data exchange for WASP, AQUATOX, CE-QUAL-W2 and EcoDynamo. These solvers
  are not installed or executed by the application.
- Report/data/map exports; research bundles include processed snapshots, figures
  in PNG/SVG/PDF, statistical tables, methodology and executable offline replay.

Satellite indices are not measured chlorophyll, turbidity or confirmed
cyanobacterial blooms. Matchups and local calibration are necessary. The app
does not certify drinking-water safety, predict earthquakes/tornadoes or supply
validated flood-inundation forecasts. See METHODS.md and RESEARCH_METHODS.md.

## Five-agent workflow

`coordinator → climate_air → geospatial_water → ecology_field → reviewer_reporter`

These are five actual CrewAI agents. They use scoped evidence/statistics tools;
no extra manager agent is created. The review records tool activity, provider,
returned model IDs and request/token usage. LLM text is interpretation, not
independent scientific validation. Numerical analysis does not require AI.

The AI page supports Gemini, OpenRouter free models and Groq. Owner-enabled Ollama
is available for local/self-hosted use. See AI_PROVIDERS.md and LOCAL_OLLAMA.md.
Hosted free APIs have quotas. The app respects those limits and retains partial
notes when a provider stops a run. A completed identical review can be reused
without another model call. A fresh run is explicit.

## Local installation

In a terminal opened in this folder, with Python 3.12 installed:

```bash
python -m venv .venv
```

Activate it on Windows: `.venv\Scripts\activate`

Activate it on macOS/Linux: `source .venv/bin/activate`

Then:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Local keys may be stored in `.streamlit/secrets.toml` (ignored by Git). The example
file itself is not loaded as a secret. No real credentials are included here.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python tests/check_research_ui.py
```

Tests use labelled synthetic fixtures and mocked provider HTTP responses. They
do not prove live account access, map-tile rendering or environmental accuracy.
See VALIDATION.md for this release's verification and remaining limits.

Research data and reviews are session-based: download results before rebooting
or closing a session. This release is a research workbench, not persistent
multi-user project storage. Provider quotas and Streamlit memory/compute limits
still apply. Start with a small reservoir and short date range.

Copyright 2026 Mobeen Jamshed Khattak. See LICENSE.
