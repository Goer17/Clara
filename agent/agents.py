import yaml, json, re
from openai import Client
from typing_extensions import List, Dict, Tuple
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

    def __add_m_item(self, m_item: Dict) -> str:
        """Add `m_item` to memory module

        Args:
            `m_item` (Dict): `m_item` is going to be added to memory module

        Returns:
            str: memory item ID of `m_item`, empty if failed
        """
        return self.memo.add_item(m_item)
    
    def __merge_item(self, m_id, m_item_dupe: Dict) -> bool:
        """Merge memory item (m_id) with `m_item_merge`

        Args:
            m_id (_type_): memory item ID
            m_item_merge (Dict): merging memory item

        Returns:
            bool: if the merge operation is successful
        """
        # m_item = self.memo.lookup(m_id=m_id)
        
        # TODO Merge the content
        update_item = {
            "content": m_item_dupe["content"]
        }
        
        return self.memo.update(m_id=m_id, update_item=update_item)
    
    def __query(self, q_text: str, n_resluts: int) -> List[Tuple]:
        """Query the most `n_resluts` relative item of `q_text`

        Args:
            q_text (str): Query text
            n_resluts (int, optional): number of results. Defaults to 3.

        Returns:
            List[Dict]: The list of memory item
        """
        return self.memo.query(q_text=q_text, n_results=n_resluts)
    
    def __generate_rela(self, prompt_name: str, m1: str, m2: str) -> Dict | None:
        rela_prompts = self.all_prompts[prompt_name]
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
        
    
    def __create_rela(self, m1_id: str, m2_id: str) -> bool:
        m1_item = self.memo.lookup(m_id=m1_id)
        m2_item = self.memo.lookup(m_id=m2_id)
        label1, label2 = m1_item["label"], m2_item["label"]
        label_cate = {
            "word": 0,
            "unfamiliar_word": 1,
            "grammar": 2,
            "image": 3,
            "passage": 4,
            "mistake": 5
        }
        prompt_name = None
        if label_cate[label1] in [0, 1] and label_cate[label2] in [0, 1]:
            prompt_name = "create_rela_word2word"
        else:
            pass
            # prompt_name = "create_rela_others"
       
        if prompt_name is None:
            return False
        m1_con = f"label: {m1_item['label']} abstract: {m1_item['abstract']}\ncontent:\n{m1_item['content']}\n"
        m2_con = f"label: {m2_item['label']} abstract: {m2_item['abstract']}\ncontent:\n{m2_item['content']}\n"
        rela = self.__generate_rela(prompt_name=prompt_name, m1=m1_con, m2=m2_con)
        if rela is None:
            return False
        rela["label"] = rela["label"].lower()
        if re.match(pattern=r"^[a-z]+$", string=rela["label"]):
            self.memo.add_rela(m1_id=m1_id, m2_id=m2_id, rela=rela)
            return True
        return False
    
    def remember(self, m_item: Dict, rela_number: int = 3) -> bool:
        for key in ["label", "abstract", "content"]:
            if key not in m_item:
                # TODO logging
                return False
        if m_item["label"] in ["word", "unfamiliar_word"]:
            m_item["abstract"] = m_item["abstract"].lower()
        relevant_items = self.__query(m_item["abstract"], n_resluts=rela_number)
        # list[tuple: (m_id, abstract)] 
        
        if len(relevant_items) > 0 and relevant_items[0][1].lower() == m_item["abstract"].lower():
            # duplicate memory
            return self.__merge_item(relevant_items[0][0], m_item)
        m_id = self.__add_m_item(m_item) 
        for item in relevant_items:
            # item: (m_id, abstract)
            if m_id != item[0]:
                self.__create_rela(m_id, item[0])
        
        return True