"""Catálogo de provas: descobre PDFs numa pasta e resolve nomes para caminhos.

Camada pura — depende apenas de stdlib e de `service.detect_mode`. Não importa
PyMuPDF/Pillow nem o SDK do MCP, então é testável em qualquer ambiente.
"""

import os
from pathlib import Path

from .service import detect_mode


def provas_dir() -> Path:
    """Pasta das provas: variável de ambiente PROVAS_DIR ou 'provas' (default)."""
    return Path(os.environ.get("PROVAS_DIR", "provas"))


def list_provas(directory=None) -> list[dict]:
    """Varre a pasta e retorna, ordenado por nome, uma lista de dicts:
    {"name", "mode", "path", "size_bytes"}. Pasta inexistente/sem PDFs -> []."""
    base = Path(directory) if directory is not None else provas_dir()
    if not base.is_dir():
        return []
    provas = []
    for pdf in sorted(base.glob("*.pdf")):
        provas.append(
            {
                "name": pdf.name,
                "mode": detect_mode(pdf.name),
                "path": str(pdf),
                "size_bytes": pdf.stat().st_size,
            }
        )
    return provas


def resolve_prova(name, directory=None) -> Path:
    """Resolve `name` (arquivo listado, com ou sem `.pdf`, ou um caminho) para um
    Path existente. Levanta FileNotFoundError se não encontrar."""
    direct = Path(name)
    if direct.is_file():
        return direct
    base = Path(directory) if directory is not None else provas_dir()
    candidate = base / name
    if candidate.is_file():
        return candidate
    if not str(name).endswith(".pdf"):
        candidate_pdf = base / f"{name}.pdf"
        if candidate_pdf.is_file():
            return candidate_pdf
    raise FileNotFoundError(f"prova não encontrada: {name!r} (em {base})")
