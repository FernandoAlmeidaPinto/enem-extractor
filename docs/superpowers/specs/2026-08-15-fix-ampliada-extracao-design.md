# Design: Correção + refatoração da extração ampliada

**Data:** 2026-08-15
**Status:** Aprovado

## Contexto e problema

O extractor `src/enem_extractor/ampliada.py` (versão de acessibilidade, letra
grande, coluna única) está **quebrado**: procura pelo texto `"QUESTÃO"`
(maiúsculo), mas a prova ampliada usa o título `"Questão NN"` (mista). Resultado:
`search_for("QUESTÃO")` retorna 0 e **nenhuma imagem é gerada**. Agravantes: o
loop só processa `range(2)` páginas e o recorte (título → última "E" da página)
não segmenta páginas com múltiplas questões.

### Estrutura real da prova ampliada (investigada)

Amostra `provas/2025_PV_impresso_D1_CD9_ampliada.pdf` (64 páginas, 90 questões):

- **Não é uma questão por página.** 31 páginas contêm múltiplas questões (ex.: a
  página impressa "11" tem as questões 06–10, curtas, que compartilham um
  texto-base na página anterior).
- **Textos-base separados:** algumas páginas são só o enunciado compartilhado
  (*"Texto para as Questões de 06 a 10"*), sem heading `Questão NN`.
- **Questões 1–5 duplicadas:** versões inglês e espanhol, ambas numeradas
  `Questão 01`..`Questão 05` (95 headings para 90 questões; 85/90 têm heading
  único, as 5 repetidas são as de língua estrangeira).
- **Sem ground-truth:** o extractor não gera nada hoje, então não há baseline de
  imagens; "correto" é definido neste design e validado por inspeção visual.

## Decisões (aprovadas)

- **Segmentação:** recorte entre headings `Questão NN` consecutivos, por página.
- **Nomes:** `questao_NNN.png` pelo número detectado; a 2ª ocorrência de um mesmo
  número (inglês→espanhol nas 1–5) vira `questao_NNN_2.png`.

## Solução

Reescrita de `ampliada.py` que corrige a extração e aplica as convenções de
legibilidade já usadas em `normal.py` (legenda de coordenadas, nomes
`left/top/right/bottom`, constantes nomeadas, funções pequenas). A API pública
`extract_questions_ampliada(path, output)` **não muda**.

### Componente 1 — Detecção de headings (genérica, cobre D1 e D2)
Para cada página, obter `page.get_text("words")` e localizar o token `"Questão"`
seguido de um número (2–3 dígitos). Produz uma lista de `(numero, rect)` onde
`rect` é o retângulo do token "Questão". Evita assumir o range 1–90 (D2 usaria
91+). Páginas sem heading (capa, texto-base) resultam em lista vazia e são
puladas. Filtro: o token seguinte a "Questão" deve ser um número, reduzindo
falsos positivos de "Questão" no corpo do texto.

### Componente 2 — Segmentação (entre headings, por página)
Ordenar os headings da página de cima para baixo (por `rect.y0`) e, para cada um:
- **top** = `heading.y0 - HEADING_TOP_PADDING`
- **bottom** = `y0` do próximo heading na página; se for o último da página,
  `page_height - FOOTER_MARGIN`
- **left** = `SIDE_MARGIN`; **right** = `page_width - SIDE_MARGIN`

Lida com páginas multi-questão. Não costura texto-base compartilhado nem questões
que cruzam páginas (tradeoff aceito).

### Componente 3 — Nomes com sufixo em duplicadas
Um `Counter` global (por execução) rastreia quantas vezes cada número já foi
emitido. 1ª ocorrência → `questao_NNN.png`; 2ª → `questao_NNN_2.png`. Como o
bloco inglês (páginas iniciais) precede o espanhol na ordem de leitura, o inglês
recebe o nome base e o espanhol o sufixo.

### Componente 4 — Legibilidade
Legenda do sistema de coordenadas no topo do módulo; nomes
`left/top/right/bottom`; constantes nomeadas (`HEADING_TOP_PADDING`,
`FOOTER_MARGIN`, `SIDE_MARGIN`, etc.); funções pequenas de responsabilidade
única: `find_question_headings(page)`, `compute_question_boxes(headings, page)`,
`render_question_image(box, page, output, filename)`.

## Verificação (sem ground-truth → duas camadas)

1. **Teste unitário puro da segmentação:** dado uma lista de `(numero, rect)` e
   as dimensões da página, verifica os boxes calculados (top/bottom/left/right,
   caso último-da-página) e a lógica do sufixo `_2`. Determinístico, sem
   PyMuPDF/Pillow — usa objetos fake com atributos `y0`/`x0`.
2. **Revisão visual manual:** gerar os PNGs de D1 ampliada; apresentar um resumo
   (contagem, números cobertos, duplicadas) e amostras para inspeção do usuário;
   ajustar paddings se necessário.
3. **Golden estendido (após aprovação visual):** incluir a ampliada no
   `tests/test_golden.py` e regenerar `tests/golden/manifest.json` (hoje `{}`
   para a ampliada) para fixar a saída aprovada e blindar regressões.

## Escopo / YAGNI

- Não costura texto-base compartilhado nem questões cross-página.
- A superampliada usa o mesmo extractor (mesma estrutura); é processada de
  brinde, mas o foco de validação é a ampliada D1.
- D2 ampliada não tem amostra disponível — a detecção genérica deve cobrir, mas
  não é testável neste momento (limitação registrada).
- Sem mudança na CLI, MCP, `service.py` ou `normal.py`.
