import random
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
    SentenceMakingQuestion,
    ListeningQuestion
)
from utils.logger import (
    logger
)
from agent.retriever import MemoryNode
from utils.string import Formatter

class Generator:
    def __init__(self, engine: LLMEngine):
        self.engine = engine
        config_path = Path("config") / "prompts" / "generator.yml"
        self.prompts_cfg = {}
        with open(config_path) as f:
            config = yaml.safe_load(f)
            self.prompts_cfg = config
        
    async def gen_gap_filling(self, rela_nodes: List[MemoryNode], temp: float = 1.0) -> GapFillingQuestion:
        prompt = "\n\n".join(rela_node.text(enclose=True) for rela_node in rela_nodes)
        sys_prompt = self.prompts_cfg["GapFillingQuestion"]["sys_prompt"]
        few_shots = self.prompts_cfg["GapFillingQuestion"]["few_shots"]
        response = await self.engine.async_generate(prompt, sys_prompt, few_shots, temperature=temp)
        try:
            response = Formatter.catch_json(response)
            content = response["question"]
            solution = response["answer"]
            question = GapFillingQuestion(content, solution, rela_nodes=rela_nodes)
            return question
        except Exception as e:
            logger.error("Generator.gen_gap_filling() : an error occurred when attempting to generate a gap filling quesion", e)
            return None
    
    async def gen_sentence_making(self, rela_nodes: List[MemoryNode], temp: float = 1.0) -> SentenceMakingQuestion:
        prompt = "\n\n".join(rela_node.text(enclose=True) for rela_node in rela_nodes)
        sys_prompt = self.prompts_cfg["SentenceMakingQuestion"]["sys_prompt"]
        few_shots = self.prompts_cfg["SentenceMakingQuestion"]["few_shots"]
        response = await self.engine.async_generate(prompt, sys_prompt, few_shots, temperature=temp)
        try:
            response = Formatter.catch_json(response)
            scenario = response["scenario"] + "\n\n\n\n" + response["role"]
            solution = response["answer"]
            lang = response["lang"]
            question = SentenceMakingQuestion(scenario, solution, rela_nodes, analysis=lang)
            logger.info(f"Generator.gen_sentence_making() : successfully generated a sentence making question: {question.content}")
            return question
        except Exception as e:
            logger.error("Generator.gen_sentence_making() : an error occurred when attempting to generate a sentence making quesion", e)
            return None
    
    async def gen_listening(self, rela_nodes: List[MemoryNode], temp: float = 1.0):
        prompt = "\n\n".join(rela_node.text(enclose=True) for rela_node in rela_nodes)
        sys_prompt = self.prompts_cfg["ListeningQuestion"]["sys_prompt"]
        few_shots = self.prompts_cfg["ListeningQuestion"]["few_shots"]
        response = await self.engine.async_generate(prompt, sys_prompt, few_shots, temperature=temp)
        try:
            response = Formatter.catch_json(response)
            sentence = response["sentence"]
            voice = random.choice(['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'])
            question = ListeningQuestion(content="", solution=sentence, rela_nodes=rela_nodes, voice=voice)
            return question
        except Exception as e:
            logger.error("Generator.gen_listening() : an error occurred when attempting to generate a listening question", e)
            return None
        
    def close(self):
        self.engine.close()
