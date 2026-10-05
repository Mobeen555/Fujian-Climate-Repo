# Research workspace: methods and interpretation

This extends METHODS.md for the water/field research tools. In the app, each
record shows its input data, settings, calculation, statistical results and
limitations. The optional single-model interpreter explains a bounded summary of recorded results.
It has no tools, cannot execute code or retrieve data, and does not provide independent scientific validation.

## Field records and spatial matching

CSV/XLSX column mapping and units require explicit confirmation. The audit
records excluded duplicate IDs, invalid coordinates/dates and invalid numeric
cells. Suspect outliers are flagged rather than silently removed. Missing values
are not imputed. Dates retain local-date/timezone information as well as UTC.
Date-only observations cannot pass a strict timed matchup without an explicit
exploratory date-only option.

Samples are matched to candidate scenes by location and acquisition time. The
user declares timing tolerance, pixel neighbourhood and clear-water fraction.
Cloud/quality masks, water pixels and shoreline screening can reject matches.
Sampling depths, laboratory methods and optical properties still require human
review. Samples sharing satellite support cannot be treated as independent
calibration and evaluation evidence.

Sentinel-2 uses surface-reflectance assets from Earth Search, a common projected
grid and metadata radiometry. NDCI is a red/red-edge index, not chlorophyll-a in
micrograms per litre. Red reflectance is not a calibrated turbidity measurement.
Atmospheric correction, sediment, bottom reflectance, adjacency effects and
sensor resolution can all affect interpretation. No universal bloom-probability
or toxin threshold is claimed.

Landsat temperature uses Collection 2 Level 2 surface-temperature and QA assets
from Planetary Computer. It screens cloud/fill/snow, saturation, water and
temperature uncertainty. The analysis grid is at least 120 m; resampled optical
pixel spacing does not imply equivalent thermal resolving power. Satellite skin
temperature may differ from a field measurement at depth. Live Landsat download
access is not verified for this release.

Sentinel-1 provides catalogue/footprint access only. Radar backscatter is not
converted into chlorophyll, turbidity, inundation depth or validated bloom maps.

## Statistical methods

- Correlation: Pearson or average-rank Spearman. Optional permutation tests and
  percentile bootstrap intervals require the user to declare independent rows.
  BH correction applies across the displayed tests. Repeated samples from a
  site/time sequence may violate this assumption.
- Regression: intercept plus least squares, or ridge-penalized additive cubic
  splines with a Gaussian response and identity link (GAM). Entire groups are
  held out before scaling/knots/model fitting. Report calibration and held-out
  RMSE, MAE, bias and predictive R-squared separately. Hyperparameter tuning on
  the held-out set would compromise its independence. This is not a universal
  published water-quality retrieval model.
- PCA: standardized numerical data, SVD, constant columns removed. Descriptive
  ordination, not proof of causal relationships.
- RDA: Hellinger-transformed community matrix constrained by environmental
  predictors, fitted with multivariate least squares/SVD. Unrestricted
  permutations are only appropriate for independent rows. A blocked sampling
  design needs a more appropriate analysis outside this implementation.
- Community indices: richness, natural-log Shannon, Simpson (1-D), Pielou
  evenness and dominance. Taxonomic resolution and abundance units must be
  comparable. Missing taxon records are not automatically interpreted as zeros.
- Clustering: average linkage with standardized Euclidean or Bray-Curtis
  distance, user-selected number of clusters and descriptive silhouette.
- Seasonality: classical additive monthly decomposition requires 24 consecutive
  observed months. No missing-month filling or forecasting; trend edges remain
  unavailable. Irregular ecological samples may not meet this design.
- Supplied-estimate agreement: compare matching physical units; a satellite
  index cannot be directly validated as a concentration by renaming its column.

Complete-case filtering, seeds, settings and sample sizes are recorded.
Statistical significance does not establish environmental causation, operational
alert validity or ecological safety.

## Reproduction and export

The research ZIP includes original uploads, cleaned inputs, statistical tables,
processed satellite arrays/masks, GeoTIFFs, figures, metadata, checksums, model
parameters and source code. `reproduce.py` reruns numerical analyses from frozen
processed snapshots with no AI key or network. It is not a complete replay from
raw satellite Level-1 data through atmospheric correction. AI wording may change
on another call, including with the same model ID. Report provider and returned
model IDs separately from deterministic scientific calculations.

Figures are available as 300 dpi PNG and vector SVG/PDF. Export resolution alone
does not make a study publication quality: methods, sampling design, calibration,
independent validation, uncertainty and journal-specific reporting need review.

External model exports are generic study-data exchanges, not ready-to-run WASP,
AQUATOX, CE-QUAL-W2 or EcoDynamo project files. Imported simulator outputs are
labelled external estimates; their calibration and solver execution are not
verified by this app.
