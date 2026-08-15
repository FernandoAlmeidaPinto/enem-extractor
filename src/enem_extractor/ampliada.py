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
# Tolerância vertical (pontos) para o número ser considerado na mesma linha do
# "Questão" — evita casar "Questão" com um número de outro bloco da página.
SAME_LINE_TOLERANCE = 3

# Um heading é a palavra "Questão" seguida do número da questão (2–3 dígitos).
_QUESTION_WORD_FORMS = ("questão", "questao")
_NUMBER_RE = re.compile(r"^\d{2,3}$")


def _is_question_word(text):
    normalized = unicodedata.normalize("NFC", text).strip().lower()
    return normalized in _QUESTION_WORD_FORMS


def find_question_headings(page):
    """Localiza os headings "Questão NN" da página via get_text("words").

    Retorna [(numero:int, top_y:float)] — o y0 da palavra "Questão". Ignora
    ocorrências de "Questão" não seguidas de número (ex.: no corpo do texto), o
    plural "Questões", e casos em que o número seguinte está em outra linha
    (outro bloco da página) — exige mesma linha dentro de SAME_LINE_TOLERANCE."""
    words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word_no)
    headings = []
    for idx, word in enumerate(words):
        text = word[4]
        if _is_question_word(text) and idx + 1 < len(words):
            next_word = words[idx + 1]
            same_line = abs(next_word[1] - word[1]) <= SAME_LINE_TOLERANCE
            if same_line and _NUMBER_RE.match(next_word[4]):
                headings.append((int(next_word[4]), word[1]))
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
