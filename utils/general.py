import os
import json
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from openai import (
    Client, AsyncClient
)
from typing_extensions import (
    List, Dict, Tuple
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
    
    def chat(self, messages: List[Dict], sys_prompt: str | Prompt | None = "", toolset: Tuple[List, Dict] = ([], {}), *args, **kwargs) -> str:
        sys_prompt = sys_prompt.value() if isinstance(sys_prompt, Prompt) else sys_prompt
        tools, functions = toolset
        prefix = [{"role": "system", "content": sys_prompt}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=prefix + messages,
            tools=tools,
            *args, **kwargs
        ).choices[0].message
        while response.tool_calls:
            tool_calls = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "arguments": tool_call.function.arguments,
                        "name": tool_call.function.name
                    }
                } for tool_call in response.tool_calls
            ]
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": tool_calls
                }
            )
            for tool_call in response.tool_calls:
                call_id = tool_call.id
                func = tool_call.function
                try:
                    logger.info(f"LLMEngine.chat() [{self.model}] : function call : {func.name}, parameters : {func.arguments}")
                    result = functions[func.name](**json.loads(func.arguments))
                    logger.info(f"Result : {result}")
                except Exception as e:
                    result = str(e)
                    logger.error(f"LLMEngine.chat() [{self.model}] : one error occurred while attempting to call function {func}", e)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": str(result)
                    }
                )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=prefix + messages,
                tools=tools,
                *args, **kwargs
            ).choices[0].message
        messages.append(
            {
                "role": "assistant",
                "content": response.content
            }
        )
        
        logger.info(f"LLMEngine.chat() [{self.model}] : {response.content}")
        return response.content
    
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
        self.async_client = AsyncClient(
            api_key=api_kay,
            base_url=base_url
        )
        self.model = model

    def generate(self, text: str, voice: str) -> str:
        logger.info(f"text: {text}, voice: {voice}")
        tag = f"[{voice}] : {text}".encode('utf-8')
        name = f"audio[{hashlib.md5(tag).hexdigest()}]"
        filename = f"{name}.mp3"
        if not os.path.exists(AMEngine.cache_path):
            os.makedirs(AMEngine.cache_path)
        path = self.cache_path / filename
        if os.path.exists(path):
            return name
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text
        )
        response.write_to_file(path)
        logger.info(f"AMEngine.generate() : an audio file was successfully generated: {str(path)}")
        
        return name

    async def async_generate(self, text: str, voice: str, timeout: int = None) -> str:
        logger.info(f"text: {text}, voice: {voice}")
        tag = f"[{voice}] : {text}".encode('utf-8')
        name = f"audio[{hashlib.md5(tag).hexdigest()}]"
        filename = f"{name}.mp3"
        if not os.path.exists(AMEngine.cache_path):
            os.makedirs(AMEngine.cache_path)
        path = self.cache_path / filename
        if os.path.exists(path):
            return name
        response = await self.async_client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            timeout=timeout
        )
        response.write_to_file(path)
        logger.info(f"AMEngine.async_generate() : an audio file was successfully generated: {str(path)}")
        
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
base_url = os.environ["OPENAI_BASE_URL"]

deepseek_api_kay = os.environ["DEEPSEEK_API_KEY"]
deepseek_base_url = os.environ["DEEPSEEK_BASE_URL"]

gpt_3_5 = LLMEngine(
    model="gpt-3.5-turbo",
    api_key=openai_api_key,
    base_url=base_url
)

gpt_4o = LLMEngine(
    model="gpt-4o",
    api_key=openai_api_key,
    base_url=base_url
)

o1_mini = LLMEngine(
    model="o1-mini",
    api_key=openai_api_key,
    base_url=base_url
)

ds_chat = LLMEngine(
    model="deepseek-chat",
    api_key=deepseek_api_kay,
    base_url=deepseek_base_url
)

ds_reasoner = LLMEngine(
    model="deepseek-reasoner",
    api_key=deepseek_api_kay,
    base_url=deepseek_base_url
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

tts_hd_1106 = AMEngine(
    model="tts-1-hd-1106",
    api_kay=openai_api_key,
    base_url=base_url
)

engine_list = {
    "gpt-3.5-turbo": gpt_3_5,
    "gpt-4o": gpt_4o,
    "deepseek-v3": ds_chat,
    "deepseek-r1": ds_reasoner
}