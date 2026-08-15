# Refatoração de Legibilidade dos Extractors — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar `normal.py` e `ampliada.py` legíveis (nomes semânticos left/top/right/bottom, legenda de coordenadas, constantes nomeadas, funções pequenas) sem alterar a saída — os PNGs devem ficar byte-idênticos.

**Architecture:** Primeiro cria-se uma rede de segurança (golden test que fixa o `sha256` de cada PNG gerado pelo código atual a partir dos PDFs reais em `provas/`). Depois refatora-se cada extractor mantendo a API pública e a aritmética exata; o golden test deve permanecer verde a cada passo.

**Tech Stack:** Python, PyMuPDF (`fitz`), Pillow, `unittest`, `uv`.

**Verificação transversal:** após cada task, rodar `uv run python -m unittest discover -s tests` (suíte completa) e garantir que `tests/test_golden.py` continua verde.

---

### Task 1: Rede de segurança — golden test + manifesto

Cria o teste golden e gera o manifesto de hashes a partir do código **atual** (pré-refatoração). Isto DEVE ser feito antes de tocar nos extractors.

**Files:**
- Create: `tests/test_golden.py`
- Create: `tests/golden/manifest.json` (gerado por comando, não escrito à mão)

- [ ] **Step 1: Escrever o golden test**

Crie `tests/test_golden.py` com este conteúdo:

```python
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

import hashlib
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
```

- [ ] **Step 2: Gerar o manifesto a partir do código ATUAL**

Run: `uv run python tests/test_golden.py update`
Expected: imprime `Manifesto gravado em .../tests/golden/manifest.json`. O arquivo `tests/golden/manifest.json` passa a existir com as chaves `2023_D1_normal` e `2025_D1_ampliada`, cada uma mapeando nomes de PNG para hashes sha256.

- [ ] **Step 3: Rodar o golden test contra o código atual (deve passar)**

Run: `uv run python -m unittest tests.test_golden -v`
Expected: `test_output_matches_manifest` PASSA (as duas subTests). Isto confirma que o teste é determinístico e reflete a saída atual.

- [ ] **Step 4: Rodar a suíte completa (sem regressão)**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK` (com alguns skips pré-existentes). O total de testes deve aumentar em relação ao baseline (37) por causa do novo teste.

- [ ] **Step 5: Commit**

```bash
git add tests/test_golden.py tests/golden/manifest.json
git commit -m "test: golden test dos extractors (fixa saída antes da refatoração)"
```

---

### Task 2: Refatorar `normal.py`

Reescreve o extractor padrão com nomes semânticos, constantes e funções menores. A aritmética e a API pública (`extract_questions_normal(path, output)`) são preservadas exatamente — o golden test é a prova.

**Files:**
- Modify (rewrite): `src/enem_extractor/normal.py`
- Test (must stay green): `tests/test_golden.py`

- [ ] **Step 1: Confirmar o golden test verde ANTES de editar**

Run: `uv run python -m unittest tests.test_golden`
Expected: `OK`. (Ponto de partida limpo.)

- [ ] **Step 2: Reescrever `src/enem_extractor/normal.py`**

Substitua TODO o conteúdo de `src/enem_extractor/normal.py` por:

```python
"""Extração de questões da prova padrão do ENEM (layout de duas colunas).

Sistema de coordenadas (PyMuPDF): a origem fica no canto superior esquerdo e o
eixo y cresce para baixo. Um Rect é (left, top, right, bottom) — equivalente a
(x0, y0, x1, y1) na nomenclatura do fitz.
"""

import io
from pathlib import Path  # noqa: F401  (mantido: paridade com o módulo original)

import fitz  # PyMuPDF
from PIL import Image

# Recuo aplicado às bordas esquerda e superior do recorte (em pontos PDF).
EDGE_PADDING = 5
# Margem removida da borda direita da página ao recortar.
RIGHT_MARGIN = 30
# Espaço extra abaixo da última alternativa "E".
BOTTOM_PADDING = 10
# Tolerância (em pontos) para considerar duas questões na mesma coluna.
COLUMN_TOLERANCE = 10
# No dia 2 (D2) a numeração das questões continua a partir de 91.
D2_QUESTION_OFFSET = 90
# Fator de zoom na renderização (2x = maior definição).
ZOOM = 2


def extract_questions_normal(path, output):
    print(f"Opening PDF {path}")
    pdf_document = fitz.open(path)

    print(f"Total pages: {len(pdf_document)}")
    question_count = D2_QUESTION_OFFSET if "/D2" in str(output) else 0

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        if len(page.search_for("QUESTÃO")) == 0:
            continue

        questions, column_divider_x = find_questions_on_page(question_count + 1, page)
        if len(questions) == 0:
            continue
        question_count += len(questions)
        crop_questions_on_page(questions, column_divider_x, page, output)


def find_questions_on_page(initial_num, page):
    """Localiza os retângulos de cada "QUESTÃO NN" na página, a partir de
    `initial_num`. Retorna (dict número_formatado -> rect, x do divisor de
    coluna ou None)."""
    i = initial_num
    questions = {}
    left_edges = set()

    while True:
        found = page.search_for(f"QUESTÃO {i:02}")
        if len(found) == 0:
            break
        rect = found[0]
        questions[f"{i:03}"] = rect
        left_edges.add(int(rect.x0))  # arredonda para evitar variações pequenas
        i += 1

    # Se há dois grupos distintos de borda esquerda, a página tem duas colunas;
    # o maior x0 marca o início da coluna da direita.
    sorted_left_edges = sorted(left_edges)
    column_divider_x = max(sorted_left_edges) if len(sorted_left_edges) >= 2 else None

    return questions, column_divider_x


def find_last_alternative_bottom(page, clip):
    """Procura a alternativa "E" mais baixa dentro de `clip` e devolve a base do
    recorte (y da última "E" + BOTTOM_PADDING)."""
    alternatives = page.search_for("E", quads=False, clip=clip)
    last_alternative = alternatives[-1]  # a "E" mais abaixo encerra a questão
    return last_alternative.y1 + BOTTOM_PADDING


def crop_questions_on_page(questions, column_divider_x, page, output):
    page_bottom = page.rect.y1
    page_right = page.rect.x1
    keys = list(questions.keys())
    first_left = questions[keys[0]].x0

    for pos in range(len(keys)):
        key = keys[pos]
        current_rect = questions[key]

        left = current_rect.x0 - EDGE_PADDING
        top = current_rect.y0 - EDGE_PADDING
        right = page_right - RIGHT_MARGIN
        bottom = page_bottom

        if pos == len(keys) - 1:
            # Última questão da página: vai até a última alternativa "E".
            bottom = find_last_alternative_bottom(
                page, (left, top, right, page.rect.y1)
            )
        else:
            next_rect = questions[keys[pos + 1]]
            # Questão na coluna da esquerda: limita a direita ao divisor.
            if column_divider_x and abs(current_rect.x0 - first_left) < COLUMN_TOLERANCE:
                right = column_divider_x
            if abs(current_rect.x0 - next_rect.x0) < COLUMN_TOLERANCE:
                # Próxima questão na mesma coluna: a base é o topo dela.
                bottom = next_rect.y0
            else:
                # Próxima questão em outra coluna: a base é a última "E".
                bottom = find_last_alternative_bottom(
                    page, (left, top, right, page.rect.y1)
                )

        render_question_image((left, top, right, bottom), page, output, int(key))


def render_question_image(box, page, output, question_number):
    left, top, right, bottom = box
    rect = fitz.Rect(left, top, right, bottom)

    # Aumenta a resolução com zoom.
    matrix = fitz.Matrix(ZOOM, ZOOM)
    pix = page.get_pixmap(matrix=matrix, clip=rect)

    img = Image.open(io.BytesIO(pix.tobytes()))
    image_path = f"{output}/questao_{question_number:03}.png"
    img.save(image_path)
```

- [ ] **Step 3: Golden test DEVE continuar verde**

Run: `uv run python -m unittest tests.test_golden -v`
Expected: `test_output_matches_manifest` PASSA. Se falhar, a refatoração alterou a saída — reverta e ajuste até bater byte-a-byte. NÃO regenere o manifesto.

- [ ] **Step 4: Suíte completa sem regressão**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK` (mesmos skips de antes).

- [ ] **Step 5: Commit**

```bash
git add src/enem_extractor/normal.py
git commit -m "refactor(normal): nomes left/top/right/bottom, constantes e funções menores"
```

---

### Task 3: Refatorar `ampliada.py`

Mesma abordagem para o extractor da versão ampliada (coluna única). API pública (`extract_questions_ampliada(path, output)`) e aritmética preservadas.

**Files:**
- Modify (rewrite): `src/enem_extractor/ampliada.py`
- Test (must stay green): `tests/test_golden.py`

- [ ] **Step 1: Confirmar o golden test verde ANTES de editar**

Run: `uv run python -m unittest tests.test_golden`
Expected: `OK`.

- [ ] **Step 2: Reescrever `src/enem_extractor/ampliada.py`**

Substitua TODO o conteúdo de `src/enem_extractor/ampliada.py` por:

```python
"""Extração de questões da versão ampliada do ENEM (layout de coluna única).

Sistema de coordenadas (PyMuPDF): origem no canto superior esquerdo, y cresce
para baixo. Um Rect é (left, top, right, bottom) — equivalente a (x0, y0, x1, y1)
na nomenclatura do fitz.
"""

import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

# Recuo à esquerda do recorte (em pontos PDF).
LEFT_PADDING = 10
# Quanto o topo do recorte sobe a partir da base do título "QUESTÃO".
TITLE_TOP_ADJUST = 30
# Espaço extra abaixo da última alternativa "E".
BOTTOM_PADDING = 10
# A prova ampliada processa apenas as duas primeiras páginas.
PAGES_TO_PROCESS = 2


def extract_questions_ampliada(path, output):
    print(f"Opening PDF {path}")
    pdf_document = fitz.open(path)
    Path(output).mkdir(parents=True, exist_ok=True)
    print(f"Extracting images to {path}")

    print(f"Total pages: {len(pdf_document)}")
    for page_num in range(PAGES_TO_PROCESS):
        page = pdf_document[page_num]
        questions = page.search_for("QUESTÃO")  # Procurar por "QUESTÃO"
        for instance_num, question in enumerate(questions):
            crop_and_save_question(page, question, page_num, instance_num, output)


def crop_and_save_question(page, question, page_num, instance_num, output):
    # O título "QUESTÃO" delimita a esquerda e o topo do recorte.
    title_left, title_top, _, title_bottom = question
    page_right = page.rect.width

    # Procurar pela última alternativa "E" após a palavra "QUESTÃO".
    clip = (title_left, title_top, page_right, page.rect.y1)
    alternatives = page.search_for("E", quads=False, clip=clip)
    if not alternatives:
        print(
            f"Não foi possível encontrar a alternativa 'E' para a questão na "
            f"página {page_num + 1}"
        )
        return

    last_alternative = alternatives[-1]  # Posição da última alternativa "E"
    _, _, _, last_alternative_bottom = last_alternative

    # Definir a área da questão (pequeno espaço abaixo da última alternativa).
    left = title_left - LEFT_PADDING
    top = title_bottom - TITLE_TOP_ADJUST
    right = page_right
    bottom = last_alternative_bottom + BOTTOM_PADDING
    question_area = fitz.Rect(left, top, right, bottom)

    # Renderizar a área da questão como imagem e salvar.
    pix = page.get_pixmap(clip=question_area)
    img = Image.open(io.BytesIO(pix.tobytes()))
    image_path = f"{output}/page_{page_num + 1}_question_{instance_num + 1}.png"
    print(f"Saving image to {image_path}")
    img.save(image_path)
    print(f"Saved image {image_path}")


if __name__ == "__main__":
    extract_questions_ampliada(
        "provas/2025_PV_impresso_D1_CD9_ampliada.pdf",
        "imagens/2025/D1",
    )
```

- [ ] **Step 3: Golden test DEVE continuar verde**

Run: `uv run python -m unittest tests.test_golden -v`
Expected: PASSA. Se falhar, a saída mudou — ajuste até bater. NÃO regenere o manifesto.

- [ ] **Step 4: Suíte completa sem regressão**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add src/enem_extractor/ampliada.py
git commit -m "refactor(ampliada): nomes semânticos, constantes e função de recorte isolada"
```

---

## Self-Review

**Spec coverage:**
- Componente 1 (golden test versionado + manifesto, skip sem libs/PDFs) → Task 1. ✅
- Componente 2 (legenda de coordenadas + left/top/right/bottom + renomear funções `denife_rect`/`get_num_of_question_in_page`/`cut_image`) → Tasks 2 e 3. ✅
- Componente 3 (constantes nomeadas com os valores atuais) → Tasks 2 e 3. ✅
- Componente 4 (funções menores: `find_last_alternative_bottom`, `crop_questions_on_page`, `render_question_image`, `crop_and_save_question`) → Tasks 2 e 3. ✅
- API pública inalterada (`extract_questions_normal/ampliada(path, output)`) → preservada em ambas as reescritas. ✅
- Verificação (golden verde antes/depois + suíte completa) → passos 1/3/4 de cada task. ✅
- Fora de escopo (service.py, CLI, MCP, comportamento) → não tocados. ✅

**Placeholder scan:** nenhum TODO/TBD; o manifesto é gerado por comando real (`... update`), não escrito à mão.

**Consistência de nomes:** as funções citadas na reescrita do `normal.py`
(`find_questions_on_page`, `find_last_alternative_bottom`, `crop_questions_on_page`,
`render_question_image`) são exatamente as usadas nas chamadas internas do mesmo
arquivo. Em `ampliada.py`, `crop_and_save_question` é definida e chamada. As
constantes referenciadas (`EDGE_PADDING`, `RIGHT_MARGIN`, `BOTTOM_PADDING`,
`COLUMN_TOLERANCE`, `D2_QUESTION_OFFSET`, `ZOOM`, `LEFT_PADDING`,
`TITLE_TOP_ADJUST`, `PAGES_TO_PROCESS`) estão todas declaradas no topo do
respectivo módulo.

**Preservação de comportamento (revisão manual da aritmética):** para questões
da coluna esquerda não-finais, `right` recebe `column_divider_x` antes do cálculo
da base — igual ao original (`x1 = division_x` antes do `cut_image`). Para a
última questão da página, o clip da busca por "E" usa `right = page_right -
RIGHT_MARGIN` (não o divisor) — igual ao original. O golden test é a prova final.
