import re, json
from typing import (
    Dict
)

class Formatter:
    def __init__(self):
        raise RuntimeError("You can't create an instance of Formatter")
    
    @staticmethod
    def catch_json(string: str) -> Dict:
        match = re.search(pattern=r"```json(.*?)```", string=string, flags=re.S)
        json_string = match.group(1)
        json_data = json.loads(json_string)
        
        return json_data