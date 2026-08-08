"""Entrada única (dispatcher) do extrator de questões do ENEM.

Os imports dos extractors que dependem de PyMuPDF/Pillow são feitos de forma
lazy dentro do roteamento, para que detecção, validação e derivação de pasta
funcionem mesmo sem essas libs instaladas.
"""

from pathlib import Path

VALID_MODES = ("auto", "normal", "ampliada")


def get_year_and_day(filename=""):
    parts = filename.split("_")
    year = parts[0]
    day = next((p for p in parts if p.startswith("D")), "D1")
    return year, day


def detect_mode(pdf_path) -> str:
    """'ampliada' se o nome contiver 'ampliada' (cobre 'superampliada'),
    senão 'normal'. Considera apenas o nome do arquivo."""
    name = Path(pdf_path).name.lower()
    return "ampliada" if "ampliada" in name else "normal"


def default_output_dir(pdf_path) -> Path:
    """Deriva imagens/<ano>/<dia> a partir do nome do PDF."""
    year, day = get_year_and_day(Path(pdf_path).name)
    return Path("imagens") / year / day
