import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from enem_extractor import catalog


class ProvasDirTests(unittest.TestCase):
    def test_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(catalog.provas_dir(), Path("provas"))

    def test_env_override(self):
        with mock.patch.dict(os.environ, {"PROVAS_DIR": "/tmp/x"}, clear=True):
            self.assertEqual(catalog.provas_dir(), Path("/tmp/x"))


class ListProvasTests(unittest.TestCase):
    def test_lista_ordenada_com_modo_e_tamanho(self):
        with TemporaryDirectory() as d:
            (Path(d) / "2025_PV_impresso_D1_CD9_ampliada.pdf").write_bytes(b"AA")
            (Path(d) / "2023_PV_impresso_D1_CD4.pdf").write_bytes(b"B")
            (Path(d) / "2025_PV_impresso_D1_CD9_superampliada.pdf").write_bytes(b"CCC")
            (Path(d) / "nota.txt").write_text("ignorar")
            provas = catalog.list_provas(d)

        names = [p["name"] for p in provas]
        self.assertEqual(
            names,
            [
                "2023_PV_impresso_D1_CD4.pdf",
                "2025_PV_impresso_D1_CD9_ampliada.pdf",
                "2025_PV_impresso_D1_CD9_superampliada.pdf",
            ],
        )
        modes = {p["name"]: p["mode"] for p in provas}
        self.assertEqual(modes["2023_PV_impresso_D1_CD4.pdf"], "normal")
        self.assertEqual(modes["2025_PV_impresso_D1_CD9_ampliada.pdf"], "ampliada")
        self.assertEqual(modes["2025_PV_impresso_D1_CD9_superampliada.pdf"], "ampliada")
        first = provas[0]
        self.assertEqual(first["size_bytes"], 1)
        self.assertTrue(first["path"].endswith("2023_PV_impresso_D1_CD4.pdf"))

    def test_pasta_inexistente(self):
        self.assertEqual(catalog.list_provas("/caminho/que/nao/existe"), [])

    def test_pasta_vazia(self):
        with TemporaryDirectory() as d:
            self.assertEqual(catalog.list_provas(d), [])


class ResolveProvaTests(unittest.TestCase):
    def test_por_nome(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"x")
            self.assertEqual(catalog.resolve_prova(pdf.name, d), pdf)

    def test_por_nome_sem_extensao(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"x")
            self.assertEqual(
                catalog.resolve_prova("2023_PV_impresso_D1_CD4", d), pdf
            )

    def test_por_caminho(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"x")
            self.assertEqual(catalog.resolve_prova(str(pdf)), pdf)

    def test_inexistente(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                catalog.resolve_prova("nao_existe.pdf", d)

    def test_diretorio_tem_prioridade_sobre_cwd(self):
        with TemporaryDirectory() as cwd, TemporaryDirectory() as provas:
            nome = "2023_PV_impresso_D1_CD4.pdf"
            (Path(cwd) / nome).write_bytes(b"CWD")
            (Path(provas) / nome).write_bytes(b"PROVAS")
            old = os.getcwd()
            os.chdir(cwd)
            try:
                resolved = catalog.resolve_prova(nome, provas)
            finally:
                os.chdir(old)
            self.assertEqual(resolved.read_bytes(), b"PROVAS")
