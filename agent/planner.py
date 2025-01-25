import asyncio, random

from typing import (
    List, Dict, Tuple
)
from agent.generator import (
    Generator
)
from agent.retriever import (
    MemoryNode,
    Retriever
)
from utils.general import (
    LLMEngine
)
from utils.questions import (
    Quiz
)
from utils.logger import logger

class Planner:
    def __init__(self,
                 engine: LLMEngine,
                 retriever: Retriever,
                 generator: Generator
                 ):
        self.engine = engine
        self.retriever = retriever
        self.generator = generator
    
    def chat(self, messages: List[Dict]) -> str:
        try:
            response = self.engine.chat(messages)
            return response
        except Exception as e:
            logger.error(f"Planner.chat() : one error occurred while attempting to chat with planner.", e)
    
    def gen_quiz(self, node_number: int, profile: Dict[str, int]) -> Tuple[str, Quiz]:
        try:
            quiz = Quiz()
            nodes = self.retriever.match_node(
                {"label" : "unfamiliar_word"},
                order=("familiarity", "ASC"),
                limit=node_number
            )
            n = len(nodes)
            for node in nodes:
                quiz.addn(node)
            async def _addq(q_type, rela_nodes):
                if q_type == "GapFillingQuestion":
                    question = await self.generator.gen_gap_filling(rela_nodes)
                elif q_type == "ListeningQuestion":
                    question = await self.generator.gen_listening(rela_nodes)
                elif q_type == "SentenceMakingQuestion":
                    question = await self.generator.gen_sentence_making(rela_nodes)
                else:
                    logger.error(f"Quiz.load() : unknown question class : {q_type}")
                    return
                quiz.addq(question)
            coro_list = []
            for q_type, cnt in profile.items():
                if q_type not in [
                    "GapFillingQuestion",
                    "SentenceMakingQuestion",
                    "ListeningQuestion"
                ]:
                    logger.error(f"Quiz.load() : unknown question class : {q_type}")
                    continue
                for i in range(cnt):
                    node = nodes[i % n]
                    matchs = self.retriever.match(
                        from_prop={"m_id": node.get_prop("m_id")},
                        to_prop={"label": "mistake", "type": q_type},
                        rela_prop={"label": "relative"},
                        bidirect=True
                    )
                    mistakes = [match[2] for match in matchs]
                    rela_nodes = [node]
                    if len(mistakes) > 0:
                        rela_nodes.append(
                            random.choices(mistakes)[0]
                        )
                    coro_list.append(
                        _addq(q_type, rela_nodes)
                    )
            asyncio.run(asyncio.wait(coro_list, timeout=None))
            filepath = quiz.save()
            return filepath, quiz
        except Exception as e:
            logger.error(f"Planner.gen_quiz() : an error occurred while attempting to generate a quiz (node_number = {node_number}) (profile: {profile})", e)
            return None, None
    
    def close(self):
        self.engine.close()
        self.retriever.close()
        self.generator.close()