import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from openai import (
    Client, AsyncClient
)
from typing_extensions import (
    List, Dict
)
from .logger import logger

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
        self.async_client = AsyncClient(
            api_key=api_key,
            base_url=base_url
        )
        
    def __pack_message(self, prompt: str | Prompt | None = None, sys_prompt: str | Prompt | None = None, few_shots: List[Dict] = []) -> List[Dict]:
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
        
        return messages
        
    def generate(self, prompt: str | Prompt | None = None, sys_prompt: str | Prompt | None = None, few_shots: List[Dict] = [],
                 *args, **kwargs) -> str:
        messages = self.__pack_message(
            prompt=prompt,
            sys_prompt=sys_prompt,
            few_shots=few_shots
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            *args, **kwargs
        ).choices[0].message.content
        logger.info(f"LLMEngine.generate() [{self.model}] : {response}")
        return response
    
    def chat(self, messages: List[Dict], sys_prompt: str | Prompt | None = "", *args, **kwargs) -> str:
        sys_prompt = sys_prompt.value() if isinstance(sys_prompt, Prompt) else sys_prompt
        messages = [{"role": "system", "content": sys_prompt}] + messages
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            *args, **kwargs
        ).choices[0].message.content
        logger.info(f"LLMEngine.chat() [{self.model}] : {response}")
        return response
    
    async def async_generate(self, prompt: str | Prompt | None = None, sys_prompt: str | Prompt | None = None, few_shots: List[Dict] = [],
                             *args, **kwargs) -> str:
        messages = self.__pack_message(
            prompt=prompt,
            sys_prompt=sys_prompt,
            few_shots=few_shots
        )
        response = (await self.async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            *args, **kwargs
        )).choices[0].message.content
        logger.info(f"LLMEngine.async_generate() [{self.model}] : {response}")
        return response

    def close(self):
        self.client.close()
        self.async_client.close()

from playsound import playsound
import hashlib

class AMEngine:
    cache_path = Path("cache") / "audio"

    def __init__(self, model: str, api_kay: str, base_url):
        self.client = Client(
            api_key=api_kay,
            base_url=base_url
        )
        self.model = model

    def generate(self, text: str, voice: str) -> str:
        tag = f"[{voice}] : {text}".encode('utf-8')
        name = f"audio[{hashlib.md5(tag).hexdigest()}]"
        filename = f"{name}.mp3"
        if not os.path.exists(AMEngine.cache_path):
            os.makedirs(path=AMEngine.cache_path)
        path = self.cache_path / filename
        if os.path.exists(path):
            return name
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text
        )
        response.write_to_file(path)

        return name
        
    @staticmethod
    def play(name: str):
        path = AMEngine.cache_path / f"{name}.mp3"
        try:
            playsound(path)
        except Exception as e:
            logger.error(f"AMEgine : An error occurred when play the mp3 file: {path}")

load_dotenv(find_dotenv())

openai_api_key = os.environ["OPENAI_API_KEY"]
base_url = os.environ["BASE_URL"]

gpt_4o = LLMEngine(
    model="gpt-4o",
    api_key=openai_api_key,
    base_url=base_url
)

tts = AMEngine(
    model="tts-1",
    api_kay=openai_api_key,
    base_url=base_url
)

tts_hd = AMEngine(
    model="tts-1-hd",
    api_kay=openai_api_key,
    base_url=base_url
)