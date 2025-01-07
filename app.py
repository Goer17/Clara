import asyncio
import pytest
from typing import (
    List, Dict
)

from agent.generator import Generator
from agent.retriever import MemoryNode, Retriever
from utils.general import (
    LLMEngine, AMEngine,
    gpt_4o,
    tts_hd
)
from utils.dictionary import (
    LLMDictionary,
    to_text
)
from utils.questions import (
    GapFillingQuestion,
    ListeningQuestion,
    Quiz
)
import time

def match_unfamiliar(retriever: Retriever, limit: int) -> List[MemoryNode]:
    node_list = retriever.match_node(
        {
            "label": "unfamiliar_word"
        },
        order=("familiarity", "ASC"),
        limit=limit
    )
    
    return node_list

def gen_gapfilling(generator, retriever, cnt):
    node_list = match_unfamiliar(retriever, limit=cnt)
    question_list = []
    async def addq(rela_nodes: List[MemoryNode]):
        question = await generator.gen_gap_filling(rela_nodes)
        if question is not None:
            question_list.append(question)
    coro_list = [addq([node]) for node in node_list]
    asyncio.run(asyncio.wait(coro_list, timeout=None))
    return question_list


def gen_listening(generator: Generator, retriever: Retriever, cnt: int) -> List[ListeningQuestion]:
    node_list = match_unfamiliar(retriever, limit=cnt)
    question_list = []
    async def addq(rela_nodes: List[MemoryNode]):
        question = await generator.gen_listening(rela_nodes)
        if question is not None:
            question_list.append(question)
    coro_list = [addq([node]) for node in node_list]
    asyncio.run(asyncio.wait(coro_list, timeout=None))
    return question_list

generator = Generator(gpt_4o)
retriever = Retriever(gpt_4o)

def listening():
    question_list = gen_listening(generator, retriever, 5)
    for question in question_list:
        name = tts_hd.generate(question.solution, "echo")
        for i in range(3):
            AMEngine.play(name)
            time.sleep(2)
        answer = input(f"{question.question()}\n: ")
        score, analysis, feedback = question.mark(answer, gpt_4o)
        print(f"score: {score}")
        print(f"analysis:\n{analysis}")
        print(question.rela_nodes[0])
        print(f"feedback:\n{feedback}")
        if score < 0.8:
            continue
        addition = int((score - 0.8) * 100)
        for node in question.rela_nodes:
            node.set_prop(
                "familiarity",
                node.get_prop("familiarity") + addition
            )
            if node.get_prop("familiarity") >= 100:
                node.set_label("word")
            node.update()
                

if __name__ == "__main__":
    dictionary = LLMDictionary(engine=gpt_4o)
    while True:
        cmd = input("$ ")
        if cmd.startswith("add "):
            word = cmd.split()[1]
            content = to_text(dictionary(word))
            if content is None:
                print("> word doesn't exist.")
            node_profile = {
                "label": "unfamiliar_word",
                "abstract": word,
                "content": content,
                "familiarity": 0
            }
            node = retriever.remember(node_profile)
            print(f"> {node}")
        elif cmd == "exit":
            break
        elif cmd == "listening":
            listening()
            