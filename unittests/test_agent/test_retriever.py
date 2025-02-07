import sys, os
sys.path.append(os.path.abspath("."))

import pytest

from agent.retriever import MemoryNode, Retriever
from utils.general import (
    gpt_4o
)

@pytest.fixture
def retriever():
    retriever = Retriever(gpt_4o)
    yield retriever
    retriever.close()

@pytest.mark.passed
def test_dup_node(retriever):
    node1 = retriever.match_node(
        {
            "label": "word",
            "abstract": "color"
        }
    )[0]
    node2 = retriever.match_node(
        {
            "label": "word",
            "abstract": "color"
        }
    )[0]
    assert node1._node == node2._node


@pytest.mark.passed
@pytest.mark.parametrize("skip", [0, 10, 20, 30, 40])
def test_match_node(retriever, skip):
    nodes = retriever.match_node({"label": "unfamiliar_word"}, order=("familiarity", "ASC"), skip=skip, limit=10)
    assert len(nodes) == 10