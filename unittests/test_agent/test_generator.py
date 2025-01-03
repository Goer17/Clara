import sys, os
sys.path.append(os.path.abspath("."))

import asyncio
import pytest
from agent.generator import Generator
from agent.retriever import MemoryNode, Retriever
from utils.general import gpt_4o

from typing import (
    List, Dict
)
from utils.questions import (
    GapFillingQuestion,
    SentenceMakingQuestion,
    ListeningQuestion
)

@pytest.fixture
def retriever():
    retriever = Retriever(gpt_4o)
    yield retriever
    retriever.close()

@pytest.fixture
def generator():
    generator = Generator(gpt_4o)
    yield generator
    generator.close()

def match_unfamiliar(retriever: Retriever, limit: int) -> List[MemoryNode]:
    node_list = retriever.match_node(
        {
            "label": "unfamiliar_word"
        },
        order=("familiarity", "ASC"),
        limit=limit
    )
    
    return node_list

@pytest.mark.passed
@pytest.mark.parametrize("cnt", [1, 2, 5, 10])
def test_gapfilling(generator, retriever, cnt):
    node_list = match_unfamiliar(retriever, limit=cnt)
    question_list = []
    async def addq(rela_nodes: List[MemoryNode]):
        question = await generator.gen_gap_filling(rela_nodes)
        if question is not None:
            question_list.append(question)
    coro_list = [addq([node]) for node in node_list]
    asyncio.run(asyncio.wait(coro_list, timeout=None))
    assert len(question_list) == cnt
    for question in question_list:
        assert isinstance(question, GapFillingQuestion)

@pytest.mark.passed
@pytest.mark.parametrize("cnt", [1, 2, 5, 10])
def test_listening(generator, retriever, cnt):
    node_list = match_unfamiliar(retriever, limit=cnt)
    question_list = []
    async def addq(rela_nodes: List[MemoryNode]):
        question = await generator.gen_listening(rela_nodes)
        if question is not None:
            question_list.append(question)
    coro_list = [addq([node]) for node in node_list]
    asyncio.run(asyncio.wait(coro_list, timeout=None))
    assert len(question_list) == cnt
    for question in question_list:
        assert isinstance(question, ListeningQuestion)

@pytest.mark.parametrize("cnt", [1, 2, 5, 10])
def test_sentence_making(generator, retriever, cnt):
    node_list = match_unfamiliar(retriever, limit=cnt)
    question_list = []
    async def addq(rela_nodes: List[MemoryNode]):
        question = await generator.gen_sentence_making(rela_nodes)
        if question is not None:
            question_list.append(question)
    coro_list = [addq([node]) for node in node_list]
    asyncio.run(asyncio.wait(coro_list, timeout=None))
    assert len(question_list) == cnt
    for question in question_list:
        assert isinstance(question, SentenceMakingQuestion)