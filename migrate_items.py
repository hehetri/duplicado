#!/usr/bin/env python3
"""Migração BOUT -> TBOT com foco em adicionar NOVOS IDs.

Padrão (`new-ids-only`):
- Mantém todos os itens já existentes no TBOT sem alteração.
- Adiciona apenas itens do BOUT cujo `id` não existe no TBOT.
- Se `icon_id` do item novo não existir no TBOT, remapeia para ícone fallback seguro.
PROTECTED_TBOT_FIELDS = {"id", "id_hex", "name", "level", "currency", "price", "icon_id", "stats"}
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
    return Counter(x["icon_id"] for x in items).most_common(1)[0][0]
def append_new_ids(
    base: list[dict[str, Any]],
    existing_ids = {x["id"] for x in base}
    known_icons = {x["icon_id"] for x in base}
    appended: list[dict[str, Any]] = []
    remapped = 0
            if icon_policy == "remap-unknown":
                remapped += 1
            elif icon_policy == "keep-unknown":
                pass
    return [*base, *appended], len(appended), skipped, remapped
def check_tbot_prefix_unchanged(original_tbot: list[dict[str, Any]], merged: list[dict[str, Any]]) -> None:
        raise RuntimeError("Falha: merge reduziu tamanho do TBOT")
                raise RuntimeError(f"Falha: prefixo TBOT alterado no índice {idx}, chave {key}")
    parser = argparse.ArgumentParser(description="Migra BOUT -> TBOT priorizando novos IDs")
        choices=["new-ids-only", "safe-hybrid", "safe-overlap", "append-all"],
        default="new-ids-only",
        help="new-ids-only (padrão) não altera itens antigos; só adiciona IDs novos",
        help="Campos copiados no modo safe-overlap/safe-hybrid",
        help="Como tratar icon_id desconhecido para itens novos",
    )
    parser.add_argument("--fallback-icon", type=int, default=None)
    if args.mode == "new-ids-only":
        merged, appended, skipped, remapped = append_new_ids(
            deepcopy(tbot), bout, icon_policy=args.icon_policy, fallback_icon=fallback_icon
        )
        stats = {
            "updated_records": 0,
            "appended_from_bout": appended,
            "skipped_incompatible": skipped,
            "remapped_icons": remapped,
        }
    elif args.mode == "safe-overlap":
    elif args.mode == "safe-hybrid":
        merged, appended, skipped, remapped = append_new_ids(
            base, bout, icon_policy=args.icon_policy, fallback_icon=fallback_icon
    else:  # append-all
        base, updated = overlay_by_intersection(tbot, bout, set(args.copy_fields))
        merged, appended, skipped, remapped = append_new_ids(
            base, bout, icon_policy="keep-unknown", fallback_icon=fallback_icon
        stats = {
            "updated_records": updated,
            "appended_from_bout": appended,
            "skipped_incompatible": skipped,
            "remapped_icons": remapped,
        }
    check_tbot_prefix_unchanged(tbot, merged)
    bout_ids = {x["id"] for x in bout}
    merged_ids = {x["id"] for x in merged}
    print(f"- tbot_total: {len(tbot)}")
    print(f"- bout_total: {len(bout)}")
    print(f"- overlap_ids: {len(bout_ids & {x['id'] for x in tbot})}")
    print(f"- updated_records: {stats['updated_records']}")
    print(f"- appended_from_bout: {stats['appended_from_bout']}")
    print(f"- skipped_incompatible: {stats['skipped_incompatible']}")
    print(f"- remapped_icons: {stats['remapped_icons']}")
    print(f"- merged_total: {len(merged)}")
    print(f"- bout_ids_missing_in_merged: {len(bout_ids - merged_ids)}")


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
