# Design: Refatoração de legibilidade dos extractors (`normal.py` + `ampliada.py`)

**Data:** 2026-08-15
**Status:** Aprovado

## Contexto e problema

Os módulos de extração `src/enem_extractor/normal.py` e
`src/enem_extractor/ampliada.py` recortam cada questão de um PDF do ENEM em
imagens PNG usando coordenadas do PyMuPDF. O código funciona, mas é difícil de
ler:

- Geometria críptica: variáveis `x0, y0, x1, y1` (no PyMuPDF um `Rect` é
  `(x0, y0, x1, y1)` = esquerda, topo, direita, base; origem no canto superior
  esquerdo, `y` cresce para baixo).
- Nomes de função confusos ou com typo: `denife_rect` (typo de "define"),
  `get_num_of_question_in_page`, `cut_image`.
- Números mágicos sem explicação: `-5`, `- 30`, `+10`, tolerância de coluna
  `< 10`, offset `90` do D2, zoom `2`.
- Funções longas com múltiplas responsabilidades (`denife_rect` calcula limites,
  detecta a última alternativa "E", trata coluna dupla e a última questão da
  página — tudo junto).

## Objetivo

Tornar o código legível **sem alterar comportamento**: a saída (os PNGs) deve
ficar **byte-idêntica**. Renomear geometria para termos claros, adicionar uma
legenda do sistema de coordenadas, extrair constantes nomeadas e quebrar funções
grandes em unidades pequenas e testáveis.

## Restrições (garantia de "sem quebrar")

- **API pública estável:** `extract_questions_normal(path, output)` e
  `extract_questions_ampliada(path, output)` são usadas por `service.py` e pelo
  lazy export em `__init__.py`. Assinaturas e nomes NÃO mudam.
- **Funções internas livres:** `get_num_of_question_in_page`, `denife_rect`,
  `cut_image` só são usadas dentro do próprio `normal.py` — podem ser renomeadas
  e reorganizadas.
- **Aritmética exata preservada:** todos os offsets e heurísticas mantêm os
  valores atuais; apenas ganham nomes.
- Ativos disponíveis para baseline: PDFs reais em `provas/`
  (`2023_PV_impresso_D1_CD4.pdf`, `2025_PV_impresso_D1_CD9_ampliada.pdf`) e 90
  PNGs em `imagens/2023/D1`.

## Solução

### Convenções decididas
- **Idioma dos nomes:** inglês — `left / top / right / bottom` para as bordas,
  com uma legenda em comentário mapeando para os cantos.
- **Rede de segurança:** teste golden automatizado e versionado.

### Componente 1 — Golden test (rede de segurança, feito ANTES da refatoração)
- Gerar `tests/golden/manifest.json` com o `sha256` de cada PNG produzido pelo
  código **atual** ao extrair os PDFs de amostra de `provas/`.
- Criar `tests/test_golden.py` que re-extrai os mesmos PDFs para uma pasta
  temporária e compara cada imagem contra o manifesto.
- O teste **skipa** (não falha) quando PyMuPDF/Pillow não estão instalados ou os
  PDFs de amostra não existem (`provas/` é gitignored, então em CI/clone limpo o
  teste pula). Nota: o manifesto é específico das versões travadas no `uv.lock`
  (PyMuPDF/Pillow) e da máquina; o propósito primário é blindar ESTA refatoração
  no ambiente de desenvolvimento e servir de guarda futura no mesmo ambiente.
- O teste fica verde com o código atual e deve permanecer verde a cada passo.

### Componente 2 — Nomes semânticos + legenda
- Legenda no topo de cada extractor: "PDF origin is top-left; y grows downward;
  a Rect = (left, top, right, bottom)".
- `x0/y0/x1/y1` → `left/top/right/bottom` e intermediários descritivos
  (`question_left`, `page_right`, `last_alternative_bottom`, etc.).
- Renomear funções:
  - `denife_rect` → `crop_questions_on_page`
  - `get_num_of_question_in_page` → `find_questions_on_page`
  - `cut_image` → `render_question_image`

### Componente 3 — Constantes nomeadas
Extrair os números mágicos para constantes de módulo com comentário, preservando
os valores:
- `normal.py`: `EDGE_PADDING = 5`, `RIGHT_MARGIN = 30`, `BOTTOM_PADDING = 10`,
  `COLUMN_TOLERANCE = 10`, `D2_QUESTION_OFFSET = 90`, `ZOOM = 2`.
- `ampliada.py`: `LEFT_PADDING = 10`, `TITLE_TOP_ADJUST = 30`,
  `BOTTOM_PADDING = 10`, `PAGES_TO_PROCESS = 2`.

(Os nomes finais podem ser afinados na implementação, desde que os valores e o
comportamento sejam preservados.)

### Componente 4 — Quebrar funções
Extrair unidades pequenas com responsabilidade única, sem alterar a aritmética:
- `find_last_alternative_bottom(page, clip)` — localiza a alternativa "E" mais
  baixa e devolve a base do recorte.
- `compute_question_rect(...)` — calcula o retângulo de uma questão (coluna
  dupla, última da página).
- `render_question_image(rect, page, output, number)` — renderiza com zoom e
  salva o PNG.
- Decomposição análoga (mais enxuta) em `ampliada.py`.

## Verificação

- `tests/test_golden.py` verde ANTES da refatoração (contra o código atual) e
  DEPOIS (contra o código refatorado) — imagens byte-idênticas.
- Suíte completa (`uv run python -m unittest discover -s tests`) passando, sem
  regressões nos testes de `service`, `catalog` e `mcp_server`.

## Fora de escopo (YAGNI)

- `service.py` (já está limpo) — não será alterado.
- Mudança de comportamento, formato de saída, zoom, ou heurísticas de detecção.
- CLI (`main.py`), MCP (`mcp_server.py`), catálogo.
- Otimização de performance ou correção de bugs existentes (ex.: o `search_for("E")`
  é heurístico; não muda nesta refatoração).
