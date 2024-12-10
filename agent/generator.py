from pathlib import Path
import yaml, json, re
from .general import (
    LLMEngine
)
from typing_extensions import (
    List, Dict
)
from utils.questions import (
    Question,
    GapFillingQuestion
)
from utils.logger import (
    logger
)
from .memory import (
    Memory
)

class Generator:
    def __init__(self, engine: LLMEngine):
        self.engine = engine
        config_path = Path("agent") / "prompts" / "generator.yml"
        self.prompts_cfg = {}
        with open(config_path) as f:
            config = yaml.safe_load(f)
            self.prompts_cfg["gap_filling"] = config["gap_filling"]
        
    def gen_gap_filling(self, rela_m_items: List[Dict]) -> GapFillingQuestion:
        prompt = ""
        for m_item in rela_m_items:
            prompt += f"```txt\n{Memory.decode_m_item(m_item)}\n```\n"
        gap_filling_prompts = self.prompts_cfg["gap_filling"]
        response = self.engine.generate(
            prompt=prompt,
            sys_prompt=gap_filling_prompts["sys_prompt"],
            few_shots=gap_filling_prompts["few_shots"]
        )
        try:
            response = re.search(pattern=r"```json(.*?)```", string=response, flags=re.S).group(1)
            response = json.loads(response)
            content = response["question"]
            if content.count("$BLANK") != 1:
                raise Exception(f"Format error: {content}")
            solution = response["answer"]
            question = GapFillingQuestion(
                content=content,
                solution=solution,
                rela_m_items=rela_m_items
            )
            logger.info(f"Generator : One gap-filling question has been generated successfully:\n{question.show_que()} answer: {question.show_sol()}")
            return question
        except Exception as e:
            logger.error(f"Generator : An error occurred when generating gap filling questions: {e}")
        return None