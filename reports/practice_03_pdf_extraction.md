# Practice 3 — PDF extraction

> Align with `specs/pdf_extraction_manifest.json` and `data/extracted/pdf_extracted_records.csv`.

## Selected PDF sources

| source_id | pdf_id | Year | Path |
|-----------|--------|------|------|
| paper_reier_2012 | reier2012 | 2012 | data/raw/pdf/reier2012.pdf |
| paper_mccrory_2015 | mccrory2015 | 2015 | data/raw/pdf/mccrory2015.pdf |
| paper_seitz_2016 | seitz2016 | 2016 | data/raw/pdf/seitz2016.pdf |

## Why these PDFs were selected

- **Reier et al. 2012** (ACS Catalysis) – provides quantitative OER data (potential at fixed specific activity, Tafel slopes, dissolution) for noble metals (Ru, Ir, Pt) in bulk and nanoparticulate forms in **acidic** electrolyte (0.1 M HClO₄). Fills a crucial gap for acidic OER with noble-metal catalysts.
- **McCrory et al. 2015** (JACS) – a widely cited benchmarking study with **26 OER catalysts** tested under standardized conditions in **both acidic (1 M H₂SO₄) and alkaline (1 M NaOH)** solutions. Supplies overpotential at 10 mA cm⁻², short-term stability (2 h and 24 h), roughness factor, and Faradaic efficiency – directly aligned with our schema. High data density from a single source.
- **Seitz et al. 2016** (Science) – reports a highly active and stable **IrOₓ/SrIrO₃ catalyst in 0.5 M H₂SO₄**. Offers complementary data for a perovskite-derived Ir-based catalyst in acidic medium, including overpotential, Tafel slope, mass activity, and 30 h stability.

All three are published as accessible PDFs (institutional or open access), contain numerical tables or text values, and together cover the alkaline/acidic and noble/non-noble catalyst spectrum required by the project.

## Pages used

### Reier 2012
- **Page 1**: abstract and introduction (metadata).
- **Pages 3–5**: Table 3 (potentials at 0.5 mA/mol active sites, Tafel slopes, dissolution data) and associated discussion. Extracted numerical data from Table 3 using regular expressions after copying text from these pages.

### McCrory 2015
- **Pages 4351–4352**: Table 2 “Relevant Benchmarking Parameters for Select HER and OER Catalysts”. This table contains OER performance data for 7 catalysts in 1 M H₂SO₄ and 7 catalysts in 1 M NaOH.
- **Pages 4348–4350**: Experimental section (used to confirm iR compensation, electrolyte concentration, temperature, electrode substrate).
- **Supporting Information (SI)**: not yet parsed, but Tables S3–S6 contain loading, Tafel slopes, and complete dataset for all 26 OER catalysts. Future extraction planned.

### Seitz 2016
- **Main paper pages 1–4**: abstract, main text (η₁₀ ≈ 270–290 mV, Tafel slope ~40 mV/dec, mass activity ~60 A/g, stability 30 h with Δη ≈ 10 mV). Data extracted via regex from text.
- **SI (separate PDF)**: Table S1 lists electrochemical parameters for different film thicknesses. Not yet parsed, but will be added later.

## Extraction methods

Three different extraction strategies were applied depending on the data format:

1. **Reier 2012** – custom Python parser using `pdfplumber` for text extraction and `re` module to locate Table 3 and parse semi‑structured rows. The table was not properly delimited by lines, so a hybrid approach with hard‑coded metal order and regular expression extraction of numeric values was used. This method was already functional and required no major modification.

2. **McCrory 2015** – initial attempts with `pdfplumber.extract_tables()` failed because Table 2 is not drawn with clear gridlines in the PDF. Switched to full‑text extraction with `pdfplumber`, then a regex‑based parser that identifies “Table 2” heading, determines the current electrolyte section (OERin1MH₂SO₄ / OERin1MNaOH), and extracts catalyst name, RF, η at 0 h, η at 2 h, η at 24 h, specific current density, and Faradaic efficiency from each line. Numeric values are split by whitespace and cleaned of footnote markers.

3. **Seitz 2016** – straightforward full‑text extraction with `pdfplumber`, followed by regex searches for overpotential and Tafel slope in the text. Since only one catalyst composition is studied, a single record is constructed with hard‑coded electrolyte, substrate, and stability parameters, supplemented by values extracted from the abstract and discussion.

All parsers were integrated into a unified driver (`extract_pdf.py`) that reads `specs/pdf_extraction_manifest.json`, dispatches to the appropriate function based on `source_id`, and outputs records conforming to `specs/dataset_schema.json`.

## Extracted fields

Mapping of PDF data to schema fields:

| Schema field | Reier 2012 source | McCrory 2015 source | Seitz 2016 source |
|--------------|-------------------|---------------------|-------------------|
| `source_doi` | DOI from footer | DOI from header | DOI from header |
| `catalyst_composition` | “{metal} bulk metal” or “{metal} nanoparticles on Vulcan XC 72R” | as given in Table 2 (e.g., “Co-(b)”, “NiFe-(b)”) | “IrOx/SrIrO3” |
| `metal_elements` | [metal] | inferred by `_guess_metals` | `["Ir","Sr"]` |
| `is_noble_metal` | True for Ru, Ir, Pt | True if Ir/Ru/Pt in name | True |
| `carbon_present` | True for nanoparticles (Vulcan carbon) | False (glassy carbon substrate not counted) | False |
| `support_substrate` | “glassy carbon” (stated in experimental) | “glassy carbon” (stated in experimental) | “Ti foil” (stated in experimental) |
| `electrolyte_composition` | “0.1 M HClO4” | “1 M H2SO4” or “1 M NaOH” depending on section | “0.5 M H2SO4” |
| `electrolyte_type` | “acidic” | “acidic” / “alkaline” | “acidic” |
| `overpotential_eta10_mV` | not available (reports potential at fixed specific activity) → stored in `potential_vs_RHE` and `notes` | η at t=0 (Table 2) | η ≈ 270 mV (regex from text) |
| `tafel_slope_mV_dec` | extracted from Table 3 | not in Table 2 (absent) | ~40 mV/dec (regex from text) |
| `stability_value` | dissolved metal string (e.g., “13.1 ± 0.2”) | (η₂ₕ − η₀) in mV | ~10 mV |

Manual corrections applied:
- For McCrory, overpotentials in Table 2 are given in V; multiplied by 1000 to convert to mV.
- Faradaic efficiency in McCrory is reported as a fraction; multiplied by 100.
- Catalyst names in McCrory are kept as in the paper; a heuristic attempts to classify them, but some may be ambiguous (e.g., “Co/P-(a)”). These are logged for manual review.

## Extraction problems

1. **McCrory 2015 – Table detection**: `pdfplumber` table extraction failed because Table 2 has no explicit grid lines. Solved by full‑text extraction and custom regex parser based on line structure. The parser depends on consistent formatting; any deviation in future PDFs would require adaptation.

2. **McCrory 2015 – missing Tafel slopes**: The main benchmarking table does not include Tafel slopes. They are available in the Supporting Information (Tables S3–S6) but have not yet been extracted. Currently these fields remain null; will be addressed in a subsequent extraction run.

3. **McCrory 2015 – heterogeneous catalyst naming**: Names like “Co-(b)”, “NiFe-(b)”, “Co/P-(a)” do not directly reveal composition or class. A rule‑based classifier (`_guess_class` and `_guess_metals`) was applied, but it may misclassify materials (e.g., “Co/P-(a)” is actually CoPi). Such records are flagged for manual verification.

4. **Reier 2012 – missing η₁₀**: The paper reports activity at a fixed specific current per active site (0.5 mA/mol), not per geometric area. Therefore `overpotential_eta10_mV` cannot be directly populated. The data is still valuable for Tafel slopes and relative comparisons, but will be excluded from analyses requiring η₁₀.

5. **Seitz 2016 – single record**: The main paper presents one catalyst composition. Additional data for various film thicknesses exists in the SI but has not yet been parsed. The current extraction yields only one record, limiting the dataset’s diversity from this source.

6. **iR compensation**: All three papers apply iR correction, but the exact percentage sometimes required careful reading (Reier states 95% in SI, McCrory 85% in Experimental, Seitz 100%). These values were hard‑coded based on manual verification.

## Output files

- `data/extracted/pdf_extracted_records.csv`: contains all extracted records from the three PDFs. Currently holds:
  - 6 records from Reier 2012 (3 metals × 2 forms)
  - 14 records from McCrory 2015 (7 catalysts in acid + 7 in base)
  - 1 record from Seitz 2016
- `data/extracted/extraction_log.jsonl`: JSON lines log with timestamp, source_id, status, and number of extracted records.
- Raw PDFs stored under `data/raw/pdf/`:
  - `reier2012.pdf`
  - `mccrory2015.pdf`
  - `seitz2016.pdf`