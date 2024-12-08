import os
from dotenv import find_dotenv, load_dotenv
import argparse
from agent.memory import Memory
from agent.general import LLMEngine
from agent.retriever import Retriever
from pathlib import Path
import json
from functools import wraps
from typing import get_type_hints

load_dotenv(find_dotenv())
base_url = os.environ["BASE_URL"]
openai_api_key = os.environ["OPENAI_API_KEY"]

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
    memo = Memory()
    memo.clear_all()

@cast_arguments
def remember_voc(max_line: int = -1):
    engine = LLMEngine(
        model='gpt-4o-mini',
        api_key=openai_api_key,
        base_url=base_url
    )
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
    engine = LLMEngine(
        model='gpt-4o-mini',
        api_key=openai_api_key,
        base_url=base_url
    )
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
            retriver.remember(voc, rela_number=5)
            line_idx += 1
            if max_line > 0 and line_idx >= max_line:
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--function", type=str, help="The function you are going to test.")
    parser.add_argument("-a", "--arguments", type=str, default="", help="The arguments passed to testing function, splited by comma.")
    
    args = parser.parse_args()
    
    func_name = args.function
    arguments = args.arguments.split(',') if len(args.arguments.strip()) > 0 else []
    
    eval(func_name)(*arguments)