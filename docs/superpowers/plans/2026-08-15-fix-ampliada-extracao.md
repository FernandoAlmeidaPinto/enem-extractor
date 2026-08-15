# Correção + Refatoração da Extração Ampliada — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer `ampliada.py` extrair uma imagem por questão (detecta "Questão NN", segmenta páginas multi-questão, cobre todas as páginas), aplicando as convenções de legibilidade da `normal.py`.

**Architecture:** A lógica de segmentação vira funções puras e testáveis (`find_question_headings`, `compute_question_boxes`, `question_filename`), separadas do render (PyMuPDF/Pillow importados de forma lazy). O orquestrador `extract_questions_ampliada` varre todas as páginas, detecta headings, calcula os recortes e renderiza. A verificação tem três camadas: testes unitários puros, revisão visual manual (paddings), e golden test estendido.

**Tech Stack:** Python, PyMuPDF (`fitz`, lazy), Pillow (lazy), `unittest`, `uv`.

**Verificação transversal:** após cada task, `uv run python -m unittest discover -s tests`.

---

### Task 1: Lógica de segmentação + reescrita de `ampliada.py`

Escreve os testes unitários das funções puras primeiro (TDD), depois reescreve o módulo.

**Files:**
- Create: `tests/test_ampliada.py`
- Modify (rewrite): `src/enem_extractor/ampliada.py`

- [ ] **Step 1: Escrever os testes unitários das funções puras**

Crie `tests/test_ampliada.py` com este conteúdo:

```python
"""Testes das funções puras de segmentação da extração ampliada.

Não exigem PyMuPDF/Pillow: as funções puras trabalham sobre listas de headings e
um objeto `page` falso (com get_text("words")). O render é lazy-import e não é
exercitado aqui.
"""

import unittest
from collections import Counter

from enem_extractor.ampliada import (
    FOOTER_MARGIN,
    HEADING_TOP_PADDING,
    SIDE_MARGIN,
    compute_question_boxes,
    find_question_headings,
    question_filename,
)


class FakePage:
    """Simula page.get_text("words") do PyMuPDF."""

    def __init__(self, words):
        self._words = words

    def get_text(self, kind):
        assert kind == "words"
        return self._words


def _word(text, x0=0.0, y0=0.0):
    # (x0, y0, x1, y1, text, block, line, word_no)
    return (x0, y0, x0 + 10, y0 + 12, text, 0, 0, 0)


class FindQuestionHeadingsTests(unittest.TestCase):
    def test_detecta_questao_seguida_de_numero(self):
        page = FakePage([_word("Questão", y0=100), _word("06", x0=60, y0=100)])
        self.assertEqual(find_question_headings(page), [(6, 100.0)])

    def test_multiplos_headings_na_pagina(self):
        page = FakePage(
            [
                _word("Questão", y0=100),
                _word("06", x0=60, y0=100),
                _word("bla", y0=150),
                _word("Questão", y0=300),
                _word("07", x0=60, y0=300),
            ]
        )
        self.assertEqual(find_question_headings(page), [(6, 100.0), (7, 300.0)])

    def test_ignora_questao_sem_numero(self):
        page = FakePage([_word("Questão", y0=100), _word("anterior", y0=100)])
        self.assertEqual(find_question_headings(page), [])

    def test_ignora_plural_questoes(self):
        page = FakePage([_word("Questões", y0=100), _word("06", y0=100)])
        self.assertEqual(find_question_headings(page), [])

    def test_aceita_sem_acento(self):
        page = FakePage([_word("Questao", y0=100), _word("06", y0=100)])
        self.assertEqual(find_question_headings(page), [(6, 100.0)])


class ComputeQuestionBoxesTests(unittest.TestCase):
    def test_entre_headings_consecutivos(self):
        boxes = compute_question_boxes([(6, 100.0), (7, 300.0)], 800, 1000)
        self.assertEqual(
            boxes[0],
            (6, (SIDE_MARGIN, 100.0 - HEADING_TOP_PADDING, 800 - SIDE_MARGIN, 300.0)),
        )

    def test_ultima_questao_vai_ate_base_menos_rodape(self):
        boxes = compute_question_boxes([(6, 100.0), (7, 300.0)], 800, 1000)
        self.assertEqual(
            boxes[1],
            (
                7,
                (
                    SIDE_MARGIN,
                    300.0 - HEADING_TOP_PADDING,
                    800 - SIDE_MARGIN,
                    1000 - FOOTER_MARGIN,
                ),
            ),
        )

    def test_ordena_por_posicao_vertical(self):
        boxes = compute_question_boxes([(7, 300.0), (6, 100.0)], 800, 1000)
        self.assertEqual([b[0] for b in boxes], [6, 7])

    def test_heading_unico_vai_ate_base(self):
        boxes = compute_question_boxes([(6, 100.0)], 800, 1000)
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0][1][3], 1000 - FOOTER_MARGIN)


class QuestionFilenameTests(unittest.TestCase):
    def test_primeira_ocorrencia(self):
        self.assertEqual(question_filename(1, Counter()), "questao_001.png")

    def test_segunda_ocorrencia_recebe_sufixo(self):
        seen = Counter()
        question_filename(1, seen)
        self.assertEqual(question_filename(1, seen), "questao_001_2.png")

    def test_numeros_diferentes_sem_sufixo(self):
        seen = Counter()
        question_filename(6, seen)
        self.assertEqual(question_filename(7, seen), "questao_007.png")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar os testes e confirmar que FALHAM**

Run: `uv run python -m unittest tests.test_ampliada`
Expected: FALHA no import (`cannot import name 'compute_question_boxes' from 'enem_extractor.ampliada'`), pois o módulo atual só expõe `extract_questions_ampliada`.

- [ ] **Step 3: Reescrever `src/enem_extractor/ampliada.py`**

Substitua TODO o conteúdo de `src/enem_extractor/ampliada.py` por:

```python
"""Extração de questões da versão ampliada do ENEM (layout de coluna única).

Sistema de coordenadas (PyMuPDF): origem no canto superior esquerdo, y cresce
para baixo. Um Rect é (left, top, right, bottom) — equivalente a (x0, y0, x1, y1)
na nomenclatura do fitz.

A prova ampliada usa o título "Questão NN" (mista), com uma ou mais questões por
página e um texto-base compartilhado em páginas separadas. Cada questão é
recortada do seu heading até o próximo heading da página (ou a base da página, se
for o último). PyMuPDF/Pillow são importados de forma lazy para que a lógica pura
de segmentação seja testável sem essas libs.
"""

import io
import re
import unicodedata
from collections import Counter
from pathlib import Path

# Recuo acima do heading "Questão NN" ao definir o topo do recorte (pontos PDF).
HEADING_TOP_PADDING = 5
# Margem removida da base da página na última questão (evita o rodapé).
FOOTER_MARGIN = 30
# Margem lateral do recorte (coluna única).
SIDE_MARGIN = 10
# Fator de zoom na renderização (2x = maior definição).
ZOOM = 2

# Um heading é a palavra "Questão" seguida do número da questão (2–3 dígitos).
_QUESTION_WORD = ("questão", "questao")
_NUMBER_RE = re.compile(r"^\d{2,3}$")


def _is_question_word(text):
    normalized = unicodedata.normalize("NFC", text).strip().lower()
    return normalized in _QUESTION_WORD


def find_question_headings(page):
    """Localiza os headings "Questão NN" da página via get_text("words").

    Retorna [(numero:int, top_y:float)] — o y0 da palavra "Questão". Ignora
    ocorrências de "Questão" não seguidas de número (ex.: no corpo do texto) e o
    plural "Questões"."""
    words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word_no)
    headings = []
    for idx, word in enumerate(words):
        text = word[4]
        if _is_question_word(text) and idx + 1 < len(words):
            next_text = words[idx + 1][4]
            if _NUMBER_RE.match(next_text):
                headings.append((int(next_text), word[1]))
    return headings


def compute_question_boxes(headings, page_width, page_height):
    """Segmenta a página: recorta cada questão do seu heading até o próximo (ou a
    base da página, se for o último). Retorna [(numero, (left, top, right,
    bottom))] ordenado de cima para baixo."""
    ordered = sorted(headings, key=lambda heading: heading[1])
    left = SIDE_MARGIN
    right = page_width - SIDE_MARGIN

    boxes = []
    for pos, (number, top_y) in enumerate(ordered):
        top = top_y - HEADING_TOP_PADDING
        if pos + 1 < len(ordered):
            bottom = ordered[pos + 1][1]  # topo do próximo heading
        else:
            bottom = page_height - FOOTER_MARGIN
        boxes.append((number, (left, top, right, bottom)))
    return boxes


def question_filename(number, seen):
    """Nome do PNG da questão. `seen` (Counter) rastreia repetições do número: a
    2ª ocorrência (inglês→espanhol nas 1–5) recebe sufixo `_2`."""
    seen[number] += 1
    suffix = "" if seen[number] == 1 else f"_{seen[number]}"
    return f"questao_{number:03}{suffix}.png"


def extract_questions_ampliada(path, output):
    import fitz  # PyMuPDF (lazy)

    print(f"Opening PDF {path}")
    pdf_document = fitz.open(path)
    Path(output).mkdir(parents=True, exist_ok=True)
    print(f"Total pages: {len(pdf_document)}")

    seen = Counter()
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        headings = find_question_headings(page)
        if not headings:
            continue
        boxes = compute_question_boxes(headings, page.rect.width, page.rect.height)
        for number, box in boxes:
            render_question_image(box, page, output, question_filename(number, seen))


def render_question_image(box, page, output, filename):
    import fitz  # PyMuPDF (lazy)
    from PIL import Image  # Pillow (lazy)

    left, top, right, bottom = box
    rect = fitz.Rect(left, top, right, bottom)
    matrix = fitz.Matrix(ZOOM, ZOOM)
    pix = page.get_pixmap(matrix=matrix, clip=rect)
    img = Image.open(io.BytesIO(pix.tobytes()))
    img.save(f"{output}/{filename}")


if __name__ == "__main__":
    extract_questions_ampliada(
        "provas/2025_PV_impresso_D1_CD9_ampliada.pdf",
        "imagens/2025/D1",
    )
```

- [ ] **Step 4: Rodar os testes unitários e confirmar que PASSAM**

Run: `uv run python -m unittest tests.test_ampliada -v`
Expected: os 11 testes PASSAM.

- [ ] **Step 5: Smoke — extrair a prova ampliada real e reportar cobertura**

Run:
```bash
uv run python - <<'PY'
import tempfile, re
from pathlib import Path
from enem_extractor.service import extract
with tempfile.TemporaryDirectory() as d:
    extract("provas/2025_PV_impresso_D1_CD9_ampliada.pdf", output_dir=d, mode="ampliada")
    pngs = sorted(p.name for p in Path(d).glob("*.png"))
    nums = sorted({int(re.match(r"questao_(\d+)", n).group(1)) for n in pngs})
    dups = [n for n in pngs if "_2" in n]
    print(f"total PNGs: {len(pngs)}")
    print(f"numeros cobertos: {nums[:5]}...{nums[-3:]}  (faltando de 1-90: {sorted(set(range(1,91))-set(nums))})")
    print(f"duplicadas (_2): {dups}")
PY
```
Expected (observação, não asserção rígida): produz muitos PNGs (~95); os números 1–90 aparecem cobertos (lista de faltando idealmente vazia); há duplicadas `questao_001_2.png`..`questao_005_2.png`. Anote os números exatos no relatório — desvios (ex.: falsos positivos, números faltando) são o que a revisão visual da Task 2 vai examinar.

- [ ] **Step 6: Suíte completa sem regressão**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK`. O golden test do `2025_D1_ampliada` ainda compara contra o manifesto `{}` atual — **espera-se que ele FALHE agora**, pois a ampliada passou a gerar imagens. Isso é esperado e será resolvido na Task 3 (regeneração do manifesto após a aprovação visual). Se preferir manter a suíte verde entre as tasks, rode apenas os testes não-golden aqui: `uv run python -m unittest tests.test_ampliada tests.test_service tests.test_catalog tests.test_main` (Expected: `OK`).

- [ ] **Step 7: Commit**

```bash
git add tests/test_ampliada.py src/enem_extractor/ampliada.py
git commit -m "fix(ampliada): detecta 'Questão NN', segmenta multi-questão e cobre todas as páginas"
```

---

### Task 2 (CHECKPOINT COM O USUÁRIO): Revisão visual e ajuste de paddings

> Esta task é um checkpoint interativo conduzido pelo controlador com o usuário —
> **não** um subagente. Os valores de `HEADING_TOP_PADDING`, `FOOTER_MARGIN` e
> `SIDE_MARGIN` são chutes iniciais e só podem ser afinados vendo as imagens.

**Files:**
- Possibly modify: `src/enem_extractor/ampliada.py` (apenas os valores das constantes)

- [ ] **Step 1: Gerar as imagens da ampliada D1 numa pasta inspecionável**

Run:
```bash
uv run python -c "from enem_extractor.service import extract; print(extract('provas/2025_PV_impresso_D1_CD9_ampliada.pdf', output_dir='imagens/_ampliada_review', mode='ampliada')['output_dir'])"
```
Expected: cria `imagens/_ampliada_review/` com os PNGs. (Pasta sob `imagens/`, ignorada pelo Git.)

- [ ] **Step 2: Apresentar amostras ao usuário e coletar feedback**

Abrir para inspeção do usuário uma amostra representativa: uma questão de página
com heading único (ex.: `questao_011.png`), uma de página multi-questão
(ex.: `questao_006.png` e `questao_007.png`), a última questão de uma página
(para conferir o rodapé), e uma duplicada (`questao_001.png` vs `questao_001_2.png`).
Perguntar: os recortes cortam conteúdo? Sobra rodapé/cabeçalho? As margens estão boas?

- [ ] **Step 3: Ajustar constantes se necessário**

Se o usuário pedir ajustes, editar SOMENTE os valores de `HEADING_TOP_PADDING`,
`FOOTER_MARGIN` e/ou `SIDE_MARGIN` em `src/enem_extractor/ampliada.py`, e repetir
os Steps 1–2 até aprovação. Os testes unitários da Task 1 continuam válidos (usam
as constantes, não valores fixos): rode `uv run python -m unittest tests.test_ampliada` para confirmar.

- [ ] **Step 4: Limpar a pasta de review e commitar ajustes (se houver)**

```bash
rm -rf imagens/_ampliada_review
# só se houve ajuste de constantes:
git add src/enem_extractor/ampliada.py
git commit -m "fix(ampliada): ajusta paddings do recorte após revisão visual"
```

---

### Task 3: Estender o golden test para cobrir a ampliada

Regenera o manifesto para fixar a saída aprovada da ampliada (hoje `{}`), blindando regressões.

**Files:**
- Modify (regenerado): `tests/golden/manifest.json`

- [ ] **Step 1: Confirmar que a ampliada agora gera imagens**

Run: `uv run python tests/test_golden.py update`
Expected: imprime `Manifesto gravado em .../manifest.json`. O comando roda o código atual (normal + ampliada) e grava os hashes.

- [ ] **Step 2: Confirmar que o manifesto da ampliada deixou de ser vazio**

Run: `uv run python -c "import json; m=json.load(open('tests/golden/manifest.json')); print('normal:', len(m['2023_D1_normal']), 'ampliada:', len(m['2025_D1_ampliada']))"`
Expected: `normal: 90 ampliada: N` com **N > 0** (dezenas de imagens). O `2023_D1_normal` permanece com 90 (inalterado).

- [ ] **Step 3: Golden test verde**

Run: `uv run python -m unittest tests.test_golden -v`
Expected: `test_output_matches_manifest` PASSA para as duas amostras (normal e ampliada).

- [ ] **Step 4: Suíte completa verde**

Run: `uv run python -m unittest discover -s tests`
Expected: `OK` (agora sem a falha do golden, pois o manifesto reflete a saída real).

- [ ] **Step 5: Commit**

```bash
git add tests/golden/manifest.json
git commit -m "test(golden): fixa a saída da extração ampliada (manifesto real)"
```

---

## Self-Review

**Spec coverage:**
- Componente 1 (detecção genérica via "Questão"+número) → `find_question_headings` (Task 1, testes incluem plural, sem-número, sem-acento). ✅
- Componente 2 (segmentação entre headings, último até base−rodapé) → `compute_question_boxes` (Task 1, testes cobrem consecutivos/último/ordenação). ✅
- Componente 3 (nomes com sufixo `_2`) → `question_filename` (Task 1, testes de 1ª/2ª ocorrência). ✅
- Componente 4 (legibilidade: legenda, left/top/right/bottom, constantes, funções pequenas, API pública inalterada, imports lazy) → reescrita na Task 1. ✅
- Verificação camada 1 (unitário puro) → Task 1. ✅
- Verificação camada 2 (revisão visual + tuning de paddings) → Task 2. ✅
- Verificação camada 3 (golden estendido, regenera manifesto) → Task 3. ✅
- Escopo/YAGNI (sem costura de texto-base/cross-página; superampliada de brinde; D2 sem amostra) → respeitado; nenhuma task adiciona isso. ✅

**Placeholder scan:** nenhum TODO/TBD; o smoke da Task 1 é observação declarada (não asserção rígida) por não haver ground-truth; o manifesto é gerado por comando real.

**Consistência de nomes:** `find_question_headings`, `compute_question_boxes`,
`question_filename`, `render_question_image` e as constantes
`HEADING_TOP_PADDING`/`FOOTER_MARGIN`/`SIDE_MARGIN`/`ZOOM` são idênticas entre a
reescrita do módulo (Task 1, Step 3) e os imports do teste (Task 1, Step 1). A API
pública `extract_questions_ampliada(path, output)` é preservada (usada por
`service.py` e `__init__.py`). O golden test (Task 3) reutiliza a amostra
`2025_D1_ampliada` já presente em `tests/test_golden.py`.

**Nota sobre a suíte entre tasks:** após a Task 1 o golden test fica
temporariamente vermelho (o manifesto ainda é `{}` para a ampliada); isso é
esperado e resolvido na Task 3. O Step 6 da Task 1 documenta como rodar só os
testes não-golden nesse intervalo.
