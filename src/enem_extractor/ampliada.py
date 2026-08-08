import fitz  # PyMuPDF
from PIL import Image
import io
from pathlib import Path

def extract_questions_ampliada(path):
    # Abrir o PDF
    pdf_path = path + ".pdf"
    print(f"Opening PDF {pdf_path}")
    pdf_document = fitz.open(pdf_path)
    Path(path).mkdir(parents=True, exist_ok=True)
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
                image_path = f"{path}/page_{page_num + 1}_question_{instance_num + 1}.png"
                print(f"Saving image to {image_path}")
                img.save(image_path)
                print(f"Saved image {image_path}")
            else:
                print(f"Não foi possível encontrar a alternativa 'E' para a questão na página {page_num + 1}")


if __name__ == "__main__":
    extract_questions_ampliada("2016_PV_impresso_D1_CD1")
