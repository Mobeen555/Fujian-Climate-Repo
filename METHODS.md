# Water data, methods and boundaries of inference

HydroScope 1.0.0 (2026-10-05) separates **field measurements**, **satellite screening indices**, **calculated statistics** and **model estimates**. A single optional AI explanation is downstream of these results. Source IDs, retrieval timestamps, periods, grids and processing settings are retained. Missing retrievals are shown as unavailable, with no simulated substitute.

## Geography and waterbody type

A geocoded name gives a reference point. Users must verify coordinates and select/draw a local WGS84 polygon. Areas use ellipsoidal geodesic calculations. Selected boundaries are not whole river basins or automatically delineated water surfaces. Forecast requests use the study centroid's nearby provider cell; returned coordinates appear in source records. Samples with invalid coordinates cannot enter spatial matching; samples without coordinates can still be used in explicitly nonspatial statistics.

Waterbody type controls the available adapters. River discharge is offered only for River studies. Marine output is offered only for Sea / coastal waters. Lake/reservoir studies use field and satellite analysis; the app does not fabricate lake outflow, bathymetry, storage or water balance.

## Sentinel-2 optical water screening

Earth Search collection `sentinel-2-c1-l2a`; STAC catalogue IDs/times and asset radiometry are retained. Bounded cloud-filtered scene candidates are searched, and a limited number are processed. This is not a complete annual/monthly census. Common projected grids use bilinear reflectance and nearest-neighbour scene classification. Raster scaling/offset are taken from metadata; fill and nonphysical reflectance are masked.

Supported clear classes are SCL 4/5/6. Water additionally requires SCL 6, NDVI below 0.3 and either NDWI or MNDWI above the selected threshold. NDVI is an internal vegetation-exclusion screen, not a terrestrial-analysis page or exported vegetation product. The conservative water mask can reject turbid, shallow, shoreline or bloom-covered pixels; no detection does not prove no water or no bloom.

- NDWI = (green − NIR) / (green + NIR).
- MNDWI = (green − SWIR) / (green + SWIR).
- NDCI = (red edge − red) / (red edge + red), on screened water only.
- Water red reflectance is retained as a scattering/turbidity-related screening variable, not a concentration in NTU.

No global chlorophyll calibration, turbidity equation, cyanobacterial classifier or toxin model is assumed. Atmospheric correction, clouds, bottom reflectance/depth, suspended sediment, adjacency, reservoir optical properties and sensor support affect estimates. Relative high-index sampling candidates are suggestions for validation, not confirmed blooms. The first/last water-area comparison uses a shared valid footprint; per-scene water areas have different clear footprints and should not be compared as if coverage were constant.

## Landsat temperature and Sentinel-1

Research matchups include Landsat Collection 2 L2 surface-temperature assets and QA via Planetary Computer. Water/clear/saturation/uncertainty checks are applied; the common analysis grid is at least 120 m. Satellite skin temperature and in-water temperature at depth differ. Read RESEARCH_METHODS.md for matching tolerances and limits. Sentinel-1 integration is scene discovery only, not a radar-to-chlorophyll retrieval or flood-depth solver.

## Measured water quality and trophic indicators

Upload XLSX/CSV, map columns and confirm units. No silent unit conversion, outlier deletion, imputation or calibration is performed. Salinity uses the common PSU notation for practical salinity; conductivity uses µS/cm and its temperature/reference convention must be documented by the researcher. Compare like laboratory methods and depths.

Site/month summaries use actual included samples, with count, mean, median, standard deviation and extrema where defined. Missing months stay missing. Unequal site sampling does not become an area average. Field bubble maps are sampled points with capped display sizes, not interpolated water-quality maps.

Only explicitly confirmed freshwater Lake/Reservoir studies enable separate measured Carlson trophic indicators:

- Chlorophyll: 9.81 × ln(chlorophyll-a µg/L) + 30.6.
- Secchi: 60 − 14.41 × ln(Secchi depth m).
- Total phosphorus: 14.42 × ln(total phosphorus µg/L) + 4.15.

Positive inputs are required. The app never averages these indices. Applicability is user-confirmed; river, coastal/marine, saline or sediment-dominated conditions may make these relationships unsuitable. Neither these indices nor phytoplankton abundance establish toxicity or safe water use.

## River and marine models

River requests use the Open-Meteo Flood API with explicit GloFAS v4 seamless selection. Historical daily model values and the present seven-day forecast are separate tables. The seamless archive combines reanalysis/archived forecasts and is not a homogeneous gauge record. Approximate 5 km grid support can select the wrong river. Model version is requested; underlying issue time is not fully echoed. Ensemble quartiles show spread, not calibrated confidence. A user threshold is an unvalidated screen, not flood depth/inundation or an official warning.

Marine requests use the Open-Meteo Marine API, sea-cell selection, UTC and seven days from the current day. Variables are sea-surface temperature, significant wave height/period, current speed/direction and sea level relative to global mean sea level. Native grid/time support varies; hourly API output can be interpolated from coarser model steps. Source/returned-unit tables and missing-variable notes are retained. Coastal/estuarine and inland support may be poor. These are model forecasts, not remote-sensing measurements, ocean chemistry or safe-navigation instructions. Wave height is significant wave height, not the maximum individual wave. No offshore ocean-colour concentration product is integrated.

## Statistics and research reproducibility

RESEARCH_METHODS.md documents the numerical methods and assumptions. Independent samples are required before enabling unrestricted permutation/bootstrap inference. Grouped held-out validation is separate from calibration. Time series may be autocorrelated; multiple observations of the same satellite pixel must not leak across training and validation. Figures alone do not establish publication validity.

The detailed research package preserves input snapshots, source/scene metadata, processed windows, masks, settings, code, seeds and SHA256 file hashes. `reproduce.py` checks hashes and reruns numerical analyses and saved-window satellite matching without network or AI. This is not a full Level-1 atmospheric-processing replay. Imported external model outputs remain imported estimates, not rerun simulations. Download files before the Streamlit session ends.

## Sources and attribution

- [Copernicus Sentinel-2](https://sentiwiki.copernicus.eu/web/s2-products) / [Earth Search](https://github.com/Element84/earth-search).
- Mishra & Mishra (2012), NDCI: https://doi.org/10.1016/j.rse.2011.10.016. Implementing an index does not establish local calibration transferability.
- [USGS Landsat surface temperature](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature) and [QA bands](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands).
- [NALMS Carlson trophic equations](https://www.nalms.org/secchidipin/monitoring-methods/trophic-state-equations/).
- [Open-Meteo river model documentation](https://open-meteo.com/en/docs/flood-api), attribution to Open-Meteo/Copernicus Emergency Management Service/GloFAS.
- [Open-Meteo marine documentation](https://open-meteo.com/en/docs/marine-weather-api), attribution to Open-Meteo and upstream providers including DWD, Météo-France and Copernicus Marine as applicable.
- [Open-Meteo terms](https://open-meteo.com/en/terms) and [access limits](https://open-meteo.com/en/pricing). Free hosted API use is subject to noncommercial restrictions/quotas; source licences and attribution still apply.
- [OpenStreetMap attribution](https://www.openstreetmap.org/copyright) and [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/). Searches are explicit, cached and throttled within this app process. Multiple replicas need coordinated compliance.
- [RDA methodology reference](https://vegandevs.github.io/vegan/reference/cca.html) and [classical seasonal decomposition](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.seasonal_decompose.html).

Parameter-contract references used for this release:

- https://github.com/open-meteo/open-meteo/blob/main/openapi/flood.yml (`models=seamless_v4`).
- https://github.com/open-meteo/open-meteo/blob/main/openapi/marine.yml (`wind_speed_unit=kmh`, `temperature_unit=celsius`, `length_unit=metric`).
