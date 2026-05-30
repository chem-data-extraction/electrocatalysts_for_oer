#!/usr/bin/env python3
"""
Extract OER experimental data from Catalysis-Hub GraphQL API.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import requests

# ----------------------------------------------------------------------
# Constants and configuration
# ----------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "specs/web_extraction_manifest.json"
LOG_PATH = ROOT / "data/extracted/extraction_log.jsonl"

NON_METALS = {
    "H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "Se", "Br", "I",
    "At", "He", "Ne", "Ar", "Kr", "Xe", "Rn"
}
NOBLE_METALS = {"Ir", "Ru", "Pt", "Au", "Ag", "Pd", "Rh", "Os"}

ACIDIC_PATTERNS = ["H2SO4", "HClO4", "HNO3", "H3PO4", "HCl"]
ALKALINE_PATTERNS = ["KOH", "NaOH", "LiOH", "Ba(OH)2"]

OUTPUT_COLUMNS = [
    "source_doi",
    "catalyst_composition",
    "metal_elements",
    "primary_metal",
    "is_noble_metal",
    "is_hybrid",
    "carbon_present",
    "support_substrate",
    "electrolyte_type",
    "electrolyte_composition",
    "pH",
    "temperature_C",
    "ir_compensation",
    "potential_vs_RHE",
    "overpotential_eta10_mV",
    "tafel_slope_mV_dec",
    "stability_value",
    "notes",
]

# ----------------------------------------------------------------------
def append_log(entry: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# ----------------------------------------------------------------------
def extract_metal_symbols(composition: str) -> List[str]:
    """Extract unique metal symbols from composition string."""
    if not composition or not isinstance(composition, str):
        return []
    found = re.findall(r"([A-Z][a-z]?)", composition)
    metals = []
    for elem in found:
        if elem not in NON_METALS and elem not in metals:
            metals.append(elem)
    return metals


def find_primary_metal(formula: str, metal_elements: list) -> Optional[str]:
    """
    Определяет приоритетный металл в формуле по количеству атомов.
    
    Если несколько металлов имеют одинаковое максимальное количество атомов,
    возвращается None.
    
    :param formula: Химическая формула (например, "NiFeCo3O4")
    :param metal_elements: Список металлов в формуле (например, ["Ni", "Fe", "Co"])
    :return: Символ приоритетного металла или None
    """
    # Регулярное выражение для поиска элементов и их количества
    pattern = r"([A-Z][a-z]?)(\d*)"
    matches = re.findall(pattern, formula)

    # Словарь для хранения количества атомов каждого металла
    metal_counts = {metal: 0 for metal in metal_elements}

    for elem, count_str in matches:
        if elem in metal_counts:
            count = int(count_str) if count_str else 1
            metal_counts[elem] += count

    # Находим максимальное количество атомов
    max_count = max(metal_counts.values())
    top_metals = [metal for metal, count in metal_counts.items() if count == max_count]

    # Если только один металл имеет максимальное количество — он приоритетный
    return top_metals[0] if len(top_metals) == 1 else '-'


def is_noble(metal_list: List[str]) -> bool:
    return any(m in NOBLE_METALS for m in metal_list)


def determine_electrolyte_type(electrolyte_str: Optional[str]) -> Optional[str]:
    if not electrolyte_str:
        return None
    upper = electrolyte_str.upper()
    if any(p.upper() in upper for p in ACIDIC_PATTERNS):
        return "acidic"
    if any(p.upper() in upper for p in ALKALINE_PATTERNS):
        return "alkaline"
    return None

# ----------------------------------------------------------------------
def transform_catalysis_hub_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Convert GraphQL reaction node to dataset schema."""
    # Extract DOI
    publication = record.get("publication")
    doi = publication.get("doi") if publication else None

    # Extract catalyst composition
    catalyst_composition = str(record.get("chemicalComposition"))

    # Extract metals
    metal_elements = extract_metal_symbols(catalyst_composition)
    primary_metal = find_primary_metal(catalyst_composition, metal_elements)
    noble_flag = is_noble(metal_elements)

    # Build notes
    record_id = record.get("id", "unknown")
    # The comment field is not available, we can skip it
    notes = f"id: {record_id}, equation: {record.get("Equation")}"

    return {
        "source_doi": doi,  # DOI will be fetched separately if needed
        "catalyst_composition": catalyst_composition,
        "metal_elements": metal_elements,
        "primary_metal": primary_metal,
        "is_noble_metal": noble_flag,
        "is_hybrid": primary_metal == '-',
        "carbon_present": False,
        "support_substrate": None,
        "electrolyte_type": None,
        "electrolyte_composition": None,
        "pH": None,
        "temperature_C": None,
        "ir_compensation": "not reported",
        "potential_vs_RHE": True,
        "overpotential_eta10_mV": None,
        "tafel_slope_mV_dec": None,
        "stability_value": None,
        "notes": notes,
    }

# ----------------------------------------------------------------------
def fetch_all_reactions_with_pagination(url: str, headers: Dict) -> List[Dict]:
    """
    Fetch all reactions from Catalysis-Hub using GraphQL with pagination.
    Returns a list of reaction nodes.
    """
    all_nodes = []
    after_cursor = None
    has_next_page = True

    # Query based on the working example from documentation
    query_template = """
    query GetReactions($first: Int, $after: String) {
      reactions(first: $first, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            Equation
            reactants
            products
            chemicalComposition
            reactionEnergy
            activationEnergy
            publication {
              doi
            }
          }
        }
      }
    }
    """

    while has_next_page:
        variables = {"first": 200, "after": after_cursor}
        try:
            response = requests.post(
                url,
                json={"query": query_template, "variables": variables},
                headers=headers,
                timeout=200,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                raise RuntimeError(f"GraphQL errors: {json.dumps(data['errors'], indent=2)}")

            # Extract nodes from edges
            reactions = data.get("data", {}).get("reactions", {})
            edges = reactions.get("edges", [])

            for edge in edges:
                node = edge.get("node")
                if node:
                    all_nodes.append(node)

            # Pagination info
            page_info = reactions.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")

            print(f"    Fetched {len(edges)} reactions (total: {len(all_nodes)})")

            # Avoid hitting rate limits
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            error_detail = ""
            if hasattr(e, 'response') and e.response is not None:
                error_detail = f" Response body: {e.response.text[:500]}"
            print(f"GraphQL request failed: {e}{error_detail}")
            break
        
        if len(all_nodes) >= 25000:
            break

    return all_nodes

# ----------------------------------------------------------------------
def extract_catalysis_hub(page: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch all reactions, then filter for OER with debug output."""
    url = page["url"]
    snapshot_path = ROOT / page["raw_snapshot_path"]

    headers = {
        "User-Agent": "OER-Dataset-Extractor/0.1",
        "Content-Type": "application/json",
    }

    print("    Fetching reactions from Catalysis-Hub (this may take a moment)...")
    all_reactions = fetch_all_reactions_with_pagination(url, headers)

    # Save raw snapshot
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("w", encoding="utf-8") as f:
        json.dump(all_reactions, f, indent=2)

    # # Debug: print first 5 reactions to understand structure
    # print("\n    === DEBUG: First 5 reactions ===")
    # for i, rec in enumerate(all_reactions[:5]):
    #     print(f"    Reaction {i+1}: id={rec.get('id')}, Equation={rec.get('Equation')}, reactants={rec.get('reactants')}")

    # Try multiple keywords
    keywords = ["o2", "h2o(g)", "h2o2"]
    filtered = []
    for rec in all_reactions:
        equation = rec.get("Equation", "")
        if not equation:
            continue
        eq_lower = equation.lower()
        if any(kw in eq_lower for kw in keywords):
            filtered.append(rec)

    print(f"\n    Found {len(filtered)} OER-related reactions out of {len(all_reactions)} total")
    if filtered:
        print("    Sample OER reaction Equation:", filtered[0].get("Equation"))

    # Transform records
    transformed_records = [transform_catalysis_hub_record(rec) for rec in filtered]
    return transformed_records


# ----------------------------------------------------------------------
def main() -> None:
    with MANIFEST.open(encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Web extraction v{manifest.get('web_extraction_version')}")
    print(f"Script: {manifest.get('script')}")
    print(f"Output: {manifest.get('output_records_file')}")
    print("\nPages to process:")

    output_records_file = ROOT / manifest["output_records_file"]
    all_records = []

    for page in manifest.get("input_pages", []):
        print(f"  - {page['page_id']}: {page['url']} "
              f"(source_id={page['source_id']}, status={page.get('extraction_status')})")

        try:
            if page["page_id"] == "catalysis_hub_oer":
                records = extract_catalysis_hub(page)
                all_records.extend(records)
                print(f"    Extracted {len(records)} OER records.")
                append_log({
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "step": "web_extraction",
                    "source_id": page["source_id"],
                    "status": "ok",
                    "records_extracted": len(records),
                    "output": str(manifest["output_records_file"]),
                })
            else:
                snap_path = ROOT / page["raw_snapshot_path"]
                snap_path.parent.mkdir(parents=True, exist_ok=True)
                snap_path.write_text(f"<!-- placeholder for {page['page_id']} -->\n", encoding="utf-8")
                print(f"    Unknown page_id, wrote placeholder snapshot.")
                append_log({
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "step": "web_extraction",
                    "source_id": page["source_id"],
                    "status": "skipped_unknown",
                    "tool": "extract_web.py",
                })
        except Exception as e:
            print(f"    ERROR processing {page['page_id']}: {e}")
            append_log({
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "step": "web_extraction",
                "source_id": page["source_id"],
                "status": "failed",
                "tool": "extract_web.py",
                "error": str(e),
            })

    if all_records:
        output_records_file.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(all_records)
        for col in OUTPUT_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[OUTPUT_COLUMNS]
        df.to_csv(output_records_file, index=False, encoding="utf-8")
        print(f"\nSaved {len(df)} records to {output_records_file.relative_to(ROOT)}")
    else:
        print("\nNo records were extracted. CSV not created.")

if __name__ == "__main__":
    main()