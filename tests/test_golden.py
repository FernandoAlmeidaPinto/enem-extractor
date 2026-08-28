"""Golden test: garante que a refatoração dos extractors não altera a saída.

Extrai os PDFs de amostra em `provas/` e compara o sha256 de cada PNG gerado
contra `tests/golden/manifest.json` (gerado a partir do código pré-refatoração).

Skipa quando PyMuPDF/Pillow não estão instalados ou quando os PDFs de amostra
não existem (a pasta `provas/` é gitignored, então em CI/clone limpo o teste
pula em vez de falhar). O manifesto é específico das versões travadas no
`uv.lock`; o objetivo é blindar a refatoração no ambiente de desenvolvimento.

Para regenerar o manifesto a partir do código atual:
    uv run python tests/test_golden.py update
"""

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import fitz  # noqa: F401  (PyMuPDF)
    import PIL  # noqa: F401  (Pillow)

    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = Path(__file__).resolve().parent / "golden" / "manifest.json"

# Cada amostra: PDF de entrada, modo forçado e uma chave estável no manifesto.
SAMPLES = [
    {
        "key": "2023_D1_normal",
        "pdf": "provas/2023_PV_impresso_D1_CD4.pdf",
        "mode": "normal",
    },
    {
        "key": "2025_D1_ampliada",
        "pdf": "provas/2025_PV_impresso_D1_CD9_ampliada.pdf",
        "mode": "ampliada",
    },
]


def _hash_extraction(sample):
    """Extrai a amostra para uma pasta temporária e devolve {nome_png: sha256}."""
    from enem_extractor.service import extract

    with tempfile.TemporaryDirectory() as out_dir:
        # Os extractors imprimem no stdout; silencia para não poluir os testes.
        with contextlib.redirect_stdout(io.StringIO()):
            extract(str(PROJECT_ROOT / sample["pdf"]), output_dir=out_dir, mode=sample["mode"])
        return {
            png.name: hashlib.sha256(png.read_bytes()).hexdigest()
            for png in sorted(Path(out_dir).glob("*.png"))
        }


def _build_manifest():
    """Gera o manifesto completo rodando o código atual sobre as amostras."""
    manifest = {}
    for sample in SAMPLES:
        pdf = PROJECT_ROOT / sample["pdf"]
        if not pdf.is_file():
            raise SystemExit(f"PDF de amostra ausente: {sample['pdf']}")
        manifest[sample["key"]] = _hash_extraction(sample)
    return manifest


@unittest.skipUnless(HAS_LIBS, "PyMuPDF/Pillow não instalados")
class GoldenImageTests(unittest.TestCase):
    def test_output_matches_manifest(self):
        manifest = json.loads(MANIFEST_PATH.read_text())
        for sample in SAMPLES:
            with self.subTest(sample=sample["key"]):
                pdf = PROJECT_ROOT / sample["pdf"]
                if not pdf.is_file():
                    self.skipTest(f"PDF de amostra ausente: {sample['pdf']}")
                expected = manifest.get(sample["key"])
                self.assertIsNotNone(
                    expected, f"manifesto sem a chave {sample['key']}"
                )
                actual = _hash_extraction(sample)
                self.assertEqual(
                    actual, expected, f"saída divergiu para {sample['key']}"
                )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(_build_manifest(), indent=2) + "\n")
        print(f"Manifesto gravado em {MANIFEST_PATH}")
    else:
        unittest.main()
