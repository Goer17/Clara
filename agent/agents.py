import os
from openai import Client
from typing_extensions import List, Dict
from agent.memory import Memory

class Prompt:
    def __init__(self, template: str, parameters: dict):
        self.template = template
        self.parameters = parameters
        self.__value = None

    @property
    def value(self):
        if self.__value is not None:
            return self.__value
        result = self.template
        for key, content in self.parameters.items():
            result = result.replace(f"${key}", content)
        self.__value = result
        
        return result


class Agent:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = Client(
            api_key=api_key,
            base_url=base_url
        )
        
    def generate(self, prompt: Prompt, sys_prompt: Prompt | None = None):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": sys_prompt.value if sys_prompt is not None else ""
                },
                {
                    "role": "user",
                    "content": prompt.value
                }
            ]
        ).choices[0].message.content
        return response


class Retriever(Agent):
    def __init__(self, model, api_key, base_url):
        super().__init__(model, api_key, base_url)
        self.memo = Memory()
    
    def __to_m_item(self, text: str) -> Dict:
        """Encode the plain text to well-structured memory item

        Args:
            text (str): the plain text

        Returns:
            Dict: Encoded memory item with dict format
        """
        pass        

    def __add_m_item(self, m_item: Dict) -> str:
        """Add `m_item` to memory module

        Args:
            `m_item` (Dict): `m_item` is going to be added to memory module

        Returns:
            str: memory item ID of `m_item`, empty if failed
        """
        pass
    
    def __query(self, q_text: str, n_resluts: int = 3) -> List[Dict]:
        """Query the most `n_resluts` relative item of `q_text`

        Args:
            q_text (str): Query text
            n_resluts (int, optional): number of results. Defaults to 3.

        Returns:
            List[Dict]: The list of memory item
        """
        pass
    
    def __create_rela(self, m1_id: str, m2_id: str) -> Dict:
        m1_item = self.memo.lookup(m_id=m1_id)
        m2_item = self.memo.lookup(m_id=m2_id)
        m1_con = f"Abstract: {m1_item['abstract']}\nContent: {m1_item['content']}"
        m2_con = f"Abstract: {m2_item['abstract']}\nContent: {m2_item['content']}"
        
        rela = {}
        
        self.memo.add_rela(m1_id=m1_id, m2_id=m2_id, rela=rela)
    
    def remember(self, text_or_m_item: str | Dict):
        if isinstance(text_or_m_item, str):
            m_item = self.__to_m_item(text_or_m_item)
        else:
            m_item = text_or_m_item
        m_id = self.__add_m_item(m_item)
        relevant_items = self.__query(m_item["abstract"])
        for item in relevant_items:
            self.__create_rela(m_id, item["m_id"])