# Practice 1 — Record definition and dataset schema

> Replace template text with your project decisions. Keep this report aligned with `project.json` and `specs/dataset_schema.json`.

## Topic

Inorganic and hybrid electrocatalysts for the oxygen evolution reaction (OER) tested under alkaline or acidic electrochemical conditions.

## Scientific task

Collect experimentally reported composition, electrolyte, testing conditions, and performance metrics (overpotential, Tafel slope, stability) for inorganic or hybrid OER electrocatalysts, to enable comparison and identification of factors associated with low overpotential and high stability.

## One-record definition

**One record** = one experimentally reported measurement of OER catalytic performance for a specific catalyst in a given electrolyte and set of testing conditions, extracted from a single source (one row in `data/processed/dataset.csv`).

## Examples of records

| Example | Why it counts |
|---------|----------------|
| NiFe-LDH on Ni foam, 1 M KOH, 25 °C, η₁₀ = 240 mV, Tafel slope = 42 mV/dec, stability 24 h at 10 mA/cm² with Δη = +15 mV (from Fig. 3 and Table 1 of Smith 2022) | Single catalyst + defined electrolyte + performance metrics + source |
| IrO₂ nanoparticles on glassy carbon, 0.1 M HClO₄, 60 °C, η₁₀ = 290 mV, mass activity = 120 A/g at 1.53 V vs RHE (from Supplementary Table S2 of Lee 2021) | Measurement in acid, different substrate and metric, still one record |
| Co₃O₄/N-doped carbon hybrid, 0.1 M KOH, η₁₀ = 320 mV, Tafel slope = 75 mV/dec, stability 1000 CV cycles with 8 % current decay (from Fig. 5 of Gomez 2023) | Hybrid material, stability from CV cycling, still a single performance record |

## Non-record examples

| Example | Why it is not a record |
|---------|-------------------------|
| A review table summarising η₁₀ for ten catalysts without experimental details (no electrolyte, no temperature) | Incomplete testing conditions, cannot be assigned a reliable row |
| DFT-calculated overpotential for a hypothetical perovskite surface | No experimental measurement |
| A sentence “the catalyst showed excellent stability” without numeric time and degradation | No quantifiable stability metric |
| A figure showing LSV curves for three catalysts but without numeric η₁₀ values (only curve) | Not extracted as numeric record (unless digitised and clearly linked to sample ID) |
| A single publication reporting η₁₀ for the same catalyst in five different electrolytes | This yields five separate records, not one |

## Dataset fields

The dataset schema (see `specs/dataset_schema.json`) organises fields into five main entities:

- **Meta-data**
  `source_doi`

- **Catalyst identification and composition**  
  `catalyst_composition`, `metal_elements`, `primary_metal`, `is_noble_metal`, `is_hybrid`, `carbon_present`

- **Electrolyte and environment**  
  `pH`

- **Testing conditions**  
  `potential_vs_RHE`

- **Performance metrics**  
  `exchange_current_density_A_cm2`

All fields are documented in the schema with types, required/optional flags, and allowed values (enums). The mandatory fields for a valid record are: `source_doi`, `catalyst_composition`, `catalyst_class`, `electrolyte_type`, `electrolyte_composition`, `ir_compensation`, `potential_vs_RHE`, and `overpotential_eta10_mV`.

## Ambiguous cases

| Case | Decision |
|------|----------|
| **Multiple η₁₀ values for the same catalyst in one paper** (e.g. different electrolyte concentrations or temperatures) | **Separate records** – each distinct set of testing conditions yields its own row. The `catalyst_composition` and `sample_id_in_source` may repeat, but `electrolyte_composition` and `temperature_C` differ. |
| **Catalyst loading given as mass on electrode without geometric area** | If the geometric area of the electrode is clearly stated elsewhere (standard disk diameter), calculate `mg/cm²`. If area is unknown, store the raw mass in `notes` and leave `catalyst_loading_mg_per_cm2` empty. |
| **Stability reported as “no degradation after X hours”** | Set `stability_metric_type` = `"current_retention_percent"` and `stability_value` = 100 (or `overpotential_increase_mV` = 0). Add `stability_test_duration_h`. |
| **Stability measured by cyclic voltammetry (e.g. 1000 cycles)** | Convert to `stability_test_type` = `"cyclic voltammetry cycling"`. The duration in hours is not directly available – leave `stability_test_duration_h` empty and record the number of cycles in `notes`. Stability value can be current retention % after cycling if reported. |
| **Overpotential reported as a range (e.g. “η₁₀ = 280–300 mV”)** | Store the **midpoint** (290 mV) and record the range in `notes` as “original range 280–300 mV”. Alternatively, if the exact value from a curve can be extracted, use that. |
| **Tafel slope extracted from a figure with poor linearity** | Enter the value as given in the paper; if it is clearly ambiguous (two different slopes), create a note. No extrapolation by curators. |
| **The same catalyst appears in two different publications (duplicate)** | Both rows are kept initially. Deduplication rules (e.g. if identical composition and electrolyte) will be defined in Practice 5; we may keep the record with more complete testing conditions or average values after manual review. |
| **Paper reports performance only as overpotential at 50 mA/cm², not 10 mA/cm²** | `overpotential_eta10_mV` is mandatory – if absent, the record cannot be completed. We may note the available overpotential in `overpotential_at_other_current_density` and `current_density_for_overpotential_mA_cm2`, but the record will be flagged as incomplete. In the future we might relax the requirement if enough data exists at other current densities. |
| **Hybrid catalyst contains carbon in acidic electrolyte** | Record all fields as usual. The `carbon_present` flag will help later analysis to filter or study degradation due to carbon corrosion. If stability is poor, it will be reflected in `stability_value`. |
