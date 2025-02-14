import yaml

from pathlib import Path
from typing import (
    List, Dict
)

from image_downloader.layer.download import GoogleURLCrawler
from image_downloader.layer.llm import Critic
from image_downloader.pipeline import Pipeline

from utils.string import Formatter

class WebCrawler:
    def __init__(self):
        from utils.general import openai_api_key, base_url
        with open(Path("config") / "prompts" / "webcrawler.yml") as f:
            cfg = yaml.safe_load(f)
            sys_prompt = cfg["sys_prompt"]
        self.pipeline = Pipeline(
            crawlers=[GoogleURLCrawler()],
            layers=[
                Critic(
                    base_url=base_url,
                    api_key=openai_api_key,
                    model="gpt-4o",
                    sys_prompt=sys_prompt,
                    filter_func=lambda content: "NOTPASS" not in content
                )
            ]
        )
    
    def fetch_image_text_pairs(self, query: str) -> List[Dict[str, str]]:
        urls = self.pipeline(
            query=query,
            text=query,
            max_n=10
        )
        results = []
        for url_info in urls:
            try:
                url, content = url_info["url"], url_info["content"]
                if "NOTPASS" in content:
                    continue
                data = Formatter.catch_json(content)
                description = data["description"]
                results.append(
                    {
                        "url": url,
                        "description": description
                    }
                )
            except Exception as e:
                pass
        return results