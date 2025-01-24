from utils.general import (
    gpt_4o
)
from agent.retriever import Retriever
from agent.generator import Generator
from agent.planner import Planner

generator = Generator(gpt_4o)
retriever = Retriever(gpt_4o)
planner = Planner(gpt_4o, retriever, generator)

from utils.dictionary import LLMDictionary, to_text

dictionaty = LLMDictionary(gpt_4o)

def add_words():
    while True:
        w = input("> ")
        if w == ":exit":
            break
        else:
            try:
                content = to_text(dictionaty(w))
                if content:
                    node_profile = {
                        "label": "unfamiliar_word",
                        "abstract": w.lower(),
                        "content": content,
                        "familiarity": 0
                    }
                    node = retriever.remember(
                        node_profile
                    )
                    print(f"* added one node : {node}")
            except Exception as e:
                pass

def learning():
    n = 5
    quiz_profile = {
        "GapFillingQuestion": 2 * n,
        "ListeningQuestion": n,
        # "SentenceMakingQuestion": n
    }
    filename, quiz = planner.gen_quiz(n, quiz_profile)
    quiz.shell(retriever=retriever)

if __name__ == "__main__":
    while True:
        cmd = input("$ ")
        if cmd == "add":
            add_words()
        elif cmd == "quiz":
            learning()
        elif cmd == "exit":
            break
