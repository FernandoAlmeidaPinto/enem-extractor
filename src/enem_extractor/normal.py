import fitz  # PyMuPDF
from PIL import Image
import io
from pathlib import Path

def extract_questions_normal(path, output):
    pdf_path = path
    print(f"Opening PDF {pdf_path}")
    pdf_document = fitz.open(pdf_path)

    print(f"Total pages: {len(pdf_document)}")
    question_count = 0
    if "/D2" in str(output):
        question_count = 90

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        questions = page.search_for("QUESTÃO")  # Procurar por "QUESTÃO"
        if(len(questions) == 0):
            continue

        dict_rect_questions, division_x = get_num_of_question_in_page(question_count + 1, page)
        if(len(dict_rect_questions) == 0):
            continue
        question_count += len(dict_rect_questions)
        denife_rect(dict_rect_questions, division_x, page, output)



def get_num_of_question_in_page(initial_num, page):
    i = initial_num
    questions = {}
    x0_values = set()

    while True:
        # Tenta com zero à esquerda (01) e sem (1), pois PDFs variam
        question = page.search_for(f"QUESTÃO {i:02}")
        if len(question) == 0:
            question = page.search_for(f"QUESTÃO {i}")
        if len(question) == 0:
            break
        rect = question[0]
        questions[f"{i:03}"] = rect
        x0_values.add(int(rect.x0))  # arredonda para evitar variações pequenas
        i += 1

    # Verifica se há dois grupos distintos de colunas
    sorted_x0 = sorted(x0_values)
    division_x = None
    if len(sorted_x0) >= 2:
        division_x = max(sorted_x0)

    return questions, division_x


def denife_rect(dict_rect_questions, division_x, page, output):
    page_height = page.rect.y1
    page_width = page.rect.x1
    keys = list(dict_rect_questions.keys())
    initial_x0 = dict_rect_questions[keys[0]].x0
    for pos in range(len(keys)):
        key = keys[pos]
        current_rect = dict_rect_questions[key]
        x0 = current_rect.x0 - 5
        y0 = current_rect.y0 + 25
        x1 = page_width - 30
        y1 = page_height + 0
        # Se for a última questão da página
        if pos == len(keys) - 1:
            alternatives = page.search_for("E", quads=False, clip=(x0, y0, x1, page.rect.y1))
            alternative = alternatives[-1]  # Posição da última alternativa "E"
            y1 = alternative.y1 + 10  # fim da página, pois a próxima está em outra coluna
        else:
            next_rect = dict_rect_questions[keys[pos + 1]]
            # Se estiver na mesma coluna (diferença pequena no x0)
            if division_x and abs(current_rect.x0 - initial_x0) < 10:
                x1 = division_x
            if abs(current_rect.x0 - next_rect.x0) < 10:
                y1 = next_rect.y0
            else:
                alternatives = page.search_for("E", quads=False, clip=(x0, y0, x1, page.rect.y1))
                alternative = alternatives[-1]  # Posição da última alternativa "E"
                y1 = alternative.y1 + 10  # fim da página, pois a próxima está em outra coluna
        cut_image(x0, y0, x1, y1, output, int(key), page)



def cut_image(x0, y0, x1, y1, output, question_count, page):
    rect = fitz.Rect(x0, y0, x1, y1)

    # Aumenta resolução com zoom
    matrix = fitz.Matrix(2, 2)  # pode usar 2.5 ou 3 se quiser ainda mais definição
    pix = page.get_pixmap(matrix=matrix, clip=rect)

    img = Image.open(io.BytesIO(pix.tobytes()))
    image_path = f"{output}/questao_{question_count:03}.png"
    img.save(image_path)
