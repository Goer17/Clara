import os
import sys

sys.path.append(os.path.abspath("."))

from typing import (
    Dict
)

from utils.general import (
    LLMEngine,
    gpt_4o_engine
)
from utils.dictionary import (
    LLMDictionary,
    to_text
)
from utils.questions import (
    GapFillingQuestion
)

from agent.planner import Planner
from agent.retriever import Retriever
from agent.generator import Generator


class ShellApp:
    def __init__(self):
        self.planner = Planner(engine=gpt_4o_engine)
        self.retriever = Retriever(engine=gpt_4o_engine)
        self.generator = Generator(engine=gpt_4o_engine)
        self.dictionary = LLMDictionary(engine=gpt_4o_engine)
    
    def __add_unfamiliar_word(self, word: str) -> bool:
        content = self.dictionary(word)
        if content is not None:
            content = to_text(content)
        if content is None:
            return False
        m_item = {
            "label": "unfamiliar_word",
            "abstract": word,
            "content": content,
            "familiarity": 0
        }
        return self.retriever.remember(m_item, rela_number=5)
    
    def __gap_filling(self, m_item: Dict) -> GapFillingQuestion:
        gap_filling = self.generator.gen_gap_filling(
            rela_m_items=[m_item]
        )
        return gap_filling
    
    def run(self):
        while True:
            cmd = input("$ ")
            if cmd == "exit":
                break
            cate, content = cmd.split()
            if cate == "add":
                result = self.__add_unfamiliar_word(content)
                if not result:
                    print("! this word doesn't exist...")
            elif cate == "quiz":
                if content == "gf":
                    m_item_ls = self.retriever.lookup_same_label(label="unfamiliar_word", limit=1, order={"by": "familiarity", "method": "asc"})
                    if m_item_ls is not None and len(m_item_ls) > 0:
                        m_item = m_item_ls[0]
                    else:
                        print("* there's no unfamiliar word")
                        continue
                    question = self.__gap_filling(m_item=m_item)
                    print(f"* {question.show_que(hint=True)}")
                    ans = input("> ")
                    mark = question.mark(answer=ans)
                    m_id, familiarity = m_item["m_id"], m_item["familiarity"]
                    if mark == 1:
                        familiarity += 20
                    elif mark == 0:
                        familiarity -= 20
                    update_item = {
                        "familiarity": familiarity
                    }
                    if familiarity >= 100:
                        update_item["label"] = "word"
                    self.retriever.update(
                        m_id=m_id,
                        update_item=update_item
                    )

if __name__ == "__main__":
    app = ShellApp()
    app.run()