from pathlib import Path
import yaml
from collections import defaultdict
from abc import ABC, abstractmethod

from typing import (
    Dict, List, Tuple
)
from agent.retriever import (
    MemoryNode
)
from utils.general import (
    LLMEngine,
    AMEngine
)
from utils.string import Formatter


prompts = Path("config") / "prompts" / "feedback.yml"
with open(prompts) as f:
    all_prompts = yaml.safe_load(f)

class Question(ABC):
    def __init__(self,
                 content: str,
                 solution: str,
                 rela_nodes: List[MemoryNode],
                 analysis: str = None,
                 *args, **kwargs
                 ):
        self.content = content
        self.solution = solution
        self.rela_nodes = rela_nodes
        self.analysis = analysis
    
    @abstractmethod
    def question(self, hint: bool = False) -> str:
        pass
    
    @abstractmethod
    def mark(self,
             answer: str,
             engine: LLMEngine
             ) -> Tuple[float, str, List[Dict[str, str]]]:
        """ Mark the student's answer
        Args:
            answer (str): student's answer

        Returns:
            float: the mark of this answer: 0 ~ 1
            str: analysis
            List[Dict[str, str]]: mistakes the student had, can be empty
        """
        pass


class GapFillingQuestion(Question):
    def __init__(self, content, solution, rela_nodes, analysis = None, *args, **kwargs):
        super().__init__(content, solution, rela_nodes, analysis, *args, **kwargs)
    
    def question(self, hint = False) -> str:
        blank = "_" * len(self.solution)
        if hint:
            blank[0] = self.solution[0]
        q = self.content.replace("$BLANK", blank)

        return q
    
    def mark(self, answer: str, engine = None):
        return int(answer.lower() == self.solution.lower()), "", []


class SentenceMakingQuestion(Question):
    def __init__(self, content, solution, rela_nodes, analysis = None, *args, **kwargs):
        super().__init__(content, solution, rela_nodes, analysis, *args, **kwargs)
    
    def question(self, hint = False):
        return self.content

    def __feedback(self, answer: str) -> List[Dict[str, str]]:
        # TODO
        pass
    
    def mark(self, answer, engine):
        # TODO
        pass

class ListeningQuestion(Question):
    def __init__(self, content, solution, rela_nodes, analysis = None, *args, **kwargs):
        super().__init__(content, solution, rela_nodes, analysis, *args, **kwargs)
    
    def question(self, hint = False):
        return "Listen to the sentence and write down what you hear."
    
    def __editing_dist(self, answer: str) -> int:
        sol_len = len(self.solution)
        ans_len = len(answer)
        dp = [[0] * (ans_len + 1) for _ in range(sol_len + 1)]
        ops = [[-1] * (ans_len + 1) for _ in range(sol_len + 1)]
        for i in range(1, sol_len + 1):
            dp[i][0] = i
            ops[i][0] = 1
        for j in range(1, ans_len + 1):
            dp[0][j] = i
            ops[0][j] = 2
        for i in range(1, sol_len + 1):
            for j in range(1, ans_len + 1):
                if self.solution[i - 1] == answer[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    ops[i][j], dp[i][j] = min(
                        enumerate([1 + dp[i - 1][j - 1], 1 + dp[i - 1][j], 1 + dp[i][j - 1]]),
                        key=lambda x: x[1]
                    )
                    # -1 : do nothing
                    # 0 : sub
                    # 1 : add +
                    # 2 : del -
        i, j = sol_len, ans_len
        analysis = answer
        while i > 0 or j > 0:
            if ops[i][j] == -1:
                i, j = i - 1, j - 1
                continue
            if ops[i][j] == 0:
                # sub : a[j - 1] -> s[i - 1]
                analysis = analysis[ : j - 1] + f"<{answer[j - 1]}:{self.solution[i - 1]}>" + analysis[j :]
                i, j = i - 1, j - 1
            elif ops[i][j] == 1:
                # add : a[ : j] + s[i - 1]
                analysis = analysis[ : j] + f"[{self.solution[i - 1]}]" + analysis[j :]
                i, j = i - 1, j
            elif ops[i][j] == 2:
                # del : a[ : j] -> a[ : j - 1]
                analysis = analysis[ : j - 1] + f"({answer[j - 1]})" + analysis[j :]
                i, j = i, j - 1
        self.analysis = analysis
        
        return dp[-1][-1]
    
    def __feedback(self, answer: str, engine: LLMEngine) -> List[Dict[str, str]]:
        sys_prompt, few_shots = all_prompts["ListeningQuestion"]["sys_prompt"], all_prompts["ListeningQuestion"]["few_shots"]
        prompt = (
            f"original: {self.solution}\n"
            f"student: {answer}"
        )
        prompt = f"```txt\n{prompt}\n```"
        responses = engine.generate(
            prompt=prompt,
            sys_prompt=sys_prompt,
            few_shots=few_shots
        )
        responses = Formatter.catch_json(responses)
        feedbacks = []
        for _, feedback in responses.items():
            feedbacks.append(feedback)
        
        return feedbacks
        
    
    def mark(self, answer, engine) -> Tuple[int, str, List[Dict[str, str]]]:
        score = 1 - self.__editing_dist(answer) / max(len(self.solution), len(answer))
        feedbacks = self.__feedback(answer, engine)

        return score, self.analysis, feedbacks


class Quiz:
    def __init__(self):
        self.problemset: Dict[str, List[Question]] = defaultdict(list)
    
    def add(self, q: Question):
        self.problemset[type(q).__name__].append(q)
    
    def shell(self):
        pass
    
    def save(self, path: str | Path) -> bool:
        # TODO
        pass
    
    @staticmethod
    def load(path: str | Path) -> 'Quiz':
        # TODO
        pass