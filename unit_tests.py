import os
from dotenv import find_dotenv, load_dotenv
import argparse
from agent._memory import Memory
from utils.general import LLMEngine
from utils.dictionary import (
    to_text,
    LLMDictionary
)
from agent.retriever import Retriever
from agent.generator import (
    Question,
    Generator
)
from pathlib import Path
import json
from functools import wraps
from typing import get_type_hints
from collections import defaultdict

load_dotenv(find_dotenv())
base_url = os.environ["BASE_URL"]
openai_api_key = os.environ["OPENAI_API_KEY"]

engine = LLMEngine(
    model='gpt-4o',
    api_key=openai_api_key,
    base_url=base_url
)

def cast_arguments(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        type_hints = get_type_hints(func)
        new_args = []
        
        for arg, (name, expected_type) in zip(args, type_hints.items()):
            if name != 'return':
                try:
                    new_args.append(expected_type(arg))
                except (ValueError, TypeError):
                    new_args.append(arg)

        new_kwargs = {}
        for name, value in kwargs.items():
            if name in type_hints and name != 'return':
                expected_type = type_hints[name]
                try:
                    new_kwargs[name] = expected_type(value)
                except (ValueError, TypeError):
                    new_kwargs[name] = value
            else:
                new_kwargs[name] = value
        
        return func(*new_args, **new_kwargs)
    
    return wrapper

def clear_all():
    retriver = Retriever(engine=engine)
    retriver.clear_all()

@cast_arguments
def remember_voc(max_line: int = -1):
    retriver = Retriever(
        engine=engine
    )
    voc_path = Path("eval_set") / "vocabulary.jsonl"
    line_idx = 0
    with open(voc_path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            voc = json.loads(line)
            voc["label"] = "word"
            retriver.remember(voc)
            line_idx += 1
            if max_line > 0 and line_idx >= max_line:
                break

@cast_arguments
def remember_unfamiliar_voc(max_line: int = -1):
    retriver = Retriever(
        engine=engine
    )
    voc_path = Path("eval_set") / "unfamiliar_vocabulary.jsonl"
    line_idx = 0
    with open(voc_path) as f:
        while True:
            line = f.readline()
            if not line:
                break
            voc = json.loads(line)
            voc["label"] = "unfamiliar_word"
            voc["familiarity"] = 0
            retriver.remember(voc, n_rela=5)
            line_idx += 1
            if max_line > 0 and line_idx >= max_line:
                break

@cast_arguments
def gap_filling():
    memory = Memory()
    results = memory.lookup_same_label(
        label="word",
        limit=5,
        order={
            "by": "abstract",
            "method": "asc"
        }
    )
    generator = Generator(engine=engine)
    question = generator.gen_gap_filling(rela_m_items=[results[2]])
    print(question.show_que(hint=True))
    print("Solution: " + question.show_sol())
    
@cast_arguments
def test_dict():
    dictionary = LLMDictionary(engine=engine)
    meanings = dictionary("example")
    if meanings is not None:
        meanings = to_text(meanings)
        print(meanings)

text = """
He was an old man who fished alone in a skiff in the Gulf Stream and he had gone eighty-four days now without taking a fish.
In the first forty days a boy had been with him.
But after forty days without a fish the boy’s parents had told him that the old man was now definitely and finally salao,
which is the worst form of unlucky, and the boy had gone at their orders in another boat which caught three good fish the first week.
It made the boy sad to see the old man come in each day with his skiff empty and he always went down to help him carry either the coiled lines or the gaff and harpoon and the sail that was furled around the mast.
The sail was patched with flour sacks and, furled, it looked like the flag of permanent defeat.
"""

@cast_arguments
def test_audio():
    from utils.general import AMEngine, tts_hd
    a_id = tts_hd.generate(text=text, voice="echo")
    AMEngine.play(a_id)

@cast_arguments
def test_orm_add():
    from utils.neo4j_orm import Graph, Node, Relationship
    graph = Graph(uri="bolt://localhost:7687", auth=("neo4j", "Yy030518neo4j"))
    node1 = graph.create_node(label="word", properties={"abstract": "apple"})
    node2 = graph.create_node(label="word", properties={"abstract": "banana"})
    node3 = graph.create_node(label="word", properties={"abstract": "melon"})
    rela1 = node1.create_rela(to=node2, label="relative", properties={"content": "fruits"})
    rela2 = node2.create_rela(to=node3, label="relative", properties={"content": "fruits"})
    rela1.set_prop("distance", 10)
    rela1.update()
    rela2.set_prop("distance", 20)
    rela2.update()
    
@cast_arguments
def test_orm_del():
    from utils.neo4j_orm import Graph, Node, Relationship
    graph = Graph(uri="bolt://localhost:7687", auth=("neo4j", "Yy030518neo4j"))
    res = graph.match(
        from_prop={"label": "word", "abstract": "melon"},
        to_prop={"label": "word", "abstract": "banana"},
        rela_prop={"label": "relative"},
        bidirect=True
    )
    if len(res) == 0:
        return
    p, r, q = res[0]
    r.destroy()

def test_async():
    import asyncio
    results = {}
    async def gen(question: str):
        results[question] = await engine.async_generate(prompt=question)
    questions = [
        "What is 1 + 1?",
        "What is 1 + 2?",
        "What is 1 + 3?",
        "What is 1 + 4?",
        "What is 1 + 5?",
        "What is 1 + 6?",
        "What is 1 + 7?",
        "What is 1 + 8?",
        "What is 1 + 9?"
    ]
    coro_list = [gen(q) for q in questions]
    asyncio.run(asyncio.wait(coro_list, timeout=None))
    for q, a in sorted(results.items()):
        print(f"{q} | {a}")
    
def test_manager():
    from agent.retriever import MemoryNode, MemoryManager
    manager = MemoryManager()
    nodes = manager.match_node({"abstract": "apple"})
    if len(nodes) == 0:
        return
    node: MemoryNode = nodes[0]
    node.set_prop("familiarity", 100)
    node.set_label("word")
    node.update()
    
text = """
Hello, world
```json
{
    "abstract": "apple"
}
```
End
"""

def test_formatter():
    from utils.string import Formatter
    data = Formatter.catch_json(text)
    print(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--function", type=str, help="The function you are going to test.")
    parser.add_argument("-a", "--arguments", type=str, default="", help="The arguments passed to testing function, splited by comma.")
    
    args = parser.parse_args()
    
    func_name = args.function
    arguments = args.arguments.split(',') if len(args.arguments.strip()) > 0 else []
    
    eval(func_name)(*arguments)