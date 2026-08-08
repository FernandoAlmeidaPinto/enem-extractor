# Worker Dispatcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar uma entrada única `extract(pdf_path, output_dir, mode)` que detecta prova ampliada pelo nome (ou aceita modo forçado) e roteia para o extractor correto, deixando o pacote pronto para uso como worker.

**Architecture:** Um módulo `service.py` concentra a API pública (`detect_mode`, `default_output_dir`, `extract`) com imports *lazy* dos extractors pesados (PyMuPDF/Pillow) para permanecer testável sem essas libs. O `__init__.py` também expõe os extractors via `__getattr__` lazy, então `import enem_extractor` não exige fitz. O roteamento passa por um dicionário `_EXTRACTORS` (seam de teste). A assinatura de `extract_questions_ampliada` é padronizada para `(path, output)`, igual à `normal`, sem tocar no algoritmo. `main.py` e o worker compartilham `extract`.

**Tech Stack:** Python 3.10+, PyMuPDF, Pillow (runtime); `unittest` stdlib (testes, zero instalação).

---

## File Structure

- Create: `src/enem_extractor/service.py` — API pública: `detect_mode`, `default_output_dir`, `get_year_and_day`, `extract`, seam `_EXTRACTORS`.
- Modify: `src/enem_extractor/__init__.py` — expõe `extract`/`detect_mode` eager (via service) e os extractors via `__getattr__` lazy.
- Modify: `src/enem_extractor/ampliada.py` — assinatura `(path, output)`; algoritmo inalterado.
- Modify: `src/enem_extractor/main.py` — passa a usar `extract`.
- Create: `tests/__init__.py` — pacote de testes (vazio).
- Create: `tests/test_service.py` — testes de `detect_mode`, `default_output_dir`, import do pacote, validações e roteamento (sem fitz/PIL).
- Modify: `README.md` — seção de uso como serviço/worker.

**Convenção de execução dos testes** (src layout, sem instalar o pacote):
`PYTHONPATH=src python3 -m unittest discover -s tests -v`

**Nota de ordenação:** o `__init__.py` atual importa `.normal`/`.ampliada` de forma eager, o que puxa `fitz` e faz `import enem_extractor` falhar sem as libs. Por isso a Task 1 já torna o `__init__.py` lazy — é pré-requisito para qualquer teste importar o pacote.

---

## Task 1: `service.py` (helpers) + `__init__.py` lazy

Torna o pacote importável sem PyMuPDF/Pillow e adiciona os helpers puros.

**Files:**
- Create: `src/enem_extractor/service.py`
- Modify: `src/enem_extractor/__init__.py`
- Create: `tests/__init__.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Criar o pacote de testes**

Criar `tests/__init__.py` vazio (arquivo sem conteúdo).

- [ ] **Step 2: Escrever os testes que falham**

Criar `tests/test_service.py`:

```python
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
```

- [ ] **Step 3: Rodar os testes e ver falhar**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: FAIL na coleta — `import enem_extractor` executa o `__init__.py` atual, que importa `.normal` → `ModuleNotFoundError: No module named 'fitz'`.

- [ ] **Step 4: Criar `src/enem_extractor/service.py` com os helpers puros**

```python
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
```

- [ ] **Step 5: Reescrever `src/enem_extractor/__init__.py` (lazy)**

```python
"""Extrator de questões do ENEM a partir de PDFs de prova."""

from .service import detect_mode, default_output_dir, get_year_and_day

__all__ = [
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
```

- [ ] **Step 6: Rodar os testes e ver passar**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS — 10 testes OK.

- [ ] **Step 7: Commit**

```bash
git add src/enem_extractor/service.py src/enem_extractor/__init__.py tests/__init__.py tests/test_service.py
git commit -m "feat(service): helpers puros + __init__ lazy (pacote importável sem fitz)"
```

---

## Task 2: `extract()` com validação e roteamento

**Files:**
- Modify: `src/enem_extractor/service.py`
- Modify: `src/enem_extractor/__init__.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: Escrever os testes que falham (validação + roteamento)**

Adicionar ao fim de `tests/test_service.py`:

```python
import tempfile


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

    def test_expoe_extract_no_pacote(self):
        import enem_extractor

        self.assertIs(enem_extractor.extract, service.extract)
```

- [ ] **Step 2: Rodar os testes e ver falhar**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: FAIL — `AttributeError: module 'enem_extractor.service' has no attribute 'extract'` / `_EXTRACTORS`.

- [ ] **Step 3: Implementar `extract` + seam `_EXTRACTORS` em `service.py`**

Adicionar ao fim de `src/enem_extractor/service.py`:

```python
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
```

- [ ] **Step 4: Expor `extract` no `__init__.py`**

Editar a linha de import e o `__all__` de `src/enem_extractor/__init__.py`:

Trocar:
```python
from .service import detect_mode, default_output_dir, get_year_and_day

__all__ = [
    "detect_mode",
```
Por:
```python
from .service import extract, detect_mode, default_output_dir, get_year_and_day

__all__ = [
    "extract",
    "detect_mode",
```

- [ ] **Step 5: Rodar os testes e ver passar**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS — 15 testes OK.

- [ ] **Step 6: Commit**

```bash
git add src/enem_extractor/service.py src/enem_extractor/__init__.py tests/test_service.py
git commit -m "feat(service): extract() com validação e roteamento por modo"
```

---

## Task 3: Padronizar assinatura de `ampliada.py`

**Files:**
- Modify: `src/enem_extractor/ampliada.py`

Objetivo: trocar `(path)` por `(path, output)` — `path` já vem com `.pdf`, saída vai para `output`. **O algoritmo (laço de 2 páginas, busca por QUESTÃO/E, matemática do retângulo) não muda.**

- [ ] **Step 1: Substituir o conteúdo de `src/enem_extractor/ampliada.py`**

```python
import fitz  # PyMuPDF
from PIL import Image
import io
from pathlib import Path

def extract_questions_ampliada(path, output):
    # Abrir o PDF (path já vem com .pdf)
    pdf_path = path
    print(f"Opening PDF {pdf_path}")
    pdf_document = fitz.open(pdf_path)
    Path(output).mkdir(parents=True, exist_ok=True)
    print(f"Extracting images to {pdf_path}")

    print(f"Total pages: {len(pdf_document)}")
    for page_num in range(2):
        page = pdf_document[page_num]
        questions = page.search_for("QUESTÃO")  # Procurar por "QUESTÃO"
        for instance_num, question in enumerate(questions):
            # Encontrar a posição inicial da questão
            x0, y0, _, y1 = question
            x1 = page.rect.width
            # Procurar pela última alternativa "E" após a palavra "QUESTÃO"
            alternatives = page.search_for("E", quads=False, clip=(x0, y0, x1, page.rect.y1))
            if alternatives:
                alternative = alternatives[-1]  # Posição da última alternativa "E"
                x2, y2, x3, y3 = alternative
                # Definir a área da questão
                question_area = fitz.Rect(x0 -10, y1 - 30, x1, y3 + 10)  # Adicionar um pequeno espaço abaixo da última alternativa

                # Renderizar a área da questão como uma imagem
                pix = page.get_pixmap(clip=question_area)
                img = Image.open(io.BytesIO(pix.tobytes()))
                # Salvar a imagem
                image_path = f"{output}/page_{page_num + 1}_question_{instance_num + 1}.png"
                print(f"Saving image to {image_path}")
                img.save(image_path)
                print(f"Saved image {image_path}")
            else:
                print(f"Não foi possível encontrar a alternativa 'E' para a questão na página {page_num + 1}")


if __name__ == "__main__":
    extract_questions_ampliada(
        "provas/2025_PV_impresso_D1_CD9_ampliada.pdf",
        "imagens/2025/D1",
    )
```

- [ ] **Step 2: Verificar que o módulo compila**

Run: `python3 -m py_compile src/enem_extractor/ampliada.py && echo OK`
Expected: `OK` (só valida sintaxe; não importa `fitz`).

- [ ] **Step 3: Garantir que os testes continuam passando**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS — 15 testes OK (os testes não abrem PDF, então independem de fitz).

- [ ] **Step 4: Commit**

```bash
git add src/enem_extractor/ampliada.py
git commit -m "refactor(ampliada): assinatura (path, output) alinhada à normal"
```

---

## Task 4: `main.py` usa o dispatcher

**Files:**
- Modify: `src/enem_extractor/main.py`

- [ ] **Step 1: Reescrever `src/enem_extractor/main.py`**

```python
from pathlib import Path

from .service import extract


def main():
    provas_dir = Path("provas")

    for pdf_file in sorted(provas_dir.glob("*.pdf")):
        result = extract(str(pdf_file))
        print(
            f"Processado: {result['pdf']} -> {result['output_dir']} "
            f"(modo={result['mode']}, {len(result['images'])} imagens)"
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar que importa sem libs pesadas**

Run: `PYTHONPATH=src python3 -c "import enem_extractor.main; print('import OK')"`
Expected: `import OK` (o import de `fitz` só acontece quando `extract` roteia de fato).

- [ ] **Step 3: Garantir que os testes continuam passando**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS — 15 testes OK.

- [ ] **Step 4: Commit**

```bash
git add src/enem_extractor/main.py
git commit -m "refactor(main): CLI usa service.extract (trata normal e ampliada)"
```

---

## Task 5: Documentar uso como worker no README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Adicionar a seção de uso como serviço no `README.md`**

Inserir, logo após a seção `## Uso` existente, o bloco abaixo:

````markdown
## Uso como serviço / worker

O pacote expõe uma entrada única `extract`, ideal para ser chamada por um worker:

```python
from enem_extractor import extract

# auto-detecção do tipo pelo nome do arquivo
result = extract("provas/2025_PV_impresso_D1_CD9_ampliada.pdf")

# forçando modo e pasta de saída
result = extract(pdf_path, output_dir="/tmp/out", mode="normal")

# result == {
#     "pdf": "...",
#     "mode": "ampliada",          # 'normal' | 'ampliada'
#     "output_dir": "imagens/2025/D1",
#     "images": ["imagens/2025/D1/page_1_question_1.png", ...],
# }
```

- `mode`: `"auto"` (padrão) detecta pelo nome (`ampliada`/`superampliada` → extractor
  ampliada; caso contrário normal). Use `"normal"` ou `"ampliada"` para forçar.
- `output_dir`: se omitido, deriva `imagens/<ano>/<dia>` do nome do arquivo.
- Erros: `FileNotFoundError` se o PDF não existir; `ValueError` se `mode` for inválido.
````

- [ ] **Step 2: Rodar os testes (garantia de que nada quebrou)**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
Expected: PASS — 15 testes OK.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: uso do pacote como serviço/worker"
```

---

## Verificação de integração (rodar em ambiente com dependências)

Estes passos exigem `pip install -r requirements.txt` (PyMuPDF/Pillow) e os PDFs em `provas/`. Não rodam neste ambiente sem as libs.

- [ ] **Ampliada (auto-detecção):**

Run:
```bash
PYTHONPATH=src python3 -c "from enem_extractor import extract; print(extract('provas/2025_PV_impresso_D1_CD9_ampliada.pdf'))"
```
Expected: dict com `"mode": "ampliada"` e a lista de imagens geradas em `imagens/2025/D1/`.

- [ ] **Normal (auto-detecção):**

Run:
```bash
PYTHONPATH=src python3 -c "from enem_extractor import extract; print(extract('provas/2023_PV_impresso_D1_CD4.pdf'))"
```
Expected: dict com `"mode": "normal"` e imagens `questao_*.png` em `imagens/2023/D1/`.

- [ ] **CLI completo:**

Run: `PYTHONPATH=src python3 -m enem_extractor.main`
Expected: uma linha `Processado: ...` por PDF em `provas/`, roteando ampliada e normal corretamente.

---

## Notas de escopo (do spec, não alterar)

- `ampliada` continua lendo **apenas 2 páginas** (hardcoded).
- Offset `/D2` da `normal` depende de `str(output_dir)` conter `/D2`; preservado com o `output_dir` derivado. `output_dir` custom sem `D2` não aplica o offset.
- Nenhuma mudança no algoritmo de recorte de nenhum extractor.
