import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import enem_extractor.main as main_module
from enem_extractor.main import main


class MainModeArgTests(unittest.TestCase):
    """Tests for the --mode CLI argument in main()."""

    def _run_in_provas_dir(self, argv, pdf_names, fake_extract):
        """
        Helper: create a temp dir with a provas/ subdir containing the given
        pdf_names (empty files), monkeypatch main_module.extract with fake_extract,
        chdir into the temp dir, run main(argv), then restore CWD and the original
        extract in a finally block. Returns nothing — callers capture results via
        closure variables defined in the fake_extract they pass in.
        """
        original_extract = main_module.extract
        main_module.extract = fake_extract
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                provas = Path(tmp) / "provas"
                provas.mkdir()
                for name in pdf_names:
                    (provas / name).write_bytes(b"%PDF-1.4")
                os.chdir(tmp)
                main(argv)
        finally:
            os.chdir(original_cwd)
            main_module.extract = original_extract

    def test_mode_ampliada_passed_to_extract(self):
        """--mode ampliada forces mode="ampliada" for every PDF."""
        recorded = []

        def fake_extract(pdf_path, output_dir=None, mode="auto"):
            recorded.append({"pdf": pdf_path, "mode": mode})
            return {
                "pdf": pdf_path,
                "output_dir": "/tmp/out",
                "mode": mode,
                "images": [],
            }

        self._run_in_provas_dir(
            ["--mode", "ampliada"],
            ["prova_D1.pdf", "prova_D2.pdf"],
            fake_extract,
        )

        self.assertEqual(len(recorded), 2)
        for call in recorded:
            self.assertEqual(call["mode"], "ampliada")

    def test_mode_normal_passed_to_extract(self):
        """--mode normal forces mode="normal" for every PDF."""
        recorded = []

        def fake_extract(pdf_path, output_dir=None, mode="auto"):
            recorded.append({"pdf": pdf_path, "mode": mode})
            return {
                "pdf": pdf_path,
                "output_dir": "/tmp/out",
                "mode": mode,
                "images": [],
            }

        self._run_in_provas_dir(
            ["--mode", "normal"],
            ["prova_D1.pdf"],
            fake_extract,
        )

        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["mode"], "normal")

    def test_default_mode_is_auto(self):
        """No --mode argument defaults to mode="auto"."""
        recorded = []

        def fake_extract(pdf_path, output_dir=None, mode="auto"):
            recorded.append({"pdf": pdf_path, "mode": mode})
            return {
                "pdf": pdf_path,
                "output_dir": "/tmp/out",
                "mode": mode,
                "images": [],
            }

        self._run_in_provas_dir(
            [],
            ["prova_D1.pdf"],
            fake_extract,
        )

        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["mode"], "auto")

    def test_invalid_mode_raises_system_exit(self):
        """--mode bogus should cause argparse to raise SystemExit with code 2."""
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main(["--mode", "bogus"])
        self.assertEqual(ctx.exception.code, 2)

    def test_empty_provas_dir_zero_calls(self):
        """An empty provas/ dir results in zero extract calls (no crash)."""
        recorded = []

        def fake_extract(pdf_path, output_dir=None, mode="auto"):
            recorded.append(pdf_path)
            return {
                "pdf": pdf_path,
                "output_dir": "/tmp/out",
                "mode": mode,
                "images": [],
            }

        self._run_in_provas_dir([], [], fake_extract)

        self.assertEqual(recorded, [])


if __name__ == "__main__":
    unittest.main()
