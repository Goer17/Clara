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

