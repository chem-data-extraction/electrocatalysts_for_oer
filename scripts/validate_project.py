#!/usr/bin/env python3
"""Validate repository artifacts against specs/validation_rules.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "project.json",
    "specs/dataset_schema.json",
    "specs/source_map.json",
    "specs/pdf_extraction_manifest.json",
    "specs/web_extraction_manifest.json",
    "specs/cleaning_pipeline.json",
    "specs/validation_rules.json",
    "data/extracted/pdf_extracted_records.csv",
    "data/extracted/web_extracted_records.csv",
    "data/processed/dataset.csv",
    "scripts/build_dataset.py",
    "scripts/clean_dataset.py",
]

CONFIDENCE_ALLOWED = {"", "high", "medium", "low", "unknown"}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def schema_field_names(schema: dict) -> list[str]:
    return [field["name"] for field in schema["fields"]]


def source_ids_from_map(source_map: dict) -> set[str]:
    ids: set[str] = set()
    for group_sources in source_map.get("source_groups", {}).values():
        for entry in group_sources:
            sid = entry.get("source_id")
            if sid:
                ids.add(sid)
    return ids


def check_required_files(root: Path = ROOT) -> list[str]:
    issues = []
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            issues.append(f"Missing required file: {rel}")
    return issues


def check_json_parseable(root: Path = ROOT) -> list[str]:
    issues = []
    for path in root.rglob("*.json"):
        if ".pytest_cache" in path.parts or "venv" in path.parts:
            continue
        try:
            load_json(path)
        except json.JSONDecodeError as exc:
            issues.append(f"Invalid JSON: {path.relative_to(root)} ({exc})")
    return issues


def load_dataset(root: Path = ROOT) -> pd.DataFrame:
    path = root / "data/processed/dataset.csv"
    return pd.read_csv(path)


def check_dataset_columns(df: pd.DataFrame, schema: dict) -> list[str]:
    expected = schema_field_names(schema)
    actual = list(df.columns)
    issues = []
    if actual != expected:
        issues.append(
            f"Dataset columns do not match schema. Expected {expected}, got {actual}"
        )
    return issues


def check_record_id(df: pd.DataFrame) -> list[str]:
    issues = []
    if df["record_id"].isna().any() or (df["record_id"].astype(str).str.strip() == "").any():
        issues.append("record_id contains null or empty values")
    if df["record_id"].duplicated().any():
        dupes = df.loc[df["record_id"].duplicated(), "record_id"].tolist()
        issues.append(f"Duplicate record_id values: {dupes}")
    return issues


def _collect_dois_from_source_map(source_map: dict) -> set[str]:
    """
    Извлекает все DOI из source_map.json.
    Обходит все группы (scientific_papers, databases и т.д.),
    собирает значения ключа 'doi' у каждой записи.
    """
    dois: set[str] = set()
    groups = source_map.get("source_groups", {})
    for group_name, entries in groups.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and "doi" in entry:
                doi = str(entry["doi"]).strip()
                if doi:
                    dois.add(doi)
    return dois


def check_source_doi(df: pd.DataFrame, source_map: dict) -> Tuple[List[str], List[str]]:
    """
    Проверяет столбец source_doi в DataFrame:
    - ошибки: отсутствие колонки, пустые значения
    - предупреждения: DOI отсутствует в source_map
    """
    errors: List[str] = []
    warnings: List[str] = []

    if "source_doi" not in df.columns:
        errors.append("Колонка 'source_doi' отсутствует в DataFrame")
        return errors, warnings

    # Проверка на пустые значения
    null_mask = df["source_doi"].isna() | (df["source_doi"].astype(str).str.strip() == "")
    if null_mask.any():
        bad_indices = sorted(df.index[null_mask].tolist())
        errors.append(f"source_doi содержит пустые значения в строках: {bad_indices}")

    # Сбор допустимых DOI из source_map
    valid_dois = _collect_dois_from_source_map(source_map)

    if not valid_dois:
        warnings.append("Не найдено ни одного DOI в source_map")
        return errors, warnings

    # Сравнение с DOI из датасета
    present_dois = set(df["source_doi"].dropna().astype(str).str.strip())
    unknown = present_dois - valid_dois
    if unknown:
        warnings.append(f"DOI не найдены в source_map: {sorted(unknown)}")

    return errors, warnings


def check_measurement_value(df: pd.DataFrame) -> list[str]:
    """
    Проверяет все колонки, объявленные в dataset_schema.json с типом 'number',
    на возможность приведения значения к float.
    Возвращает список строк с описанием проблем.
    """
    import json
    from pathlib import Path

    schema_path = Path(__file__).resolve().parents[1] / "specs/dataset_schema.json"
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    numeric_fields = [field["name"] for field in schema["fields"] if field["type"] == "number"]
    issues = []

    for col in numeric_fields:
        if col not in df.columns:
            continue
        for idx, val in df[col].items():
            if pd.isna(val) or val == "" or val is None:
                continue
            try:
                float(val)
            except (TypeError, ValueError):
                issues.append(f"{col} not numeric at row {idx}: {val!r}")

    return issues


def check_extraction_confidence(df: pd.DataFrame) -> list[str]:
    warnings = []
    if "extraction_confidence" not in df.columns:
        return warnings
    for val in df["extraction_confidence"].fillna("").astype(str):
        if val.lower() not in CONFIDENCE_ALLOWED and val not in CONFIDENCE_ALLOWED:
            warnings.append(f"Unexpected extraction_confidence: {val!r}")
            break
    return warnings


def validate(root: Path = ROOT) -> tuple[list[str], list[str]]:
    """Return (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(check_required_files(root))
    errors.extend(check_json_parseable(root))

    dataset_path = root / "data/processed/dataset.csv"
    if not dataset_path.is_file():
        return errors, warnings

    schema = load_json(root / "specs/dataset_schema.json")
    source_map = load_json(root / "specs/source_map.json")
    df = load_dataset(root)

    errors.extend(check_dataset_columns(df, schema))
    errors.extend(check_record_id(df))
    errors.extend(check_measurement_value(df))

    src_errors, src_warnings = check_source_doi(df, source_map)
    errors.extend(src_errors)
    warnings.extend(src_warnings)
    warnings.extend(check_extraction_confidence(df))

    return errors, warnings


def main() -> int:
    errors, warnings = validate()
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        print(f"\nValidation failed with {len(errors)} error(s).")
        return 1
    print("Validation passed.")
    if warnings:
        print(f"({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
