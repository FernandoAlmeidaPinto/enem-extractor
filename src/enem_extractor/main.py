from pathlib import Path

from .normal import extract_questions_normal


def get_year_and_day(filename=""):
    parts = filename.split("_")
    year = parts[0]
    day = next((p for p in parts if p.startswith("D")), "D1")
    return year, day


def main():
    provas_dir = Path("provas")
    output_base = Path("imagens")

    for pdf_file in sorted(provas_dir.glob("*.pdf")):
        filename = str(pdf_file)
        year, day = get_year_and_day(pdf_file.name)

        output_dir = output_base / year / day
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processando: {filename} -> Salvando em: {output_dir}")
        # Passa o nome-base, e o extract já sabe onde buscar e salvar
        extract_questions_normal(filename, output_dir)


if __name__ == "__main__":
    main()
