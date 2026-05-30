# Final report

> Summarize the completed project for instructors and future users. Update when you submit.

## Project summary

**Project**: Electrocatalysts for oxygen evolution reaction – experimental benchmark dataset  
**Authors**: Aleksei Suvorov (ITMO University)  
**Version**: 0.1.0  
**Date**: 2026-05-29  

## Dataset goal

The dataset supports comparison of OER electrocatalysts by capturing composition, electrolyte, testing conditions, and key performance metrics (overpotential at 10 mA cm⁻², Tafel slope, short‑term stability). It is intended for researchers and students who want to:

- Identify catalyst compositions and operating conditions associated with low overpotential and high durability.
- Build machine learning models that predict OER activity from elemental or structural features.
- Learn structured data extraction, schema design, and data‑cleaning pipelines on real electrochemical data.

## Source summary

The current release includes data from **3 primary research articles**, all listed in `specs/source_map.json` under the `scientific_papers` group:

| Source ID | DOI | Year | Catalyst types | Electrolyte |
|-----------|-----|------|----------------|-------------|
| paper_reier_2012 | 10.1021/cs3003098 | 2012 | Ru, Ir, Pt (bulk & nanoparticles) | 0.1 M HClO₄ |
| paper_mccrory_2015 | 10.1021/ja510442p | 2015 | 7 OER catalysts (Co‑based, Ni‑based, Ru, Ir) | 1 M H₂SO₄ and 1 M NaOH |
| paper_seitz_2016 | 10.1126/science.aaf5050 | 2016 | IrOₓ/SrIrO₃ thin film | 0.5 M H₂SO₄ |

All articles were accessed via institutional subscription or open‑access. No web scraping or database import has been performed yet. License of the dataset itself is CC‑BY‑4.0, but original articles may carry additional publisher terms.

## Extraction summary

### PDF extraction
Data were extracted with `scripts/extract_pdf.py`, which uses `pdfplumber` for text extraction and custom parsers for each source. The strategy per source:

- **Reier 2012**: Table 3 (potentials at 0.5 mA mol⁻¹ active sites, Tafel slopes, dissolution data). Output: 6 records (3 metals × 2 forms). Limitation: no η₁₀ available.
- **McCrory 2015**: Table 2 (benchmarking parameters for select OER catalysts). Regular‑expression parser that separates acidic and alkaline sections. Output: 14 records (7 catalysts × 2 electrolytes). Limitation: Tafel slopes not present in Table 2; they are available in the SI but have not yet been extracted.
- **Seitz 2016**: Main text and abstract (overpotential, Tafel slope, mass activity, stability). Output: 1 record. Limitation: only a single catalyst composition.

Total extracted records before cleaning: **22**.

### Web extraction
Data were extracted with `scripts/extract_web.py`. Used sources:

- **Catalysis-hub** - A web-platform for sharing data and software for computational catalysis research! The Surface Reactions database contains thousands of reaction energies and barriers from density functional theory (DFT) calculations on surface systems. Reactions can also be browsed under Contributors and Publications, and under Apps is a selection of computational tools.  

Total extracted records before cleaning: **1900**

Detailed reports for PDF and web extraction are available in Practice 3 and Practice 4 documents.

## Cleaning and normalization summary

The cleaning pipeline (`scripts/clean_dataset.py`) processes `data/interim/merged_records.csv` and writes the final dataset to `data/processed/dataset.csv`. Steps applied:

1. **Schema alignment**: column order and presence enforced according to `specs/dataset_schema.json`.
2. **Missing required fields**: rows missing values in any field marked `required` in the schema are dropped (e.g., `source_doi`, `catalyst_composition`, `metal_elements`, `primary_metal`, `electrolyte_type`, `electrolyte_composition`, `ir_compensation`, `potential_vs_RHE`). No rows were dropped in the current version (all records pass this check).
3. **String normalisation**: leading/trailing whitespace removed; common null tokens (`"na"`, `"-"`, etc.) replaced with `None`.
4. **Type coercion**:
   - Boolean fields (`is_noble_metal`, `is_hybrid`, `carbon_present`, `potential_vs_RHE`) are converted to `True`/`False`/`None`.
   - Numeric fields (`overpotential_eta10_mV`, `tafel_slope_mV_dec`, `stability_value`, `pH`, `temperature_C`) are cast to `float` where possible; non‑convertible values become `None`.
5. **Deduplication**: `record_id` is generated (if missing) from `source_doi` and `catalyst_composition`, and duplicate records are dropped.
6. **Output**: 19 cleaned records written to `data/processed/dataset.csv`. All web records was dropped (not enough information).

No unit normalization was required because all numerical values are already in the target units (mV for potentials, mV dec⁻¹ for Tafel slope, °C for temperature, etc.).

## Validation summary

The project is validated using `scripts/validate_project.py` and pytest tests in `tests/test_required_artifacts.py`. The checks confirm:

- Existence of all required files (CSV, schema, manifest, logs, etc.).
- Column names in `dataset.csv` exactly match the schema.
- No empty values in required fields.
- Numeric fields contain only valid float values or `None`.
- DOIs in the dataset are consistent with those listed in `specs/source_map.json`.

**Current status**: All checks pass with no errors. No outstanding warnings.

## Limitations

- **Source coverage**: Only three papers are included, covering a narrow range of catalyst classes (noble metals, a few Co/Ni oxides, one Ir‑based perovskite). Many important families (layered double hydroxides, phosphides, sulfides) and common electrolytes (KOH) are missing.
- **Missing fields**: Tafel slopes are absent for the McCrory 2015 data (they exist only in the Supporting Information). Catalyst loading is missing for most records.
- **Data density**: 19 records are insufficient for training complex machine learning models. The dataset is suitable for demonstration and prototyping.
- **Partial metrics**: Reier 2012 records lack η₁₀; they report potential at a fixed specific activity, which cannot be directly compared to the common benchmark.
- **Heuristic labelling**: Catalyst class and metal elements were inferred from catalyst names using simple rules. Some assignments (e.g., Co/P‑(a) → `other`) may be inaccurate.
- **No web data**: The dataset contains no information from public databases or community repositories.
- **License**: While the dataset itself is CC‑BY‑4.0, redistribution of extracted data from subscription‑only articles may be restricted. Verify before public release.

## Final artifacts

| Artifact | Path |
|----------|------|
| Processed dataset | `data/processed/dataset.csv` |
| Merged (pre‑cleaning) | `data/interim/merged_records.csv` |
| PDF‑extracted records | `data/extracted/pdf_extracted_records.csv` |
| Web‑extracted records | `data/extracted/web_extracted_records.csv` |
| Extraction log | `data/extracted/extraction_log.jsonl` |
| Schema | `specs/dataset_schema.json` |
| Source map | `specs/source_map.json` |
| PDF extraction manifest | `specs/pdf_extraction_manifest.json` |
| Project metadata | `project.json` |
| Dataset card | `dataset_card.md` |
| Citation | `CITATION.cff` |
| License | `LICENSE` |