#!/usr/bin/env python3
"""Migração de itens BOUT -> TBOT com foco em compatibilidade em runtime.

Motivação:
- A estratégia de anexar *todos* os itens do BOUT pode introduzir dados que o cliente TBOT
  não espera em batalha (mesmo aparecendo no shop).
- O modo padrão deste script faz migração por interseção de IDs, mantendo o tamanho
  e a estrutura-base do TBOT.

Modo padrão (safe-overlap):
1) Mantém exatamente os mesmos registros do TBOT (mesma quantidade e ordem).
2) Para IDs existentes nos dois arquivos, copia apenas campos permitidos.
3) Preserva campos críticos de configuração do TBOT (id, id_hex, level, currency, icon_id, name).

Modo opcional (append-missing):
- Mantém o comportamento antigo de anexar IDs ausentes do BOUT ao final.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
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

PROTECTED_TBOT_FIELDS = {"id", "id_hex", "name", "level", "currency", "icon_id"}
COPYABLE_FIELDS = {"price", "stats"}


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


def migrate_safe_overlap(
    base_tbot: list[dict[str, Any]],
    source_bout: list[dict[str, Any]],
    copy_fields: set[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not copy_fields.issubset(COPYABLE_FIELDS):
        invalid = sorted(copy_fields - COPYABLE_FIELDS)
        raise ValueError(f"Campos não permitidos para cópia: {invalid}")

    bout_by_id = {item["id"]: item for item in source_bout}
    merged = []
    overlap = 0
    changed = 0

    for item in base_tbot:
        result = deepcopy(item)
        other = bout_by_id.get(item["id"])
        if other is not None:
            overlap += 1
            before = json.dumps(result, sort_keys=True, ensure_ascii=False)
            for field in copy_fields:
                result[field] = deepcopy(other[field])
            after = json.dumps(result, sort_keys=True, ensure_ascii=False)
            if before != after:
                changed += 1
        merged.append(result)

    stats = {
        "mode": 0,  # 0 = safe-overlap
        "tbot_total": len(base_tbot),
        "bout_total": len(source_bout),
        "overlap_ids": overlap,
        "updated_records": changed,
        "appended_from_bout": 0,
        "merged_total": len(merged),
    }
    return merged, stats


def migrate_append_missing(base_tbot: list[dict[str, Any]], source_bout: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    tbot_ids = {item["id"] for item in base_tbot}
    appended = [deepcopy(item) for item in source_bout if item["id"] not in tbot_ids]
    merged = [*deepcopy(base_tbot), *appended]

    stats = {
        "mode": 1,  # 1 = append-missing
        "tbot_total": len(base_tbot),
        "bout_total": len(source_bout),
        "overlap_ids": len({x['id'] for x in source_bout} & {x['id'] for x in base_tbot}),
        "updated_records": 0,
        "appended_from_bout": len(appended),
        "merged_total": len(merged),
    }
    return merged, stats


def duplicate_id_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for _, c in Counter(x["id"] for x in items).items() if c > 1)


def check_compatibility_guard(original_tbot: list[dict[str, Any]], merged: list[dict[str, Any]], mode: str) -> None:
    if mode == "safe-overlap":
        if len(original_tbot) != len(merged):
            raise RuntimeError("Falha de segurança: modo safe-overlap não pode alterar quantidade de registros")
        for idx, (old, new) in enumerate(zip(original_tbot, merged)):
            for key in PROTECTED_TBOT_FIELDS:
                if old[key] != new[key]:
                    raise RuntimeError(
                        f"Falha de segurança: campo protegido alterado em índice {idx}, chave {key}"
                    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra BOUT -> TBOT com compatibilidade de runtime")
    parser.add_argument("--tbot", default="itemTBOT.json", type=Path)
    parser.add_argument("--bout", default="itemBOUT.json", type=Path)
    parser.add_argument("--out", default="itemTBOT.migrated.json", type=Path)
    parser.add_argument(
        "--mode",
        choices=["safe-overlap", "append-missing"],
        default="safe-overlap",
        help="safe-overlap (padrão) evita expandir catálogo; append-missing replica comportamento antigo",
    )
    parser.add_argument(
        "--copy-fields",
        nargs="+",
        default=["price", "stats"],
        choices=sorted(COPYABLE_FIELDS),
        help="Campos copiados do BOUT no modo safe-overlap",
    )
    args = parser.parse_args()

    tbot = load_json(args.tbot)
    bout = load_json(args.bout)

    validate_items(tbot, "TBOT")
    validate_items(bout, "BOUT")

    if args.mode == "safe-overlap":
        merged, stats = migrate_safe_overlap(tbot, bout, set(args.copy_fields))
    else:
        merged, stats = migrate_append_missing(tbot, bout)

    check_compatibility_guard(tbot, merged, args.mode)

    with args.out.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Migração concluída.")
    print(f"- mode: {args.mode}")
    for k, v in stats.items():
        if k == "mode":
            continue
        print(f"- {k}: {v}")
    print(f"- duplicate_ids_tbot: {duplicate_id_count(tbot)}")
    print(f"- duplicate_ids_merged: {duplicate_id_count(merged)}")
    print(f"Arquivo de saída: {args.out}")


if __name__ == "__main__":
    main()
