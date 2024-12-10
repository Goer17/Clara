from abc import ABC, abstractmethod

from typing_extensions import (
    Dict, List
)

class Question(ABC):
    def __init__(self,
                 content: str,
                 solution: str,
                 rela_m_items: List[Dict],
                 *args, **kwargs
                 ):
        self.content = content
        self.solution = solution
        self.rela_m_items = rela_m_items
    
    @abstractmethod
    def show_que(self, *args, **kwargs) -> str:
        pass
    
    @abstractmethod
    def show_sol(self, *args, **kwargs) -> str:
        pass
    
    @abstractmethod
    def show_knowledge(self, *args, **kwargs) -> List[str]:
        pass
    
    @abstractmethod
    def mark(self,
             answer: str,
             *args, **kwargs
             ) -> float:
        """ Mark the student's answer
        Args:
            answer (str): student's answer

        Returns:
            int: the mark of this answer: 0 ~ 1
        """
        pass


class GapFillingQuestion(Question):
    """Gap-filling question
    - Focuses on gap-filling to assess vocabulary skills
    Eg:
        question: He was very $BLANK about his relationship with the actress
        answer: frank
    """
    def __init__(self, content, solution, rela_m_items, *args, **kwargs):
        super().__init__(content, solution, rela_m_items, *args, **kwargs)
        
    def show_que(self, *args, **kwargs) -> str:
        hint = self.solution[0] + (len(self.solution) - 1) * '_' if kwargs.get("hint", False) else len(self.solution) * "_"
        question = self.content.replace("$BLANK", hint)
        
        return question

    def show_sol(self, *args, **kwargs) -> str:
        return self.solution
    
    def show_knowledge(self, *args, **kwargs) -> List[str]:
        # TODO
        return self.rela_m_items
    
    def mark(self, answer, *args, **kwargs) -> float:
        if answer.lower() == self.solution.lower():
            return 1
        else:
            return 0
    