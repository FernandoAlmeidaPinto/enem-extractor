"""Extração de questões da prova padrão do ENEM (layout de duas colunas).

Sistema de coordenadas (PyMuPDF): a origem fica no canto superior esquerdo e o
eixo y cresce para baixo. Um Rect é (left, top, right, bottom) — equivalente a
(x0, y0, x1, y1) na nomenclatura do fitz.
"""

import io

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
        # Tenta com zero à esquerda (01) e sem (1), pois PDFs variam.
        found = page.search_for(f"QUESTÃO {i:02}")
        if len(found) == 0:
            found = page.search_for(f"QUESTÃO {i}")
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
    recorte (y da última "E" + BOTTOM_PADDING).

    Precondição: `clip` deve conter ao menos uma "E" — o chamador garante isso
    (senão levanta IndexError, comportamento herdado do código original)."""
    alternatives = page.search_for("E", quads=False, clip=clip)
    last_alternative = alternatives[-1]  # a "E" mais abaixo encerra a questão
    return last_alternative.y1 + BOTTOM_PADDING


def crop_questions_on_page(questions, column_divider_x, page, output):
    page_bottom = page.rect.y1
    page_right = page.rect.x1
    keys = list(questions.keys())
    # x0 de referência da coluna da esquerda (a primeira questão da página).
    left_column_x = questions[keys[0]].x0

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
            if column_divider_x and abs(current_rect.x0 - left_column_x) < COLUMN_TOLERANCE:
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
