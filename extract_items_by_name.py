#!/usr/bin/env python3
"""Extrai itens por nome de um JSON e salva em arquivo .txt (bloco de notas)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_items(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Arquivo JSON deve ter um array na raiz")
    return data


def name_match(item_name: str, query: str, *, exact: bool, ignore_case: bool) -> bool:
    left = item_name.casefold() if ignore_case else item_name
    right = query.casefold() if ignore_case else query
    if exact:
        return left == right
    return right in left


def extract(items: list[dict[str, Any]], queries: list[str], *, exact: bool, ignore_case: bool) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for item in items:
        name = str(item.get("name", ""))
        if any(name_match(name, q, exact=exact, ignore_case=ignore_case) for q in queries):
            found.append(item)
    return found


def write_txt(output: Path, matches: list[dict[str, Any]], queries: list[str]) -> None:
    with output.open("w", encoding="utf-8") as f:
        f.write("EXTRATOR DE ITENS POR NOME\n")
        f.write(f"Consulta(s): {', '.join(queries)}\n")
        f.write(f"Total encontrado: {len(matches)}\n")
        f.write("=" * 80 + "\n\n")

        for idx, item in enumerate(matches, start=1):
            f.write(f"Item #{idx}\n")
            f.write(json.dumps(item, ensure_ascii=False, indent=2))
            f.write("\n" + "-" * 80 + "\n\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai itens por nome de itemTBOT.migrated.json e salva em .txt"
    )
    parser.add_argument("--input", type=Path, default=Path("itemTBOT.migrated.json"), help="Arquivo JSON de entrada")
    parser.add_argument(
        "--name",
        dest="names",
        action="append",
        required=True,
        help="Nome (ou parte do nome) para buscar. Pode repetir --name várias vezes",
    )
    parser.add_argument("--output", type=Path, default=Path("itens_extraidos.txt"), help="Arquivo .txt de saída")
    parser.add_argument("--exact", action="store_true", help="Busca por igualdade exata do nome")
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Busca sensível a maiúsculas/minúsculas",
    )
    args = parser.parse_args()

    items = load_items(args.input)
    matches = extract(
        items,
        args.names,
        exact=args.exact,
        ignore_case=not args.case_sensitive,
    )
    write_txt(args.output, matches, args.names)

    print(f"Itens lidos: {len(items)}")
    print(f"Itens encontrados: {len(matches)}")
    print(f"Arquivo salvo em: {args.output}")


if __name__ == "__main__":
    main()
