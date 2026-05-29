#!/usr/bin/env python3
"""Clean and normalize merged OER records into the final dataset.

Drops rows that miss any required field (as declared in
specs/dataset_schema.json).  Reads from interim/merged_records.csv
and writes the cleaned dataset to processed/dataset.csv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

MERGED_PATH = ROOT / "data/interim/merged_records.csv"
SCHEMA_PATH = ROOT / "specs/dataset_schema.json"
DATASET_PATH = ROOT / "data/processed/dataset.csv"

# Tokens that should be treated as missing values
MISSING_TOKENS = {"", "na", "n/a", "none", "null", "-", "nan"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_schema() -> dict:
    """Return the full schema dictionary."""
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def get_required_fields(schema: dict) -> list[str]:
    """List of field names that have 'required': true."""
    return [f["name"] for f in schema["fields"] if f.get("required", False)]


def is_missing(value: object) -> bool:
    """Return True if value is considered missing (NaN, None, or a token)."""
    if pd.isna(value):
        return True
    if isinstance(value, (int, float)):
        return False
    text = str(value).strip().lower()
    if text in MISSING_TOKENS:
        return True
    return text == ""


def normalize_string(value: object) -> str | None:
    """Return a stripped string or None if missing."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text.lower() in MISSING_TOKENS:
        return None
    return text


def coerce_boolean(value: object) -> bool | None:
    """Convert various representations to a boolean (True/False) or None."""
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "t"):
        return True
    if text in ("false", "0", "no", "f"):
        return False
    return None


def coerce_float(value: object) -> float | None:
    """Try to convert value to float, return None on failure."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# cleaning pipeline
# ---------------------------------------------------------------------------
def clean_dataframe(df: pd.DataFrame, required_fields: list[str]) -> pd.DataFrame:
    """
    Clean the merged DataFrame:
      1. Ensure a unique 'record_id' column exists.
      2. Drop rows where any required field is missing.
      3. Normalise data types and whitespace.
      4. Remove duplicate records based on 'record_id'.
    Returns a new DataFrame.
    """
    out = df.copy()

    # ---- step 1: drop records with missing required fields ----
    mask_valid = pd.Series(True, index=out.index)
    for field in required_fields:
        if field not in out.columns:
            mask_valid = False
            break
        missing_mask = out[field].apply(is_missing)
        mask_valid &= ~missing_mask
    out = out.loc[mask_valid].copy()

    if out.empty:
        return out

    # ---- step 2: string normalisation ----
    string_cols = ["source_doi", "catalyst_composition", "electrolyte_type",
                   "electrolyte_composition", "ir_compensation", "notes",
                   "support_substrate", "record_id", "primary_metal"]
    for col in string_cols:
        if col in out.columns:
            out[col] = out[col].map(normalize_string)

    if "metal_elements" in out.columns:
        out["metal_elements"] = out["metal_elements"].map(
            lambda x: normalize_string(x) if not isinstance(x, list) else str(x)
        )

    # ---- step 3: boolean & numeric coercions ----
    if "potential_vs_RHE" in out.columns:
        out["potential_vs_RHE"] = out["potential_vs_RHE"].map(coerce_boolean)

    for col in ("overpotential_eta10_mV", "tafel_slope_mV_dec",
                "stability_value", "pH", "temperature_C"):
        if col in out.columns:
            out[col] = out[col].map(coerce_float)

    for col in ("is_noble_metal", "is_hybrid", "carbon_present"):
        if col in out.columns:
            out[col] = out[col].map(coerce_boolean)

    # ---- step 4: deduplicate by record_id ----
    if "record_id" in out.columns:
        out = out.drop_duplicates(subset=["record_id"], keep="first")

    return out


# ---------------------------------------------------------------------------
def main() -> None:
    # load schema
    schema = load_schema()
    all_columns = [f["name"] for f in schema["fields"]]
    required_fields = get_required_fields(schema)

    # load merged data
    if not MERGED_PATH.is_file():
        print(f"ERROR: {MERGED_PATH} not found. Run build_dataset.py first.",
              file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(MERGED_PATH)

    # ensure all schema columns exist
    schema_cols = all_columns.copy()
    for col in schema_cols:
        if col not in df.columns:
            df[col] = None
    df = df[schema_cols]

    # clean
    cleaned = clean_dataframe(df, required_fields)

    # keep record_id in final output (even if not in schema, it's useful)
    if "record_id" not in cleaned.columns:
        cleaned["record_id"] = None

    # write final dataset
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(DATASET_PATH, index=False)
    print(f"Wrote {len(cleaned)} cleaned rows to {DATASET_PATH.relative_to(ROOT)}")
    print(f"Dropped {len(df) - len(cleaned)} rows due to missing required fields.")


if __name__ == "__main__":
    main()