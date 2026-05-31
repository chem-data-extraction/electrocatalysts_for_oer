# Practice 4 — Web extraction

> Align with `specs/web_extraction_manifest.json` and `data/extracted/web_extracted_records.csv`.

## Selected web sites

| source_id | page_id | URL |
|-----------|---------|-----|
| db_catalysis_hub | catalysis_hub_oer | https://api.catalysis-hub.org/graphql |

## Why these sites were selected

- **Catalysis-Hub** provides structured catalytic reaction data via a GraphQL API.
- Potentially contains experimental data for the oxygen evolution reaction (OER) needed for our dataset.
- Open license for academic use; updates are community-driven.
- API allows bulk data retrieval without HTML parsing.

## Page structure

The site does not provide a traditional HTML page for scraping. Instead, it exposes a **GraphQL API** at: https://api.catalysis-hub.org/graphql

Responses are JSON following the Relay Connection Specification:
```json
{
  "data": {
    "reactions": {
      "edges": [{ "node": { "id", "Equation", ... } }],
      "pageInfo": { "hasNextPage", "endCursor" }
    }
  }
}
```

## Extraction methods
- **Tools**: `requests`, `pandas`, built‑in JSON processing.

- **Queries**: GraphQL with cursor‑based pagination (`after`, `first`).

- **Selectors**: defined in the `parser_plan` of the manifest (method `graphql`).

- **Rate limiting**: a 0.5 s delay added between pagination requests to be respectful.

- **robots.txt**: not applicable for an API endpoint, but general courtesies are observed (User‑Agent set).

## Extracted fields
| DOM / JSON path |	Dataset field |	Notes |
|-----------------|---------------|-------|
| node.Equation |	(used for filtering) |	Contains the chemical equation of the reaction |
| node.reactants |	catalyst_composition |	Extracted as a string or the name field of an object |
| node.publication.doi	| source_doi	| DOI of the source publication |
| node.id |	notes	| Added to notes as the record identifier |  

**All other fields** (e.g., `overpotential_eta10_mV`, `electrolyte_type`) are absent from Catalysis‑Hub and are set to `None` or default values. **That says that we can't use this data for dataset**

## Extraction problems
1. **Schema mismatch**

   - Fields such as `overpotential`, `tafel_slope`, `electrolyte`, `pH`, `temperature` do not exist in the API (the database is designed for DFT calculations, not experimental electrochemical data).

   - Consequently, records obtained from Catalysis‑Hub contain only catalyst composition and DOI.

2. **No OER reactions found**

   - After fetching 4000 reactions, none contained equations with `O2`, `H2O`, or `OH‑` characteristic of OER. All reactions were related to hydrogen adsorption/dissociation (HER).

   - This means **this source is unsuitable for building an OER dataset.**

3. **GraphQL peculiarities**

   - The API requires exact field names (case‑sensitive: `Equation` vs `equation`).

   - Pagination uses `edges { node }`, not `nodes`.

   - Arguments `experimental` or `filter` are not supported.

4. **Dynamic content** – not applicable because this is a REST‑like API without JavaScript.

## Output files
`data/extracted/web_extracted_records.csv` – contains 1900 OER records.

`data/raw/web/catalysis_hub_snapshot.json` – raw JSON response from the API.

`data/extracted/extraction_log.jsonl` – log entries with the step web_extraction, status success or failed on errors.