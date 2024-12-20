import os
from dotenv import load_dotenv, find_dotenv
from openai import Client
from typing_extensions import (
    List, Dict
)

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

class LLMEngine:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = Client(
            api_key=api_key,
            base_url=base_url
        )
        
    def generate(self, prompt: str | Prompt | None = None, sys_prompt: str | Prompt | None = None, few_shots: List[Dict] | None = None,
                 *args, **kwargs):
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
            messages=messages,
            *args, **kwargs
        ).choices[0].message.content
        return response

load_dotenv(find_dotenv())

openai_api_key = os.environ["OPENAI_API_KEY"]
base_url = os.environ["BASE_URL"]

gpt_4o_engine = LLMEngine(
    model="gpt-4o",
    api_key=openai_api_key,
    base_url=base_url
)