from .general import (
    LLMEngine
)

class Generator:
    def __init__(self, engine: LLMEngine):
        self.engine = engine