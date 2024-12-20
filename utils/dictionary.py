import yaml, json
from pathlib import Path
import re
from typing import (
    Dict
)

from utils.general import LLMEngine

def to_text(content: Dict) -> str | None:
    try:
        res = ""
        for meaning in content["meanings"]:
            res += f"[{meaning['pos']}] {meaning['meaning']}\n"
            for example in meaning["examples"]:
                res += f"> {example}\n"
        return res
    except Exception as e:
        pass    
    return None


class LLMDictionary:
    def __init__(self,
                 engine: LLMEngine
                 ):
        self.engine = engine
        config_path = Path("config") / "prompts" / "dictionary.yml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        self.sys_prompt = config["sys_prompt"]
        self.few_shots = config["few_shots"]    
    
    def __call__(self, word: str) -> Dict | None:
        response = self.engine.generate(
            prompt=word,
            sys_prompt=self.sys_prompt,
            few_shots=self.few_shots
        )
        if "NO_EXIST" in response:
            return None
        try:
            content = re.search(pattern=r"```json(.*?)```", string=response, flags=re.S).group(1)
            content = json.loads(content)
            return content
        except Exception as e:
            print(e)
        
        return None