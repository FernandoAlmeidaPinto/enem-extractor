"""Extrator de questões do ENEM a partir de PDFs de prova."""

from .normal import extract_questions_normal
from .ampliada import extract_questions_ampliada

__all__ = ["extract_questions_normal", "extract_questions_ampliada"]

__version__ = "0.1.0"
