from utils.general import (
    gpt_4o,
    tts_hd
)

from agent.retriever import Retriever
from agent.generator import Generator
from agent.planner import Planner

retriever = Retriever(gpt_4o)
generator = Generator(gpt_4o)
planner = Planner(gpt_4o, retriever, generator)

from utils.dictionary import LLMDictionary, to_text

dictionaty = LLMDictionary(gpt_4o)

from utils.questions import Quiz

def add_words():
    while True:
        w = input("> ")
        if w == ":exit":
            break
        else:
            content = to_text(dictionaty(w))
            if content:
                node_profile = {
                    "label": "unfamiliar_word",
                    "abstract": w.lower(),
                    "content": content,
                    "familiarity": 0
                }
                retriever.remember(
                    node_profile
                )

def learning():
    n = 5
    quiz_profile = {
        "GapFillingQuestion": 2 * n,
        "ListeningQuestion": n
    }
    filename, quiz = planner.gen_quiz(n, quiz_profile)
    quiz.shell()

if __name__ == "__main__":
    while True:
        cmd = input("$ ")
        if cmd == "add":
            add_words()
        elif cmd == "quiz":
            learning()
