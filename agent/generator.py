import asyncio
from pathlib import Path
import yaml, json, re
from utils.general import (
    LLMEngine
)
from typing_extensions import (
    List, Dict
)
from utils.questions import (
    Question,
    GapFillingQuestion,
    Quiz
)
from utils.logger import (
    logger
)
from agent.retriever import MemoryNode, Retriever
from utils.string import Formatter

class Generator:
    def __init__(self, engine: LLMEngine):
        self.engine = engine
        config_path = Path("config") / "prompts" / "generator.yml"
        self.prompts_cfg = {}
        with open(config_path) as f:
            config = yaml.safe_load(f)
            self.prompts_cfg = config
        
    async def gen_gap_filling(self, rela_nodes: List[MemoryNode]) -> GapFillingQuestion:
        prompt = "\n\n".join(rela_node.text(enclose=True) for rela_node in rela_nodes)
        sys_prompt = self.prompts_cfg["GapFillingQuestion"]["sys_prompt"]
        few_shots = self.prompts_cfg["GapFillingQuestion"]["few_shots"]
        response = await self.engine.async_generate(prompt, sys_prompt, few_shots)
        try:
            response = Formatter.catch_json(response)
            content = response["question"]
            solution = response["answer"]
            question = GapFillingQuestion(content, solution, rela_nodes=rela_nodes)
            return question
        except Exception as e:
            logger.error("Generator.gen_gap_filling() : an error occurred when attempting to generate a gap filling quesion", e)
            return None
    
    async def gen_sentence_making(self, rela_nodes: List[MemoryNode]):
        pass
    
    async def gen_listening(self, rela_nodes: List[MemoryNode]):
        pass

    def gen_quiz(self, config: Dict[str, int], retriever: Retriever):
        quiz = Quiz()
        if (gap_filling_cnt := config.get("GapFillingQuestion", 0)) > 0:
            unfamiliar_nodes = retriever.match_node(
                {
                    "label": "unfamiliar_word"
                },
                order=("familiarity", "ASC"),
                limit=gap_filling_cnt
            )
            async def add_gap_filling(rela_nodes: List[MemoryNode]):
                question = await self.gen_gap_filling(rela_nodes)
                if question is not None:
                    quiz.add(question)
            coro_list = [add_gap_filling([unfamiliar_node]) for unfamiliar_node in unfamiliar_nodes]
            asyncio.run(asyncio.wait(coro_list, timeout=None))
        
        return quiz