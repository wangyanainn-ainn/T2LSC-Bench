"""T2LSC-Bench metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def _binary(value: Any) -> bool:
    return value in (0, 1, False, True)


def compute_metrics(records: Iterable[dict[str, Any]]) -> dict[str, float | int | None]:
    rows = list(records)
    ssp_valid = [row for row in rows if _binary(row.get("ssp"))]
    slr_valid = [row for row in rows if _binary(row.get("slr"))]
    cslr_valid = [row for row in slr_valid if row.get("taa") in (1, True)]

    def rate(valid: list[dict[str, Any]], key: str, positive: int = 1) -> float | None:
        if not valid:
            return None
        return 100.0 * sum(int(row[key]) == positive for row in valid) / len(valid)

    return {
        "n": len(rows),
        "taa_n": len(rows),
        "taa": (100.0 * sum(row.get("taa") in (1, True) for row in rows) / len(rows)) if rows else None,
        "ssp_n": len(ssp_valid),
        "ssp": rate(ssp_valid, "ssp"),
        "slr_n": len(slr_valid),
        "slr": rate(slr_valid, "slr"),
        "cslr_n": len(cslr_valid),
        "cslr": rate(cslr_valid, "slr"),
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute TAA, SSP, SLR, and cSLR from final JSONL labels.")
    parser.add_argument("labels", type=Path, help="JSONL file containing taa, ssp, and slr fields")
    args = parser.parse_args()
    print(json.dumps(compute_metrics(read_jsonl(args.labels)), indent=2))


if __name__ == "__main__":
    main()
