import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    import mcp  # noqa: F401
    from enem_extractor import mcp_server

    _HAS_MCP = True
except Exception:
    _HAS_MCP = False


@unittest.skipUnless(_HAS_MCP, "mcp não instalado")
class McpServerTests(unittest.TestCase):
    def test_build_server_ok(self):
        srv = mcp_server.build_server()
        self.assertEqual(srv.name, "enem-extractor")

    def test_resource_specs_inclui_provas_e_agregado(self):
        with TemporaryDirectory() as d:
            (Path(d) / "2023_PV_impresso_D1_CD4.pdf").write_bytes(b"%PDF")
            (Path(d) / "2025_PV_impresso_D1_CD9_ampliada.pdf").write_bytes(b"%PDF")
            specs = mcp_server._resource_specs(d)

        uris = [s["uri"] for s in specs]
        self.assertIn("prova://2023_PV_impresso_D1_CD4.pdf", uris)
        self.assertIn("prova://2025_PV_impresso_D1_CD9_ampliada.pdf", uris)
        self.assertIn("provas://list", uris)

    def test_list_provas_tool_scan_ao_vivo(self):
        with TemporaryDirectory() as d:
            (Path(d) / "2023_PV_impresso_D1_CD4.pdf").write_bytes(b"%PDF")
            old = os.environ.get("PROVAS_DIR")
            os.environ["PROVAS_DIR"] = d
            try:
                provas = mcp_server.list_provas_tool()
            finally:
                if old is None:
                    os.environ.pop("PROVAS_DIR", None)
                else:
                    os.environ["PROVAS_DIR"] = old

        self.assertEqual(len(provas), 1)
        self.assertEqual(provas[0]["mode"], "normal")

    def test_extract_prova_tool_arquivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            mcp_server.extract_prova_tool("nao_existe.pdf")

    def test_extract_prova_tool_mode_invalido(self):
        with TemporaryDirectory() as d:
            pdf = Path(d) / "2023_PV_impresso_D1_CD4.pdf"
            pdf.write_bytes(b"%PDF")
            with self.assertRaises(ValueError):
                mcp_server.extract_prova_tool(str(pdf), mode="bogus")
