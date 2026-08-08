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
