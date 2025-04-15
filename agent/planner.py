import asyncio, random
import os
import yaml
from pathlib import Path
from collections import defaultdict
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
from utils.string import (
    Formatter
)
from utils.general import (
    LLMEngine,
    engine_list
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
            n = 4
            config = {
                "GapFillingQuestion": n,
                "ListeningQuestion": n,
                "SentenceMakingQuestion": n
            }
            filename, _ = self.gen_task(n, config)
            name = str(filename).split("/")[-1].removesuffix(".json")
            link = f"learn/task?name={name}"
            if filename is not None:
                return f"A learning task has been created for the student (by model {self.generator.engine.model}), located at: [link]({link}). You can notify him or her to complete it now."
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
            with open(Path("config") / "setting" / "generator.yml") as f:
                cfg = yaml.safe_load(f)
                model = cfg.get("model", "gpt-4o")
                self.generator.engine = engine_list.get(model, "gpt-4o")
                temp = cfg.get("temp", 1.0)

            async def _addq(q_type, rela_nodes):
                if q_type == "GapFillingQuestion":
                    question = await self.generator.gen_gap_filling(rela_nodes, temp)
                elif q_type == "ListeningQuestion":
                    question = await self.generator.gen_listening(rela_nodes, temp)
                elif q_type == "SentenceMakingQuestion":
                    question = await self.generator.gen_sentence_making(rela_nodes, temp)
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
                topic = {
                    "GapFillingQuestion": "grammar",
                    "SentenceMakingQuestion": "grammar",
                    "ListeningQuestion": "listening"
                }[q_type]
                for i in range(cnt):
                    node = nodes[i % n]
                    matchs = self.retriever.match(
                        from_prop={"label": "topic", "abstract": topic},
                        to_prop={"label": "weakness"},
                        rela_prop={},
                        bidirect=True
                    )
                    w_list = [match[2] for match in matchs]
                    rela_nodes = [node]
                    if len(w_list) > 0:
                        rela_nodes.append(
                            random.choices(w_list)[0]
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
        f_prompt = ""
        for q_type, problems in quiz.problemset.items():
            low = {
                "GapFillingQuestion": 0,
                "ListeningQuestion": 0.85,
                "SentenceMakingQuestion": 0.6
            }[q_type]
            for problem in problems:
                if problem.score <= low:
                    mistakes.addq(problem)
                    f_prompt += (
                        f"type: {q_type}\n"
                        f"question: {problem.question()}\n"
                        f"student's answer: {problem.answer}\n"
                        f"right answer: {problem.solution}\n\n"
                    )
                else:
                    for node in problem.rela_nodes:
                        if node.label == "unfamiliar_word":
                            familiarity = node.get_prop("familiarity")
                            if familiarity is None:
                                familiarity = 0
                            familiarity += 10
                            node.set_prop("familiarity", familiarity)
                            if familiarity >= 100:
                                node.set_label("word")
                            node.update()
                        elif node.label == "weakness" and node._node._alive:
                            familiarity = node.get_prop("familarity")
                            if familiarity is None:
                                familiarity = 0
                            familiarity += 50
                            node.set_prop("familiarity", familiarity)
                            node.update()
                            if familiarity >= 100:
                                node.destroy()
                            
        if mistakes.problemset:    
            mistakes.save(Path("material") / "mistake")
        os.remove(quiz.filepath)
        
        if len(f_prompt) == 0:
            return []
        
        with open(Path("config") / "prompts" / "planner.yml") as f:
            cfg = yaml.safe_load(f)
            sys_prompt = cfg["critic"]["sys_prompt"]            
        response = self.engine.generate(
            prompt=f_prompt,
            sys_prompt=sys_prompt
        )    
        data = Formatter.catch_json(response)
        for w_type in ["grammar", "listening"]:
            w_list = data.get(w_type, [])
            if len(w_type) == 0:
                continue
            result = self.retriever.match_node({"label": "topic", "abstract": w_type})
            if len(result) > 0:
                topic_node = result[0]
            elif len(result) == 0:
                topic_node = self.retriever.remember({"label": "topic", "abstract": w_type, "content": ""}, n_rela=0)
            if topic_node is None:
                continue
            for w in w_list:
                try:
                    w_node = self.retriever.remember({"label": "weakness", "abstract": w["abstract"], "content": w["content"], "familiarity": 0}, n_rela=0)
                    w_node.create_rela(topic_node, label="belong", properties={})
                except Exception as e:
                    logger.error(f"Planner.critic_task() : one error occurred while attempting to critic one quiz.", e)

        return []
    
    def close(self):
        self.engine.close()
        self.retriever.close()
        self.generator.close()