import asyncio, random
import os
import yaml
from pathlib import Path
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

from datetime import datetime
class Toolbox:
    def __init__(self):
        raise RuntimeError("Toolbox is a static class.")
    
    @staticmethod
    def get_current_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M")
        

class Planner:
    def __init__(self,
                 engine: LLMEngine,
                 retriever: Retriever,
                 generator: Generator
                 ):
        self.engine = engine
        self.retriever = retriever
        self.generator = generator
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "get current timestamp with format YY-MM-DD H:M:S",
                    "parameters": {}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_task",
                    "description": "Generate a learning task for the student to practice.",
                    "parameters": {}
                }
            }
        ]
        def generate_task():
            n = 7
            config = {
                "GapFillingQuestion": 2 * n,
                "ListeningQuestion": n,
                "SentenceMakingQuestion": n
            }
            filename, _ = self.gen_task(n, config)
            name = str(filename).split("/")[-1].removesuffix(".json")
            link = f"learn/task?name={name}"
            if filename is not None:
                return f"A learning task has been created for the student, located at: [link]({link}). You can notify him or her to complete it now."
            else:
                return "Something goes wrong."
        self.functions = {
            "get_current_time": Toolbox.get_current_time,
            "generate_task": generate_task
        }
    
    def chat(self, messages: List[Dict]) -> str:
        config_path = Path("config") / "prompts" / "planner.yml"
        toolset = (self.tools, self.functions)
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
            sys_prompt = cfg["chat"]["sys_prompt"]
        try:
            response = self.engine.chat(messages, sys_prompt=sys_prompt, toolset=toolset)
            return response
        except Exception as e:
            logger.error(f"Planner.chat() : one error occurred while attempting to chat with planner.", e)
            return str(e)
    
    def gen_task(self, node_number: int, profile: Dict[str, int]) -> Tuple[str, Quiz]:
        try:
            quiz = Quiz()
            nodes = self.retriever.match_node(
                {"label" : "unfamiliar_word"},
                order=("familiarity", "ASC"),
                limit=node_number
            )
            n = len(nodes)
            if n == 0:
                raise RuntimeError("There's no unfamiliar word.")
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
    
    def critic_task(self, quiz: Quiz) -> List[Dict[str, str]]:
        mistakes = Quiz()
        mistakes.description = "This is a collection of mistakes based on a summary of your previous practice."
        for q_type, problems in quiz.problemset.items():
            low = {
                "GapFillingQuestion": 0,
                "ListeningQuestion": 0.9,
                "SentenceMakingQuestion": 0.7
            }[q_type]
            for problem in problems:
                if problem.score <= low:
                    mistakes.addq(problem)
        if mistakes.problemset:    
            mistakes.save(Path("material") / "mistake")
        os.remove(quiz.filepath)

        return []
    
    def close(self):
        self.engine.close()
        self.retriever.close()
        self.generator.close()