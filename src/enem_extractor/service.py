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


def _run_normal(pdf_path, output_dir):
    from .normal import extract_questions_normal

    extract_questions_normal(pdf_path, str(output_dir))


def _run_ampliada(pdf_path, output_dir):
    from .ampliada import extract_questions_ampliada

    extract_questions_ampliada(pdf_path, str(output_dir))


_EXTRACTORS = {"normal": _run_normal, "ampliada": _run_ampliada}


def extract(pdf_path, output_dir=None, mode="auto") -> dict:
    """Ponto de entrada único.

    - valida `mode` e a existência do PDF
    - resolve o modo (detecta pelo nome se 'auto', senão usa o forçado)
    - resolve a pasta de saída (imagens/<ano>/<dia> se `output_dir` é None)
    - roteia para o extractor correto
    - retorna metadados do job

    Nota: `images` lista todos os PNGs em `output_dir` após a extração; se a
    pasta for reutilizada, pode incluir imagens de execuções anteriores. Para
    resultados limpos, use uma pasta de saída vazia (o padrão derivado já é
    por ano/dia).
    """
    if mode not in VALID_MODES:
        raise ValueError(f"mode inválido: {mode!r}. Use um de {VALID_MODES}.")

    pdf = Path(pdf_path)
    if not pdf.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    resolved_mode = detect_mode(pdf_path) if mode == "auto" else mode
    out = Path(output_dir) if output_dir is not None else default_output_dir(pdf_path)
    out.mkdir(parents=True, exist_ok=True)

    _EXTRACTORS[resolved_mode](str(pdf), out)

    images = sorted(str(p) for p in out.glob("*.png"))
    return {
        "pdf": str(pdf),
        "mode": resolved_mode,
        "output_dir": str(out),
        "images": images,
    }
