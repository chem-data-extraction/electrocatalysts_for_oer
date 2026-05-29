# Dataset card — Electrocatalysts for Oxygen Evolution Reaction

## Dataset title

Electrocatalysts for Oxygen Evolution Reaction – experimental dataset (v0.1.0)

## Dataset summary

Tabular collection of experimentally reported composition, electrolyte, testing conditions, and performance metrics (overpotential, Tafel slope, stability) for inorganic or hybrid OER electrocatalysts tested under alkaline or acidic electrochemical conditions. The dataset is built from scientific publications and is intended to facilitate comparison and identification of catalyst features associated with low overpotential and high stability.

## Scientific task

Compare OER electrocatalysts and discover which compositions and testing conditions are associated with lower overpotential and better stability. The dataset can be used for exploratory analysis, machine learning model training, and systematic benchmarking.

## Record unit

One row = one experimentally reported measurement of OER catalytic performance for a specific catalyst in a given electrolyte and set of testing conditions, extracted from a single source.

## Data sources

Defined in `specs/source_map.json`. Currently the dataset is populated from three primary research articles:

- Reier et al. 2012 (ACS Catalysis, DOI: 10.1021/cs3003098) – Ru, Ir, Pt catalysts in 0.1 M HClO₄
- McCrory et al. 2015 (JACS, DOI: 10.1021/ja510442p) – 7 OER catalysts in 1 M H₂SO₄ and 1 M NaOH
- Seitz et al. 2016 (Science, DOI: 10.1126/science.aaf5050) – IrOₓ/SrIrO₃ in 0.5 M H₂SO₄

Supplementary materials and web sources are not yet extracted; placeholder files exist to accommodate future expansion (e.g., `web_extracted_records.csv` is currently empty).

## Data extraction procedure

1. **PDF extraction**: `scripts/extract_pdf.py` guided by `specs/pdf_extraction_manifest.json`. Data are extracted using `pdfplumber`, custom text parsers, and manual verification.
2. **Web extraction**: `scripts/extract_web.py` is prepared but has not been executed; the corresponding manifest and output file are placeholders for future use.
3. **Logs**: `data/extracted/extraction_log.jsonl` records timestamps, source identifiers, statuses, and record counts.

## Data cleaning and normalization

`scripts/build_dataset.py` merges PDF- and web-extracted records into `data/interim/merged_records.csv`.  
`scripts/clean_dataset.py` then:
- Removes rows where any field marked `required` in `specs/dataset_schema.json` is missing or empty.
- Normalises string fields (strips whitespace, replaces common missing-value tokens with `None`).
- Coerces numeric fields (`overpotential_eta10_mV`, `tafel_slope_mV_dec`, `stability_value`, `pH`, `temperature_C`) to float where possible; non-convertible values become `None`.
- Coerces boolean fields (`potential_vs_RHE`, `is_noble_metal`, `is_hybrid`, `carbon_present`).
- Generates or normalises `record_id` for deduplication; duplicates are dropped.

The cleaned dataset is written to `data/processed/dataset.csv`.

## Dataset schema

Field definitions, types, and constraints are maintained in `specs/dataset_schema.json`. The schema covers:
- Catalyst identification and composition (catalyst_composition, metal_elements, primary_metal, is_noble_metal, is_hybrid, carbon_present, support_substrate)
- Electrolyte and environment (electrolyte_type, electrolyte_composition, pH, temperature_C)
- Testing conditions (ir_compensation, potential_vs_RHE)
- Performance metrics (overpotential_eta10_mV, tafel_slope_mV_dec, stability_value)
- Provenance (source_doi, notes)

## Validation

Validation rules and checks are implemented in `scripts/validate_project.py` and `tests/test_required_artifacts.py`. They verify:
- Presence of required files (CSV outputs, schema, manifest, logs)
- Consistency of column names against the schema
- Non‑emptiness of mandatory fields
- Numeric fields contain valid float values
- DOI consistency with `specs/source_map.json`

## Known limitations

- **Limited source coverage**: The current release includes data from only three journal articles. Many catalyst classes and conditions are not yet represented (e.g., perovskites, LDH, phosphides in alkaline media).
- **Missing fields**: Tafel slopes and catalyst loading are absent for some records (e.g., McCrory 2015 main text lacks Tafel slopes; they are available in the SI but not yet extracted).
- **Manual labelling**: Catalyst class and metal elements were inferred using heuristics; some assignments may be approximate (e.g., Co/P‑(a) classified as “other” instead of “phosphide”).
- **Web data**: No data from public databases or community repositories has been integrated yet. The `web_extracted_records.csv` file is empty.
- **Data volume**: The current dataset contains 21 records, which is sufficient for demonstration but too small for training machine learning models without augmentation.

## Recommended use

- Comparing OER catalyst performance under standardised conditions.
- Teaching structured scientific data extraction, data cleaning, and schema design.
- Prototyping small‑scale ML pipelines (e.g., predicting overpotential from composition).
- Benchmarking parsing workflows on electrochemistry tables.

## Not recommended use

- Industrial catalyst selection or commercial decision‑making without independent validation.
- Meta‑analysis requiring statistical power (insufficient number of records).
- Any use that ignores the license terms of the original journal articles.

## License

This dataset is made available under the Creative Commons Attribution 4.0 International license (CC‑BY‑4.0). See `LICENSE` for the full legal text. Note that the underlying articles may be subject to additional publisher terms—verify redistributability before publication.

## Citation

Please reference this dataset using the information in `CITATION.cff`. Update the author list, version, and repository URL before releasing your own copy.