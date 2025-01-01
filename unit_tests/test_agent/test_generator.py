import sys, os
sys.path.append(os.path.abspath("."))

import pytest

from agent.generator import Generator
from agent.retriever import Retriever
from utils.general import gpt_4o

retriever = Retriever(gpt_4o)
generator = Generator(gpt_4o)

@pytest.fixture
def only_gap_filling():
    return {
        "GapFillingQuestion": 10
    }

def test_gap_filling(only_gap_filling):
    quiz = generator.gen_quiz(only_gap_filling, retriever)
    assert len(quiz.problemset["GapFillingQuestion"]) == 10