# Practice 2 — Source map

> Document how you found sources and maintain `specs/source_map.json` as the machine-readable authority.

## Source search strategy

**Databases and search engines:**
- Scopus, Web of Science, Google Scholar (primary)
- arXiv, ChemRxiv (preprints, for early access)
- Publisher portals: ACS, RSC, Elsevier, Wiley, Springer

**Keywords and search strings:**
- Core: `"oxygen evolution reaction"` AND `electrocatalyst` AND (`overpotential` OR `Tafel slope`)
- Materials: `layered double hydroxide` OER, `perovskite` OER, `spinel` OER, `phosphide` OER, `IrO2` OER, `RuO2` OER, `non‑precious metal` OER
- Conditions: `alkaline` OER, `acidic` OER, `KOH` OER, `HClO4` OER
- Performance: `stability` OER, `chronopotentiometry` OER, `mass activity` OER
- Combined example: `"NiFe LDH" AND "1 M KOH" AND "overpotential"`

**Snowballing:**
- References from high‑impact reviews (e.g., *Chem. Soc. Rev.*, *Energy Environ. Sci.*, *Adv. Mater.*) and benchmarking studies.
- Citation tracking of seminal papers (e.g., the first report of a popular catalyst class).

**Inclusion criteria:**
- Experimental study (no purely computational papers).
- Inorganic or hybrid catalyst tested under alkaline (KOH/NaOH) or acidic (HClO₄/H₂SO₄) aqueous electrolyte.
- Reports at least an overpotential at a defined current density (preferably η at 10 mA cm⁻²).
- Provides enough metadata (electrolyte, catalyst composition) to build a complete record.

**Exclusion criteria:**
- Purely computational DFT studies without experimental validation.
- Photocatalytic or photoelectrochemical OER (different benchmarking).
- Solid‑oxide electrolysis cells (high temperature > 100 °C, molten salts) – out of scope.
- OER in organic solvents or non‑aqueous systems.

## Source groups

| Group | Description | Examples / Notes |
|-------|-------------|------------------|
| `scientific_papers` | Primary research articles with experimental OER data. | *J. Am. Chem. Soc.*, *ACS Catal.*, *Angew. Chem. Int. Ed.* |
| `review_papers` | Reviews and perspectives containing large comparison tables. | Used **only** to locate primary sources; data extracted directly from the original paper. |
| `supplementary_materials` | PDF or Excel files attached to primary papers. | Often contain the most complete tables of performance metrics. |
| `databases` | Public repositories with curated OER data. | *Catalysis‑Hub.org* (mainly DFT), *NREL MatDB* (limited OER), community‑driven datasets on GitHub (e.g., “OER‑data”). |
| `aggregators` | Websites that compile catalyst properties. | Not yet identified a reliable one; will be added if found. |
| `preprint_servers` | ChemRxiv, arXiv. | Used when final published version is behind paywall and author manuscript is not available. |

All sources are recorded in `specs/source_map.json` with a unique `source_id`, `type`, `doi`/`url`, `access_status`, and `priority`.

## Priority sources

We will extract sources in the following order:

1. **Primary research articles with tabulated performance data** (overpotential, Tafel slope, electrolyte, loading clearly given in a table). Highest reliability, lowest extraction effort.
2. **Benchmarking/comparative studies** (multiple catalysts measured under identical conditions). Provide many records from a single source and help standardise comparisons.
3. **Highly cited papers** that introduced a widely used catalyst (e.g., NiFe LDH, BSCF perovskite). They define baseline performance and are often referenced.
4. **Supplementary materials** of the above – if the main text lacks numeric η values but the SI contains tables, we extract from SI.
5. **Papers with only graphical data** – overpotential will be digitised from LSV curves using WebPlotDigitizer. Lower priority because of added uncertainty and manual effort.

## Access conditions

| Condition | Typical source | Handling |
|-----------|----------------|----------|
| Institutional subscription | Most journals (ACS, RSC, Wiley, etc.) | Download via university VPN; record `access_status: institutional`. |
| Open Access | *Nature Commun.* (OA articles), *Chem. Sci.*, many preprints | Direct download; `access_status: open_access`. |
| Paywall, no institutional access | Some older papers, small‑society journals | Try preprint server, ResearchGate, or inter‑library loan. If unobtainable, mark `access_status: restricted` and skip (with note). |
| Supplementary materials freely available | Most SI files accessible even if main paper is behind paywall. | Direct download; `access_method: direct_url`. |

All records in `source_map.json` will carry the fields `access_status`, `access_method`, and `access_date`.

## Expected data types

- **Structured tables (HTML/PDF text):** Numeric data for η, Tafel slope, electrolyte, loading. Copy‑paste or PDF text extraction (e.g., `tabula`).  
- **Excel/CSV supplementary files:** Directly importable.  
- **LSV curves (figures):** If no numeric η is reported, digitise the curve to obtain overpotential at 10, 100 mA cm⁻² and current density at 1.55 V vs RHE. Mark records with `digitized: true` in `notes`.  
- **Stability data:** Chronopotentiometric curves → digitise final overpotential or use reported Δη. Number of cycles from CV stability tests → store as string in `notes` and extract retention percentage if given.  
- **Material characterisation:** XRD, TEM, XPS – not directly extracted, but used to verify catalyst phase/identity if ambiguous.

## Expected conflicts and overlaps

**Multiple sources for the same catalyst:**
- A material may appear in several papers (e.g., “Ni₀.₈Fe₀.₂ LDH” tested by different groups). We keep all records as separate rows, because electrolyte purity, electrode preparation, and testing protocols differ.
- If two sources report the **identical catalyst batch** in the **same electrolyte** but give different η₁₀, we:
  - Prefer the original paper (first publication) unless a later work explicitly corrects an error.
  - Document the discrepancy in `notes` (e.g., “η₁₀ = 240 mV here, but Ref X reports 255 mV under identical conditions; possible difference in iR‑compensation”).

**Duplicates within a single paper:**
- If the same measurement appears in both a table and a figure, use the table value (less ambiguity).
- If only graphical data is available, digitise once and note the figure number.

**iR‑compensation differences:**
- Overpotential values are strongly affected by iR‑compensation. We record the `ir_compensation` field exactly (e.g., “100%”, “95%”, “none”). In later analysis, we will either filter by compensation level or treat it as a feature.

**Review paper tables:**
- We **do not** create records directly from review tables. The review is only a signpost; we locate the original article and extract data from it. If the original is inaccessible, we may store the data in a “secondary” flag and exclude from primary analysis.

## Coverage gaps

The following gaps are anticipated and will be monitored:

- **Acidic OER with non‑noble metals:** Very few stable catalysts exist; most data come from Ir‑ or Ru‑based materials. We will capture all available examples but expect sparse coverage.
- **Long‑term stability (> 100 h):** The majority of reports test stability for 10–24 h. Real‑world electrolysers require thousands of hours. We record any duration, but the dataset will be biased toward short‑term tests.
- **High‑temperature operation (60–80 °C):** Industrially relevant for PEM electrolysis, but most academic tests are at room temperature. We will tag temperature and note that the dataset predominantly reflects 20–25 °C.
- **Non‑standard electrolytes:** Seawater, 0.1 M PBS, or KOH with deliberate Fe additions are excluded for now to keep conditions comparable. This may be relaxed in later project phases.
- **Missing geometric area / loading:** Some papers do not report the exact electrode area or catalyst loading. Such records are omitted if critical fields are absent; otherwise we store `null` and flag incompleteness.
- **Faradaic efficiency:** Not always measured; we record it when available but do not require it for inclusion.

These gaps define the limitations of the final dataset and will be documented alongside any trained models. 
