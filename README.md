# HydroScope Water Research

A separate water-only Streamlit project for rivers, lakes, reservoirs and sea/coastal study areas. Python **3.12**. Entry point **app.py**.

**Start here: [UPDATE_SAME_GITHUB_REPO.md](UPDATE_SAME_GITHUB_REPO.md).** This replaces the old app's files while keeping the existing repository and Streamlit link. For a second independent deployment, use [DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md).

## What changed

- Removed CrewAI, all agents, agent files and agent dependencies.
- Removed general climate, air quality, earthquake, tornado, terrestrial biodiversity and weather-alert modules.
- Kept one optional AI results interpreter: a single request explaining already-computed evidence. No autonomous retrieval, calculations, tools, delegation or framework loop.
- Added explicit River / Lake / Reservoir / Sea or coastal study types and a marine model outlook.
- Added salinity and conductivity field columns, recorded site/month water summaries and explicitly gated measured Carlson trophic indices for appropriate freshwater lakes/reservoirs.
- No decorative images, picture frames or custom icons. Scientific maps and figures remain.

## Water workflows

| Capability | Actual implementation |
|---|---|
| Study area | Place search, coordinates, drawn/uploaded WGS84 polygon; sampling points |
| Optical satellites | Sentinel-2 L2A water mask, NDWI/MNDWI, NDCI and red reflectance, common-footprint comparisons and candidate sampling points |
| Thermal satellite | Landsat Collection 2 L2 surface-temperature/QA extraction and field matchups |
| Radar | Sentinel-1 scene catalogue/footprints only; no radar-derived water quality |
| Original measurements | XLSX/CSV mapping, units confirmation, local dates/timezones, row audit, duplicates, missingness and outlier flags |
| Water quality | Measured chlorophyll-a, turbidity, transparency/Secchi, temperature, nutrients, dissolved oxygen, pH, phycocyanin, cyanobacteria cells, salinity and conductivity |
| Validation | Coordinate/date/time matchups, water/cloud/shoreline screens, regression with whole-group held-out evaluation, same-unit agreement metrics |
| Statistics | Pearson/Spearman, permutation/bootstrap if independence declared, linear/Gaussian additive regression, PCA, RDA, clustering, monthly seasonal decomposition |
| Phytoplankton | Species/genus abundance, Shannon/Simpson/Pielou/richness, community composition and nutrient/environment associations |
| River | GloFAS modelled history plus seven-day discharge outlook, separately labelled |
| Sea/coastal waters | Modelled sea-surface temperature, significant wave height, currents and sea level; seven-day outlook |
| External models | Study-data exchange and imported outputs for WASP, AQUATOX, CE-QUAL-W2 and EcoDynamo; solvers do not execute in the app |
| Exports | PDF/HTML reports, Excel/CSV, PNG scientific figures, GeoJSON/GeoTIFF, and research ZIP with 300 dpi/vector figures, code, hashes and offline replay |

**Optical indices are not measured concentrations.** NDCI is not chlorophyll µg/L; red reflectance is not turbidity NTU. A local fitted model needs independent field validation. No verified cyanobacterial bloom/toxin classifier or universal water-safety score is supplied. Offshore ocean-colour products such as Sentinel-3 chlorophyll are not integrated. Sea support is a local coastal/field and marine-model workflow, not a global ocean biogeochemistry system.

## First use

1. Open **Water study**, select the waterbody type and coordinates/dates. Inspect/draw the boundary.
2. Select optional water sources, or leave the list empty to use your field dataset only. Click **Save water study and run selected analyses**.
3. In **Water research → Field data**, download the template, upload CSV/XLSX, map columns, confirm units and attach data.
4. Record **site and monthly summaries**. For appropriate freshwater lakes/reservoirs, explicitly confirm applicability before calculating measured Carlson indices.
5. Use **Satellite matchups**, **Statistics** and **Phytoplankton** as appropriate. Inspect the recorded methods and limitations.
6. Optionally open **AI interpretation**, select a provider, inspect the evidence summary and request one explanation. AI is not required for any other feature.
7. Open **Reports & sources → Build complete water report package**. Research replay files are inside `research_reproducibility.zip` within the full report ZIP. Download before ending the session.

## Local run

```bash
python -m venv .venv
```

Activate on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Activate on macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Use Python 3.12. No Supabase, Vercel, Node.js or CrewAI configuration is needed. Set optional AI credentials in `.streamlit/secrets.toml` locally, or Streamlit Cloud Secrets. Never commit real credentials. Provider keys remain optional.

## Source files

| File | Purpose |
|---|---|
| app.py | Streamlit interface and inspectable research calculations/replay export |
| environment.py | Geometry, optical retrieval, map/chart rendering and reports |
| water_data.py | Waterbody scope plus river/marine adapters |
| evidence.py | Quality checks and evidence fingerprints |
| interpretation.py | One optional LLM request, bounded evidence packet and stale-result checks |
| ai_providers.py | Provider metadata and endpoint validation |
| requirements.txt | Pinned deployment dependencies, without CrewAI |
| .streamlit/config.toml | Accessible dark water-themed UI settings |
| tests/ | Synthetic offline checks; never used as research data in the running app |
| examples/ | Blank CSV templates; also downloadable as XLSX inside the app |

## Limits and operational notes

Satellite processing is restricted to local areas up to 250 km², a bounded pixel count and a limited number of scenes; no promise of gap-free time series. Waterbody names do not select whole rivers or ocean basins. Forecasts represent nearby model cells, not polygon means. Models, satellite observations and field samples are separate evidence types. Marine model output is not suitable for navigation; river output is not a validated flood-warning system.

Uploaded data stays in application session memory unless you download it. Public provider responses are cached; API quotas/service terms apply. Map/place search uses OpenStreetMap/Nominatim. Only the displayed evidence summary is submitted to the selected AI provider after an explicit click. Public apps using owner-provided AI keys share that account's quota; provider quotas are never bypassed.

Read [METHODS.md](METHODS.md), [RESEARCH_METHODS.md](RESEARCH_METHODS.md), [AI_PROVIDERS.md](AI_PROVIDERS.md) and [VALIDATION.md](VALIDATION.md). This is a research workbench, not an independently validated regulatory assessment or automatic publication-quality guarantee.
