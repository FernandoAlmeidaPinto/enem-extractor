"""Extrator de questões do ENEM a partir de PDFs de prova."""

from .service import extract, detect_mode, default_output_dir, get_year_and_day

__all__ = [
    "extract",
    "detect_mode",
    "default_output_dir",
    "get_year_and_day",
    "extract_questions_normal",
    "extract_questions_ampliada",
]

__version__ = "0.1.0"


def __getattr__(name):
    # Exposição lazy dos extractors que dependem de PyMuPDF/Pillow, para que
    # `import enem_extractor` não exija essas libs.
    if name == "extract_questions_normal":
        from .normal import extract_questions_normal

        return extract_questions_normal
    if name == "extract_questions_ampliada":
        from .ampliada import extract_questions_ampliada

        return extract_questions_ampliada
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
