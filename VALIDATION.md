# Release verification — AquaTerra Research AI 1.0

Verified locally on Python 3.12 with the supplied dependency pins, 4 October 2026.

- **56 automated tests passed**: core data handling, geographic calculations,
  radiometry/nodata, quality checks, five-agent CrewAI execution, tool use,
  provider payloads, credential separation, quota-error handling, statistical
  calculations, satellite matchup logic and numerical export/replay.
- **22 Streamlit interface checks passed**: original application pages, all
  research sections and the statistical forms.
- The real CrewAI orchestration ran with mocked HTTP replies. The tests included
  five agent completions, actual scoped tool execution, partial-note preservation
  on errors and inclusion of a current review in the standard report.
- The research export test generated a ZIP containing processed satellite
  snapshots, GeoTIFF, PDF/SVG/PNG figures and analysis code, extracted it and ran
  `reproduce.py` in a subprocess. Recomputed values matched the synthetic fixture.
- No supplied image assets are bundled. Exactly five agent definition files
  are included. Source/configuration files parse successfully.

## What these checks do not establish

No real Gemini, OpenRouter or Ollama credentials/server were supplied. Their
request adapters were checked against official documentation and mocked provider
responses, not authenticated live generation. Use the in-app connection test
with your own account. Model availability, quotas, regional access, latency and
answer quality depend on the service and your account.

Live Landsat download access remains unverified. The previous connection check
failed; a trusted-CA configuration is included without disabling TLS checks.
No fresh live retrieval from every environmental provider or full Streamlit
Community Cloud deployment was performed for this package. Source outages,
cloud cover, resource limits or catalogue gaps may prevent a particular study.

Streamlit AppTest checks do not fully render third-party map widgets/map tiles
in a browser. Inspect the deployed maps with your own study boundary and dates.

Synthetic numerical tests do not validate a scientific study. Satellite
chlorophyll/turbidity proxies need local calibration and independent field
evaluation. Figures/exports alone do not guarantee publication suitability.

The release uses CrewAI's explicitly selected synchronous executor supported by
the pinned version. That executor has upstream deprecation warnings; keep the
pins and rerun tests when upgrading. `crewai_compat.py` addresses this version's
Python 3.12 warning-wrapper incompatibility so scientific PDF exports still work.
