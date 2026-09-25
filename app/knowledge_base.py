import json
from pathlib import Path
from typing import Any

DATA_DIRECTORY = Path(__file__).parent / "data"


def _load_records(file_name: str) -> list[dict[str, Any]]:
    with (DATA_DIRECTORY / file_name).open(encoding="utf-8") as file:
        records: list[dict[str, Any]] = json.load(file)
    return records


MATERIALS: list[dict[str, Any]] = _load_records("materials.json")
COMMODITY_REFERENCE: list[dict[str, Any]] = _load_records("commodities.json")


def find_commodity_reference(name: str) -> dict[str, Any] | None:
    normalized_name = name.strip().casefold()
    for record in COMMODITY_REFERENCE:
        names = [record["name"], *record.get("aliases", [])]
        if normalized_name in {value.strip().casefold() for value in names}:
            return record
    return None
