#!/usr/bin/env python3
"""Migração de itens BOUT -> TBOT com foco em compatibilidade em runtime.

Estratégia padrão (`safe-hybrid`):
1) Mantém base TBOT (ordem + campos protegidos).
2) Atualiza apenas `price`/`stats` por interseção de ID.
3) Anexa itens novos do BOUT apenas se forem "compatíveis" com TBOT
   (por padrão: `icon_id` já existente no TBOT).

PROTECTED_TBOT_FIELDS = {"id", "id_hex", "level", "currency", "icon_id"}
COPYABLE_FIELDS = {"name", "price", "stats"}
- migrar itens novos de fato (não só sobreposição).
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


def overlay_by_intersection(
    base_tbot: list[dict[str, Any]],
    source_bout: list[dict[str, Any]],
    copy_fields: set[str],
) -> tuple[list[dict[str, Any]], int]:
    if not copy_fields.issubset(COPYABLE_FIELDS):
        invalid = sorted(copy_fields - COPYABLE_FIELDS)
        raise ValueError(f"Campos não permitidos para cópia: {invalid}")

    bout_by_id = {item["id"]: item for item in source_bout}
    merged = []
    changed = 0

    for item in base_tbot:
        result = deepcopy(item)
        other = bout_by_id.get(item["id"])
        if other is not None:
            before = json.dumps(result, sort_keys=True, ensure_ascii=False)
            for field in copy_fields:
                result[field] = deepcopy(other[field])
            after = json.dumps(result, sort_keys=True, ensure_ascii=False)
            if before != after:
                changed += 1
        merged.append(result)

    return merged, changed


def append_compatible_missing(
    merged_from_tbot: list[dict[str, Any]],
    source_bout: list[dict[str, Any]],
    *,
    allow_new_icons: bool,
) -> tuple[list[dict[str, Any]], int, int]:
    existing_ids = {item["id"] for item in merged_from_tbot}
    known_icons = {item["icon_id"] for item in merged_from_tbot}

    appended = []
    skipped = 0
    for item in source_bout:
        if item["id"] in existing_ids:
            continue
        if (not allow_new_icons) and (item["icon_id"] not in known_icons):
            skipped += 1
            continue
        appended.append(deepcopy(item))
        existing_ids.add(item["id"])

    return [*merged_from_tbot, *appended], len(appended), skipped


def migrate_safe_hybrid(
    base_tbot: list[dict[str, Any]],
    source_bout: list[dict[str, Any]],
    *,
    copy_fields: set[str],
    allow_new_icons: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    overlapped, updated_records = overlay_by_intersection(base_tbot, source_bout, copy_fields)
    merged, appended_from_bout, skipped_incompatible = append_compatible_missing(
        overlapped,
        source_bout,
        allow_new_icons=allow_new_icons,
    )
    stats = {
        "tbot_total": len(base_tbot),
        "bout_total": len(source_bout),
        "overlap_ids": len({x['id'] for x in source_bout} & {x['id'] for x in base_tbot}),
        "updated_records": updated_records,
        "appended_from_bout": appended_from_bout,
        "skipped_incompatible": skipped_incompatible,
        "merged_total": len(merged),
    }
    return merged, stats


def duplicate_id_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for _, c in Counter(x["id"] for x in items).items() if c > 1)


def check_compatibility_guard(original_tbot: list[dict[str, Any]], merged: list[dict[str, Any]]) -> None:
    if len(merged) < len(original_tbot):
        raise RuntimeError("Falha de segurança: merge não pode reduzir registros do TBOT")
    for idx, (old, new) in enumerate(zip(original_tbot, merged)):
        for key in PROTECTED_TBOT_FIELDS:
            if old[key] != new[key]:
                raise RuntimeError(
                    f"Falha de segurança: campo protegido alterado em índice {idx}, chave {key}"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra BOUT -> TBOT com estratégia híbrida segura")
    parser.add_argument("--tbot", default="itemTBOT.json", type=Path)
    parser.add_argument("--bout", default="itemBOUT.json", type=Path)
    parser.add_argument("--out", default="itemTBOT.migrated.json", type=Path)
    parser.add_argument(
        "--mode",
        choices=["safe-hybrid", "safe-overlap", "append-all"],
        default="safe-hybrid",
        default=["name", "price", "stats"],
    )
    parser.add_argument(
        "--copy-fields",
        nargs="+",
        default=["price", "stats"],
        choices=sorted(COPYABLE_FIELDS),
        help="Campos copiados do BOUT para IDs em comum",
    )
    parser.add_argument(
        "--allow-new-icons",
        action="store_true",
        help="No safe-hybrid, também anexa itens com icon_id não visto no TBOT",
    )
    args = parser.parse_args()

    tbot = load_json(args.tbot)
    bout = load_json(args.bout)

    validate_items(tbot, "TBOT")
    validate_items(bout, "BOUT")

    if args.mode == "safe-overlap":
        merged, updated = overlay_by_intersection(tbot, bout, set(args.copy_fields))
        stats = {
            "tbot_total": len(tbot),
            "bout_total": len(bout),
            "overlap_ids": len({x['id'] for x in bout} & {x['id'] for x in tbot}),
            "updated_records": updated,
            "appended_from_bout": 0,
            "skipped_incompatible": 0,
            "merged_total": len(merged),
        }
    elif args.mode == "append-all":
        base, updated = overlay_by_intersection(tbot, bout, set(args.copy_fields))
        merged, appended, skipped = append_compatible_missing(base, bout, allow_new_icons=True)
        stats = {
            "tbot_total": len(tbot),
            "bout_total": len(bout),
            "overlap_ids": len({x['id'] for x in bout} & {x['id'] for x in tbot}),
            "updated_records": updated,
            "appended_from_bout": appended,
            "skipped_incompatible": skipped,
            "merged_total": len(merged),
        }
    else:
        merged, stats = migrate_safe_hybrid(
            tbot,
            bout,
            copy_fields=set(args.copy_fields),
            allow_new_icons=args.allow_new_icons,
        )

    check_compatibility_guard(tbot, merged)

    with args.out.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Migração concluída.")
    print(f"- mode: {args.mode}")
    print(f"- allow_new_icons: {args.allow_new_icons}")
    for k, v in stats.items():
        print(f"- {k}: {v}")
    print(f"- duplicate_ids_tbot: {duplicate_id_count(tbot)}")
    print(f"- duplicate_ids_merged: {duplicate_id_count(merged)}")
    print(f"Arquivo de saída: {args.out}")


if __name__ == "__main__":
    main()
