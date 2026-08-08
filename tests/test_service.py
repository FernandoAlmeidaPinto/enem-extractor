import tempfile
import unittest
from pathlib import Path

from enem_extractor import service


class DetectModeTests(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(service.detect_mode("2023_PV_impresso_D1_CD4.pdf"), "normal")

    def test_ampliada(self):
        self.assertEqual(
            service.detect_mode("2025_PV_impresso_D1_CD9_ampliada.pdf"), "ampliada"
        )

    def test_superampliada_usa_rota_ampliada(self):
        self.assertEqual(
            service.detect_mode("2025_PV_impresso_D1_CD9_superampliada.pdf"), "ampliada"
        )

    def test_case_insensitive(self):
        self.assertEqual(service.detect_mode("2025_PV_AMPLIADA.PDF"), "ampliada")

    def test_usa_apenas_o_nome_do_arquivo(self):
        # pasta chamada "ampliada" não deve influenciar
        self.assertEqual(service.detect_mode("/x/ampliada/2023_CD4.pdf"), "normal")


class DefaultOutputDirTests(unittest.TestCase):
    def test_dia1(self):
        self.assertEqual(
            service.default_output_dir("2023_PV_impresso_D1_CD4.pdf"),
            Path("imagens/2023/D1"),
        )

    def test_dia2(self):
        self.assertEqual(
            service.default_output_dir("2023_PV_impresso_D2_CD4.pdf"),
            Path("imagens/2023/D2"),
        )

    def test_sem_dia_usa_d1(self):
        self.assertEqual(
            service.default_output_dir("2023_PV_impresso_CD4.pdf"),
            Path("imagens/2023/D1"),
        )


class PublicApiTests(unittest.TestCase):
    def test_importa_pacote_sem_libs_pesadas(self):
        import enem_extractor

        self.assertTrue(callable(enem_extractor.detect_mode))

    def test_atributo_inexistente(self):
        import enem_extractor

        with self.assertRaises(AttributeError):
            enem_extractor.nao_existe


class ExtractValidationTests(unittest.TestCase):
    def test_mode_invalido(self):
        with self.assertRaises(ValueError):
            service.extract("qualquer.pdf", mode="bogus")

    def test_arquivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            service.extract("nao_existe.pdf", mode="normal")


class ExtractRoutingTests(unittest.TestCase):
    def test_roteia_normal_e_retorna_metadados(self):
        calls = {}

        def fake(pdf_path, output_dir):
            calls["pdf"] = pdf_path
            calls["out"] = str(output_dir)
            (Path(output_dir) / "questao_001.png").write_bytes(b"x")

        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            out = Path(d) / "out"
            original = service._EXTRACTORS["normal"]
            service._EXTRACTORS["normal"] = fake
            try:
                res = service.extract(str(pdf), output_dir=str(out), mode="auto")
            finally:
                service._EXTRACTORS["normal"] = original

        self.assertEqual(res["mode"], "normal")
        self.assertEqual(res["output_dir"], str(out))
        self.assertEqual(res["images"], [str(out / "questao_001.png")])
        self.assertEqual(calls["pdf"], str(pdf))

    def test_auto_detecta_ampliada(self):
        seen = {}

        def fake(pdf_path, output_dir):
            seen["called"] = True

        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "2025_PV_impresso_D1_CD9_ampliada.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            out = Path(d) / "o"
            original = service._EXTRACTORS["ampliada"]
            service._EXTRACTORS["ampliada"] = fake
            try:
                res = service.extract(str(pdf), output_dir=str(out))
            finally:
                service._EXTRACTORS["ampliada"] = original

        self.assertEqual(res["mode"], "ampliada")
        self.assertTrue(seen.get("called"))

    def test_forca_modo_normal(self):
        seen = {}

        def fake(pdf_path, output_dir):
            seen["called"] = True

        with tempfile.TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            out = Path(d) / "out"
            original = service._EXTRACTORS["normal"]
            service._EXTRACTORS["normal"] = fake
            try:
                res = service.extract(str(pdf), output_dir=str(out), mode="normal")
            finally:
                service._EXTRACTORS["normal"] = original

        self.assertEqual(res["mode"], "normal")
        self.assertTrue(seen.get("called"))

    def test_expoe_extract_no_pacote(self):
        import enem_extractor

        self.assertIs(enem_extractor.extract, service.extract)
