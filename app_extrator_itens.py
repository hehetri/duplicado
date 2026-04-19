#!/usr/bin/env python3
"""Aplicação desktop (Tkinter) para extrair itens por nome e exportar em TXT."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
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
    return left == right if exact else (right in left)


def extract(items: list[dict[str, Any]], queries: list[str], *, exact: bool, ignore_case: bool) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for item in items:
        item_name = str(item.get("name", ""))
        if any(name_match(item_name, q, exact=exact, ignore_case=ignore_case) for q in queries):
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


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Extrator de Itens JSON -> TXT")
        self.root.geometry("760x420")

        self.input_var = tk.StringVar(value="itemTBOT.migrated.json")
        self.output_var = tk.StringVar(value="itens_extraidos.txt")
        self.query_var = tk.StringVar(value="")
        self.exact_var = tk.BooleanVar(value=False)
        self.case_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 6}

        tk.Label(self.root, text="Arquivo JSON:").grid(row=0, column=0, sticky="w", **pad)
        tk.Entry(self.root, textvariable=self.input_var, width=70).grid(row=0, column=1, sticky="we", **pad)
        tk.Button(self.root, text="Selecionar", command=self.choose_input).grid(row=0, column=2, **pad)

        tk.Label(self.root, text="Arquivo TXT saída:").grid(row=1, column=0, sticky="w", **pad)
        tk.Entry(self.root, textvariable=self.output_var, width=70).grid(row=1, column=1, sticky="we", **pad)
        tk.Button(self.root, text="Salvar como", command=self.choose_output).grid(row=1, column=2, **pad)

        tk.Label(
            self.root,
            text="Nome(s) para buscar (separe múltiplos por vírgula):",
        ).grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        tk.Entry(self.root, textvariable=self.query_var, width=100).grid(row=3, column=0, columnspan=3, sticky="we", **pad)

        tk.Checkbutton(self.root, text="Busca exata", variable=self.exact_var).grid(row=4, column=0, sticky="w", **pad)
        tk.Checkbutton(self.root, text="Case sensitive", variable=self.case_var).grid(row=4, column=1, sticky="w", **pad)

        tk.Button(self.root, text="Extrair e salvar TXT", command=self.run_extract, bg="#2f80ed", fg="white").grid(
            row=5, column=0, columnspan=3, sticky="we", padx=8, pady=12
        )

        self.log = tk.Text(self.root, height=10)
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=8, pady=8)

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(6, weight=1)

    def choose_input(self) -> None:
        p = filedialog.askopenfilename(
            title="Selecione o JSON",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
        )
        if p:
            self.input_var.set(p)

    def choose_output(self) -> None:
        p = filedialog.asksaveasfilename(
            title="Salvar TXT como",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Todos", "*.*")],
        )
        if p:
            self.output_var.set(p)

    def _queries(self) -> list[str]:
        raw = self.query_var.get().strip()
        return [q.strip() for q in raw.split(",") if q.strip()]

    def log_msg(self, msg: str) -> None:
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def run_extract(self) -> None:
        try:
            in_path = Path(self.input_var.get().strip())
            out_path = Path(self.output_var.get().strip())
            queries = self._queries()

            if not in_path.exists():
                raise FileNotFoundError(f"JSON não encontrado: {in_path}")
            if not queries:
                raise ValueError("Informe ao menos um nome para busca")

            items = load_items(in_path)
            matches = extract(
                items,
                queries,
                exact=self.exact_var.get(),
                ignore_case=not self.case_var.get(),
            )
            write_txt(out_path, matches, queries)

            self.log_msg(f"Itens lidos: {len(items)}")
            self.log_msg(f"Itens encontrados: {len(matches)}")
            self.log_msg(f"Arquivo salvo: {out_path}")
            messagebox.showinfo("Sucesso", f"Extração concluída!\n\nEncontrados: {len(matches)}")
        except Exception as exc:
            self.log_msg(f"Erro: {exc}")
            messagebox.showerror("Erro", str(exc))


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
