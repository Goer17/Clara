from .general import (
    LLMEngine
)

class Planner:
    def __init__(self,
                 engine: LLMEngine
                 ):
        self.engine = engine
    
    