#!/usr/bin/env python3
"""Merge extracted CSVs and write interim and processed datasets for OER project."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

PDF_CSV = ROOT / "data/extracted/pdf_extracted_records.csv"
WEB_CSV = ROOT / "data/extracted/web_extracted_records.csv"
SCHEMA_PATH = ROOT / "specs/dataset_schema.json"
MERGED_PATH = ROOT / "data/interim/merged_records.csv"
DATASET_PATH = ROOT / "data/processed/dataset.csv"


def load_schema_columns() -> list[str]:
    """Return list of field names from the dataset schema."""
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)
    return [field["name"] for field in schema["fields"]]


def safe_read_csv(path: Path, fallback_columns: list[str]) -> pd.DataFrame:
    """
    Read a CSV file, returning an empty DataFrame with the given columns
    if the file is missing, empty, or otherwise unreadable.
    """
    if not path.exists():
        print(f"File not found: {path} – using empty DataFrame", file=sys.stderr)
        return pd.DataFrame(columns=fallback_columns)
    try:
        df = pd.read_csv(path)
        if df.empty:
            print(f"File is empty: {path} – using empty DataFrame", file=sys.stderr)
            return pd.DataFrame(columns=fallback_columns)
        return df
    except Exception as exc:
        print(f"Error reading {path}: {exc} – using empty DataFrame", file=sys.stderr)
        return pd.DataFrame(columns=fallback_columns)


def map_record(row: pd.Series, schema_columns: list[str], source_type: str) -> dict:
    """
    Extract only the fields defined in the schema from an input row.
    Missing keys are filled with None.
    The 'source_type' is stored in a temporary column (will be dropped later if needed).
    """
    record = {}
    for col in schema_columns:
        record[col] = row.get(col, None)
    # Optional: keep track of where the record came from
    record["extraction_source"] = source_type
    return record


def build() -> pd.DataFrame:
    # Load the official set of columns for the final dataset
    schema_cols = load_schema_columns()

    # Read PDF‑extracted records (must exist)
    if not PDF_CSV.exists():
        raise FileNotFoundError(f"Required PDF CSV not found: {PDF_CSV}")
    pdf_df = pd.read_csv(PDF_CSV)

    # Read web‑extracted records (may be empty or non‑existent)
    web_df = safe_read_csv(WEB_CSV, fallback_columns=schema_cols)

    # Map each row to a dictionary containing only schema fields + source flag
    pdf_records = [map_record(row, schema_cols, "pdf") for _, row in pdf_df.iterrows()]
    web_records = [map_record(row, schema_cols, "web") for _, row in web_df.iterrows()]

    # Combine all records
    all_records = pdf_records + web_records

    # Create a DataFrame with schema columns (plus optionally the source column)
    merged = pd.DataFrame(all_records)
    # Ensure columns are in the exact order of the schema (drop any extra columns)
    final_columns = schema_cols + ["extraction_source"] if "extraction_source" in merged.columns else schema_cols
    merged = merged[final_columns]

    # Generate a simple unique id using DOI and catalyst composition
    def make_id(row):
        doi = str(row.get("source_doi", "")).strip()
        comp = str(row.get("catalyst_composition", "")).strip()
        # Fallback to row number if both empty
        base = f"{doi}_{comp}" if doi or comp else f"row_{row.name}"
        return base
    merged["record_id"] = merged.apply(make_id, axis=1)
    # Ensure uniqueness by appending index to duplicates
    dup_mask = merged["record_id"].duplicated()
    merged.loc[dup_mask, "record_id"] = merged.loc[dup_mask, "record_id"] + "_" + merged.loc[dup_mask].index.astype(str)
    print("Generated 'record_id' column because it was missing.")

    return merged


def main() -> None:
    MERGED_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        df = build()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Write full merged set (includes 'extraction_source' for traceability)
    df.to_csv(MERGED_PATH, index=False)

    print(f"Wrote {len(df)} rows to {MERGED_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()