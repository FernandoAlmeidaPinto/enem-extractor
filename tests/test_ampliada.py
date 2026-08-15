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
