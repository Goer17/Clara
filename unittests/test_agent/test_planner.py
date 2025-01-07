import sys, os
sys.path.append(os.path.abspath("."))

import pytest

from agent.retriever import Retriever
from agent.generator import Generator
from agent.planner import Planner
from utils.general import (
    gpt_4o
)

@pytest.fixture
def planner():
    retriever = Retriever(gpt_4o)
    generator = Generator(gpt_4o)
    planner = Planner(gpt_4o, retriever, generator)
    yield planner
    planner.close()


def test_gen_quiz(planner):
    node_number = 5
    profile = {
        "GapFillingQuestion": 10,
        "ListeningQuestion": 5
    }
    filepath, quiz = planner.gen_quiz(
        node_number=node_number,
        profile=profile
    )
    assert os.path.exists(filepath)
    assert len(quiz.knowledges) == node_number
    for key, cnt in profile.items():
        assert len(quiz.problemset[key]) == cnt
