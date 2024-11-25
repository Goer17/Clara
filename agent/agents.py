import yaml, json, re
from openai import Client
from typing_extensions import List, Dict
from agent.memory import Memory
from pathlib import Path
from logging import getLogger

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
        
    def generate(self, prompt: str | Prompt | None = None, sys_prompt: str | Prompt | None = None, few_shots: List[Dict] | None = None):
        messages = []
        if sys_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": sys_prompt.value if isinstance(sys_prompt, Prompt) else sys_prompt
                }
            )
        for shot in few_shots:
            messages.append(
                {
                    "role": shot["role"],
                    "content": shot["content"]
                }
            )
        if prompt:
            messages.append(
                {
                    "role": "user",
                    "content": prompt.value if isinstance(prompt, Prompt) else prompt
                }
            )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        ).choices[0].message.content
        return response



class Retriever(Agent):
    def __init__(self, model, api_key, base_url):
        super().__init__(model, api_key, base_url)
        self.memo = Memory()
        retriever_path = Path("agent") / "prompts" / "retriever.yml"
        with open(retriever_path) as f:
            self.all_prompts = yaml.safe_load(f)
    
    def __to_m_item(self, text: str) -> Dict:
        """Encode the plain text to well-structured memory item

        Args:
            text (str): the plain text

        Returns:
            Dict: encoded memory item with dict format
        """
        pass
    
    def __to_m_text(self, m_item: Dict) -> str:
        """Decode the memory item dictionary to plain text

        Args:
            m_item (Dict): the memory item

        Returns:
            str: decoded plain text
        """

    def __add_m_item(self, m_item: Dict) -> str:
        """Add `m_item` to memory module

        Args:
            `m_item` (Dict): `m_item` is going to be added to memory module

        Returns:
            str: memory item ID of `m_item`, empty if failed
        """
        return self.memo.add_item(m_item)
    
    def __query(self, q_text: str, n_resluts) -> List[Dict]:
        """Query the most `n_resluts` relative item of `q_text`

        Args:
            q_text (str): Query text
            n_resluts (int, optional): number of results. Defaults to 3.

        Returns:
            List[Dict]: The list of memory item
        """
        return self.memo.query(q_text=q_text, n_results=n_resluts)
    
    def __generate_rela(self, m1: str, m2: str) -> Dict | None:
        rela_prompts = self.all_prompts["create_rela"]
        prompt = Prompt(
            template=(
                "```txt\n"
                "$m1\n"
                "```\n\n"
                "```txt\n"
                "$m2\n"
                "```\n"
            ),
            parameters={
                "m1": m1,
                "m2": m2
            }
        )
        response = self.generate(
            prompt=prompt,
            sys_prompt=rela_prompts["sys_prompt"],
            few_shots=rela_prompts["few_shots"]
        )
        # TODO: Store the reasoning stage in Log
        json_block = re.search(pattern=r"```json\n(.*?)\n```", string=response, flags=re.S)
        if "NO_RELA" in response or not json_block:
            return None
        try:
            dict_response = json.loads(json_block.group(1))
            return dict_response
        except Exception as e:
            # TODO
            pass
        return None
        
    
    def __create_rela(self, m1_id: str, m2_id: str) -> Dict:
        m1_item = self.memo.lookup(m_id=m1_id)
        m2_item = self.memo.lookup(m_id=m2_id)
        m1_con = f"label: {m1_item['label']}\nabstract: {m1_item['abstract']}\ncontent:\n{m1_item['content']}\n"
        m2_con = f"label: {m2_item['label']}\nabstract: {m2_item['abstract']}\ncontent:\n{m2_item['content']}\n"
        
        rela = self.__generate_rela(m1=m1_con, m2=m2_con)
        if rela is not None:
            self.memo.add_rela(m1_id=m1_id, m2_id=m2_id, rela=rela)
    
    def remember(self, text_or_m_item: str | Dict, rela_number: int = 3):
        if isinstance(text_or_m_item, str):
            m_item = self.__to_m_item(text_or_m_item)
        else:
            m_item = text_or_m_item
        m_id = self.__add_m_item(m_item)
        relevant_items = self.__query(m_item["abstract"], n_resluts=rela_number)
        for item in relevant_items:
            # item: (m_id, abstract)
            if m_id != item[0]:
                self.__create_rela(m_id, item[0])