#!/usr/bin/env python3
"""
Placeholder PDF extraction driver.

Real implementation: install PyMuPDF (fitz), pdfplumber, or Camelot and parse
tables from paths listed in specs/pdf_extraction_manifest.json.
"""

from __future__ import annotations

import json
import pandas as pd
import pdfplumber
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "specs/pdf_extraction_manifest.json"
LOG_PATH = ROOT / "data/extracted/extraction_log.jsonl"


def append_log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def extract_table(text: str) -> Dict[tuple, Dict[str, Any]]:
    """
    Извлекает числовые значения из таблицы 3 (потенциал при 0.5 mA/mol,
    тафелевский наклон, масса растворённого металла) для каждого катализатора.
    Возвращает словарь: {(metal, form): {"potential": float, "tafel_slope": float/None, "dissolved_metal": str/None}}
    """
    # Ищем блок, содержащий таблицу 3
    # Ориентируемся на характерные фразы
    table_start = re.search(r"Table ?3\..*?potential ?at ?0\.5 ?mA ?mol", text, re.IGNORECASE | re.DOTALL)
    if not table_start:
        return {}

    # Обрезаем текст от начала таблицы до следующей пустой строки или конца блока
    block_start = table_start.start()

    # Ищем конец таблицы (конец страницы)
    end_match = re.search(r"17\d{2} dx\.doi\.org\/(10\.1021\/cs\d+)", text[block_start:])
    if end_match:
        block_end = block_start + end_match.start()
    else:
        block_end = len(text)
    table_block = text[block_start:block_end]

    # Регулярное выражение для строк с металлами
    # Пример: "Ru 1.449 1.504 44  13.1 ± 0.2 1.7 ± 0.4"
    # Ищем металл и следующие за ним строки с числами (до следующего металла или конца)
    metals = ["Ru", "Ir", "Pt"]
    data = {}

    print(table_block)
    for i, metal in enumerate(metals):
        # Ищем позицию металла в блоке
        metal_pos = table_block.find(f"\n{metal} 1")
        if metal_pos == -1:
            continue

        # Определяем конец данных для этого металла (начало следующего металла или конец блока)
        next_metal_pos = len(table_block)
        for next_m in metals[i+1:]:
            pos = table_block.find(f"\n{next_m} ", metal_pos + len(metal))
            if pos != -1:
                next_metal_pos = pos
                break

        metal_lines = table_block[metal_pos:next_metal_pos].strip().split(" ")

        # Собираем все числовые значения из строк после металла
        values = []
        for line in metal_lines[1:]:
            # Ищем числа с плавающей точкой, целые, "blda", "±"
            # Разделяем по пробелам/табуляциям
            tokens = re.findall(r"(\d+\.?\d*|\d+|blda|±)", line, re.IGNORECASE)
            # Обрабатываем токены, склеивая числа с ±
            combined = []
            i_token = 0
            while i_token < len(tokens):
                if tokens[i_token] == "±" and combined:
                    # предыдущее число плюс ± и следующее число
                    prev = combined.pop()
                    if i_token + 1 < len(tokens):
                        combined.append(f"{prev} ± {tokens[i_token+1]}")
                        i_token += 2
                    else:
                        combined.append(prev)
                        combined.append("±")
                        i_token += 1
                else:
                    combined.append(tokens[i_token])
                    i_token += 1
            values.extend(combined)

        # Очищаем от "blda" и пустых
        values = [v for v in values if v.lower() != "blda"]

        # Ожидаемая структура (по порядку):
        # potential_bulk, potential_np, tafel_bulk, tafel_np, diss_bulk, diss_np
        # Возможны пропусков – обрабатываем гибко
        potentials = []
        tafels = []
        dissolutions = []
        for v in values:
            if re.match(r"\d+\.\d+", v):
                if len(potentials) < 2:
                    potentials.append(float(v))
                else:
                    tafels.append(float(v) if v.replace('.', '').isdigit() else None)
            elif v.isdigit() and len(v) <= 3:
                tafels.append(float(v))
            else:
                dissolutions.append(v)

        # Заполняем данные для bulk и nanoparticles
        if len(potentials) >= 2:
            bulk_pot = potentials[0]
            np_pot = potentials[1]
        else:
            bulk_pot = np_pot = None

        # Tafel: может быть 0, 1 или 2 значения
        bulk_tafel = tafels[0] if len(tafels) > 0 else None
        np_tafel = tafels[1] if len(tafels) > 1 else None

        # Dissolution: может быть строка типа "13.1 ± 0.2"
        bulk_diss = dissolutions[0] if len(dissolutions) > 0 else None
        np_diss = dissolutions[1] if len(dissolutions) > 1 else None

        # Сохраняем
        data[(metal, "bulk")] = {
            "potential": bulk_pot,
            "tafel_slope": bulk_tafel,
            "dissolved_metal": bulk_diss
        }
        data[(metal, "nanoparticles")] = {
            "potential": np_pot,
            "tafel_slope": np_tafel,
            "dissolved_metal": np_diss
        }

    return data


def parse_text(text: str) -> List[Dict]:
    """
    Парсит статью Reier et al. 2012, извлекает данные о катализаторах OER.
    Поля:
    - source_doi
    - catalyst_composition, metal_elements, primary_metal, is_noble_metal, is_hybrid, carbon_present
    - electrolyte_type, electrolyte_composition, pH
    - temperature_C (комнатная, 25°C)
    - potential_vs_RHE (из таблицы 3, при удельной активности 0.5 mA/моль сайтов)
    - overpotential_eta10_mV = None (не приводится в статье)
    - tafel_slope_mV_dec (из таблицы 3)
    - exchange_current_density_A_cm2 = None
    """
    results = []

    # DOI
    doi_match = re.search(r'dx\.doi\.org\/(10\.1021\/cs\d+)', text)
    source_doi = doi_match.group(1) if doi_match else None

    # Электролит и температура
    electrolyte_type = "acidic"
    electrolyte_composition = "0.1 M HClO4"
    ph = 1.0
    temperature_C = 25.0   # комнатная температура

    # Список катализаторов
    catalysts = [
        {"metal": "Ru", "form": "bulk"},
        {"metal": "Ru", "form": "nanoparticles"},
        {"metal": "Ir", "form": "bulk"},
        {"metal": "Ir", "form": "nanoparticles"},
        {"metal": "Pt", "form": "bulk"},
        {"metal": "Pt", "form": "nanoparticles"},
    ]

    # Извлечение данных из таблицы
    table_data = extract_table(text)
    if not table_data:
        print(table_data)
        print("Не удалось извлечь таблицу из текста")

    # Формирование записей
    for cat in catalysts:
        metal = cat["metal"]
        form = cat["form"]
        key = (metal, form)

        # Состав
        if form == "bulk":
            catalyst_composition = f"{metal} bulk metal"
            carbon_present = False
        else:
            catalyst_composition = f"{metal} nanoparticles supported on Vulcan XC 72R carbon"
            carbon_present = True

        metal_elements = [metal]
        primary_metal = metal
        is_noble_metal = metal in {"Ru", "Ir", "Pt"}
        is_hybrid = False

        # Потенциал из таблицы 3 (при удельной активности 0.5 mA/моль сайтов)
        potential_vs_RHE = None
        tafel_slope = None
        stability_value = None
        if key in table_data:
            experiment_data = table_data[key]
            potential_vs_RHE = experiment_data.get("potential")
            tafel_slope = experiment_data.get("tafel_slope")
            stability_value = experiment_data.get("dissolved_metal")

        result = {
            "source_doi": source_doi,
            "catalyst_composition": catalyst_composition,
            "metal_elements": metal_elements,
            "primary_metal": primary_metal,
            "is_noble_metal": is_noble_metal,
            "is_hybrid": is_hybrid,
            "carbon_present": carbon_present,
            "electrolyte_type": electrolyte_type,
            "electrolyte_composition": electrolyte_composition,
            "pH": ph,
            "temperature_C": temperature_C,
            "potential_vs_RHE": potential_vs_RHE,
            "tafel_slope_mV_dec": tafel_slope,
            "stability_value": stability_value,
            # служебные поля
            "catalyst_form": form,
            "notes": "",
        }
        results.append(result)

    return results


def main() -> None:
    with MANIFEST.open(encoding="utf-8") as f:
        manifest = json.load(f)

    print(manifest.get("pdf_extraction_process", "PDF extraction"))
    print(f"Output: {manifest.get('output_records_file')}")
    print("\nPDFs to process:")

    for src in manifest.get("input_sources", []):
        print(
            f"  - {src['pdf_id']}: {src['pdf_path']} "
            f"(source_id={src['source_id']}, status={src.get('extraction_status')})"
        )
        # Example integration points:
        full_text = ""
        with pdfplumber.open(ROOT / src["pdf_path"]) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text()

        # Get text output (for logs)
        # with open(ROOT / f"data/extracted/{src["pdf_id"]}.txt", "w", encoding="utf-8") as f:
        #     f.write(full_text)

        data = parse_text(full_text)
        for entry in data:
            print(f"{entry['primary_metal']} {entry['catalyst_form']}:")
            print(f"  potential_vs_RHE = {entry['potential_vs_RHE']} V")
            print(f"  temperature_C = {entry['temperature_C']}")
            print(f"  tafel_slope = {entry['tafel_slope_mV_dec']} mV/dec")

        if data:
            df = pd.DataFrame(data)
            df.to_csv("data/extracted/pdf_extracted_records.csv", index=False, encoding="utf-8")

            append_log(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "step": "pdf_extraction",
                    "source_id": src["source_id"],
                    "status": "ok",
                    "tool": "extract_pdf.py",
                    "output": str(manifest.get("output_records_file")),
                    "issue": "",
                }
            )

    print(f"\nAppended placeholder event to {LOG_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
