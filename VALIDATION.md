# Release validation — HydroScope Water Research 1.0.0

Date: 2026-10-05. Target runtime: Python 3.12. Tests use synthetic fixtures, clearly confined to `tests/`; the deployed app never substitutes them for provider or field data.

## Completed checks

- 33 distinct automated regression checks passed across the final core/research and water-specific test runs (20 retained core/research checks, 13 water-specific checks).
- 28 Streamlit AppTest workflow checks passed: all seven pages, research subsections, statistical forms, recorded correlation, site/month summaries, measured trophic indicators, the interpreter form, complete PDF/HTML/Excel/research-ZIP generation, different waterbody types and field-only marine study creation.
- Python syntax validation and source import scan found no CrewAI/agent imports. The new package has no agent folder or CrewAI dependency.
- Numerical checks cover geodesic area, invalid geometry, reflectance masks/scaling, formula-safe exports, field cleaning/duplicate/coordinate/date flags, Pearson/Spearman/BH, grouped linear/additive regression, PCA, RDA, clustering, seasonality/gap rejection and same-unit agreement.
- Saved-window satellite matchups and numerical analyses were replayed offline from exported snapshots. New measured trophic and water-summary calculations were also exported and independently rerun by `reproduce.py`.
- Water-only checks cover module availability, absence of fabricated fallback data, Carlson restrictions/positive-input handling, salinity/conductivity validation, marine missingness/units, and river history failures preserving separately available outlook data.
- Mocked AI checks verify one HTTP request, no tools, no retry on quota errors, source-ID rejection, JSON-safe evidence, absence of credentials in saved provenance and invalidation when measurements change.
- Maps tolerate missing field coordinates. Report ZIP/PDF generation and rejection of stale AI interpretation were tested. Scientific PNG exports use 300 dpi; detailed research figures also include SVG/PDF.

## Live integration checks and remaining limits

A direct live Open-Meteo river request at a test coordinate returned HTTP 200 with daily discharge and quartile units after using the provider's supported `models=seamless_v4` identifier. This confirms a sample request, not global river accuracy or successful historical retrieval for every date/location.

Live marine requests timed out from this execution environment. The adapter's variables and parameters were checked against the provider's official OpenAPI specification; parsing, units, missing values and failure handling were checked with fixtures. Marine retrieval must be confirmed after deployment at a supported sea coordinate. A timeout is displayed as unavailable, not replaced with invented results.

No real LLM API credential was supplied; a live provider interpretation was not tested. Sentinel/Landsat live scene retrieval was not revalidated during this release. The source preserves the bounded adapters and CA-trust handling from the previous research workbench; coverage/clouds/permissions/provider availability can still prevent a retrieval. Landsat download access is not claimed verified.

The supplied deployed Streamlit URL could not be inspected through the available page reader. This project was built from the latest saved working source, not by extracting code from the live website. No files were pushed to GitHub and no cloud deployment was changed.

AppTest verifies Streamlit rendering/control execution, not pixel-perfect visual appearance on every browser or phone. End-to-end Streamlit Community Cloud deployment has not been performed for this ZIP. Data accuracy, local water-quality calibration, community taxonomic identification, laboratory QA and publication suitability require independent scientific evaluation.

## Repeat the offline checks

From this project's root with Python 3.12:

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest tests -q
python tests/check_ui.py
```

The numerical tests do not require API keys or live provider availability. They validate implementation on controlled fixtures, not a scientific model's suitability for a particular waterbody. Rasterio/affine may emit non-failing upstream deprecation warnings.
