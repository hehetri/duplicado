#!/usr/bin/env python3
"""Migra itens de itemBOUT.json para itemTBOT.json sem sobrescrever configs do TBOT.

Regras de segurança:
1) Mantém TODOS os registros originais do TBOT na mesma ordem.
2) Adiciona apenas IDs que não existem no TBOT.
3) Valida schema básico antes de gravar.
4) Não altera o itemTBOT.json original por padrão.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_KEYS = {"id", "id_hex", "name", "level", "currency", "price", "icon_id", "stats"}
REQUIRED_STATS = {
    "hp",
    "atk_basic",
    "atk_trans",
    "atk_trans2",
    "trans_gauge",
    "critical",
    "secondary_speed",
    "trans_def",
    "trans_attack",
}


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} precisa ser um array JSON na raiz")
    return data


def validate_items(items: list[dict[str, Any]], label: str) -> None:
    for i, item in enumerate(items):
        missing = REQUIRED_KEYS - set(item.keys())
        if missing:
            raise ValueError(f"{label}[{i}] sem chaves obrigatórias: {sorted(missing)}")
        stats = item.get("stats", {})
        if not isinstance(stats, dict):
            raise ValueError(f"{label}[{i}].stats precisa ser objeto")
        missing_stats = REQUIRED_STATS - set(stats.keys())
        if missing_stats:
            raise ValueError(f"{label}[{i}].stats sem chaves: {sorted(missing_stats)}")


def migrate(base_tbot: list[dict[str, Any]], source_bout: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    tbot_ids = {item["id"] for item in base_tbot}
    appended = [item for item in source_bout if item["id"] not in tbot_ids]
    merged = [*base_tbot, *appended]

    stats = {
        "tbot_total": len(base_tbot),
        "bout_total": len(source_bout),
        "overlap_ids": len({x['id'] for x in source_bout} & {x['id'] for x in base_tbot}),
        "appended_from_bout": len(appended),
        "merged_total": len(merged),
    }
    return merged, stats


def duplicate_id_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for _, c in Counter(x["id"] for x in items).items() if c > 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra BOUT -> TBOT sem sobrescrever registros TBOT")
    parser.add_argument("--tbot", default="itemTBOT.json", type=Path)
    parser.add_argument("--bout", default="itemBOUT.json", type=Path)
    parser.add_argument("--out", default="itemTBOT.migrated.json", type=Path)
    args = parser.parse_args()

    tbot = load_json(args.tbot)
    bout = load_json(args.bout)

    validate_items(tbot, "TBOT")
    validate_items(bout, "BOUT")

    merged, stats = migrate(tbot, bout)

    # Segurança: não reduzir quantidade de itens TBOT nem perder duplicatas originais
    if merged[: len(tbot)] != tbot:
        raise RuntimeError("Falha de segurança: início do arquivo migrado difere do TBOT original")

    with args.out.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Migração concluída.")
    for k, v in stats.items():
        print(f"- {k}: {v}")
    print(f"- duplicate_ids_tbot: {duplicate_id_count(tbot)}")
    print(f"- duplicate_ids_merged: {duplicate_id_count(merged)}")
    print(f"Arquivo de saída: {args.out}")


if __name__ == "__main__":
    main()
